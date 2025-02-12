from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy import func

from fastapi import UploadFile, HTTPException
import csv
from datetime import datetime
from typing import List, Optional, Dict
from io import StringIO
import json

from app.models import User, FruitType, Fruit, Recipe, Group, SavedFilter, Service, Owner
from passlib.hash import bcrypt
from app import schemas
from .schemas import ServiceList, ServiceResponse, OwnerList, OwnerResponse


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
    limit: int = 100,
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
    limit: int = 100,
    fruit_type_id: Optional[int] = None,
    country: Optional[str] = None,
    search: Optional[str] = None
) -> schemas.FruitList:
    query = db.query(Fruit)
    
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
                Fruit.country_of_origin.ilike(search_term)
            )
        )
    
    # Get total before pagination
    total = query.count()
    
    # Apply pagination
    fruits = query.order_by(Fruit.name).offset(skip).limit(limit).all()
    pages = (total + limit - 1) // limit

    return schemas.FruitList(
        items=[schemas.FruitResponse.model_validate(f) for f in fruits],
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=pages
    )

def get_fruit_countries(db: Session) -> List[str]:
    """Get list of all unique countries that have fruits."""
    return [r[0] for r in db.query(Fruit.country_of_origin).distinct().all()]

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
    limit: int = 100,
    search: Optional[str] = None,
    fruit_type_id: Optional[int] = None,
    max_time: Optional[int] = None
) -> schemas.RecipeList:
    """
    Get recipes with optional filtering and search.
    """
    query = db.query(Recipe)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Recipe.name.ilike(search_filter),
                Recipe.description.ilike(search_filter)
            )
        )
    
    if fruit_type_id:
        query = query.filter(Recipe.fruit_types.any(FruitType.id == fruit_type_id))
    
    if max_time:
        query = query.filter(Recipe.preparation_time <= max_time)
    
    total = query.count()
    recipes = query.order_by(Recipe.name).offset(skip).limit(limit).all()
    pages = (total + limit - 1) // limit

    return schemas.RecipeList(
        items=[schemas.RecipeResponse.model_validate(r) for r in recipes],
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=pages
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

def get_recipes_by_fruit_type(
    db: Session,
    fruit_type_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Recipe]:
    """
    Get all recipes that use a specific fruit type.
    Returns a list of recipes that include this fruit type.
    """
    # Verify fruit type exists
    fruit_type = get_fruit_type(db, fruit_type_id)
    if not fruit_type:
        raise HTTPException(404, "Fruit type not found")
    
    # Query recipes that include this fruit type
    query = db.query(Recipe).filter(
        Recipe.fruit_types.any(FruitType.id == fruit_type_id)
    )
    
    recipes = query.offset(skip).limit(limit).all()
    return recipes

def get_owner(db: Session, owner_id: int) -> Optional[Owner]:
    return db.query(Owner).filter(Owner.id == owner_id).first()

def get_owners(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    direction: Optional[str] = "asc"
) -> OwnerList:
    # First create a subquery to count services for each owner
    service_count = (
        db.query(
            Service.owner_id,
            func.count(Service.id).label('service_count'),
            func.count(Service.ip).label('ip_count')
        )
        .group_by(Service.owner_id)
        .subquery()
    )

    # Main query including the counts
    query = (
        db.query(
            Owner,
            func.coalesce(service_count.c.service_count, 0).label('service_count'),
            func.coalesce(service_count.c.ip_count, 0).label('ip_count')
        )
        .outerjoin(service_count, Owner.id == service_count.c.owner_id)
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
        if sort == 'service_count':
            order_col = service_count.c.service_count
        elif sort == 'ip_count':
            order_col = service_count.c.ip_count
        else:
            order_col = getattr(Owner, sort, Owner.name)
            
        if direction == "desc":
            order_col = order_col.desc()
        query = query.order_by(order_col)
    else:
        query = query.order_by(Owner.name)
    
    total = query.count()
    results = query.offset(skip).limit(limit).all()
    
    # Convert results to response objects with counts
    owners = []
    for owner, service_count, ip_count in results:
        owner_dict = OwnerResponse.model_validate(owner)
        owner_dict.service_count = service_count
        owner_dict.ip_count = ip_count
        owners.append(owner_dict)

    return OwnerList(
        items=owners,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )

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
    limit: int = 100
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