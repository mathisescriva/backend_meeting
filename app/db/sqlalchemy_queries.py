import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from .sqlalchemy_database import User, Meeting
import logging

# Logger pour le du00e9bogage
logger = logging.getLogger("fastapi")

def create_meeting(db: Session, meeting_data: dict, user_id: str):
    """
    Cru00e9er une nouvelle ru00e9union avec SQLAlchemy
    """
    logger.info(f"Cru00e9ation d'une nouvelle ru00e9union pour l'utilisateur {user_id}")
    
    try:
        # Gu00e9nu00e9rer un ID unique pour la ru00e9union
        meeting_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # Utiliser le statut fourni ou 'pending' par du00e9faut
        transcript_status = meeting_data.get("transcript_status", "pending")
        
        # Cru00e9er un nouvel objet Meeting
        new_meeting = Meeting(
            id=meeting_id,
            user_id=user_id,
            title=meeting_data["title"],
            file_url=meeting_data["file_url"],
            transcript_status=transcript_status,
            created_at=created_at
        )
        
        # Ajouter et valider la transaction
        db.add(new_meeting)
        db.commit()
        db.refresh(new_meeting)
        
        # Convertir l'objet SQLAlchemy en dictionnaire
        meeting = {
            "id": new_meeting.id,
            "user_id": new_meeting.user_id,
            "title": new_meeting.title,
            "file_url": new_meeting.file_url,
            "transcript_text": new_meeting.transcript_text,
            "transcript_status": new_meeting.transcript_status,
            "created_at": new_meeting.created_at.isoformat() if new_meeting.created_at else None,
            "duration_seconds": new_meeting.duration_seconds,
            "speakers_count": new_meeting.speakers_count,
            "summary_text": new_meeting.summary_text,
            "summary_status": new_meeting.summary_status
        }
        
        logger.info(f"Ru00e9union {meeting_id} cru00e9u00e9e avec succu00e8s")
        return meeting
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de la cru00e9ation de la ru00e9union: {str(e)}")
        raise e

def get_meeting(db: Session, meeting_id: str, user_id: str):
    """
    Ru00e9cupu00e9rer les du00e9tails d'une ru00e9union spu00e9cifique
    """
    try:
        # Ru00e9cupu00e9rer la ru00e9union avec SQLAlchemy
        meeting_obj = db.query(Meeting).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.user_id == user_id
            )
        ).first()
        
        if not meeting_obj:
            return None
        
        # Convertir l'objet SQLAlchemy en dictionnaire
        meeting = {
            "id": meeting_obj.id,
            "user_id": meeting_obj.user_id,
            "title": meeting_obj.title,
            "file_url": meeting_obj.file_url,
            "transcript_text": meeting_obj.transcript_text,
            "transcript_status": meeting_obj.transcript_status,
            "created_at": meeting_obj.created_at.isoformat() if meeting_obj.created_at else None,
            "duration_seconds": meeting_obj.duration_seconds,
            "speakers_count": meeting_obj.speakers_count,
            "summary_text": meeting_obj.summary_text,
            "summary_status": meeting_obj.summary_status
        }
        
        # Normaliser le format de la transcription si nu00e9cessaire
        if meeting["transcript_text"]:
            meeting["transcript_text"] = normalize_transcript_format(meeting["transcript_text"])
        
        return meeting
    
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration de la ru00e9union {meeting_id}: {str(e)}")
        return None

def normalize_transcript_format(text):
    """
    Normalise le format des transcriptions pour u00eatre cohu00e9rent
    Convertit tout format de transcription ('A: texte') 
    vers un format standard 'Speaker A: texte'
    """
    if not text:
        return text
    
    lines = text.split('\n')
    normalized_lines = []
    
    for line in lines:
        if ': ' in line and not line.startswith('Speaker '):
            parts = line.split(': ', 1)
            if len(parts) == 2 and len(parts[0]) <= 3:  # Vu00e9rifier si c'est un identifiant de speaker court
                normalized_lines.append(f"Speaker {parts[0]}: {parts[1]}")
            else:
                normalized_lines.append(line)
        else:
            normalized_lines.append(line)
    
    return '\n'.join(normalized_lines)

def get_meetings_by_user(db: Session, user_id: str, status: str = None):
    """
    Ru00e9cupu00e9rer toutes les ru00e9unions d'un utilisateur
    """
    try:
        # Construire la requu00eate de base
        query = db.query(Meeting).filter(Meeting.user_id == user_id)
        
        # Ajouter le filtre de statut si spu00e9cifiu00e9
        if status:
            query = query.filter(Meeting.transcript_status == status)
        
        # Trier par date de cru00e9ation (plus ru00e9cent en premier)
        query = query.order_by(Meeting.created_at.desc())
        
        # Exu00e9cuter la requu00eate
        meetings_obj = query.all()
        
        # Convertir les objets SQLAlchemy en dictionnaires
        meetings = []
        for meeting_obj in meetings_obj:
            meeting = {
                "id": meeting_obj.id,
                "user_id": meeting_obj.user_id,
                "title": meeting_obj.title,
                "file_url": meeting_obj.file_url,
                "transcript_status": meeting_obj.transcript_status,
                "created_at": meeting_obj.created_at.isoformat() if meeting_obj.created_at else None,
                "duration_seconds": meeting_obj.duration_seconds,
                "speakers_count": meeting_obj.speakers_count,
                "summary_status": meeting_obj.summary_status
            }
            meetings.append(meeting)
        
        return meetings
    
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des ru00e9unions pour l'utilisateur {user_id}: {str(e)}")
        return []

def update_meeting(db: Session, meeting_id: str, user_id: str, update_data: dict):
    """
    Mettre u00e0 jour une ru00e9union
    """
    try:
        # Ru00e9cupu00e9rer la ru00e9union u00e0 mettre u00e0 jour
        meeting_obj = db.query(Meeting).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.user_id == user_id
            )
        ).first()
        
        if not meeting_obj:
            return None
        
        # Mettre u00e0 jour les champs spu00e9cifiu00e9s
        for key, value in update_data.items():
            if hasattr(meeting_obj, key) and value is not None:
                setattr(meeting_obj, key, value)
        
        # Valider les modifications
        db.commit()
        db.refresh(meeting_obj)
        
        # Convertir l'objet SQLAlchemy en dictionnaire
        meeting = {
            "id": meeting_obj.id,
            "user_id": meeting_obj.user_id,
            "title": meeting_obj.title,
            "file_url": meeting_obj.file_url,
            "transcript_text": meeting_obj.transcript_text,
            "transcript_status": meeting_obj.transcript_status,
            "created_at": meeting_obj.created_at.isoformat() if meeting_obj.created_at else None,
            "duration_seconds": meeting_obj.duration_seconds,
            "speakers_count": meeting_obj.speakers_count,
            "summary_text": meeting_obj.summary_text,
            "summary_status": meeting_obj.summary_status
        }
        
        return meeting
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de la mise u00e0 jour de la ru00e9union {meeting_id}: {str(e)}")
        raise e

def delete_meeting(db: Session, meeting_id: str, user_id: str):
    """
    Supprimer une ru00e9union
    """
    try:
        # Ru00e9cupu00e9rer la ru00e9union u00e0 supprimer
        meeting_obj = db.query(Meeting).filter(
            and_(
                Meeting.id == meeting_id,
                Meeting.user_id == user_id
            )
        ).first()
        
        if not meeting_obj:
            return False
        
        # Supprimer la ru00e9union
        db.delete(meeting_obj)
        db.commit()
        
        return True
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de la suppression de la ru00e9union {meeting_id}: {str(e)}")
        return False

def get_pending_transcriptions(db: Session, max_age_hours=24):
    """
    Ru00e9cupu00e8re les transcriptions en attente qui ne sont pas trop anciennes
    """
    try:
        # Calculer la date limite
        cutoff_date = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Ru00e9cupu00e9rer les ru00e9unions en attente
        meetings_obj = db.query(Meeting).filter(
            and_(
                Meeting.transcript_status == "pending",
                Meeting.created_at >= cutoff_date
            )
        ).all()
        
        # Convertir les objets SQLAlchemy en dictionnaires
        meetings = []
        for meeting_obj in meetings_obj:
            meeting = {
                "id": meeting_obj.id,
                "user_id": meeting_obj.user_id,
                "title": meeting_obj.title,
                "file_url": meeting_obj.file_url,
                "transcript_status": meeting_obj.transcript_status,
                "created_at": meeting_obj.created_at.isoformat() if meeting_obj.created_at else None
            }
            meetings.append(meeting)
        
        return meetings
    
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des transcriptions en attente: {str(e)}")
        return []

def get_meetings_by_status(db: Session, status: str, max_age_hours=72):
    """
    Ru00e9cupu00e8re les ru00e9unions avec un statut spu00e9cifique qui ne sont pas trop anciennes
    """
    try:
        # Calculer la date limite
        cutoff_date = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Ru00e9cupu00e9rer les ru00e9unions avec le statut spu00e9cifiu00e9
        meetings_obj = db.query(Meeting).filter(
            and_(
                Meeting.transcript_status == status,
                Meeting.created_at >= cutoff_date
            )
        ).all()
        
        # Convertir les objets SQLAlchemy en dictionnaires
        meetings = []
        for meeting_obj in meetings_obj:
            meeting = {
                "id": meeting_obj.id,
                "user_id": meeting_obj.user_id,
                "title": meeting_obj.title,
                "file_url": meeting_obj.file_url,
                "transcript_status": meeting_obj.transcript_status,
                "created_at": meeting_obj.created_at.isoformat() if meeting_obj.created_at else None,
                "duration_seconds": meeting_obj.duration_seconds,
                "speakers_count": meeting_obj.speakers_count
            }
            meetings.append(meeting)
        
        return meetings
    
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des ru00e9unions avec le statut {status}: {str(e)}")
        return []
