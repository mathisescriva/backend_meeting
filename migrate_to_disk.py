import sqlite3
import os
import shutil
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Chemins
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DB_PATH = CURRENT_DIR / "app.db"
RENDER_DISK_PATH = os.environ.get("RENDER_DISK_PATH", "/data")
TARGET_DB_PATH = Path(RENDER_DISK_PATH) / "app.db"

def migrate_database():
    """Migre la base de donnu00e9es du chemin actuel vers le disque persistant"""
    
    # Vu00e9rifier si le ru00e9pertoire de destination existe
    if not os.path.exists(RENDER_DISK_PATH):
        logging.error(f"Le ru00e9pertoire de destination {RENDER_DISK_PATH} n'existe pas.")
        logging.info("Cette erreur est normale en local. Sur Render, vu00e9rifiez que le disque est correctement montu00e9.")
        return False
        
    # Vu00e9rifier si la BDD source existe
    if not os.path.exists(SOURCE_DB_PATH):
        logging.error(f"La base de donnu00e9es source {SOURCE_DB_PATH} n'existe pas.")
        return False
    
    # Vu00e9rifier si la BDD destination existe du00e9ju00e0
    if os.path.exists(TARGET_DB_PATH):
        logging.warning(f"La base de donnu00e9es cible {TARGET_DB_PATH} existe du00e9ju00e0.")
        backup_path = TARGET_DB_PATH.with_suffix(".db.backup")
        logging.info(f"Cru00e9ation d'une sauvegarde u00e0 {backup_path}")
        shutil.copy2(TARGET_DB_PATH, backup_path)
    
    try:
        # Copier la base de donnu00e9es vers le disque persistant
        logging.info(f"Copie de {SOURCE_DB_PATH} vers {TARGET_DB_PATH}")
        shutil.copy2(SOURCE_DB_PATH, TARGET_DB_PATH)
        
        # Vu00e9rifier que la nouvelle base de donnu00e9es est accessible
        conn = sqlite3.connect(str(TARGET_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logging.info(f"Tables dans la nouvelle base de donnu00e9es: {[t[0] for t in tables]}")
        conn.close()
        
        logging.info("Migration ru00e9ussie!")
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de la migration: {str(e)}")
        return False

if __name__ == "__main__":
    logging.info("Du00e9but de la migration de la base de donnu00e9es vers le disque persistant")
    
    # Afficher les chemins pour du00e9boguer
    logging.info(f"Base de donnu00e9es source: {SOURCE_DB_PATH}")
    logging.info(f"Disque persistant Render: {RENDER_DISK_PATH}")
    logging.info(f"Base de donnu00e9es cible: {TARGET_DB_PATH}")
    
    if migrate_database():
        logging.info("Migration terminu00e9e avec succu00e8s")
    else:
        logging.error("La migration a u00e9chouu00e9")
