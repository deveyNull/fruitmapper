from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
import app.crud as crud
import app.schemas as schemas
from app.dependencies import get_current_user, get_current_admin_user

router = APIRouter(prefix="/fruit-types", tags=["fruit_types"])

@router.get("/", response_model=schemas.FruitTypeList)
async def list_fruit_types(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all fruit types with optional search filter.
    """
    return crud.get_fruit_types(
        db,
        skip=skip,
        limit=limit,
        search=search
    )

@router.post("/", response_model=schemas.FruitTypeResponse)
async def create_fruit_type(
    fruit_type: schemas.FruitTypeCreate,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new fruit type (admin only).
    """
    existing = crud.get_fruit_type_by_name(db, fruit_type.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fruit type with this name already exists"
        )
    return crud.create_fruit_type(db, fruit_type)

@router.get("/{type_id}", response_model=schemas.FruitTypeResponse)
async def get_fruit_type(
    type_id: int,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific fruit type.
    """
    fruit_type = crud.get_fruit_type(db, type_id)
    if not fruit_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit type not found"
        )
    return fruit_type

@router.put("/{type_id}", response_model=schemas.FruitTypeResponse)
async def update_fruit_type(
    type_id: int,
    fruit_type_update: schemas.FruitTypeUpdate,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update a fruit type (admin only).
    """
    fruit_type = crud.get_fruit_type(db, type_id)
    if not fruit_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit type not found"
        )
    
    if fruit_type_update.name and fruit_type_update.name != fruit_type.name:
        existing = crud.get_fruit_type_by_name(db, fruit_type_update.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fruit type with this name already exists"
            )
    
    return crud.update_fruit_type(db, type_id, fruit_type_update)

@router.delete("/{type_id}", response_model=schemas.SuccessResponse)
async def delete_fruit_type(
    type_id: int,
    force: bool = False,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a fruit type (admin only).
    Will fail if there are fruits or recipes associated unless force=True.
    """
    fruit_type = crud.get_fruit_type(db, type_id)
    if not fruit_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit type not found"
        )
    
    if not force and (fruit_type.fruits or fruit_type.recipes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete fruit type with associated fruits or recipes. Use force=True to override."
        )
    
    crud.delete_fruit_type(db, type_id)
    return {"message": "Fruit type deleted successfully"}

@router.post("/upload", response_model=schemas.FileUploadResponse)
async def upload_fruit_types(
    file: UploadFile = File(...),
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Upload multiple fruit types via CSV file (admin only).
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    try:
        result = await crud.upload_fruit_types(db, file)
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

@router.get("/{type_id}/fruits", response_model=List[schemas.FruitResponse])
async def list_fruits_by_type(
    type_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all fruits of a specific type.
    """
    fruit_type = crud.get_fruit_type(db, type_id)
    if not fruit_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit type not found"
        )
    return crud.get_fruits_by_type(db, type_id, skip=skip, limit=limit)

@router.get("/{type_id}/recipes", response_model=List[schemas.RecipeResponse])
async def list_recipes_by_type(
    type_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all recipes that use a specific fruit type.
    """
    fruit_type = crud.get_fruit_type(db, type_id)
    if not fruit_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fruit type not found"
        )
    return crud.get_recipes_by_fruit_type(db, type_id, skip=skip, limit=limit)


@router.post("/{type_id}/merge/{target_id}", response_model=schemas.FruitTypeResponse)
async def merge_fruit_types(
    type_id: int,
    target_id: int,
    current_user: schemas.UserResponse = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Merge one fruit type into another (admin only).
    All fruits and recipes from source type will be moved to target type.
    """
    source_type = crud.get_fruit_type(db, type_id)
    target_type = crud.get_fruit_type(db, target_id)
    
    if not source_type or not target_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both fruit types not found"
        )
    
    if type_id == target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot merge a fruit type with itself"
        )
    
    return crud.merge_fruit_types(db, type_id, target_id)