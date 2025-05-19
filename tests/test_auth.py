import os
import psycopg2
import psycopg2.extras
import bcrypt
from dotenv import load_dotenv
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test-auth')

# Charger les variables d'environnement
os.environ['ENVIRONMENT'] = 'production'
load_dotenv('.env.local.postgres')

# Afficher les variables d'environnement pour du00e9bogage
logger.info(f"POSTGRES_DB: {os.environ.get('POSTGRES_DB')}")
logger.info(f"POSTGRES_USER: {os.environ.get('POSTGRES_USER')}")
logger.info(f"POSTGRES_SERVER: {os.environ.get('POSTGRES_SERVER')}")
logger.info(f"POSTGRES_PORT: {os.environ.get('POSTGRES_PORT')}")

def get_user_by_email(email):
    """Ru00e9cupu00e9rer un utilisateur par son email depuis PostgreSQL"""
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

def verify_password(plain_password, hashed_password):
    """Vu00e9rifier un mot de passe avec bcrypt"""
    try:
        # Log pour du00e9bogage
        logger.info(f"Vu00e9rification du mot de passe pour l'utilisateur")
        
        # Vu00e9rifier le mot de passe avec bcrypt
        result = bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
        logger.info(f"Ru00e9sultat de la vu00e9rification du mot de passe: {result}")
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la vu00e9rification du mot de passe: {str(e)}")
        return False

# Tester l'authentification avec l'email admin@example.com et le mot de passe password123
email = 'admin@example.com'
password = 'password123'

# Ru00e9cupu00e9rer l'utilisateur
user = get_user_by_email(email)
if user:
    # Vu00e9rifier le mot de passe
    is_valid = verify_password(password, user['hashed_password'])
    print(f"Authentification pour {email}: {is_valid}")
else:
    print(f"Utilisateur {email} non trouvu00e9")
