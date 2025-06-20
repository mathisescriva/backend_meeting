#!/usr/bin/env python3
"""
Script pour vu00e9rifier la structure de la table 'users'
"""

import logging
from app.db.database import get_db_connection, release_db_connection

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('table-checker')

def check_table_structure(table_name):
    """Vu00e9rifie la structure d'une table dans la base de donnu00e9es"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Obtenir les informations sur les colonnes de la table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        if not columns:
            logger.info(f"La table {table_name} n'existe pas ou est vide")
            return
        
        logger.info(f"Structure de la table {table_name}:")
        for col in columns:
            logger.info(f"Colonne: {col['name']}, Type: {col['type']}")
            
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    check_table_structure("users")
