from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from ..core.config import settings
from ..db.database import get_user_by_email, get_user_by_id
import functools
import psycopg2
import psycopg2.extras
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Cache pour les vérifications de mot de passe récentes (5 minutes)
password_verify_cache = {}

# Fonctions de vérification mot de passe
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using bcrypt with cache optimization"""
    # Log pour débogage
    print(f"Vérification du mot de passe: {plain_password[:2]}*** (longueur: {len(plain_password)})")
    print(f"Hash stocké: {hashed_password[:10]}... (longueur: {len(hashed_password)})")
    
    # Clé de cache (combinaison du mot de passe en clair et du hash)
    cache_key = f"{plain_password}:{hashed_password}"
    current_time = datetime.utcnow()
    
    # Vérifier si la combinaison existe dans le cache et est encore valide
    if cache_key in password_verify_cache:
        timestamp, result = password_verify_cache[cache_key]
        # Valide pour 5 minutes
        if (current_time - timestamp).total_seconds() < 300:
            print(f"Résultat du cache: {result}")
            return result
    
    # Si pas dans le cache ou expiré, vérifier avec bcrypt
    try:
        print(f"Vérification avec bcrypt...")
        result = bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
        print(f"Résultat de la vérification bcrypt: {result}")
        # Stocker dans le cache
        password_verify_cache[cache_key] = (current_time, result)
        return result
    except Exception as e:
        # En cas d'erreur, retourner False par sécurité
        print(f"Erreur lors de la vérification du mot de passe: {str(e)}")
        return False
    
# Purge périodique du cache (cache limité à 100 entrées)
def purge_password_cache():
    """Purge les entrées de cache expirées ou si le cache dépasse 100 entrées"""
    global password_verify_cache
    current_time = datetime.utcnow()
    
    # Conserver uniquement les entrées de moins de 10 minutes
    password_verify_cache = {
        k: v for k, v in password_verify_cache.items() 
        if (current_time - v[0]).total_seconds() < 600
    }
    
    # Si le cache est toujours trop grand, conserver seulement les 50 entrées les plus récentes
    if len(password_verify_cache) > 100:
        sorted_cache = sorted(password_verify_cache.items(), key=lambda x: x[1][0], reverse=True)
        password_verify_cache = dict(sorted_cache[:50])

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Créer un token JWT pour l'authentification"""
    to_encode = data.copy()
    
    # S'assurer que le sujet (sub) est une chaîne de caractères
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
        print(f"ID utilisateur converti en chaîne pour le token JWT: {to_encode['sub']}")
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Valider un token JWT et récupérer l'utilisateur correspondant"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Log du token pour débogage
        print(f"Token reçu: {token[:10]}...")
        
        # Décodage du token
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            print(f"Token décodé avec succès. Payload: {payload}")
        except Exception as e:
            print(f"Erreur lors du décodage du token: {str(e)}")
            raise credentials_exception
            
        user_id = payload.get("sub")
        if user_id is None:
            print("Aucun ID utilisateur (sub) dans le token")
            raise credentials_exception
        
        print(f"ID utilisateur extrait du token: {user_id}, Type: {type(user_id)}")
        
        # Connexion directe à la base de données PostgreSQL pour récupérer l'utilisateur
        conn = None
        user = None
        
        try:
            # Connexion directe à la base de données PostgreSQL avec valeurs codées en dur
            conn = psycopg2.connect(
                dbname='meeting_transcriber',
                user='meeting_transcriber_user',
                password='rlpb7cswwmJ5egbYXW3U1FF78g9kN308',
                host='dpg-d0lfghogjchc73f1mvjg-a.oregon-postgres.render.com',
                port='5432'
            )
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Requête SQL pour récupérer l'utilisateur
            print(f"Exécution de la requête SQL: SELECT id, email, hashed_password, full_name, created_at FROM users WHERE id = {user_id}")
            
            cursor.execute("""
            SELECT id, email, hashed_password, full_name, created_at
            FROM users
            WHERE id = %s
            """, (user_id,))
            
            user_row = cursor.fetchone()
            if user_row:
                user = dict(user_row)
                print(f"Utilisateur trouvé: {user.get('email')}, ID: {user.get('id')}, Type ID: {type(user.get('id'))}")
            else:
                print(f"Aucun utilisateur trouvé avec ID: {user_id}")
        except Exception as e:
            print(f"Erreur lors de la récupération de l'utilisateur: {str(e)}")
            raise credentials_exception
        finally:
            if conn:
                conn.close()
        
        if user is None:
            print(f"Utilisateur avec ID {user_id} non trouvé")
            raise credentials_exception
        
        print(f"Utilisateur trouvé: {user.get('email') if isinstance(user, dict) else 'Non dictionnaire'}")
        
        # Convertir l'objet datetime en chaîne de caractères ISO 8601 pour le champ created_at
        if isinstance(user, dict) and 'created_at' in user and user['created_at'] is not None:
            if not isinstance(user['created_at'], str):
                user['created_at'] = user['created_at'].isoformat()
                print(f"Conversion de created_at en ISO 8601: {user['created_at']}")
        
        return user
        
    except JWTError:
        raise credentials_exception
