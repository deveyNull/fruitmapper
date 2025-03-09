from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy import func

from fastapi import UploadFile, HTTPException
import csv
from datetime import datetime
from typing import List, Optional, Dict
from io import StringIO
import json

from app.models import User, FruitType, Fruit, Recipe, Group, SavedFilter, Service, Owner, OwnerIP, OwnerDomain, fruit_recipe
from passlib.hash import bcrypt
from app import schemas
from .schemas import ServiceList, ServiceResponse, OwnerList, OwnerResponse
import re


# User operations
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate) -> User:
    if get_user_by_username(db, user.username):
        raise HTTPException(400, "Username already registered")
    if get_user_by_email(db, user.email):
        raise HTTPException(400, "Email already registered")
    
    hashed_password = bcrypt.hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        is_admin=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> User:
    db_user = get_user(db, user_id)
    if not db_user:
        raise HTTPException(404, "User not found")
    
    if user_update.email:
        existing = get_user_by_email(db, user_update.email)
        if existing and existing.id != user_id:
            raise HTTPException(400, "Email already registered")
        db_user.email = user_update.email
    
    if user_update.password:
        db_user.password_hash = bcrypt.hash(user_update.password)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user or not bcrypt.verify(password, user.password_hash):
        return None
    return user

# FruitType operations
def get_fruit_type(db: Session, fruit_type_id: int) -> Optional[FruitType]:
    return db.query(FruitType).filter(FruitType.id == fruit_type_id).first()

def get_fruit_types(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None
) -> schemas.FruitTypeList:
    query = db.query(
        FruitType,
        func.count(Fruit.id).label('fruit_count')
    ).outerjoin(Fruit)
    
    if search:
        search = f"%{search}%"
        query = query.filter(FruitType.name.ilike(search) | 
                           FruitType.description.ilike(search))
    
    # Group by and order by fruit count
    query = query.group_by(FruitType.id).order_by(func.count(Fruit.id).desc())
    
    total = db.query(FruitType).count()
    items = query.offset(skip).limit(limit).all()
    
    # Convert to response objects with fruit count
    fruit_types = []
    for ft, count in items:
        ft_dict = schemas.FruitTypeResponse.model_validate(ft)
        ft_dict.fruit_count = count
        fruit_types.append(ft_dict)

    return schemas.FruitTypeList(
        items=fruit_types,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

def create_fruit_type(db: Session, fruit_type: schemas.FruitTypeCreate) -> FruitType:
    if db.query(FruitType).filter(FruitType.name == fruit_type.name).first():
        raise HTTPException(400, "Fruit type name already exists")
    
    db_fruit_type = FruitType(**fruit_type.dict())
    db.add(db_fruit_type)
    db.commit()
    db.refresh(db_fruit_type)
    return db_fruit_type

def update_fruit_type(
    db: Session,
    fruit_type_id: int,
    fruit_type_update: schemas.FruitTypeUpdate
) -> FruitType:
    db_fruit_type = get_fruit_type(db, fruit_type_id)
    if not db_fruit_type:
        raise HTTPException(404, "Fruit type not found")
    
    for field, value in fruit_type_update.dict(exclude_unset=True).items():
        setattr(db_fruit_type, field, value)
    
    db.commit()
    db.refresh(db_fruit_type)
    return db_fruit_type

def delete_fruit_type(db: Session, fruit_type_id: int) -> bool:
    db_fruit_type = get_fruit_type(db, fruit_type_id)
    if db_fruit_type:
        db.delete(db_fruit_type)
        db.commit()
        return True
    return False

# Fruit operations
def get_fruit(db: Session, fruit_id: int) -> Optional[Fruit]:
    return db.query(Fruit).filter(Fruit.id == fruit_id).first()

def get_fruits(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    fruit_type_id: Optional[int] = None,
    country: Optional[str] = None,
    search: Optional[str] = None
) -> schemas.FruitList:
    # First create a subquery to count services
    service_count = db.query(
        Service.fruit_id,
        func.count(Service.id).label('service_count')
    ).group_by(Service.fruit_id).subquery()
    
    # Create the base query for fruits
    query = db.query(Fruit)
    
    # Apply eager loading
    query = query.options(
        joinedload(Fruit.fruit_type),
        joinedload(Fruit.services)
    )
    
    # Apply filters
    if fruit_type_id:
        query = query.filter(Fruit.fruit_type_id == fruit_type_id)
    
    if country:
        query = query.filter(Fruit.country_of_origin == country)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Fruit.name.ilike(search_term),
            )
        )
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    query = query.order_by(Fruit.name).offset(skip).limit(limit)
    
    # Execute the query to get fruits
    fruits = query.all()
    
    # Now retrieve service counts for these specific fruits
    fruit_ids = [fruit.id for fruit in fruits]
    
    # Get service counts in a separate query
    counts = {}
    if fruit_ids:
        count_results = db.query(
            Service.fruit_id,
            func.count(Service.id).label('count')
        ).filter(
            Service.fruit_id.in_(fruit_ids)
        ).group_by(Service.fruit_id).all()
        
        counts = {fruit_id: count for fruit_id, count in count_results}
    
    # Create response objects with service count
    fruit_responses = []
    for fruit in fruits:
        fruit_response = schemas.FruitResponse.model_validate(fruit)
        # Add service_count as an attribute (assuming you've added this field to FruitResponse)
        setattr(fruit_response, 'service_count', counts.get(fruit.id, 0))
        fruit_responses.append(fruit_response)
    
    return schemas.FruitList(
        items=fruit_responses,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

def get_fruits_by_type(
    db: Session,
    fruit_type_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Fruit]:
    return (db.query(Fruit)
            .filter(Fruit.fruit_type_id == fruit_type_id)
            .offset(skip)
            .limit(limit)
            .all())

def create_fruit(db: Session, fruit: schemas.FruitCreate) -> Fruit:
    # Validate fruit type exists
    if not get_fruit_type(db, fruit.fruit_type_id):
        raise HTTPException(400, "Fruit type not found")
    
    # Create the fruit
    db_fruit = Fruit(**fruit.dict())
    db.add(db_fruit)
    db.commit()
    db.refresh(db_fruit)
    
    # Match existing services if match_type and match_regex are provided
    if fruit.match_type and fruit.match_regex:
        try:
            pattern = re.compile(fruit.match_regex)
            print(pattern)
            # Query services based on match_type
            if fruit.match_type == 'banner':
                matching_services = db.query(Service).filter(
                    Service.banner_data.isnot(None)
                ).all()
                for service in matching_services:
                    print(service.banner_data)
                    if service.banner_data and pattern.search(service.banner_data):
                        service.fruit_id = db_fruit.id
                        service.fruit_type_id = db_fruit.fruit_type_id
            
            elif fruit.match_type == 'html_data':
                matching_services = db.query(Service).filter(
                    Service.html.isnot(None)
                ).all()
                for service in matching_services:
                    if service.html_data and pattern.search(service.html_data):
                        service.fruit_id = db_fruit.id
                        service.fruit_type_id = db_fruit.fruit_type_id
            
            # Add more match_types as needed
            
            db.commit()
        except re.error as e:
            raise HTTPException(400, f"Invalid regex pattern: {str(e)}")
    
    return db_fruit

def update_fruit(
    db: Session,
    fruit_id: int,
    fruit_update: schemas.FruitUpdate
) -> Fruit:
    db_fruit = get_fruit(db, fruit_id)
    if not db_fruit:
        raise HTTPException(404, "Fruit not found")
    
    update_data = fruit_update.dict(exclude_unset=True)
    if 'fruit_type_id' in update_data:
        if not get_fruit_type(db, update_data['fruit_type_id']):
            raise HTTPException(400, "Fruit type not found")
    
    # Update fruit fields
    for field, value in update_data.items():
        setattr(db_fruit, field, value)
    
    # Re-match services if match_type or match_regex was updated
    if ('match_type' in update_data or 'match_regex' in update_data) and db_fruit.match_type and db_fruit.match_regex:
        try:
            # Clear existing fruit matches
            db.query(Service).filter(Service.fruit_id == fruit_id).update(
                {"fruit_id": None, "fruit_type_id": None}
            )
            
            pattern = re.compile(db_fruit.match_regex)
            # Query services based on match_type
            if db_fruit.match_type == 'banner':
                matching_services = db.query(Service).filter(
                    Service.banner_data.isnot(None)
                ).all()
                for service in matching_services:
                    if service.banner_data and pattern.search(service.banner_data):
                        service.fruit_id = db_fruit.id
                        service.fruit_type_id = db_fruit.fruit_type_id
            
            elif db_fruit.match_type == 'domain':
                matching_services = db.query(Service).filter(
                    Service.domain.isnot(None)
                ).all()
                for service in matching_services:
                    if service.domain and pattern.search(service.domain):
                        service.fruit_id = db_fruit.id
                        service.fruit_type_id = db_fruit.fruit_type_id
            
            # Add more match_types as needed
            
        except re.error as e:
            raise HTTPException(400, f"Invalid regex pattern: {str(e)}")
    
    db.commit()
    db.refresh(db_fruit)
    return db_fruit

def delete_fruit(db: Session, fruit_id: int) -> bool:
    db_fruit = get_fruit(db, fruit_id)
    if db_fruit:
        db.delete(db_fruit)
        db.commit()
        return True
    return False

# Group operations
def get_group(db: Session, group_id: int) -> Optional[Group]:
    return db.query(Group).filter(Group.id == group_id).first()

def get_groups(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None
) -> schemas.GroupList:
    query = db.query(Group)
    if user_id:
        query = query.filter(Group.members.any(id=user_id))
    
    total = query.count()
    groups = query.offset(skip).limit(limit).all()
    pages = (total + limit - 1) // limit

    return schemas.GroupList(
        items=[schemas.GroupResponse.model_validate(g) for g in groups],
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=pages
    )

def create_group(db: Session, group: schemas.GroupCreate, creator_id: int) -> Group:
    creator = get_user(db, creator_id)
    if not creator:
        raise HTTPException(404, "Creator user not found")
    
    db_group = Group(**group.dict())
    db_group.members.append(creator)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

def update_group(
    db: Session,
    group_id: int,
    group_update: schemas.GroupUpdate
) -> Group:
    db_group = get_group(db, group_id)
    if not db_group:
        raise HTTPException(404, "Group not found")
    
    for field, value in group_update.dict(exclude_unset=True).items():
        setattr(db_group, field, value)
    
    db.commit()
    db.refresh(db_group)
    return db_group


def manage_group_members(
    db: Session,
    group_id: int,
    user_id: int,
    add: bool = True
) -> Group:
    db_group = get_group(db, group_id)
    db_user = get_user(db, user_id)
    
    if not db_group or not db_user:
        raise HTTPException(404, "Group or user not found")
    
    if add and db_user not in db_group.members:
        db_group.members.append(db_user)
    elif not add and db_user in db_group.members:
        db_group.members.remove(db_user)
    
    db.commit()
    db.refresh(db_group)
    return db_group

# SavedFilter operations
def get_filter(db: Session, filter_id: int) -> Optional[SavedFilter]:
    return db.query(SavedFilter).filter(SavedFilter.id == filter_id).first()

def get_filters(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    group_id: Optional[int] = None
) -> schemas.FilterList:
    query = db.query(SavedFilter)
    if user_id:
        query = query.filter(
            or_(
                SavedFilter.user_id == user_id,
                SavedFilter.group_id.in_(
                    db.query(Group.id)
                    .filter(Group.members.any(id=user_id))
                )
            )
        )
    if group_id:
        query = query.filter(SavedFilter.group_id == group_id)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return schemas.FilterList(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )

def create_filter(
    db: Session,
    filter_create: schemas.FilterCreate,
    user_id: int
) -> SavedFilter:
    if filter_create.group_id:
        group = get_group(db, filter_create.group_id)
        if not group or not any(m.id == user_id for m in group.members):
            raise HTTPException(400, "User not in specified group")
    
    db_filter = SavedFilter(
        **filter_create.dict(),
        user_id=user_id,
        filter_criteria=json.dumps(filter_create.filter_criteria),
        visible_columns=json.dumps(filter_create.visible_columns)
    )
    db.add(db_filter)
    db.commit()
    db.refresh(db_filter)
    return db_filter

def update_filter(
    db: Session,
    filter_id: int,
    filter_update: schemas.FilterUpdate,
    user_id: int
) -> SavedFilter:
    db_filter = get_filter(db, filter_id)
    if not db_filter:
        raise HTTPException(404, "Filter not found")
    
    if db_filter.user_id != user_id:
        raise HTTPException(403, "Not authorized to update this filter")
    
    update_data = filter_update.dict(exclude_unset=True)
    if 'group_id' in update_data:
        group = get_group(db, update_data['group_id'])
        if not group or not any(m.id == user_id for m in group.members):
            raise HTTPException(400, "User not in specified group")
    
    if 'filter_criteria' in update_data:
        update_data['filter_criteria'] = json.dumps(update_data['filter_criteria'])
    if 'visible_columns' in update_data:
        update_data['visible_columns'] = json.dumps(update_data['visible_columns'])
    
    for field, value in update_data.items():
        setattr(db_filter, field, value)
    
    db_filter.modified_at = datetime.utcnow()
    db.commit()
    db.refresh(db_filter)
    return db_filter

def get_recipe(db: Session, recipe_id: int) -> Optional[Recipe]:
    return db.query(Recipe).filter(Recipe.id == recipe_id).first()

def get_recipes(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    fruit_id: Optional[int] = None,  # Changed from fruit_type_id to fruit_id
    max_time: Optional[int] = None
) -> schemas.RecipeList:
    """
    Get recipes with optional filtering and search, with optimized service counting.
    """
    # Create base query
    query = db.query(Recipe)
    
    # Apply eager loading for relationships
    query = query.options(
        joinedload(Recipe.fruits),  # Eager load fruits
        joinedload(Recipe.fruits).joinedload(Fruit.fruit_type)  # Also load fruit types
    )
    
    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Recipe.name.ilike(search_filter),
                Recipe.description.ilike(search_filter)
            )
        )
    
    if fruit_id:
        # Changed to filter by fruit instead of fruit type
        query = query.filter(Recipe.fruits.any(Fruit.id == fruit_id))
    
    if max_time:
        query = query.filter(Recipe.preparation_time <= max_time)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination and fetch recipes
    recipes = query.order_by(Recipe.name).offset(skip).limit(limit).all()
    
    # Get the recipe ids for service count calculation
    recipe_ids = [recipe.id for recipe in recipes]
    
    # Compute service counts in a separate efficient query using subqueries
    # This avoids the N+1 query problem
    service_counts = {}
    if recipe_ids:
        # First get the fruits associated with each recipe
        recipe_fruits = db.query(
            fruit_recipe.c.recipe_id,
            fruit_recipe.c.fruit_id
        ).filter(
            fruit_recipe.c.recipe_id.in_(recipe_ids)
        ).all()
        
        # Group fruits by recipe
        recipe_to_fruits = {}
        for recipe_id, fruit_id in recipe_fruits:
            if recipe_id not in recipe_to_fruits:
                recipe_to_fruits[recipe_id] = []
            recipe_to_fruits[recipe_id].append(fruit_id)
        
        # Get service counts for each fruit
        all_fruit_ids = [fruit_id for fruit_ids in recipe_to_fruits.values() for fruit_id in fruit_ids]
        if all_fruit_ids:
            fruit_service_counts = db.query(
                Service.fruit_id,
                func.count(Service.id).label('count')
            ).filter(
                Service.fruit_id.in_(all_fruit_ids)
            ).group_by(Service.fruit_id).all()
            
            # Map fruit IDs to service counts
            fruit_to_service_count = {fruit_id: count for fruit_id, count in fruit_service_counts}
            
            # Calculate total service count for each recipe
            for recipe_id, fruit_ids in recipe_to_fruits.items():
                service_counts[recipe_id] = sum(fruit_to_service_count.get(fruit_id, 0) for fruit_id in fruit_ids)
    
    # Create response objects with service count
    recipe_responses = []
    for recipe in recipes:
        recipe_response = schemas.RecipeResponse.model_validate(recipe)
        # Add service_count as an attribute
        setattr(recipe_response, 'service_count', service_counts.get(recipe.id, 0))
        recipe_responses.append(recipe_response)
    
    return schemas.RecipeList(
        items=recipe_responses,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

def get_recipe_count(db: Session) -> int:
    print("Querying recipe count...")  # Debug output
    count = db.query(Recipe).count()
    print(f"Found {count} recipes")  # Debug output
    return count

def get_fruit_type_count(db: Session) -> int:
    print("Querying fruit type count...")  # Debug output
    count = db.query(FruitType).count()
    print(f"Found {count} fruit types")  # Debug output
    return count

def get_filter_count(db: Session, username: str) -> int:
    print(f"Querying filter count for user {username}...")  # Debug output
    user = get_user_by_username(db, username)
    if not user:
        return 0
    count = db.query(SavedFilter).filter_by(user_id=user.id).count()
    print(f"Found {count} filters")  # Debug output
    return count

def get_recipes_by_fruit(
    db: Session,
    fruit_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Recipe]:
    """
    Get all recipes that use a specific fruit.
    Returns a list of recipes that include this fruit.
    """
    # Verify fruit exists
    fruit = get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(404, "Fruit not found")
    
    # Query recipes that include this fruit
    query = db.query(Recipe).filter(
        Recipe.fruits.any(Fruit.id == fruit_id)
    )
    
    recipes = query.offset(skip).limit(limit).all()
    return recipes

def create_recipe(db: Session, recipe: schemas.RecipeCreate) -> Recipe:
    """
    Create a new recipe with associated fruits.
    """
    # Verify fruits exist
    for fruit_id in recipe.fruit_ids:
        if not get_fruit(db, fruit_id):
            raise HTTPException(status_code=404, detail=f"Fruit with id {fruit_id} not found")
    
    # Create recipe without fruits first
    db_recipe = Recipe(
        name=recipe.name,
        description=recipe.description,
        instructions=recipe.instructions,
        preparation_time=recipe.preparation_time
    )
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    
    # Add fruits to recipe
    for fruit_id in recipe.fruit_ids:
        fruit = db.query(Fruit).get(fruit_id)
        db_recipe.fruits.append(fruit)
    
    db.commit()
    db.refresh(db_recipe)
    return db_recipe

def update_recipe(
    db: Session,
    recipe_id: int,
    recipe_update: schemas.RecipeUpdate
) -> Recipe:
    """
    Update an existing recipe and its fruit associations.
    """
    db_recipe = get_recipe(db, recipe_id)
    if not db_recipe:
        raise HTTPException(404, "Recipe not found")
    
    # Update recipe fields
    update_data = recipe_update.dict(exclude_unset=True)
    fruit_ids = update_data.pop("fruit_ids", None)
    
    for field, value in update_data.items():
        setattr(db_recipe, field, value)
    
    # Update fruit associations if provided
    if fruit_ids is not None:
        # Verify all fruits exist
        for fruit_id in fruit_ids:
            if not get_fruit(db, fruit_id):
                raise HTTPException(status_code=404, detail=f"Fruit with id {fruit_id} not found")
        
        # Clear existing associations and add new ones
        db_recipe.fruits = []
        for fruit_id in fruit_ids:
            fruit = db.query(Fruit).get(fruit_id)
            db_recipe.fruits.append(fruit)
    
    db.commit()
    db.refresh(db_recipe)
    return db_recipe

def delete_recipe(db: Session, recipe_id: int) -> bool:
    recipe = get_recipe(db, recipe_id)
    if recipe:
        db.delete(recipe)
        db.commit()
        return True
    return False

def add_fruit_to_recipe(
    db: Session,
    recipe_id: int,
    fruit_id: int
) -> Recipe:
    """
    Add a fruit to a recipe.
    """
    recipe = get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    
    fruit = get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(404, "Fruit not found")
    
    # Check if fruit is already associated with recipe
    if fruit in recipe.fruits:
        raise HTTPException(400, "Fruit already associated with recipe")
    
    recipe.fruits.append(fruit)
    db.commit()
    db.refresh(recipe)
    return recipe

def remove_fruit_from_recipe(
    db: Session,
    recipe_id: int,
    fruit_id: int
) -> Recipe:
    """
    Remove a fruit from a recipe.
    """
    recipe = get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    
    fruit = get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(404, "Fruit not found")
    
    # Check if fruit is associated with recipe
    if fruit not in recipe.fruits:
        raise HTTPException(400, "Fruit not associated with recipe")
    
    # Make sure we're not removing the last fruit
    if len(recipe.fruits) <= 1:
        raise HTTPException(400, "Cannot remove the last fruit from a recipe")
    
    recipe.fruits.remove(fruit)
    db.commit()
    db.refresh(recipe)
    return recipe

def get_recipe_service_count(db: Session, recipe_id: int) -> int:
    """
    Get the count of services associated with a recipe through its fruits.
    
    Args:
        db: Database session
        recipe_id: ID of the recipe
        
    Returns:
        int: Count of associated services
    """
    recipe = get_recipe(db, recipe_id)
    if not recipe:
        return 0
        
    service_count = 0
    for fruit in recipe.fruits:
        service_count += len(fruit.services)
        
    return service_count

def get_owner(db: Session, owner_id: int) -> Optional[Owner]:
    return db.query(Owner).filter(Owner.id == owner_id).first()

from sqlalchemy.orm import joinedload

def get_owners(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    direction: Optional[str] = "asc"
) -> OwnerList:
    query = db.query(Owner).options(
        joinedload(Owner.services),
        joinedload(Owner.owned_ips),
        joinedload(Owner.owned_domains)
    )
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Owner.name.ilike(search_filter),
                Owner.description.ilike(search_filter),
                Owner.contact_info.ilike(search_filter)
            )
        )
    
    # Handle sorting
    if sort:
        if sort == 'name':
            order_col = getattr(Owner, sort)
            if direction == "desc":
                order_col = order_col.desc()
            query = query.order_by(order_col)
    
    total = query.count()
    owners = query.offset(skip).limit(limit).all()
    
    return OwnerList(
        items=[OwnerResponse.model_validate(owner) for owner in owners],
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

# def get_owners(
#     db: Session,
#     skip: int = 0,
#     limit: int = 100,
#     search: Optional[str] = None,
#     sort: Optional[str] = None,
#     direction: Optional[str] = "asc"
# ) -> OwnerList:
#     # First create a subquery to count services for each owner
#     service_count = (
#         db.query(
#             Service.owner_id,
#             func.count(Service.id).label('service_count'),
#             func.count(Service.ip).label('ip_count')
#         )
#         .group_by(Service.owner_id)
#         .subquery()
#     )

#     # Main query including the counts
#     query = (
#         db.query(
#             Owner,
#             func.coalesce(service_count.c.service_count, 0).label('service_count'),
#             func.coalesce(service_count.c.ip_count, 0).label('ip_count')
#         )
#         .outerjoin(service_count, Owner.id == service_count.c.owner_id)
#     )
    
#     if search:
#         search_filter = f"%{search}%"
#         query = query.filter(
#             or_(
#                 Owner.name.ilike(search_filter),
#                 Owner.description.ilike(search_filter),
#                 Owner.contact_info.ilike(search_filter)
#             )
#         )
    
#     # Handle sorting
#     if sort:
#         if sort == 'service_count':
#             order_col = service_count.c.service_count
#         elif sort == 'ip_count':
#             order_col = service_count.c.ip_count
#         else:
#             order_col = getattr(Owner, sort, Owner.name)
            
#         if direction == "desc":
#             order_col = order_col.desc()
#         query = query.order_by(order_col)
#     else:
#         query = query.order_by(Owner.name)
    
#     total = query.count()
#     results = query.offset(skip).limit(limit).all()
    
#     # Convert results to response objects with counts
#     owners = []
#     for owner, service_count, ip_count in results:
#         owner_dict = OwnerResponse.model_validate(owner)
#         owner_dict.service_count = service_count
#         owner_dict.ip_count = ip_count
#         owners.append(owner_dict)

#     return OwnerList(
#         items=owners,
#         total=total,
#         page=(skip // limit) + 1,
#         size=limit,
#         pages=(total + limit - 1) // limit
#     )

def create_owner(db: Session, owner: schemas.OwnerCreate) -> Owner:
    db_owner = Owner(**owner.dict())
    db.add(db_owner)
    db.commit()
    db.refresh(db_owner)
    return db_owner

def update_owner(db: Session, owner_id: int, owner: schemas.OwnerUpdate) -> Optional[Owner]:
    db_owner = get_owner(db, owner_id)
    if db_owner is None:
        return None
    
    update_data = owner.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_owner, field, value)
    
    db.commit()
    db.refresh(db_owner)
    return db_owner

def delete_owner(db: Session, owner_id: int) -> bool:
    owner = get_owner(db, owner_id)
    if owner is None:
        return False
    
    db.delete(owner)
    db.commit()
    return True

# Service operations
def get_service(db: Session, service_id: int) -> Optional[Service]:
    return db.query(Service).filter(Service.id == service_id).first()

def get_services(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: Optional[int] = None,
    fruit_id: Optional[int] = None,
    ip: Optional[str] = None,
    port: Optional[int] = None,
    country: Optional[str] = None,
    asn: Optional[str] = None,
    domain: Optional[str] = None,
    search: Optional[str] = None
) -> ServiceList:
    query = db.query(Service)
    
    if owner_id:
        query = query.filter(Service.owner_id == owner_id)
    if fruit_id:
        query = query.filter(Service.fruit_id == fruit_id)
    if ip:
        query = query.filter(Service.ip.ilike(f"%{ip}%"))
    if port:
        query = query.filter(Service.port == port)
    if country:
        query = query.filter(Service.country.ilike(f"%{country}%"))
    if asn:
        query = query.filter(Service.asn.ilike(f"%{asn}%"))
    if domain:
        query = query.filter(Service.domain.ilike(f"%{domain}%"))
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Service.banner_data.ilike(search_filter),
                Service.domain.ilike(search_filter),
                Service.country.ilike(search_filter),
                Service.asn.ilike(search_filter)
            )
        )
    
    total = query.count()
    services = query.offset(skip).limit(limit).all()
    
    return ServiceList(
        items=services,
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )

def create_service(db: Session, service: schemas.ServiceCreate) -> Service:
    # Convert http_data to JSON string if it's provided
    service_data = service.dict()
    if service_data.get('http_data'):
        service_data['http_data'] = json.dumps(service_data['http_data'])
    
    db_service = Service(**service_data)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

def update_service(db: Session, service_id: int, service: schemas.ServiceUpdate) -> Optional[Service]:
    db_service = get_service(db, service_id)
    if db_service is None:
        return None
    
    update_data = service.dict(exclude_unset=True)
    if 'http_data' in update_data and update_data['http_data']:
        update_data['http_data'] = json.dumps(update_data['http_data'])
    
    for field, value in update_data.items():
        setattr(db_service, field, value)
    
    db.commit()
    db.refresh(db_service)
    return db_service

def delete_service(db: Session, service_id: int) -> bool:
    service = get_service(db, service_id)
    if service is None:
        return False
    
    db.delete(service)
    db.commit()
    return True

# Additional utility functions
def get_services_by_owner(
    db: Session,
    owner_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Service]:
    return (db.query(Service)
            .filter(Service.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all())

def get_services_by_fruit(
    db: Session,
    fruit_id: int,
    skip: int = 0,
    limit: int = 20
) -> List[Service]:
    return (db.query(Service)
            .filter(Service.fruit_id == fruit_id)
            .offset(skip)
            .limit(limit)
            .all())


def get_unique_asns(db: Session) -> List[str]:
    """Get list of unique ASNs from services table."""
    asns = db.query(Service.asn).distinct().order_by(Service.asn).all()
    return [asn[0] for asn in asns if asn[0]]

def get_unique_countries(db: Session) -> List[str]:
    """Get list of unique countries from services table."""
    countries = db.query(Service.country).distinct().order_by(Service.country).all()
    return [country[0] for country in countries if country[0]]

# Owner IP operations
def add_owner_ip(db: Session, owner_id: int, ip: str) -> OwnerIP:
    """Add an IP address or CIDR range to an owner"""
    # Validate owner exists
    owner = get_owner(db, owner_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found"
        )
        
    # Check if this IP/CIDR is already owned by someone else
    existing = db.query(OwnerIP).filter_by(ip=ip).first()
    if existing and existing.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This IP or range is already owned by another organization"
        )
    
    # Create new record if it doesn't exist for this owner
    if not existing:
        try:
            owner_ip = OwnerIP(
                owner_id=owner_id,
                ip=ip
            )
            db.add(owner_ip)
            db.commit()
            db.refresh(owner_ip)
            return owner_ip
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    return existing

def remove_owner_ip(db: Session, owner_id: int, ip_id: int) -> bool:
    """Remove an IP address from an owner"""
    owner_ip = db.query(OwnerIP).filter_by(id=ip_id, owner_id=owner_id).first()
    if not owner_ip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IP not found or not owned by this owner"
        )
    
    db.delete(owner_ip)
    db.commit()
    return True

def add_owner_domain(db: Session, owner_id: int, domain: str, include_subdomains: bool = True) -> OwnerDomain:
    """Add a domain to an owner"""
    # Validate owner exists
    owner = get_owner(db, owner_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found"
        )
    
    # Clean domain (remove http://, www. prefixes)
    domain = domain.lower().strip()
    if domain.startswith('http://'):
        domain = domain[7:]
    if domain.startswith('https://'):
        domain = domain[8:]
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Check if this domain is already owned by someone else
    existing = db.query(OwnerDomain).filter_by(domain=domain).first()
    if existing and existing.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This domain is already owned by another organization"
        )
    
    # Create new record if it doesn't exist for this owner
    if not existing:
        owner_domain = OwnerDomain(
            owner_id=owner_id,
            domain=domain,
            include_subdomains=include_subdomains
        )
        db.add(owner_domain)
        db.commit()
        db.refresh(owner_domain)
        return owner_domain
    
    # Update include_subdomains flag if it changed
    if existing.include_subdomains != include_subdomains:
        existing.include_subdomains = include_subdomains
        db.commit()
        db.refresh(existing)
        
    return existing

def remove_owner_domain(db: Session, owner_id: int, domain_id: int) -> bool:
    """Remove a domain from an owner"""
    owner_domain = db.query(OwnerDomain).filter_by(id=domain_id, owner_id=owner_id).first()
    if not owner_domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found or not owned by this owner"
        )
    
    db.delete(owner_domain)
    db.commit()
    return True

# Function to manually reassign all services to proper owners
def reassign_service_owners(db: Session) -> dict:
    """
    Reassign all services to their proper owners based on current IP and domain rules.
    Used after adding new ownership rules or when migrating existing data.
    
    Returns a dictionary with counts of updated services.
    """
    results = {
        "total_services": 0,
        "ip_matches": 0,
        "cidr_matches": 0,
        "domain_matches": 0,
        "subdomain_matches": 0
    }
    
    # Get all services
    services = db.query(Service).all()
    results["total_services"] = len(services)
    
    # Get all ownership rules
    ip_rules = db.query(OwnerIP).all()
    cidr_rules = [r for r in ip_rules if r.is_cidr]
    exact_ip_rules = [r for r in ip_rules if not r.is_cidr]
    
    domain_rules = db.query(OwnerDomain).all()
    
    # Process each service
    for service in services:
        old_owner_id = service.owner_id
        
        # Try exact IP match first
        if service.ip:
            for rule in exact_ip_rules:
                if service.ip == rule.ip:
                    service.owner_id = rule.owner_id
                    results["ip_matches"] += 1
                    break
        
        # Try CIDR match if no exact match
        if service.ip and service.owner_id == old_owner_id:
            try:
                ip_obj = ipaddress.ip_address(service.ip)
                for rule in cidr_rules:
                    try:
                        network = ipaddress.ip_network(rule.ip, strict=False)
                        if ip_obj in network:
                            service.owner_id = rule.owner_id
                            results["cidr_matches"] += 1
                            break
                    except ValueError:
                        continue
            except ValueError:
                pass
        
        # Try exact domain match
        if service.domain and service.owner_id == old_owner_id:
            for rule in domain_rules:
                if service.domain == rule.domain:
                    service.owner_id = rule.owner_id
                    results["domain_matches"] += 1
                    break
        
        # Try subdomain match if enabled
        if service.domain and service.owner_id == old_owner_id:
            for rule in domain_rules:
                if rule.include_subdomains and rule.domain and service.domain.endswith('.' + rule.domain):
                    service.owner_id = rule.owner_id
                    results["subdomain_matches"] += 1
                    break
    
    db.commit()
    return results