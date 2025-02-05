from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from database import get_db
import crud
import schemas
from dependencies import get_current_user, get_current_admin_user
from config import get_settings, DATASET_COLUMNS

router = APIRouter(prefix="/datasets", tags=["datasets"])

    
@router.get("/", response_model=schemas.FruitList)
async def get_dataset(
    skip: int = 0,
    limit: int = 100,
    filter_id: Optional[int] = None,
    filter_criteria: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    columns: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get dataset with optional filtering, sorting, and column selection.
    Can apply a saved filter or direct filter criteria.
    """
    # Parse filter criteria if provided
    criteria = None
    if filter_criteria:
        try:
            criteria = json.loads(filter_criteria)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filter criteria format"
            )
    
    # Get filter if filter_id provided
    if filter_id:
        saved_filter = crud.get_filter(db, filter_id)
        if not saved_filter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Filter not found"
            )
        # Check if user has access to filter
        if (saved_filter.user_id != current_user.id and 
            (not saved_filter.group_id or 
             not crud.is_user_in_group(db, current_user.id, saved_filter.group_id))):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to use this filter"
            )
        criteria = json.loads(saved_filter.filter_criteria)
    
    # Parse columns if provided
    visible_columns = None
    if columns:
        visible_columns = columns.split(',')
        # Validate column names
        valid_columns = {col["field"] for col in DATASET_COLUMNS}
        if not all(col in valid_columns for col in visible_columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid column name"
            )
    
    return crud.get_fruit_dataset(
        db,
        skip=skip,
        limit=limit,
        filter_criteria=criteria,
        sort_by=sort_by,
        sort_desc=sort_desc,
        columns=visible_columns
    )

@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    replace_existing: bool = False,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Upload a new dataset or update existing data.
    Admin only endpoint.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    return await crud.upload_fruit_dataset(db, file, replace_existing)

@router.get("/columns")
async def get_dataset_columns(
    current_user = Depends(get_current_user)
):
    """Get the list of available columns and their properties."""
    return DATASET_COLUMNS

@router.get("/download")
async def download_dataset(
    filter_id: Optional[int] = None,
    filter_criteria: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download the dataset as CSV.
    Applies any specified filters before downloading.
    """
    # Similar filtering logic as get_dataset
    criteria = None
    if filter_criteria:
        try:
            criteria = json.loads(filter_criteria)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filter criteria format"
            )
    
    if filter_id:
        saved_filter = crud.get_filter(db, filter_id)
        if not saved_filter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Filter not found"
            )
        if (saved_filter.user_id != current_user.id and 
            (not saved_filter.group_id or 
             not crud.is_user_in_group(db, current_user.id, saved_filter.group_id))):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to use this filter"
            )
        criteria = json.loads(saved_filter.filter_criteria)
    
    return crud.export_fruit_dataset(db, filter_criteria=criteria)

@router.get("/stats")
async def get_dataset_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistical information about the dataset."""
    return crud.get_dataset_statistics(db)
