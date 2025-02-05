from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import get_db
import crud
import schemas
from dependencies import get_current_user, get_current_admin_user

# Initialize routers
fruit_router = APIRouter(prefix="/fruits", tags=["fruits"])
recipe_router = APIRouter(prefix="/recipes", tags=["recipes"])
group_router = APIRouter(prefix="/groups", tags=["groups"])
filter_router = APIRouter(prefix="/filters", tags=["filters"])

# Fruit routes
@fruit_router.get("/", response_model=schemas.FruitList)
async def list_fruits(
    skip: int = 0,
    limit: int = 100,
    fruit_type_id: Optional[int] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_fruits(db, skip=skip, limit=limit, fruit_type_id=fruit_type_id)

@fruit_router.post("/", response_model=schemas.FruitResponse)
async def create_fruit(
    fruit: schemas.FruitCreate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    return crud.create_fruit(db, fruit)

@fruit_router.get("/{fruit_id}", response_model=schemas.FruitResponse)
async def get_fruit(
    fruit_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fruit = crud.get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(status_code=404, detail="Fruit not found")
    return fruit

@fruit_router.put("/{fruit_id}", response_model=schemas.FruitResponse)
async def update_fruit(
    fruit_id: int,
    fruit_update: schemas.FruitUpdate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    return crud.update_fruit(db, fruit_id, fruit_update)

# Recipe routes
@recipe_router.get("/", response_model=schemas.RecipeList)
async def list_recipes(
    skip: int = 0,
    limit: int = 100,
    fruit_type_id: Optional[int] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_recipes(db, skip=skip, limit=limit, fruit_type_id=fruit_type_id)

@recipe_router.post("/", response_model=schemas.RecipeResponse)
async def create_recipe(
    recipe: schemas.RecipeCreate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    return crud.create_recipe(db, recipe)

@recipe_router.get("/{recipe_id}", response_model=schemas.RecipeResponse)
async def get_recipe(
    recipe_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recipe = crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

@recipe_router.put("/{recipe_id}", response_model=schemas.RecipeResponse)
async def update_recipe(
    recipe_id: int,
    recipe_update: schemas.RecipeUpdate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    return crud.update_recipe(db, recipe_id, recipe_update)

# Group routes
@group_router.get("/", response_model=schemas.GroupList)
async def list_groups(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_groups(db, skip=skip, limit=limit, user_id=current_user.id)

@group_router.post("/", response_model=schemas.GroupResponse)
async def create_group(
    group: schemas.GroupCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.create_group(db, group, current_user.id)

@group_router.put("/{group_id}/members/{user_id}")
async def manage_group_member(
    group_id: int,
    user_id: int,
    add: bool = True,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify group ownership or admin status
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if not current_user.is_admin and group.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return crud.manage_group_members(db, group_id, user_id, add)

# Filter routes
@filter_router.get("/", response_model=schemas.FilterList)
async def list_filters(
    skip: int = 0,
    limit: int = 100,
    group_id: Optional[int] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_filters(
        db,
        skip=skip,
        limit=limit,
        user_id=current_user.id,
        group_id=group_id
    )

@filter_router.post("/", response_model=schemas.FilterResponse)
async def create_filter(
    filter_create: schemas.FilterCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.create_filter(db, filter_create, current_user.id)

@filter_router.put("/{filter_id}", response_model=schemas.FilterResponse)
async def update_filter(
    filter_id: int,
    filter_update: schemas.FilterUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return crud.update_filter(db, filter_id, filter_update, current_user.id)

# Admin routes for file uploads
@fruit_router.post("/upload")
async def upload_fruits(
    file: UploadFile = File(...),
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    return await crud.upload_fruits(db, file)

@recipe_router.post("/upload")
async def upload_recipes(
    file: UploadFile = File(...),
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    return await crud.upload_recipes(db, file)