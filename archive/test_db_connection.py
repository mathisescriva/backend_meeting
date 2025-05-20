import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test-db-connection')

# Charger les variables d'environnement
os.environ['ENVIRONMENT'] = 'production'
load_dotenv('.env.local.postgres')

# Afficher les variables d'environnement pour du00e9bogage
logger.info(f"POSTGRES_DB: {os.environ.get('POSTGRES_DB')}")
logger.info(f"POSTGRES_USER: {os.environ.get('POSTGRES_USER')}")
logger.info(f"POSTGRES_SERVER: {os.environ.get('POSTGRES_SERVER')}")
logger.info(f"POSTGRES_PORT: {os.environ.get('POSTGRES_PORT')}")

def test_get_user_by_email(email):
    """Tester la ru00e9cupu00e9ration d'un utilisateur par email"""
    conn = None
    try:
        # Log pour du00e9bogage
        logger.info(f"Recherche de l'utilisateur avec email: {email}")
        
        # Connexion directe u00e0 la base de donnu00e9es PostgreSQL
        conn = psycopg2.connect(
            dbname=os.environ.get('POSTGRES_DB'),
            user=os.environ.get('POSTGRES_USER'),
            password=os.environ.get('POSTGRES_PASSWORD'),
            host=os.environ.get('POSTGRES_SERVER'),
            port=os.environ.get('POSTGRES_PORT')
        )
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Log de la requu00eate SQL
        logger.info(f"Exu00e9cution de la requu00eate SQL: SELECT id, email, hashed_password, full_name, created_at FROM users WHERE email = '{email}'")
        
        cursor.execute("""
        SELECT id, email, hashed_password, full_name, created_at
        FROM users
        WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        if user:
            # Convertir en dictionnaire
            user_dict = dict(user)
            logger.info(f"Utilisateur trouvu00e9 avec email {email}: ID={user_dict.get('id')}, Type ID={type(user_dict.get('id'))}")
            return user_dict
        
        logger.info(f"Aucun utilisateur trouvu00e9 avec email: {email}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration de l'utilisateur par email: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

# Tester la fonction avec l'email admin@example.com
user = test_get_user_by_email('admin@example.com')
print(f"Ru00e9sultat: {user}")

# Tester la fonction avec un email qui n'existe pas
user = test_get_user_by_email('nonexistent@example.com')
print(f"Ru00e9sultat: {user}")
