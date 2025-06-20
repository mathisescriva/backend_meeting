#!/usr/bin/env python3
"""
Script pour retrouver les informations d'un utilisateur
"""

import logging
from app.db.database import get_db_connection, release_db_connection

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('user-finder')

def find_user_info(email):
    """Retrouve les informations d'un utilisateur par son email"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Rechercher l'utilisateur par email
        cursor.execute("""
            SELECT id, email, password_hash, is_active, created_at, role
            FROM users
            WHERE email = ?
        """, (email,))
        
        user = cursor.fetchone()
        
        if not user:
            logger.info(f"Aucun utilisateur trouvé avec l'email {email}")
            return
        
        logger.info("Informations de l'utilisateur:")
        logger.info(f"ID: {user['id']}")
        logger.info(f"Email: {user['email']}")
        logger.info(f"Hash du mot de passe: {user['password_hash']}")
        logger.info(f"Compte actif: {user['is_active']}")
        logger.info(f"Créé le: {user['created_at']}")
        logger.info(f"Rôle: {user['role']}")
        
        # Vérifier si un compte test a un mot de passe standard
        if user['email'] == 'test@example.com':
            logger.info("Compte de test détecté - le mot de passe par défaut est probablement 'password123'")
            
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    find_user_info("test@example.com")
