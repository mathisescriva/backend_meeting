import sys
import logging
from pathlib import Path
import re

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix-transcript-format")

# Assurez-vous que le chemin du projet est dans sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.db.database import get_db_connection, release_db_connection
from app.db.queries import normalize_transcript_format

def format_raw_text(text):
    """
    Formate un texte brut en ajoutant le préfixe "Speaker A: " s'il n'a aucun format de locuteur.
    """
    # Si le texte a déjà un format avec des locuteurs (A:, B:, etc.), on le normalise
    if any(re.match(r'^[A-Z0-9]+:', line.strip()) for line in text.split('\n')):
        return normalize_transcript_format(text)
    
    # Si le texte contient déjà "Speaker", on le normalise
    if "Speaker " in text:
        return normalize_transcript_format(text)
    
    # Sinon, on ajoute le préfixe "Speaker A: "
    return f"Speaker A: {text}"

def fix_transcript_formats():
    """
    Corrige le format des transcriptions existantes dans la base de données.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Récupérer toutes les réunions avec une transcription
        logger.info("Récupération des réunions avec transcription...")
        cursor.execute(
            "SELECT id, user_id, transcript_text FROM meetings WHERE transcript_text IS NOT NULL AND transcript_text != '' AND transcript_status = 'completed'"
        )
        meetings = cursor.fetchall()
        
        logger.info(f"Nombre de réunions à traiter: {len(meetings)}")
        
        # Traiter chaque réunion
        fixed_count = 0
        for meeting in meetings:
            meeting_id = meeting['id']
            user_id = meeting['user_id']
            text = meeting['transcript_text']
            
            # Appliquer la normalisation et le formatage
            formatted_text = format_raw_text(text)
            
            # Si le texte a été modifié, mettre à jour la base de données
            if formatted_text != text:
                logger.info(f"Correction du format pour la réunion {meeting_id}...")
                cursor.execute(
                    "UPDATE meetings SET transcript_text = ? WHERE id = ? AND user_id = ?",
                    (formatted_text, meeting_id, user_id)
                )
                fixed_count += 1
        
        # Valider les modifications
        conn.commit()
        logger.info(f"Formatage terminé. {fixed_count} réunions mises à jour sur {len(meetings)}.")
        
        # Vérifier les réunions sans préfixe "Speaker"
        cursor.execute(
            "SELECT COUNT(*) FROM meetings WHERE transcript_text IS NOT NULL AND transcript_text != '' AND transcript_status = 'completed' AND transcript_text NOT LIKE '%Speaker %'"
        )
        count_without_prefix = cursor.fetchone()[0]
        logger.info(f"Réunions sans préfixe 'Speaker' après correction: {count_without_prefix}")

    except Exception as e:
        logger.error(f"Erreur lors de la correction du format: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    logger.info("=== DÉBUT DE LA CORRECTION DU FORMAT DES TRANSCRIPTIONS ===")
    fix_transcript_formats()
    logger.info("=== FIN DE LA CORRECTION ===")
