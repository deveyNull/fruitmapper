# File: app/routes/owners.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
import app.crud as crud
import app.schemas as schemas
from app.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def list_owners(
    request: Request,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all owners with optional search."""
    skip = (page - 1) * page_size
    
    owners = crud.get_owners(
        db,
        skip=skip,
        limit=page_size,
        search=search
    )
    
    return templates.TemplateResponse(
        "owners.html",
        {
            "request": request,
            "owners": owners,
            "search": search
        }
    )

@router.post("/", response_model=schemas.OwnerResponse)
async def create_owner(
    owner: schemas.OwnerCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new owner."""
    return crud.create_owner(db, owner)

@router.get("/{owner_id}", response_class=HTMLResponse)
async def view_owner(
    request: Request,
    owner_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """View a specific owner's details."""
    owner = crud.get_owner(db, owner_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found"
        )
    
    # Get services for this owner
    services = crud.get_services_by_owner(db, owner_id)
    
    return templates.TemplateResponse(
        "owner_detail.html",
        {
            "request": request,
            "owner": owner,
            "services": services
        }
    )

@router.put("/{owner_id}", response_model=schemas.OwnerResponse)
async def update_owner(
    owner_id: int,
    owner_update: schemas.OwnerUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update an owner."""
    updated_owner = crud.update_owner(db, owner_id, owner_update)
    if not updated_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found"
        )
    return updated_owner

@router.delete("/{owner_id}")
async def delete_owner(
    owner_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete an owner."""
    # Check if owner has any services
    owner = crud.get_owner(db, owner_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found"
        )
    
    services = crud.get_services_by_owner(db, owner_id)
    if services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete owner with associated services"
        )
    
    success = crud.delete_owner(db, owner_id)
    return {"message": "Owner deleted successfully"}

@router.get("/{owner_id}/services")
async def list_owner_services(
    owner_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all services belonging to an owner."""
    owner = crud.get_owner(db, owner_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found"
        )
    
    return crud.get_services_by_owner(db, owner_id, skip=skip, limit=limit)