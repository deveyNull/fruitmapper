# File: app/routes/services.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
from io import StringIO

from app.database import get_db
import app.crud as crud
import app.schemas as schemas
from app.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def list_services(
    request: Request,
    owner_id: Optional[int] = None,
    fruit_id: Optional[int] = None,
    ip: Optional[str] = None,
    port: Optional[int] = None,
    country: Optional[str] = None,
    asn: Optional[str] = None,
    domain: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all services with optional filtering."""
    skip = (page - 1) * page_size
    
    services = crud.get_services(
        db,
        skip=skip,
        limit=page_size,
        owner_id=owner_id,
        fruit_id=fruit_id,
        ip=ip,
        port=port,
        country=country,
        asn=asn,
        domain=domain,
        search=search
    )
    
    # Get filter options
    owners = crud.get_owners(db)
    fruits = crud.get_fruits(db)
    countries = crud.get_unique_countries(db)
    asns = crud.get_unique_asns(db)
    
    return templates.TemplateResponse(
        "services.html",
        {
            "request": request,
            "services": services,
            "owners": owners,
            "fruits": fruits,
            "countries": countries,
            "asns": asns,
            "selected_owner": owner_id,
            "selected_fruit": fruit_id,
            "selected_country": country,
            "selected_asn": asn,
            "search": search
        }
    )

@router.post("/", response_model=schemas.ServiceResponse)
async def create_service(
    service: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new service."""
    return crud.create_service(db, service)

@router.get("/{service_id}", response_class=HTMLResponse)
async def view_service(
    request: Request,
    service_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """View a specific service's details."""
    service = crud.get_service(db, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    return templates.TemplateResponse(
        "service_detail.html",
        {
            "request": request,
            "service": service
        }
    )

@router.put("/{service_id}", response_model=schemas.ServiceResponse)
async def update_service(
    service_id: int,
    service_update: schemas.ServiceUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a service."""
    updated_service = crud.update_service(db, service_id, service_update)
    if not updated_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    return updated_service

@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a service."""
    success = crud.delete_service(db, service_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    return {"message": "Service deleted successfully"}

@router.post("/upload")
async def upload_services(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Upload multiple services via CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    try:
        content = await file.read()
        text = content.decode('utf-8')
        reader = csv.DictReader(StringIO(text))
        
        results = {
            "created": 0,
            "updated": 0,
            "errors": []
        }
        
        for row in reader:
            try:
                service = schemas.ServiceCreate(
                    ip=row['ip'],
                    port=int(row['port']),
                    asn=row.get('asn'),
                    country=row.get('country'),
                    domain=row.get('domain'),
                    banner_data=row.get('banner_data'),
                    http_data=row.get('http_data'),
                    fruit_id=int(row['fruit_id']) if row.get('fruit_id') else None,
                    owner_id=int(row['owner_id']) if row.get('owner_id') else None
                )
                crud.create_service(db, service)
                results["created"] += 1
            except Exception as e:
                results["errors"].append(f"Error processing row {row.get('ip', 'unknown')}: {str(e)}")
        
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing file: {str(e)}"
        )

@router.get("/stats")
async def get_service_statistics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get statistical information about services."""
    return crud.get_service_statistics(db)