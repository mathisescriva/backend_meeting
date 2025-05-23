import sqlite3
import os
import shutil
from pathlib import Path
import logging
import subprocess
import sys

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Chemins
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
RENDER_DISK_PATH = os.environ.get("RENDER_DISK_PATH", "/data")

# Sur Render, le chemin peut u00eatre diffu00e9rent
POSSIBLE_SOURCE_PATHS = [
    CURRENT_DIR / "app.db",  # Chemin relatif standard
    Path("/opt/render/project/src/app.db"),  # Chemin absolu sur Render
    Path("app.db")  # Fichier dans le ru00e9pertoire courant
]

# Trouver le premier chemin qui existe
SOURCE_DB_PATH = None
for path in POSSIBLE_SOURCE_PATHS:
    if os.path.exists(path):
        SOURCE_DB_PATH = path
        break

TARGET_DB_PATH = Path(RENDER_DISK_PATH) / "app.db"

def migrate_database():
    """Migre la base de données du chemin actuel vers le disque persistant"""
    
    # Vérifier si le répertoire de destination existe
    if not os.path.exists(RENDER_DISK_PATH):
        logging.error(f"Le répertoire de destination {RENDER_DISK_PATH} n'existe pas.")
        logging.info("Cette erreur est normale en local. Sur Render, vérifiez que le disque est correctement monté.")
        return False
        
    # Vérifier si la BDD source existe
    if SOURCE_DB_PATH is None:
        logging.error("Aucune base de données source n'a été trouvée.")
        
        # Vérifier si la base de données cible existe déjà
        if os.path.exists(TARGET_DB_PATH):
            logging.info(f"La base de données cible {TARGET_DB_PATH} existe déjà, aucune migration nécessaire.")
            return True
        else:
            logging.error("Aucune base de données source ou cible n'a été trouvée.")
            return False
    
    # Vérifier si la BDD destination existe déjà
    if os.path.exists(TARGET_DB_PATH):
        logging.warning(f"La base de données cible {TARGET_DB_PATH} existe déjà.")
        backup_path = TARGET_DB_PATH.with_suffix(".db.backup")
        logging.info(f"Création d'une sauvegarde à {backup_path}")
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

def migrate_profile_pictures():
    """Migre les photos de profil vers le disque persistant en appelant le script dédié"""
    try:
        # Chemin du script de migration des photos de profil
        script_path = CURRENT_DIR / "migrate_profile_pictures.py"
        
        if not os.path.exists(script_path):
            logging.error(f"Le script de migration des photos de profil {script_path} n'existe pas.")
            return False
            
        # Exécuter le script de migration des photos de profil
        logging.info(f"Exécution du script de migration des photos de profil: {script_path}")
        result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("Migration des photos de profil réussie!")
            logging.info(result.stdout)
            return True
        else:
            logging.error(f"Erreur lors de la migration des photos de profil: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"Erreur lors de l'exécution du script de migration des photos de profil: {str(e)}")
        return False

if __name__ == "__main__":
    logging.info("Début de la migration des données vers le disque persistant")
    
    # Afficher les chemins pour déboguer
    logging.info(f"Base de données source: {SOURCE_DB_PATH}")
    logging.info(f"Disque persistant Render: {RENDER_DISK_PATH}")
    logging.info(f"Base de données cible: {TARGET_DB_PATH}")
    
    # Migrer la base de données
    db_success = migrate_database()
    if db_success:
        logging.info("Migration de la base de données terminée avec succès")
    else:
        logging.error("La migration de la base de données a échoué")
    
    # Migrer les photos de profil
    pics_success = migrate_profile_pictures()
    if pics_success:
        logging.info("Migration des photos de profil terminée avec succès")
    else:
        logging.error("La migration des photos de profil a échoué")
        
    # Résultat global
    if db_success and pics_success:
        logging.info("Migration complète terminée avec succès")
    else:
        logging.error("La migration complète a échoué")
