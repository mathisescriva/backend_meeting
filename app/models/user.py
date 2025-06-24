from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    profile_picture_url: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserCreateOAuth(UserBase):
    """Modèle pour la création d'utilisateur via OAuth (sans mot de passe)"""
    oauth_provider: str
    oauth_id: str

class User(UserBase):
    id: str
    created_at: Optional[str] = None
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_picture_url: Optional[str] = None
    
class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str
