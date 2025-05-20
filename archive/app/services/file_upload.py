import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
import shutil
import logging
import mimetypes

# Configurer le logging
logger = logging.getLogger("file_upload")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Obtenir le chemin de base du projet
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Dossier des uploads
UPLOADS_DIR = BASE_DIR / "uploads"
PROFILE_PICTURES_DIR = UPLOADS_DIR / "profile_pictures"

# S'assurer que les dossiers d'upload existent
os.makedirs(PROFILE_PICTURES_DIR, exist_ok=True)

def validate_image_file(file: UploadFile):
    """
    Valide que le fichier est bien une image
    """
    # Liste des types MIME autorisés
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    # Vérifier l'extension du fichier
    content_type = file.content_type
    
    if not content_type or content_type not in allowed_types:
        # Essayer de deviner le type à partir de l'extension
        filename = file.filename
        guessed_type, _ = mimetypes.guess_type(filename)
        
        if not guessed_type or guessed_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail="Le fichier doit être une image (formats acceptés: JPEG, PNG, GIF, WEBP)"
            )
    
    # Vérifier la taille du fichier (max 5MB)
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)  # Remettre le curseur au début
    
    max_size = 5 * 1024 * 1024  # 5MB
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"L'image est trop volumineuse ({file_size} bytes). Taille maximum: 5MB"
        )
    
    return True

async def save_profile_picture(file: UploadFile, user_id: str) -> str:
    """
    Sauvegarde une image de profil pour un utilisateur et retourne l'URL relative
    """
    # Valider le fichier
    validate_image_file(file)
    
    # Créer un dossier spécifique pour l'utilisateur
    user_upload_dir = PROFILE_PICTURES_DIR / user_id
    os.makedirs(user_upload_dir, exist_ok=True)
    
    # Générer un nom de fichier unique
    timestamp = uuid.uuid4().hex[:8]
    extension = os.path.splitext(file.filename)[1]
    new_filename = f"profile_{timestamp}{extension}"
    
    # Chemin complet du fichier
    file_path = user_upload_dir / new_filename
    
    # Enregistrer le fichier
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # URL relative pour stockage en base de données
        relative_path = f"/uploads/profile_pictures/{user_id}/{new_filename}"
        
        logger.info(f"Image de profil enregistrée: {relative_path}")
        return relative_path
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de l'image de profil: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'enregistrement de l'image de profil"
        )

def delete_profile_picture(file_url: str):
    """
    Supprime une image de profil existante
    """
    if not file_url or not file_url.startswith("/uploads/profile_pictures/"):
        return False
    
    # Construire le chemin complet
    file_path = BASE_DIR / file_url.lstrip("/")
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Image de profil supprimée: {file_url}")
            return True
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'image de profil: {str(e)}")
        return False
