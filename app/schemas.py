# File: app/schemas.py
from pydantic import BaseModel, EmailStr, constr
from typing import Optional, List, Dict, Any
from datetime import datetime

class SuccessResponse(BaseModel):
    message: str
    status: str = "success"

class ErrorResponse(BaseModel):
    detail: str
    status: str = "error"

# Fruit schemas with proper response type
class FruitBase(BaseModel):
    name: str
    country_of_origin: str
    date_picked: datetime
    fruit_type_id: int

class FruitCreate(FruitBase):
    pass
class FruitTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class FruitTypeCreate(FruitTypeBase):
    pass

class FruitTypeUpdate(FruitTypeBase):
    pass



class FruitTypeResponse(FruitTypeBase):
    id: int
    fruits: List['Fruit']

    class Config:
        orm_mode = True

# Keeping FruitType as an alias for backwards compatibility
FruitType = FruitTypeResponse

class FruitUpdate(BaseModel):
    name: Optional[str] = None
    country_of_origin: Optional[str] = None
    date_picked: Optional[datetime] = None
    fruit_type_id: Optional[int] = None

class FruitResponse(FruitBase):
    id: int
    fruit_type: FruitTypeResponse

    class Config:
        orm_mode = True

# Alias for backwards compatibility
Fruit = FruitResponse

# List response types
class FruitList(BaseModel):
    items: List[FruitResponse]
    total: int
    page: int = 1
    size: int = 10

class FruitTypeList(BaseModel):
    items: List[FruitTypeResponse]
    total: int
    page: int = 1
    size: int = 10



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
        orm_mode = True


class RecipeList(BaseModel):
    items: List[RecipeResponse]
    total: int
    page: int = 1
    size: int = 10

# API specific schemas
class APIResponse(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None

class PaginationParams(BaseModel):
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_desc: bool = False

class FilterParams(BaseModel):
    search: Optional[str] = None
    fruit_type_id: Optional[int] = None
    country: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

# File upload schemas
class FileUploadResponse(BaseModel):
    filename: str
    success: bool
    message: str



# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
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
        orm_mode = True

# Alias User to UserResponse for backwards compatibility
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

class FruitType(FruitTypeBase):
    id: int
    fruits: List['Fruit']

    class Config:
        orm_mode = True

class FruitTypeList(BaseModel):
    fruit_types: List[FruitType]
    total: int
    page: int
    size: int
    pages: int

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

class Fruit(FruitBase):
    id: int
    fruit_type: FruitType

    class Config:
        orm_mode = True

class FruitList(BaseModel):
    fruits: List[Fruit]
    total: int
    page: int
    size: int
    pages: int


class FruitResponse(FruitTypeBase):
    id: int
    fruits: List['Fruit']

    class Config:
        orm_mode = True

# Keeping FruitType as an alias for backwards compatibility
Fruit = FruitResponse








# Group schemas
class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupUpdate(GroupBase):
    pass

class Group(GroupBase):
    id: int
    created_at: datetime
    members: List[User]

    class Config:
        orm_mode = True


class GroupResponse(GroupBase):
    id: int
    group: List['Group']

    class Config:
        orm_mode = True

# Keeping Group as an alias for backwards compatibility
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

class Filter(FilterBase):
    id: int
    user_id: int
    created_at: datetime
    modified_at: datetime
    user: User
    group: Optional[Group] = None

    class Config:
        orm_mode = True


class FilterResponse(FilterBase):
    id: int
    filters: List['Filter']

    class Config:
        orm_mode = True


# Response schemas for pagination
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


# GroupList schema
class GroupList(BaseModel):
    groups: List[Group]
    total: int
    page: int
    size: int
    pages: int

# FilterList schema
class FilterList(BaseModel):
    filters: List[Filter]
    total: int
    page: int
    size: int
    pages: int


# Group membership schemas
class GroupMemberAdd(BaseModel):
    user_id: int

class GroupMemberRemove(BaseModel):
    user_id: int

# Filter sharing schemas
class FilterShare(BaseModel):
    group_id: int

# Batch operation schemas
class BatchOperation(BaseModel):
    ids: List[int]
    operation: str

class BatchResponse(BaseModel):
    success: bool
    processed: int
    failed: int
    errors: Optional[List[str]] = None
