import os
import sys
import sqlite3
import logging
import threading
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test-summary")

# Chemin de la base de données
db_path = Path(os.path.dirname(__file__)) / "app.db"

def test_summary_generation(meeting_id):
    """
    Teste la génération de résumé pour une réunion spécifique.
    
    Cette fonction simule la fin d'une transcription et déclenche la génération du résumé.
    
    Args:
        meeting_id: ID de la réunion à traiter
    """
    try:
        # Créer une connexion à la base de données
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Vérifier si la réunion existe
        cursor.execute("SELECT id, user_id, transcript_status FROM meetings WHERE id = ?", (meeting_id,))
        meeting = cursor.fetchone()
        
        if not meeting:
            logger.error(f"Réunion {meeting_id} non trouvée")
            return False
        
        meeting_id, user_id, transcript_status = meeting
        
        logger.info(f"Réunion trouvée: {meeting_id}, utilisateur: {user_id}, statut: {transcript_status}")
        
        # Importer les fonctions nécessaires
        sys.path.append(os.path.dirname(__file__))
        from app.services.mistral_summary import process_meeting_summary
        
        # Lancer la génération du résumé
        logger.info(f"Lancement de la génération du résumé pour la réunion {meeting_id}")
        process_meeting_summary(meeting_id, user_id)
        
        # Vérifier le statut du résumé après un court délai
        import time
        time.sleep(2)
        
        cursor.execute("SELECT summary_status FROM meetings WHERE id = ?", (meeting_id,))
        summary_status = cursor.fetchone()[0]
        
        logger.info(f"Statut du résumé après lancement: {summary_status}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors du test de génération du résumé: {str(e)}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Veuillez spécifier l'ID de la réunion en argument")
        sys.exit(1)
    
    meeting_id = sys.argv[1]
    logger.info(f"Test de génération de résumé pour la réunion {meeting_id}")
    
    success = test_summary_generation(meeting_id)
    
    if success:
        logger.info("Test terminé avec succès")
    else:
        logger.error("Le test a échoué")
