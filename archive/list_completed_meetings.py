from app.db.queries import get_meetings_by_status
import logging
import json
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('meeting-lister')

# Charger les variables d'environnement
load_dotenv()

def list_completed_meetings():
    """Liste toutes les ru00e9unions complu00e9tu00e9es"""
    try:
        # Ru00e9cupu00e9rer toutes les ru00e9unions complu00e9tu00e9es
        completed_meetings = get_meetings_by_status('completed')
        logger.info(f"Ru00e9unions complu00e9tu00e9es: {len(completed_meetings)}")
        
        if not completed_meetings:
            logger.info("Aucune ru00e9union complu00e9tu00e9e trouvu00e9e")
            return
        
        # Afficher les informations de chaque ru00e9union
        for i, meeting in enumerate(completed_meetings, 1):
            logger.info(f"Ru00e9union {i}:")
            logger.info(f"  ID: {meeting.get('id')}")
            logger.info(f"  Utilisateur: {meeting.get('user_id')}")
            logger.info(f"  Titre: {meeting.get('title')}")
            logger.info(f"  Fichier: {meeting.get('file_url')}")
            logger.info(f"  Statut: {meeting.get('transcript_status')}")
            logger.info(f"  Cru00e9u00e9e le: {meeting.get('created_at')}")
            
            # Afficher un extrait du texte de transcription
            transcript_text = meeting.get('transcript_text', '')
            if transcript_text:
                # Limiter l'affichage u00e0 100 caractu00e8res
                preview = transcript_text[:100] + '...' if len(transcript_text) > 100 else transcript_text
                logger.info(f"  Texte: {preview}")
            else:
                logger.info("  Texte: [Vide]")
            
            logger.info("---")
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des ru00e9unions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Liste des ru00e9unions complu00e9tu00e9es:")
    list_completed_meetings()
