from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
import app.crud
import app.schemas
from app.dependencies import get_current_user

router = APIRouter(prefix="/filters", tags=["filters"])

@router.get("/", response_model=app.schemas.FilterList)
async def list_filters(
    skip: int = 0,
    limit: int = 100,
    group_id: Optional[int] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all filters accessible to the current user."""
    return app.crud.get_filters(
        db,
        skip=skip,
        limit=limit,
        user_id=current_user.id,
        group_id=group_id
    )

@router.post("/", response_model=app.schemas.FilterResponse)
async def create_filter(
    filter_create: app.schemas.FilterCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new filter."""
    if filter_create.group_id:
        group = app.crud.get_group(db, filter_create.group_id)
        if not group or not any(member.id == current_user.id for member in group.members):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of the specified group"
            )
    
    return app.crud.create_filter(db, filter_create, current_user.id)

@router.get("/{filter_id}", response_model=app.schemas.FilterResponse)
async def get_filter(
    filter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific filter."""
    filter = app.crud.get_filter(db, filter_id)
    if not filter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter not found"
        )
    
    # Check if user has access to filter
    if (filter.user_id != current_user.id and 
        (not filter.group_id or 
         not app.crud.is_user_in_group(db, current_user.id, filter.group_id))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this filter"
        )
    
    return filter

@router.put("/{filter_id}", response_model=app.schemas.FilterResponse)
async def update_filter(
    filter_id: int,
    filter_update: app.schemas.FilterUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a filter."""
    filter = app.crud.get_filter(db, filter_id)
    if not filter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter not found"
        )
    
    # Only filter owner can update
    if filter.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this filter"
        )
    
    # If updating group_id, verify membership
    if filter_update.group_id:
        group = app.crud.get_group(db, filter_update.group_id)
        if not group or not any(member.id == current_user.id for member in group.members):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of the specified group"
            )
    
    return app.crud.update_filter(db, filter_id, filter_update, current_user.id)

@router.delete("/{filter_id}")
async def delete_filter(
    filter_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a filter."""
    filter = app.crud.get_filter(db, filter_id)
    if not filter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter not found"
        )
    
    # Only filter owner can delete
    if filter.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this filter"
        )
    
    app.crud.delete_filter(db, filter_id)
    return {"message": "Filter deleted successfully"}

@router.post("/{filter_id}/share/{group_id}")
async def share_filter_with_group(
    filter_id: int,
    group_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Share a filter with a group."""
    filter = app.crud.get_filter(db, filter_id)
    if not filter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter not found"
        )
    
    # Only filter owner can share
    if filter.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to share this filter"
        )
    
    # Verify group membership
    group = app.crud.get_group(db, group_id)
    if not group or not any(member.id == current_user.id for member in group.members):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of the specified group"
        )
    
    filter.group_id = group_id
    db.commit()
    return {"message": "Filter shared successfully"}