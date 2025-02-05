from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
import app.crud as crud
import app.schemas as schemas
from app.dependencies import get_current_user, get_current_admin_user

router = APIRouter(prefix="/recipes", tags=["recipes"])

@router.get("/", response_model=schemas.RecipeList)
async def list_recipes(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    fruit_type_id: Optional[int] = None,
    max_prep_time: Optional[int] = None,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all recipes with optional filtering.
    - search: Search in name and description
    - fruit_type_id: Filter by fruit type
    - max_prep_time: Filter by maximum preparation time in minutes
    """
    return crud.get_recipes(
        db,
        skip=skip,
        limit=limit,
        search=search,
        fruit_type_id=fruit_type_id,
        max_prep_time=max_prep_time
    )

@router.post("/", response_model=schemas.RecipeResponse)
async def create_recipe(
    recipe: schemas.RecipeCreate,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new recipe (admin only).
    """
    # Verify fruit types exist
    for type_id in recipe.fruit_type_ids:
        if not crud.get_fruit_type(db, type_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fruit type with id {type_id} not found"
            )
    
    # Check if recipe name already exists
    if crud.get_recipe_by_name(db, recipe.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe with this name already exists"
        )
    
    return crud.create_recipe(db, recipe)

@router.get("/{recipe_id}", response_model=schemas.RecipeResponse)
async def get_recipe(
    recipe_id: int,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific recipe.
    """
    recipe = crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    return recipe

@router.put("/{recipe_id}", response_model=schemas.RecipeResponse)
async def update_recipe(
    recipe_id: int,
    recipe_update: schemas.RecipeUpdate,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update a recipe (admin only).
    """
    recipe = crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    # Verify fruit types if provided
    if recipe_update.fruit_type_ids:
        for type_id in recipe_update.fruit_type_ids:
            if not crud.get_fruit_type(db, type_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Fruit type with id {type_id} not found"
                )
    
    # Check name uniqueness if name is being updated
    if recipe_update.name and recipe_update.name != recipe.name:
        if crud.get_recipe_by_name(db, recipe_update.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipe with this name already exists"
            )
    
    return crud.update_recipe(db, recipe_id, recipe_update)

@router.delete("/{recipe_id}", response_model=schemas.SuccessResponse)
async def delete_recipe(
    recipe_id: int,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a recipe (admin only).
    """
    recipe = crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    crud.delete_recipe(db, recipe_id)
    return {"message": "Recipe deleted successfully"}

@router.post("/upload", response_model=schemas.FileUploadResponse)
async def upload_recipes(
    file: UploadFile = File(...),
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Upload multiple recipes via CSV file (admin only).
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    try:
        result = await crud.upload_recipes(db, file)
        return {
            "filename": file.filename,
            "success": True,
            "message": f"Successfully processed: {result['added']} added, {result['updated']} updated"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{recipe_id}/fruit-types/{type_id}")
async def add_fruit_type_to_recipe(
    recipe_id: int,
    type_id: int,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Add a fruit type to a recipe (admin only).
    """
    recipe = crud.get_recipe(db, recipe_id)
    fruit_type = crud.get_fruit_type(db, type_id)
    
    if not recipe or not fruit_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe or fruit type not found"
        )
    
    if fruit_type in recipe.fruit_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This fruit type is already associated with the recipe"
        )
    
    return crud.add_fruit_type_to_recipe(db, recipe_id, type_id)

@router.delete("/{recipe_id}/fruit-types/{type_id}")
async def remove_fruit_type_from_recipe(
    recipe_id: int,
    type_id: int,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Remove a fruit type from a recipe (admin only).
    """
    recipe = crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    if len(recipe.fruit_types) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last fruit type from a recipe"
        )
    
    return crud.remove_fruit_type_from_recipe(db, recipe_id, type_id)

@router.get("/by-fruit/{fruit_id}", response_model=List[schemas.RecipeResponse])
async def get_recipes_by_fruit(
    fruit_id: int,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all recipes compatible with a specific fruit.
    """
    fruit = crud.get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit not found"
        )
    
    return crud.get_recipes_by_fruit_type(db, fruit.fruit_type_id)
