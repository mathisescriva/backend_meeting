import os
import sys
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-migration")

# Ajouter le ru00e9pertoire du projet au path pour pouvoir importer les modules
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Importer la fonction de migration
from app.db.migrations import ensure_transcript_metadata_column

def main():
    """Test de la fonction de migration automatique"""
    logger.info("=== TEST DE LA MIGRATION AUTOMATIQUE ===")
    
    # Supprimer la colonne transcript_metadata si elle existe
    from remove_metadata_column import remove_metadata_column
    logger.info("Suppression de la colonne transcript_metadata pour le test")
    remove_metadata_column()
    
    # Exu00e9cuter la fonction de migration
    logger.info("Exu00e9cution de la fonction de migration automatique")
    result = ensure_transcript_metadata_column()
    
    if result:
        logger.info("La migration a ru00e9ussi !")
    else:
        logger.error("La migration a u00e9chouu00e9")
    
    logger.info("=== FIN DU TEST ===")

if __name__ == "__main__":
    main()
