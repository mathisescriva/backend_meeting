from pydantic import BaseModel
from typing import Optional

class Client(BaseModel):
    """Modèle pour les clients"""
    id: str
    name: str
    summary_template: Optional[str] = None
    created_at: Optional[str] = None

class ClientCreate(BaseModel):
    """Modèle pour la création d'un client"""
    name: str
    summary_template: Optional[str] = None

class ClientUpdate(BaseModel):
    """Modèle pour la mise à jour d'un client"""
    name: Optional[str] = None
    summary_template: Optional[str] = None
