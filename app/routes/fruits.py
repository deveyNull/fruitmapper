from fastapi import APIRouter, Depends, HTTPException, Request, status, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
import app.crud as crud
import app.schemas as schemas
from app.dependencies import get_current_user, get_current_admin_user


router = APIRouter(prefix="", tags=["fruits"])

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def list_fruits(
    request: Request,
    fruit_type_id: Optional[int] = None,
    country: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all fruits with optional filtering."""
    # Get fruits with pagination
    page_size = 10
    skip = (page - 1) * page_size
    
    # Get fruits with filters
    fruits = crud.get_fruits(
        db,
        skip=skip,
        limit=page_size,
        fruit_type_id=fruit_type_id,
        country=country,
        search=search
    )
    
    # Get fruit types for filter dropdown
    fruit_types = crud.get_fruit_types(db).items
    
    # Get unique countries for filter dropdown
    countries = crud.get_fruit_countries(db)
    
    return templates.TemplateResponse(
        "fruits.html",
        {
            "request": request,
            "fruits": fruits,
            "fruit_types": fruit_types,
            "countries": countries,
            "selected_type": fruit_type_id,
            "selected_country": country,
            "search": search,
            "current_page": page
        }
    )

@router.post("/", response_model=schemas.FruitResponse)
async def create_fruit(
    fruit: schemas.FruitCreate,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new fruit (admin only).
    """
    # Verify fruit type exists
    fruit_type = crud.get_fruit_type(db, fruit.fruit_type_id)
    if not fruit_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit type not found"
        )
    
    return crud.create_fruit(db, fruit)

@router.get("/{fruit_id}", response_class=HTMLResponse)
async def get_fruit(
    request: Request,
    fruit_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """View a specific fruit's details."""
    fruit = crud.get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit not found"
        )
    
    # Get compatible recipes for this fruit type
    compatible_recipes = crud.get_recipes_by_fruit_type(db, fruit.fruit_type_id)
    
    return templates.TemplateResponse(
        "fruit_detail.html",
        {
            "request": request,
            "fruit": fruit,
            "compatible_recipes": compatible_recipes
        }
    )

@router.put("/{fruit_id}", response_model=schemas.FruitResponse)
async def update_fruit(
    fruit_id: int,
    fruit_update: schemas.FruitUpdate,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update a fruit's information (admin only).
    """
    fruit = crud.get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit not found"
        )
    
    if fruit_update.fruit_type_id:
        fruit_type = crud.get_fruit_type(db, fruit_update.fruit_type_id)
        if not fruit_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fruit type not found"
            )
    
    return crud.update_fruit(db, fruit_id, fruit_update)

@router.delete("/{fruit_id}", response_model=schemas.SuccessResponse)
async def delete_fruit(
    fruit_id: int,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a fruit (admin only).
    """
    fruit = crud.get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit not found"
        )
    
    crud.delete_fruit(db, fruit_id)
    return {"message": "Fruit deleted successfully"}

@router.post("/upload", response_model=schemas.FileUploadResponse)
async def upload_fruits(
    file: UploadFile = File(...),
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Upload multiple fruits via CSV file (admin only).
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    try:
        result = await crud.upload_fruits(db, file)
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

@router.get("/by-type/{type_id}", response_model=List[schemas.FruitResponse])
async def get_fruits_by_type(
    type_id: int,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all fruits of a specific type.
    """
    fruit_type = crud.get_fruit_type(db, type_id)
    if not fruit_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit type not found"
        )
    return crud.get_fruits_by_type(db, type_id)

@router.get("/countries", response_model=List[str])
async def get_countries(
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of all countries that have fruits.
    """
    return crud.get_fruit_countries(db)


@router.post("/{fruit_id}/change-type", response_model=schemas.FruitResponse)
async def change_fruit_type(
    fruit_id: int,
    fruit_type_id: int,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Change the type of a fruit (admin only).
    """
    fruit = crud.get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit not found"
        )
    
    fruit_type = crud.get_fruit_type(db, fruit_type_id)
    if not fruit_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit type not found"
        )
    
    return crud.update_fruit(
        db,
        fruit_id,
        schemas.FruitUpdate(fruit_type_id=fruit_type_id)
    )

