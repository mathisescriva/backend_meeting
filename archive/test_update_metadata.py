#!/usr/bin/env python3
"""
Script pour tester la mise à jour des métadonnées d'une réunion
"""

import sys
import logging
from app.db.queries import update_meeting, get_meeting

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('metadata-updater')

def update_meeting_metadata(meeting_id, user_id="1"):
    """Met à jour les métadonnées d'une réunion existante"""
    logger.info(f"Mise à jour des métadonnées pour la réunion {meeting_id}")
    
    # Vérifier que la réunion existe
    meeting = get_meeting(meeting_id, user_id)
    if not meeting:
        logger.error(f"Réunion non trouvée: {meeting_id}")
        return False
    
    # Mettre à jour avec des valeurs de test
    update_data = {
        "duration_seconds": 42,  # Une durée de test
        "speakers_count": 2,     # Un nombre de locuteurs de test
    }
    
    success = update_meeting(meeting_id, user_id, update_data)
    
    if success:
        logger.info(f"Métadonnées mises à jour avec succès: {update_data}")
        
        # Vérifier si les métadonnées ont été correctement enregistrées
        updated_meeting = get_meeting(meeting_id, user_id)
        
        if updated_meeting:
            if updated_meeting.get('duration_seconds') == 42:
                logger.info("✅ La durée a été correctement mise à jour")
            else:
                logger.error(f"❌ La durée n'a pas été mise à jour correctement. Valeur: {updated_meeting.get('duration_seconds')}")
                
            if updated_meeting.get('speakers_count') == 2:
                logger.info("✅ Le nombre de locuteurs a été correctement mis à jour")
            else:
                logger.error(f"❌ Le nombre de locuteurs n'a pas été mis à jour correctement. Valeur: {updated_meeting.get('speakers_count')}")
    else:
        logger.error("Échec de la mise à jour des métadonnées")
    
    return success

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_update_metadata.py <meeting_id> [user_id]")
        sys.exit(1)
    
    meeting_id = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else "ed5b605f-6882-444f-b7b6-a92441b3a2cb"  # Utilisateur par défaut
    
    update_meeting_metadata(meeting_id, user_id)

if __name__ == "__main__":
    main()
