"""
Module pour gérer le stockage de fichiers.
Remplace l'ancienne implémentation Firebase/Supabase par un stockage local.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from ..core.config import settings
from fastapi.logger import logger

def get_uploads_dir(user_id: str = None):
    """
    Renvoie le chemin du répertoire de uploads pour un utilisateur donné.
    Crée le répertoire s'il n'existe pas.
    """
    uploads_dir = settings.UPLOADS_DIR
    
    if user_id:
        user_dir = uploads_dir / user_id
    else:
        user_dir = uploads_dir
        
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def upload_mp3(file_path: str, user_id: str):
    """
    Upload un fichier MP3 vers le stockage local.
    
    Args:
        file_path: Chemin vers le fichier temporaire
        user_id: ID de l'utilisateur
        
    Returns:
        str: URL relative du fichier uploadé
    """
    # Création d'un nom de fichier unique
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(file_path)
    new_filename = f"{timestamp}_{filename}"
    
    # Chemin du répertoire utilisateur
    user_dir = get_uploads_dir(user_id)
    
    # Chemin complet pour le nouveau fichier
    target_path = user_dir / new_filename
    
    # Copier le fichier
    try:
        shutil.copy2(file_path, target_path)
        logger.info(f"Fichier uploadé avec succès: {target_path}")
    except Exception as e:
        logger.error(f"Erreur lors de l'upload du fichier: {str(e)}")
        raise e
    
    # Renvoyer l'URL relative (sans le chemin absolu)
    relative_path = f"/uploads/{user_id}/{new_filename}"
    logger.info(f"URL relative du fichier: {relative_path}")
    logger.info(f"Chemin absolu du fichier: {target_path}")
    
    return relative_path
