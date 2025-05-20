import sqlite3
import os
import sys
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("db-test")

# Chemin vers la base de donnu00e9es
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"

def remove_metadata_column():
    """Supprime la colonne transcript_metadata pour tester la migration automatique"""
    try:
        # Vu00e9rifier si la base de donnu00e9es existe
        if not os.path.exists(DB_PATH):
            logger.error(f"Base de donnu00e9es non trouvu00e9e: {DB_PATH}")
            return False
        
        # Connexion u00e0 la base de donnu00e9es
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Vu00e9rifier si la colonne existe
        cursor.execute("PRAGMA table_info(meetings)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "transcript_metadata" not in column_names:
            logger.info("La colonne transcript_metadata n'existe pas du00e9ju00e0")
            conn.close()
            return True
        
        # En SQLite, on ne peut pas simplement supprimer une colonne
        # Il faut cru00e9er une nouvelle table sans cette colonne, copier les donnu00e9es, puis renommer
        logger.info("Cru00e9ation d'une table temporaire sans la colonne transcript_metadata")
        
        # 1. Obtenir la structure de la table actuelle
        cursor.execute("PRAGMA table_info(meetings)")
        columns = cursor.fetchall()
        
        # 2. Cru00e9er une liste de colonnes sans transcript_metadata
        columns_without_metadata = [col for col in columns if col[1] != "transcript_metadata"]
        column_names_without_metadata = [col[1] for col in columns_without_metadata]
        
        # 3. Cru00e9er une nouvelle table temporaire
        create_temp_table_sql = f"CREATE TABLE meetings_temp ({', '.join([f'{col[1]} {col[2]}' for col in columns_without_metadata])});"
        cursor.execute(create_temp_table_sql)
        
        # 4. Copier les donnu00e9es
        copy_data_sql = f"INSERT INTO meetings_temp SELECT {', '.join(column_names_without_metadata)} FROM meetings;"
        cursor.execute(copy_data_sql)
        
        # 5. Supprimer l'ancienne table
        cursor.execute("DROP TABLE meetings;")
        
        # 6. Renommer la table temporaire
        cursor.execute("ALTER TABLE meetings_temp RENAME TO meetings;")
        
        conn.commit()
        
        # Vu00e9rifier que la colonne a bien u00e9tu00e9 supprimu00e9e
        cursor.execute("PRAGMA table_info(meetings)")
        columns_after = cursor.fetchall()
        column_names_after = [col[1] for col in columns_after]
        
        if "transcript_metadata" not in column_names_after:
            logger.info("Colonne transcript_metadata supprimu00e9e avec succu00e8s")
            conn.close()
            return True
        else:
            logger.error("u00c9chec de la suppression de la colonne transcript_metadata")
            conn.close()
            return False
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la colonne: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("=== TEST DE MIGRATION DE LA BASE DE DONNu00c9ES ===")
    success = remove_metadata_column()
    if success:
        logger.info("Suppression de la colonne terminu00e9e avec succu00e8s")
    else:
        logger.error("u00c9chec de la suppression de la colonne")
    logger.info("=== FIN DU TEST ===")
