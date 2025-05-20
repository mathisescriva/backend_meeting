from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from ..core.config import settings
from ..db.database import get_user_by_email, get_user_by_id
import functools

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Cache pour les vérifications de mot de passe récentes (5 minutes)
password_verify_cache = {}

# Fonctions de vérification mot de passe
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using bcrypt with cache optimization"""
    # Clé de cache (combinaison du mot de passe en clair et du hash)
    cache_key = f"{plain_password}:{hashed_password}"
    current_time = datetime.utcnow()
    
    # Vérifier si la combinaison existe dans le cache et est encore valide
    if cache_key in password_verify_cache:
        timestamp, result = password_verify_cache[cache_key]
        # Valide pour 5 minutes
        if (current_time - timestamp).total_seconds() < 300:
            return result
    
    # Si pas dans le cache ou expiré, vérifier avec bcrypt
    try:
        result = bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
        # Stocker dans le cache
        password_verify_cache[cache_key] = (current_time, result)
        return result
    except Exception:
        # En cas d'erreur, retourner False par sécurité
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
        # Décodage du token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        # Récupération de l'utilisateur
        user = get_user_by_id(user_id)
        if user is None:
            raise credentials_exception
            
        return user
        
    except JWTError:
        raise credentials_exception
