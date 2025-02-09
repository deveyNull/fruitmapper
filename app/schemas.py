# File: app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# Base response models
class SuccessResponse(BaseModel):
    message: str
    status: str = "success"

class ErrorResponse(BaseModel):
    detail: str
    status: str = "error"

# User schemas
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

# Use UserResponse as the main User schema
User = UserResponse

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# FruitType schemas
class FruitTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class FruitTypeCreate(FruitTypeBase):
    pass

class FruitTypeUpdate(FruitTypeBase):
    pass

class FruitTypeResponse(FruitTypeBase):
    id: int

    class Config:
        from_attributes = True

# Use FruitTypeResponse as the main FruitType schema
FruitType = FruitTypeResponse

# Fruit schemas
class FruitBase(BaseModel):
    name: str
    country_of_origin: str
    date_picked: datetime
    fruit_type_id: int

class FruitCreate(FruitBase):
    pass

class FruitUpdate(BaseModel):
    name: Optional[str] = None
    country_of_origin: Optional[str] = None
    date_picked: Optional[datetime] = None
    fruit_type_id: Optional[int] = None

class FruitResponse(FruitBase):
    id: int
    fruit_type: FruitTypeResponse

    class Config:
        from_attributes = True

# Use FruitResponse as the main Fruit schema
Fruit = FruitResponse

# Group schemas
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

# Use GroupResponse as the main Group schema
Group = GroupResponse

# Filter schemas
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

# Use FilterResponse as the main Filter schema
Filter = FilterResponse

# Recipe schemas
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

# Pagination and List Response schemas
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        from_attributes = True

class FruitList(PaginatedResponse):
    items: List[FruitResponse]

class FruitTypeList(PaginatedResponse):
    items: List[FruitTypeResponse]

class RecipeList(PaginatedResponse):
    items: List[RecipeResponse]

class GroupList(PaginatedResponse):
    items: List[GroupResponse]

class FilterList(PaginatedResponse):
    items: List[FilterResponse]

# File upload schemas
class FileUploadResponse(BaseModel):
    filename: str
    success: bool
    message: str

# Batch operation schemas
class BatchOperation(BaseModel):
    ids: List[int]
    operation: str

class BatchResponse(BaseModel):
    success: bool
    processed: int
    failed: int
    errors: Optional[List[str]] = None