# Purpose: Routes for managing user groups and access control

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
import app.crud
import app.schemas
from app.dependencies import get_current_user, get_current_admin_user

router = APIRouter(prefix="/groups", tags=["groups"])

@router.get("/", response_model=app.schemas.GroupList)
async def list_groups(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all groups the current user is a member of."""
    return app.crud.get_groups(
        db, 
        skip=skip, 
        limit=limit, 
        user_id=current_user.id
    )

@router.post("/", response_model=app.schemas.GroupResponse)
async def create_group(
    group: app.schemas.GroupCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new group with the current user as creator."""
    # Check for duplicate group name
    if app.crud.get_group_by_name(db, group.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group name already exists"
        )
    return app.crud.create_group(db, group, current_user.id)

@router.get("/{group_id}", response_model=app.schemas.GroupResponse)
async def get_group(
    group_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific group."""
    group = app.crud.get_group(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if user is member
    if not app.crud.is_user_in_group(db, current_user.id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this group"
        )
    
    return group

@router.put("/{group_id}", response_model=app.schemas.GroupResponse)
async def update_group(
    group_id: int,
    group_update: app.schemas.GroupUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a group's details (creator or admin only)."""
    group = app.crud.get_group(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if user is creator or admin
    if not current_user.is_admin and group.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this group"
        )
    
    # Check for duplicate name if name is being updated
    if group_update.name:
        existing = app.crud.get_group_by_name(db, group_update.name)
        if existing and existing.id != group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group name already exists"
            )
    
    return app.crud.update_group(db, group_id, group_update)

@router.delete("/{group_id}")
async def delete_group(
    group_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a group (creator or admin only)."""
    group = app.crud.get_group(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if user is creator or admin
    if not current_user.is_admin and group.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this group"
        )
    
    # Check if group has shared filters
    if app.crud.group_has_shared_filters(db, group_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete group with shared filters"
        )
    
    app.crud.delete_group(db, group_id)
    return {"message": "Group deleted successfully"}

@router.post("/{group_id}/members/{user_id}")
async def add_group_member(
    group_id: int,
    user_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a user to a group (creator or admin only)."""
    group = app.crud.get_group(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if user is creator or admin
    if not current_user.is_admin and group.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify group members"
        )
    
    # Check if user exists
    user = app.crud.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is already a member
    if app.crud.is_user_in_group(db, user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this group"
        )
    
    return app.crud.manage_group_members(db, group_id, user_id, add=True)

@router.delete("/{group_id}/members/{user_id}")
async def remove_group_member(
    group_id: int,
    user_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a user from a group (creator or admin only)."""
    group = app.crud.get_group(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if user is creator or admin
    if not current_user.is_admin and group.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify group members"
        )
    
    # Prevent removing the creator
    if user_id == group.creator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove group creator"
        )
    
    # Check if user is a member
    if not app.crud.is_user_in_group(db, user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this group"
        )
    
    return app.crud.manage_group_members(db, group_id, user_id, add=False)

@router.get("/{group_id}/members", response_model=List[app.schemas.UserResponse])
async def list_group_members(
    group_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all members of a group."""
    group = app.crud.get_group(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if user is member
    if not app.crud.is_user_in_group(db, current_user.id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this group"
        )
    
    return app.crud.get_group_members(db, group_id)