# File: app/routes/owners.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
import app.crud as crud
import app.schemas as schemas
from app.dependencies import get_current_user, get_current_admin_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def list_owners(
    request: Request,
    search: Optional[str] = None,
    sort: Optional[str] = "name",
    direction: Optional[str] = "asc",
    page: int = 1,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    page_size = 10
    skip = (page - 1) * page_size
    
    owners = crud.get_owners(
        db,
        skip=skip,
        limit=page_size,
        search=search,
        sort=sort,
        direction=direction
    )
    
    # Debug print
    for owner in owners.items:
        print(f"Owner: {owner.name}")
        print(f"Services count: {len(owner.services) if owner.services else 0}")
        print(f"IPs count: {len(owner.owned_ips) if owner.owned_ips else 0}")
        print(f"Domains count: {len(owner.owned_domains) if owner.owned_domains else 0}")
    
    return templates.TemplateResponse(
        "owners.html",
        {
            "request": request,
            "owners": owners,
            "search": search,
            "current_user": current_user,
            "sort": sort,
            "direction": direction
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

@router.patch("/{owner_id}/domains/{domain_id}", response_model=schemas.OwnerDomainResponse)
async def update_domain_settings(
    owner_id: int,
    domain_id: int,
    update_data: schemas.OwnerDomainUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update domain settings like subdomain inclusion."""
    # Check if domain exists and belongs to this owner
    domain = db.query(OwnerDomain).filter_by(id=domain_id, owner_id=owner_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found or not owned by this owner"
        )
    
    # Update include_subdomains setting
    if update_data.include_subdomains is not None:
        domain.include_subdomains = update_data.include_subdomains
    
    db.commit()
    db.refresh(domain)
    
    # If we're enabling subdomain matching, refresh service ownership
    if update_data.include_subdomains:
        # Find services with matching subdomains and assign ownership
        services = db.query(Service).filter(
            and_(
                Service.domain.isnot(None),
                Service.owner_id.is_(None),
                Service.domain.like(f"%.{domain.domain}")
            )
        ).all()
        
        for service in services:
            service.owner_id = owner_id
        
        db.commit()
    
    return domain
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

@router.post("/{owner_id}/ips", response_model=schemas.OwnerIPResponse)
async def add_ip_to_owner(
    owner_id: int,
    ip_data: schemas.OwnerIPCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add an IP address or CIDR range to an owner."""
    return crud.add_owner_ip(db, owner_id, ip_data.ip)

@router.delete("/{owner_id}/ips/{ip_id}")
async def remove_ip_from_owner(
    owner_id: int,
    ip_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove an IP address from an owner."""
    crud.remove_owner_ip(db, owner_id, ip_id)
    return {"message": "IP address removed successfully"}

@router.post("/{owner_id}/domains", response_model=schemas.OwnerDomainResponse)
async def add_domain_to_owner(
    owner_id: int,
    domain_data: schemas.OwnerDomainCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add a domain to an owner."""
    return crud.add_owner_domain(db, owner_id, domain_data.domain, domain_data.include_subdomains)

@router.delete("/{owner_id}/domains/{domain_id}")
async def remove_domain_from_owner(
    owner_id: int,
    domain_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove a domain from an owner."""
    crud.remove_owner_domain(db, owner_id, domain_id)
    return {"message": "Domain removed successfully"}

@router.post("/reassign-services", response_model=schemas.ReassignmentResponse)
async def reassign_all_services(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)  # Admin only
):
    """
    Reassign all services to their proper owners based on current IP and domain rules.
    This is useful after adding new ownership rules or when migrating data.
    Admin only operation.
    """
    results = crud.reassign_service_owners(db)
    results["message"] = f"Successfully reassigned {results['ip_matches'] + results['cidr_matches'] + results['domain_matches'] + results['subdomain_matches']} services"
    return results