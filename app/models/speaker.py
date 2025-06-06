from pydantic import BaseModel
from typing import Optional, List


class SpeakerBase(BaseModel):
    """Modèle de base pour les informations d'un locuteur"""
    speaker_id: str
    custom_name: str


class SpeakerCreate(SpeakerBase):
    """Modèle pour créer un nouveau nom personnalisé de locuteur"""
    pass


class Speaker(SpeakerBase):
    """Modèle complet d'un locuteur"""
    id: str
    meeting_id: str
    created_at: Optional[str] = None
    
    class Config:
        orm_mode = True


class SpeakersList(BaseModel):
    """Modèle pour une liste de locuteurs"""
    speakers: List[Speaker]
