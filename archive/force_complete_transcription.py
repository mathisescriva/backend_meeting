from app.db.queries import get_meetings_by_status, update_meeting, get_meeting
from dotenv import load_dotenv
import os
import logging
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('transcription-force-complete')

# Charger les variables d'environnement
load_dotenv()

def force_complete_transcription(meeting_id, user_id):
    """Force la mise u00e0 jour d'une transcription en la marquant comme complu00e9tu00e9e"""
    try:
        # Ru00e9cupu00e9rer les informations de la ru00e9union
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Ru00e9union {meeting_id} non trouvu00e9e")
            return False
        
        logger.info(f"Statut actuel de la ru00e9union {meeting_id}: {meeting.get('transcript_status')}")
        
        # Demander confirmation
        confirm = input(f"Voulez-vous forcer la complu00e9tion de la transcription {meeting_id} ? (o/n) ")
        if confirm.lower() != 'o':
            logger.info("Opu00e9ration annulu00e9e")
            return False
        
        # Mettre u00e0 jour la base de donnu00e9es
        update_meeting(meeting_id, user_id, {
            "transcript_status": "completed",
            "transcript_text": "Cette transcription a u00e9tu00e9 marquu00e9e comme complu00e9tu00e9e manuellement."
        })
        
        # Vu00e9rifier que la mise u00e0 jour a fonctionnu00e9
        updated_meeting = get_meeting(meeting_id, user_id)
        logger.info(f"Nouveau statut de la ru00e9union {meeting_id}: {updated_meeting.get('transcript_status')}")
        
        return updated_meeting.get('transcript_status') == "completed"
    except Exception as e:
        logger.error(f"Erreur lors de la mise u00e0 jour forcu00e9e: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def list_processing_meetings():
    """Liste toutes les ru00e9unions en cours de traitement"""
    try:
        # Ru00e9cupu00e9rer toutes les transcriptions en cours
        processing_meetings = get_meetings_by_status('processing')
        logger.info(f"Transcriptions en cours: {len(processing_meetings)}")
        
        if not processing_meetings:
            logger.info("Aucune transcription en cours trouvu00e9e")
            return
        
        # Afficher les informations de chaque ru00e9union
        for i, meeting in enumerate(processing_meetings, 1):
            logger.info(f"Ru00e9union {i}:")
            logger.info(f"  ID: {meeting.get('id')}")
            logger.info(f"  Utilisateur: {meeting.get('user_id')}")
            logger.info(f"  Titre: {meeting.get('title')}")
            logger.info(f"  Fichier: {meeting.get('file_url')}")
            logger.info(f"  Statut: {meeting.get('transcript_status')}")
            logger.info(f"  Cru00e9u00e9e le: {meeting.get('created_at')}")
            logger.info("---")
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des ru00e9unions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Lister toutes les ru00e9unions en cours
        logger.info("Liste des ru00e9unions en cours de traitement:")
        list_processing_meetings()
    elif len(sys.argv) == 3:
        # Forcer la complu00e9tion d'une ru00e9union spu00e9cifique
        meeting_id = sys.argv[1]
        user_id = sys.argv[2]
        logger.info(f"Tentative de complu00e9tion forcu00e9e de la ru00e9union {meeting_id} pour l'utilisateur {user_id}")
        if force_complete_transcription(meeting_id, user_id):
            logger.info("Complu00e9tion forcu00e9e ru00e9ussie")
        else:
            logger.error("Complu00e9tion forcu00e9e u00e9chouu00e9e")
    else:
        logger.error("Usage: python force_complete_transcription.py [meeting_id user_id]")
        logger.error("  Sans arguments: liste toutes les ru00e9unions en cours")
        logger.error("  Avec meeting_id et user_id: force la complu00e9tion de la ru00e9union spu00e9cifiu00e9e")
