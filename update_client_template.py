#!/usr/bin/env python3
"""
Script pour mettre u00e0 jour le modu00e8le de compte rendu d'un client
"""

import logging
from app.db.database import get_db_connection, release_db_connection

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('template-updater')

# Nouveau modu00e8le de compte rendu pour le client test
NEW_TEMPLATE = """
# Rapport de ru00e9union - {meeting_title}

## Ru00e9sumu00e9 exu00e9cutif

Ce document pru00e9sente une synthu00e8se des points discutu00e9s lors de la ru00e9union.

## u00c9lu00e9ments principaux

1. **Introduction**
   - Contexte et objectifs de la ru00e9union
   - Pru00e9sentation des participants

2. **Analyse des points discutu00e9s**
   - Point 1: [Description]
   - Point 2: [Description]
   - Point 3: [Description]

3. **Du00e9cisions stratu00e9giques**
   - Orientations adoptu00e9es
   - Actions u00e0 entreprendre

4. **Plan d'action**
   - Responsables et du00e9lais
   - Ressources nu00e9cessaires

## Conclusion

Synthu00e8se finale et perspectives.

---

Transcription complu00e8te:

{transcript_text}

---

Gu00e9nu00e9ru00e9 le {date_generated}
"""

def update_client_template(client_id, new_template):
    """Met u00e0 jour le modu00e8le de compte rendu d'un client"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Vu00e9rifier si le client existe
        cursor.execute(
            "SELECT name, user_id FROM clients WHERE id = ?", 
            (client_id,)
        )
        client = cursor.fetchone()
        
        if not client:
            logger.info(f"Aucun client trouvu00e9 avec l'ID {client_id}")
            return False
        
        # Mettre u00e0 jour le modu00e8le de compte rendu
        cursor.execute(
            "UPDATE clients SET summary_template = ? WHERE id = ?",
            (new_template, client_id)
        )
        
        conn.commit()
        
        logger.info(f"Modu00e8le mis u00e0 jour pour le client {client['name']}")
        
        # Afficher le modu00e8le mis u00e0 jour
        cursor.execute(
            "SELECT summary_template FROM clients WHERE id = ?",
            (client_id,)
        )
        updated_client = cursor.fetchone()
        
        return updated_client and updated_client['summary_template'] == new_template
    finally:
        release_db_connection(conn)

def find_client_by_email(email):
    """Trouve un client par l'email de son utilisateur"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.name, c.user_id, c.summary_template, u.email 
            FROM clients c
            JOIN users u ON c.user_id = u.id
            WHERE u.email = ?
        """, (email,))
        
        client = cursor.fetchone()
        
        if not client:
            logger.info(f"Aucun client trouvu00e9 pour l'utilisateur avec l'email {email}")
            return None
        
        logger.info(f"Client trouvu00e9: {client['name']} (ID: {client['id']})")
        return client
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    # Trouver le client test
    client = find_client_by_email("test@example.com")
    
    if client:
        # Mettre u00e0 jour le modu00e8le de compte rendu
        success = update_client_template(client['id'], NEW_TEMPLATE)
        
        if success:
            logger.info("Le modu00e8le de compte rendu a u00e9tu00e9 mis u00e0 jour avec succu00e8s.")
        else:
            logger.error("Erreur lors de la mise u00e0 jour du modu00e8le de compte rendu.")
    else:
        logger.error("Impossible de trouver le client test.")
