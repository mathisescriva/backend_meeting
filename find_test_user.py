#!/usr/bin/env python3
"""
Script pour retrouver les informations d'un utilisateur test
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
            SELECT id, email, hashed_password, full_name, created_at
            FROM users
            WHERE email = ?
        """, (email,))
        
        user = cursor.fetchone()
        
        if not user:
            logger.info(f"Aucun utilisateur trouvu00e9 avec l'email {email}")
            return
        
        logger.info("Informations de l'utilisateur:")
        logger.info(f"ID: {user['id']}")
        logger.info(f"Email: {user['email']}")
        logger.info(f"Mot de passe hashu00e9: {user['hashed_password']}")
        logger.info(f"Nom complet: {user['full_name']}")
        logger.info(f"Cru00e9u00e9 le: {user['created_at']}")
        
        # Pour les utilisateurs de test, cherchons les mots de passe connus
        if email == 'test@example.com':
            logger.info("\nCompte de test du00e9tectu00e9 - vu00e9rification des mots de passe communs:")
            common_passwords = ["password", "test123", "testuser", "password123", "12345678"]
            
            # Note: Dans un environnement de production, on ne recommanderait pas cette approche
            # C'est uniquement pour un compte de test dans un environnement de du00e9veloppement
            if user['hashed_password'] == "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW":
                logger.info("Mot de passe du00e9tectu00e9: 'password'")
            elif user['hashed_password'].startswith("$2b$"):
                logger.info("Le mot de passe est hashu00e9 avec bcrypt.")
                logger.info("Mot de passe par du00e9faut probable: 'password' ou 'testuser'")
            
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    find_user_info("test@example.com")
