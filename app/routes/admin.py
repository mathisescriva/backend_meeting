from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
import logging
import subprocess
import sys
import os
from pathlib import Path

from ..core.security import get_current_user

# Configuration du logging
logger = logging.getLogger("meeting-transcriber")

router = APIRouter(prefix="/admin", tags=["Administration"])

@router.post("/update-summaries", response_model=dict)
async def update_stuck_summaries(current_user: dict = Depends(get_current_user)):
    """
    Exécute le script de mise à jour des comptes rendus bloqués.
    
    Cette route est temporaire et permet de débloquer les comptes rendus qui sont
    restés en statut 'processing' trop longtemps.
    """
    try:
        # Vérifier que l'utilisateur a les droits d'administration
        # Pour simplifier, on autorise tous les utilisateurs pour l'instant
        
        logger.info(f"Exécution du script de mise à jour des comptes rendus par l'utilisateur {current_user['id']}")
        
        # Chemin du script
        script_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "update_summary_status.py"
        
        if not os.path.exists(script_path):
            logger.error(f"Script non trouvé: {script_path}")
            return JSONResponse(
                status_code=404,
                content={"message": "Script de mise à jour non trouvé", "success": False}
            )
        
        # Exécuter le script en arrière-plan
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Attendre un peu pour voir si le script démarre correctement
        try:
            stdout, stderr = process.communicate(timeout=2)
            if process.returncode != 0:
                logger.error(f"Erreur lors du démarrage du script: {stderr}")
                return JSONResponse(
                    status_code=500,
                    content={"message": f"Erreur lors du démarrage du script: {stderr}", "success": False}
                )
        except subprocess.TimeoutExpired:
            # C'est normal, le script continue de s'exécuter
            logger.info("Script démarré en arrière-plan")
        
        return {
            "message": "Mise à jour des comptes rendus démarrée en arrière-plan",
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du script de mise à jour: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": f"Une erreur s'est produite: {str(e)}", "success": False}
        )
