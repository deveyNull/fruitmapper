from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
import app.crud as crud
import app.schemas as schemas
from app.dependencies import get_current_user, get_current_admin_user

router = APIRouter()  # Remove the prefix, it's handled in main.py

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def list_recipes(
    request: Request,
    fruit_id: Optional[int] = None,  # Changed from fruit_type_id
    max_time: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all recipes with optional filtering."""
    page_size = 10
    skip = (page - 1) * page_size

    # Convert max_time to integer if provided
    max_time = int(max_time) if max_time else None
    fruit_id = int(fruit_id) if fruit_id else None
    
    # Get recipes with filters
    recipes = crud.get_recipes(
        db,
        skip=skip,
        limit=page_size,
        search=search,
        fruit_id=fruit_id,  # Changed from fruit_type_id
        max_time=max_time
    )
    
    # Get fruits for filter dropdown (instead of fruit types)
    fruits = crud.get_fruits(db).items
    
    # Calculate service counts for each recipe
    for recipe in recipes.items:
        recipe.service_count = 0
        for fruit in recipe.fruits:
            recipe.service_count += len(fruit.services)
    
    return templates.TemplateResponse(
        "recipes.html",
        {
            "request": request,
            "recipes": recipes,
            "fruits": fruits,  # Changed from fruit_types
            "selected_fruit": fruit_id,  # Changed from selected_type
            "max_time": max_time,
            "search": search,
            "current_user": current_user
        }
    )

@router.get("/api", response_model=schemas.RecipeList)
async def list_recipes_api(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    fruit_id: Optional[int] = None,  # Changed from fruit_type_id
    max_time: Optional[int] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """API endpoint for listing recipes."""
    return crud.get_recipes(
        db,
        skip=skip,
        limit=limit,
        search=search,
        fruit_id=fruit_id,  # Changed from fruit_type_id
        max_time=max_time
    )
@router.get("/{recipe_id}", response_class=HTMLResponse)
async def view_recipe(
    request: Request,
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """View a specific recipe's details."""
    recipe = crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    # Calculate the total service count
    recipe.service_count = 0
    for fruit in recipe.fruits:
        recipe.service_count += len(fruit.services)
    
    # Get available fruits for admin management (instead of fruit types)
    available_fruits = crud.get_fruits(db).items if current_user.is_admin else []
    
    # Check if there are any services associated with the recipe's fruits
    has_services = recipe.service_count > 0
    
    return templates.TemplateResponse(
        "recipe_detail.html",
        {
            "request": request,
            "recipe": recipe,
            "current_user": current_user,
            "available_fruits": available_fruits,  # Changed from available_fruit_types
            "has_services": has_services
        }
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
    # Verify fruits exist
    for fruit_id in recipe.fruit_ids:  # Changed from recipe.fruit_type_ids
        if not crud.get_fruit(db, fruit_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fruit with id {fruit_id} not found"
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
    
    # Verify fruits if provided
    if recipe_update.fruit_ids:  # Changed from recipe_update.fruit_type_ids
        for fruit_id in recipe_update.fruit_ids:
            if not crud.get_fruit(db, fruit_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Fruit with id {fruit_id} not found"
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

@router.post("/{recipe_id}/fruits/{fruit_id}")  # Changed from fruit-types to fruits
async def add_fruit_to_recipe(  # Changed from add_fruit_type_to_recipe
    recipe_id: int,
    fruit_id: int,  # Changed from type_id
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Add a fruit to a recipe (admin only).
    """
    recipe = crud.get_recipe(db, recipe_id)
    fruit = crud.get_fruit(db, fruit_id)  # Changed from fruit_type
    
    if not recipe or not fruit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe or fruit not found"  # Changed from "Recipe or fruit type not found"
        )
    
    if fruit in recipe.fruits:  # Changed from fruit_types
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This fruit is already associated with the recipe"  # Changed from "fruit type"
        )
    
    return crud.add_fruit_to_recipe(db, recipe_id, fruit_id)  # Changed function name

@router.delete("/{recipe_id}/fruits/{fruit_id}")  # Changed from fruit-types to fruits
async def remove_fruit_from_recipe(  # Changed from remove_fruit_type_from_recipe
    recipe_id: int,
    fruit_id: int,  # Changed from type_id
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Remove a fruit from a recipe (admin only).
    """
    recipe = crud.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    
    if len(recipe.fruits) <= 1:  # Changed from fruit_types
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last fruit from a recipe"  # Changed from "fruit type"
        )
    
    return crud.remove_fruit_from_recipe(db, recipe_id, fruit_id)  # Changed function name

@router.get("/by-fruit/{fruit_id}", response_model=List[schemas.RecipeResponse])  # Changed from by-fruit-type to by-fruit
async def get_recipes_by_fruit(  # Changed from get_recipes_by_fruit_type
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
    
    return crud.get_recipes_by_fruit(db, fruit_id)  # Changed function name