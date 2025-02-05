from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
import app.crud as crud
import app.schemas as schemas
from app.dependencies import get_current_user, get_current_admin_user

router = APIRouter(prefix="/fruits", tags=["fruits"])

@router.get("/", response_model=schemas.FruitList)
async def list_fruits(
    skip: int = 0,
    limit: int = 100,
    fruit_type_id: Optional[int] = None,
    country: Optional[str] = None,
    search: Optional[str] = None,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all fruits with optional filtering.
    """
    return crud.get_fruits(
        db, 
        skip=skip,
        limit=limit,
        fruit_type_id=fruit_type_id,
        country=country,
        search=search
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

@router.get("/{fruit_id}", response_model=schemas.FruitResponse)
async def get_fruit(
    fruit_id: int,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific fruit.
    """
    fruit = crud.get_fruit(db, fruit_id)
    if not fruit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit not found"
        )
    return fruit

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