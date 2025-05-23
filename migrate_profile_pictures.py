#!/usr/bin/env python

"""
Script pour migrer les photos de profil du chemin local vers le disque persistant de Render.

Ce script identifie les photos de profil stocku00e9es localement et les copie vers le disque persistant
de Render, en maintenant la mu00eame structure de ru00e9pertoires.
"""

import os
import shutil
from pathlib import Path
import logging
import sqlite3

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Chemins
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
LOCAL_UPLOADS_DIR = CURRENT_DIR / "uploads"
LOCAL_PROFILE_PICTURES_DIR = LOCAL_UPLOADS_DIR / "profile_pictures"
RENDER_DISK_PATH = os.environ.get("RENDER_DISK_PATH", "/data")
RENDER_UPLOADS_DIR = Path(RENDER_DISK_PATH) / "uploads"
RENDER_PROFILE_PICTURES_DIR = RENDER_UPLOADS_DIR / "profile_pictures"

# Base de donnu00e9es
LOCAL_DB_PATH = CURRENT_DIR / "app.db"
RENDER_DB_PATH = Path(RENDER_DISK_PATH) / "app.db"

def migrate_profile_pictures():
    """
    Migre les photos de profil du chemin local vers le disque persistant de Render.
    """
    # Vu00e9rifier si le ru00e9pertoire de destination existe
    if not os.path.exists(RENDER_DISK_PATH):
        logging.error(f"Le ru00e9pertoire de destination {RENDER_DISK_PATH} n'existe pas.")
        logging.info("Cette erreur est normale en local. Sur Render, vu00e9rifiez que le disque est correctement montu00e9.")
        return False
    
    # Vu00e9rifier si le ru00e9pertoire source existe
    if not os.path.exists(LOCAL_PROFILE_PICTURES_DIR):
        logging.warning(f"Le ru00e9pertoire source {LOCAL_PROFILE_PICTURES_DIR} n'existe pas.")
        logging.info("Aucune photo de profil u00e0 migrer.")
        return True
    
    # Cru00e9er les ru00e9pertoires de destination s'ils n'existent pas
    os.makedirs(RENDER_UPLOADS_DIR, exist_ok=True)
    os.makedirs(RENDER_PROFILE_PICTURES_DIR, exist_ok=True)
    
    # Compter les fichiers u00e0 migrer
    total_files = 0
    for root, _, files in os.walk(LOCAL_PROFILE_PICTURES_DIR):
        total_files += len(files)
    
    if total_files == 0:
        logging.info("Aucun fichier u00e0 migrer.")
        return True
    
    logging.info(f"Migration de {total_files} photos de profil...")
    
    # Copier les fichiers
    migrated_files = 0
    for root, _, files in os.walk(LOCAL_PROFILE_PICTURES_DIR):
        # Cru00e9er le chemin relatif
        rel_path = os.path.relpath(root, LOCAL_PROFILE_PICTURES_DIR)
        target_dir = RENDER_PROFILE_PICTURES_DIR / rel_path
        os.makedirs(target_dir, exist_ok=True)
        
        # Copier chaque fichier
        for file in files:
            source_file = os.path.join(root, file)
            target_file = os.path.join(target_dir, file)
            
            try:
                shutil.copy2(source_file, target_file)
                logging.info(f"Copiu00e9: {source_file} -> {target_file}")
                migrated_files += 1
            except Exception as e:
                logging.error(f"Erreur lors de la copie de {source_file}: {str(e)}")
    
    logging.info(f"Migration terminu00e9e. {migrated_files}/{total_files} fichiers migru00e9s.")
    return True

def update_profile_picture_urls():
    """
    Met u00e0 jour les URLs des photos de profil dans la base de donnu00e9es sur le disque persistant.
    """
    # Vu00e9rifier si la base de donnu00e9es cible existe
    if not os.path.exists(RENDER_DB_PATH):
        logging.error(f"La base de donnu00e9es cible {RENDER_DB_PATH} n'existe pas.")
        return False
    
    try:
        # Se connecter u00e0 la base de donnu00e9es
        conn = sqlite3.connect(str(RENDER_DB_PATH))
        cursor = conn.cursor()
        
        # Vu00e9rifier si des utilisateurs ont des photos de profil
        cursor.execute("SELECT COUNT(*) FROM users WHERE profile_picture_url IS NOT NULL")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logging.info("Aucun utilisateur avec photo de profil u00e0 mettre u00e0 jour.")
            conn.close()
            return True
        
        logging.info(f"Mise u00e0 jour des URLs de photos de profil pour {count} utilisateurs...")
        
        # Aucune modification n'est nu00e9cessaire car les chemins relatifs restent les mu00eames
        # Les photos sont stocku00e9es avec des chemins relatifs comme "/uploads/profile_pictures/user_id/filename.jpg"
        # Ces chemins sont toujours valides mu00eame si le ru00e9pertoire physique change
        
        logging.info("Les URLs des photos de profil sont du00e9ju00e0 au bon format (chemins relatifs).")
        conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de la mise u00e0 jour des URLs: {str(e)}")
        return False

if __name__ == "__main__":
    logging.info("Du00e9but de la migration des photos de profil vers le disque persistant")
    
    # Afficher les chemins pour du00e9boguer
    logging.info(f"Ru00e9pertoire source: {LOCAL_PROFILE_PICTURES_DIR}")
    logging.info(f"Disque persistant Render: {RENDER_DISK_PATH}")
    logging.info(f"Ru00e9pertoire cible: {RENDER_PROFILE_PICTURES_DIR}")
    
    if migrate_profile_pictures():
        logging.info("Migration des fichiers terminu00e9e avec succu00e8s")
        
        if update_profile_picture_urls():
            logging.info("Mise u00e0 jour des URLs terminu00e9e avec succu00e8s")
        else:
            logging.error("La mise u00e0 jour des URLs a u00e9chouu00e9")
    else:
        logging.error("La migration des fichiers a u00e9chouu00e9")
