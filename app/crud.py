from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import UploadFile, HTTPException
import csv
from datetime import datetime
from typing import List, Optional, Dict
from io import StringIO
import json

from app.models import User, FruitType, Fruit, Recipe, Group, SavedFilter
from passlib.hash import bcrypt

from app import schemas
from sqlalchemy.orm import Session

# User operations
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate) -> User:
    # Check if username or email already exists
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
    limit: int = 100,
    search: Optional[str] = None
) -> schemas.FruitTypeList:
    query = db.query(FruitType)
    
    if search:
        search = f"%{search}%"
        query = query.filter(FruitType.name.ilike(search) | 
                           FruitType.description.ilike(search))
    total = db.query(FruitType).count()
    items = db.query(FruitType).offset(skip).limit(limit).all()
    return schemas.FruitTypeList(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )

def create_fruit_type(db: Session, fruit_type: schemas.FruitTypeCreate) -> FruitType:
    if db.query(FruitType).filter(FruitType.name == fruit_type.name).first():
        raise HTTPException(400, "Fruit type name already exists")
    
    db_fruit_type = FruitType(**fruit_type.dict())
    db.add(db_fruit_type)
    db.commit()
    db.refresh(db_fruit_type)
    return db_fruit_type

def delete_fruit_type(db: Session, fruit_type_id: int) -> bool:
    """Delete a fruit type if it has no associated fruits or recipes."""
    db_fruit_type = get_fruit_type(db, fruit_type_id)
    if db_fruit_type:
        db.delete(db_fruit_type)
        db.commit()
        return True
    return False

def get_fruits_by_type(
    db: Session,
    fruit_type_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Fruit]:
    """Get all fruits of a specific type."""
    return (db.query(Fruit)
            .filter(Fruit.fruit_type_id == fruit_type_id)
            .offset(skip)
            .limit(limit)
            .all())

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

# Fruit operations
def get_fruit(db: Session, fruit_id: int) -> Optional[Fruit]:
    return db.query(Fruit).filter(Fruit.id == fruit_id).first()

def get_fruits(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    fruit_type_id: Optional[int] = None
) -> schemas.FruitList:
    query = db.query(Fruit)
    if fruit_type_id:
        query = query.filter(Fruit.fruit_type_id == fruit_type_id)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return schemas.FruitList(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )

def create_fruit(db: Session, fruit: schemas.FruitCreate) -> Fruit:
    # Validate fruit type exists
    if not get_fruit_type(db, fruit.fruit_type_id):
        raise HTTPException(400, "Fruit type not found")
    
    db_fruit = Fruit(**fruit.dict())
    db.add(db_fruit)
    db.commit()
    db.refresh(db_fruit)
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
    if 'fruit_type_id' in update_data and not get_fruit_type(db, update_data['fruit_type_id']):
        raise HTTPException(400, "Fruit type not found")
    
    for field, value in update_data.items():
        setattr(db_fruit, field, value)
    
    db.commit()
    db.refresh(db_fruit)
    return db_fruit

# Recipe operations
def get_recipe(db: Session, recipe_id: int) -> Optional[Recipe]:
    return db.query(Recipe).filter(Recipe.id == recipe_id).first()

def get_recipes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    fruit_type_id: Optional[int] = None
) -> schemas.RecipeList:
    query = db.query(Recipe)
    if fruit_type_id:
        query = query.filter(Recipe.fruit_types.any(id=fruit_type_id))
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return schemas.RecipeList(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )

def create_recipe(db: Session, recipe: schemas.RecipeCreate) -> Recipe:
    # Validate fruit types exist
    fruit_types = db.query(FruitType).filter(FruitType.id.in_(recipe.fruit_type_ids)).all()
    if len(fruit_types) != len(recipe.fruit_type_ids):
        raise HTTPException(400, "One or more fruit types not found")
    
    db_recipe = Recipe(
        name=recipe.name,
        description=recipe.description,
        instructions=recipe.instructions,
        preparation_time=recipe.preparation_time,
        fruit_types=fruit_types
    )
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return db_recipe

def update_recipe(
    db: Session,
    recipe_id: int,
    recipe_update: schemas.RecipeUpdate
) -> Recipe:
    db_recipe = get_recipe(db, recipe_id)
    if not db_recipe:
        raise HTTPException(404, "Recipe not found")
    
    update_data = recipe_update.dict(exclude_unset=True)
    if 'fruit_type_ids' in update_data:
        fruit_types = db.query(FruitType).filter(
            FruitType.id.in_(update_data['fruit_type_ids'])
        ).all()
        if len(fruit_types) != len(update_data['fruit_type_ids']):
            raise HTTPException(400, "One or more fruit types not found")
        db_recipe.fruit_types = fruit_types
        del update_data['fruit_type_ids']
    
    for field, value in update_data.items():
        setattr(db_recipe, field, value)
    
    db.commit()
    db.refresh(db_recipe)
    return db_recipe

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
    items = query.offset(skip).limit(limit).all()
    return schemas.GroupList(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit
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