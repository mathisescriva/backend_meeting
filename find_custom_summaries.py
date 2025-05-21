#!/usr/bin/env python3
"""
Script pour trouver des utilisateurs avec des modèles de compte rendu différents
"""

import logging
from app.db.database import get_db_connection, release_db_connection

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('summary-finder')

def find_custom_summaries():
    """Trouve des utilisateurs avec des modèles de compte rendu différents"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Trouver tous les clients avec des modèles de compte rendu définis
        cursor.execute("""
            SELECT c.id, c.name, c.user_id, c.summary_template, u.email 
            FROM clients c
            JOIN users u ON c.user_id = u.id
            WHERE c.summary_template IS NOT NULL
            AND c.summary_template <> ''
            ORDER BY c.user_id
        """)
        
        clients = cursor.fetchall()
        
        if not clients:
            logger.info("Aucun client avec modèle de compte rendu personnalisé trouvé")
            return
        
        logger.info(f"Total des clients avec modèle personnalisé: {len(clients)}")
        
        # Afficher les détails de chaque client
        shown_count = 0
        prev_template = None
        for client in clients:
            # Pour avoir 2 modèles différents, on affiche les clients avec des modèles différents
            if prev_template != client['summary_template'] and shown_count < 2:
                logger.info("---------------------------------------")
                logger.info(f"Client ID: {client['id']}")
                logger.info(f"Nom: {client['name']}")
                logger.info(f"Utilisateur ID: {client['user_id']}")
                logger.info(f"Email utilisateur: {client['email']}")
                logger.info(f"Modèle de compte rendu: {client['summary_template'][:100]}..." 
                           if len(client['summary_template']) > 100 
                           else f"Modèle de compte rendu: {client['summary_template']}")
                
                prev_template = client['summary_template']
                shown_count += 1
        
        if shown_count < 2:
            logger.info("Moins de 2 modèles de compte rendu différents trouvés")
            
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    find_custom_summaries()
