#!/usr/bin/env python3
"""
Script pour ru00e9cupu00e9rer le contenu des modu00e8les de compte rendu personnalisu00e9s
"""

import logging
from app.db.database import get_db_connection, release_db_connection

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('template-viewer')

def get_summary_template(client_id):
    """Ru00e9cupu00e8re le modu00e8le de compte rendu d'un client"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Ru00e9cupu00e9rer le client et son modu00e8le
        cursor.execute("""
            SELECT c.id, c.name, c.user_id, c.summary_template, u.email 
            FROM clients c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = ?
        """, (client_id,))
        
        client = cursor.fetchone()
        
        if not client:
            logger.info(f"Aucun client trouvu00e9 avec l'ID {client_id}")
            return
        
        logger.info(f"\n=== Modu00e8le de compte rendu pour le client {client['name']} ({client['email']}) ===\n")
        logger.info(client['summary_template'])
        logger.info("\n" + "=" * 80 + "\n")
        
    finally:
        release_db_connection(conn)

def list_all_clients_with_templates():
    """Liste tous les clients avec modu00e8les personnalisu00e9s"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Ru00e9cupu00e9rer tous les clients avec des modu00e8les
        cursor.execute("""
            SELECT c.id, c.name, c.user_id, u.email 
            FROM clients c
            JOIN users u ON c.user_id = u.id
            WHERE c.summary_template IS NOT NULL
            AND c.summary_template <> ''
            ORDER BY c.name
        """)
        
        clients = cursor.fetchall()
        
        if not clients:
            logger.info("Aucun client avec modu00e8le personnalisu00e9 trouvu00e9")
            return
        
        logger.info(f"Clients avec modu00e8les personnalisu00e9s ({len(clients)}):\n")
        
        for i, client in enumerate(clients, 1):
            logger.info(f"{i}. {client['name']} - {client['email']} (ID: {client['id']})")
            
            # Afficher le modu00e8le complet pour chaque client
            get_summary_template(client['id'])
            
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    logger.info("Ru00e9cupu00e9ration des modu00e8les de compte rendu personnalisu00e9s\n")
    list_all_clients_with_templates()
