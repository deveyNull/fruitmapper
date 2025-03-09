from pydantic import BaseModel, EmailStr, constr, validator, IPvAnyAddress
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

# Base Response Models
class SuccessResponse(BaseModel):
    message: str
    status: str = "success"

class ErrorResponse(BaseModel):
    detail: str
    status: str = "error"

# Base Pagination Model
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int = 1
    size: int = 10
    pages: int = 1

    class Config:
        from_attributes = True

# User Models
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    password_confirm: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Alias for backwards compatibility
User = UserResponse

# FruitType Models
class FruitTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class FruitTypeCreate(FruitTypeBase):
    pass

class FruitTypeUpdate(FruitTypeBase):
    pass

class FruitTypeResponse(FruitTypeBase):
    id: int
    fruit_count: Optional[int] = 0

    class Config:
        from_attributes = True

# Alias for backwards compatibility
FruitType = FruitTypeResponse

# Owner Models
class OwnerBase(BaseModel):
    name: str
    description: Optional[str] = None
    contact_info: Optional[str] = None

class OwnerCreate(OwnerBase):
    pass

class OwnerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    contact_info: Optional[str] = None

class OwnerIPBase(BaseModel):
    ip: str

class OwnerIPCreate(OwnerIPBase):
    pass

class OwnerIPResponse(OwnerIPBase):
    id: int
    owner_id: int
    is_cidr: bool
    added_at: datetime

    class Config:
        from_attributes = True

class OwnerDomainBase(BaseModel):
    domain: str
    include_subdomains: bool = True

class OwnerDomainCreate(OwnerDomainBase):
    pass

class OwnerDomainResponse(OwnerDomainBase):
    id: int
    owner_id: int
    added_at: datetime

    class Config:
        from_attributes = True

class ServiceBasicResponse(BaseModel):
    id: int
    ip: str
    port: int
    domain: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

class OwnerResponse(OwnerBase):
    id: int
    created_at: datetime
    services: List[ServiceBasicResponse] = []
    owned_ips: List[OwnerIPResponse] = []
    owned_domains: List[OwnerDomainResponse] = []

    class Config:
        from_attributes = True


class ReassignmentResponse(BaseModel):
    total_services: int
    ip_matches: int
    cidr_matches: int
    domain_matches: int
    subdomain_matches: int
    message: str

class OwnerDomainUpdate(BaseModel):
    include_subdomains: Optional[bool] = None

class ServiceBase(BaseModel):
    ip: str
    port: int
    asn: Optional[str] = None
    country: Optional[str] = None
    domain: Optional[str] = None
    banner_data: Optional[str] = None
    http_data: Optional[str] = None  # Changed from Dict[str, Any] to str
    fruit_id: Optional[int] = None
    owner_id: Optional[int] = None

    @validator('port')
    def validate_port(cls, v):
        if not 0 <= v <= 65535:
            raise ValueError('Port must be between 0 and 65535')
        return v

    @validator('ip')
    def validate_ip(cls, v):
        try:
            IPvAnyAddress(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address')

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    ip: Optional[str] = None
    port: Optional[int] = None
    asn: Optional[str] = None
    country: Optional[str] = None
    domain: Optional[str] = None
    banner_data: Optional[str] = None
    http_data: Optional[str] = None  # Changed from Dict[str, Any] to str
    fruit_id: Optional[int] = None
    owner_id: Optional[int] = None

    @validator('port')
    def validate_port(cls, v):
        if v is not None and not 0 <= v <= 65535:
            raise ValueError('Port must be between 0 and 65535')
        return v

    @validator('ip')
    def validate_ip(cls, v):
        if v is not None:
            try:
                IPvAnyAddress(v)
                return v
            except ValueError:
                raise ValueError('Invalid IP address')
        return v

class ServiceResponseBase(ServiceBase):
    id: int
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
    owner: Optional['OwnerResponse'] = None

    class Config:
        from_attributes = True

# ... [other schema definitions remain the same] ...

class ServiceResponse(ServiceResponseBase):
    fruit: Optional['FruitResponse'] = None

    class Config:
        from_attributes = True

class FruitBase(BaseModel):
    name: str
    date_picked: datetime
    fruit_type_id: int
    match_type: Optional[str] = None
    match_regex: Optional[str] = None

class FruitCreate(FruitBase):
    pass

class FruitUpdate(BaseModel):
    name: Optional[str] = None
    date_picked: Optional[datetime] = None
    fruit_type_id: Optional[int] = None
    match_type: Optional[str] = None
    match_regex: Optional[str] = None

class FruitResponse(FruitBase):
    id: int
    fruit_type: FruitTypeResponse
    services: List[ServiceResponseBase] = []

    class Config:
        from_attributes = True

# Alias for backwards compatibility
Fruit = FruitResponse
   
class ServiceResponse(ServiceBasicResponse):
    fruit: Optional[FruitResponse] = None
    owner: Optional[OwnerResponse] = None

    class Config:
        from_attributes = True


# Alias for backwards compatibility
Fruit = FruitResponse

# Recipe Models
class RecipeBase(BaseModel):
    name: str
    description: str
    instructions: str
    preparation_time: int

class RecipeCreate(RecipeBase):
    fruit_type_ids: List[int]

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    preparation_time: Optional[int] = None
    fruit_type_ids: Optional[List[int]] = None

class RecipeResponse(RecipeBase):
    id: int
    fruit_types: List[FruitTypeResponse]
    created_at: datetime

    class Config:
        from_attributes = True

# Typed List Response Models
class FruitTypeList(PaginatedResponse):
    items: List[FruitTypeResponse]

class FruitList(PaginatedResponse):
    items: List[FruitResponse]

class RecipeList(PaginatedResponse):
    items: List[RecipeResponse]


class ServiceResponse(ServiceResponseBase):
    fruit: Optional[FruitResponse] = None

    class Config:
        from_attributes = True

# Add to your Typed List Response Models section:
class ServiceList(PaginatedResponse):
    items: List[ServiceResponse]

class OwnerList(PaginatedResponse):
    items: List[OwnerResponse]

# Group Models
class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupUpdate(GroupBase):
    pass

class GroupResponse(GroupBase):
    id: int
    created_at: datetime
    members: List[UserResponse]

    class Config:
        from_attributes = True

# Alias for backwards compatibility
Group = GroupResponse

class GroupList(PaginatedResponse):
    items: List[GroupResponse]

# Filter Models
class FilterBase(BaseModel):
    name: str
    description: Optional[str] = None
    filter_criteria: Dict[str, Any]
    visible_columns: List[str]
    group_id: Optional[int] = None

class FilterCreate(FilterBase):
    pass

class FilterUpdate(FilterBase):
    pass

class FilterResponse(FilterBase):
    id: int
    user_id: int
    created_at: datetime
    modified_at: datetime
    user: UserResponse
    group: Optional[GroupResponse] = None

    class Config:
        from_attributes = True

class FilterList(PaginatedResponse):
    items: List[FilterResponse]

# Utility Models
class FileUploadResponse(BaseModel):
    filename: str
    success: bool
    message: str

class BatchOperation(BaseModel):
    ids: List[int]
    operation: str

class BatchResponse(BaseModel):
    success: bool
    processed: int
    failed: int
    errors: Optional[List[str]] = None

# Authentication Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

FruitResponse.update_forward_refs()
ServiceResponse.update_forward_refs()
OwnerResponse.update_forward_refs()
