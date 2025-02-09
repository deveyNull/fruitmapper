from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

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

# Fruit Models
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