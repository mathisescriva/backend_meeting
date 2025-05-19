import psycopg2
import psycopg2.extras
import os
import bcrypt
import logging
from datetime import datetime
from ..core.config import settings

# Configuration du logging
logger = logging.getLogger("postgres_adapter")

def get_db_connection():
    """Obtenir une connexion à la base de données PostgreSQL"""
    try:
        # Connexion à PostgreSQL
        conn = psycopg2.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            dbname=settings.POSTGRES_DB
        )
        logger.info("Connexion PostgreSQL établie avec succès")
        return conn
    except Exception as e:
        logger.error(f"Erreur lors de la connexion à PostgreSQL: {str(e)}")
        raise
        
def release_db_connection(conn):
    """Libérer une connexion PostgreSQL"""
    if conn:
        try:
            conn.close()
            logger.info("Connexion PostgreSQL fermée")
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture de la connexion PostgreSQL: {str(e)}")
            
def reset_db_pool():
    """Fonction de compatibilité avec le reste du code"""
    # PostgreSQL n'utilise pas de pool de connexions dans cette implémentation
    # mais nous gardons cette fonction pour la compatibilité
    return True

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def create_user(user_data):
    """Créer un nouvel utilisateur dans PostgreSQL"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Insérer l'utilisateur dans la base de données
        cursor.execute("""
        INSERT INTO users (email, hashed_password, full_name, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id, email, full_name, created_at
        """, (
            user_data["email"],
            user_data["hashed_password"],
            user_data.get("full_name"),
            datetime.utcnow()
        ))
        
        # Récupérer l'utilisateur créé
        user = cursor.fetchone()
        conn.commit()
        
        # Convertir en dictionnaire
        user_dict = dict(user)
        return user_dict
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Erreur lors de la création de l'utilisateur: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_user_by_email(email):
    """Récupérer un utilisateur par son email depuis PostgreSQL"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
        SELECT id, email, hashed_password, full_name, created_at
        FROM users
        WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        if user:
            # Convertir en dictionnaire
            return dict(user)
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'utilisateur par email: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_by_id(user_id):
    """Récupérer un utilisateur par son ID depuis PostgreSQL"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
        SELECT id, email, hashed_password, full_name, created_at
        FROM users
        WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        if user:
            # Convertir en dictionnaire
            return dict(user)
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'utilisateur par ID: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

# Cache utilisateur (pour limiter les requêtes à la base de données)
user_cache = {}

# Fonctions avec cache pour les utilisateurs
def get_user_by_email_cached(email, max_age_seconds=60):
    """Version mise en cache de get_user_by_email"""
    cache_key = f"email:{email}"
    current_time = datetime.utcnow().timestamp()
    
    # Vérifier si l'utilisateur est dans le cache et si le cache est encore valide
    if cache_key in user_cache:
        timestamp, user = user_cache[cache_key]
        if current_time - timestamp < max_age_seconds:
            return user
    
    # Si pas dans le cache ou expiré, récupérer depuis la base de données
    user = get_user_by_email(email)
    
    # Mettre à jour le cache
    if user:
        user_cache[cache_key] = (current_time, user)
    
    return user

def get_user_by_id_cached(user_id, max_age_seconds=300):
    """Version mise en cache de get_user_by_id"""
    cache_key = f"id:{user_id}"
    current_time = datetime.utcnow().timestamp()
    
    # Vérifier si l'utilisateur est dans le cache et si le cache est encore valide
    if cache_key in user_cache:
        timestamp, user = user_cache[cache_key]
        if current_time - timestamp < max_age_seconds:
            return user
    
    # Si pas dans le cache ou expiré, récupérer depuis la base de données
    user = get_user_by_id(user_id)
    
    # Mettre à jour le cache
    if user:
        user_cache[cache_key] = (current_time, user)
    
    return user

def clear_user_cache():
    """Vider le cache utilisateur"""
    global user_cache
    user_cache = {}

def purge_old_entries_from_cache(max_age_seconds=600):
    """Purger les entrées de cache trop anciennes"""
    global user_cache
    current_time = datetime.utcnow().timestamp()
    
    # Supprimer les entrées trop anciennes
    user_cache = {
        k: v for k, v in user_cache.items() 
        if current_time - v[0] < max_age_seconds
    }
