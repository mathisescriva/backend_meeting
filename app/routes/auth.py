from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from ..db.database import get_user_by_email_cached, create_user, get_password_hash, purge_old_entries_from_cache, get_user_by_oauth
from ..models.user import UserCreate, User, UserCreateOAuth
from ..core.security import create_access_token, verify_password, get_current_user, purge_password_cache
from ..core.config import settings
from ..services.oauth_state_manager import oauth_state_manager
from pydantic import BaseModel
import httpx
import secrets
import urllib.parse
from typing import Optional
import time
import logging

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Configuration Google OAuth
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleCallbackRequest(BaseModel):
    code: str
    state: str

@router.post("/register", response_model=dict, status_code=201, tags=["Authentication"])
async def register(user_data: UserCreate = Body(..., description="Informations de l'utilisateur à créer")):
    """
    Enregistre un nouvel utilisateur.
    
    - **email**: Adresse email valide
    - **password**: Mot de passe (minimum 8 caractères)
    - **full_name**: Nom complet
    
    Retourne les informations de l'utilisateur créé sans le mot de passe.
    
    Exemple de réponse:
    ```json
    {
      "message": "Utilisateur créé avec succès",
      "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "utilisateur@example.com",
        "full_name": "Nom Complet",
        "created_at": "2024-03-01T14:30:45.123456"
      }
    }
    ```
    """
    try:
        # Vérifier si l'email est déjà utilisé
        existing_user = get_user_by_email_cached(user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
            
        # Créer le nouvel utilisateur
        hashed_password = get_password_hash(user_data.password)
        
        user_dict = {
            "email": user_data.email,
            "hashed_password": hashed_password,
            "full_name": user_data.full_name
        }
        
        new_user = create_user(user_dict)
        
        return {
            "message": "Utilisateur créé avec succès",
            "user": new_user
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=dict, tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authentifie un utilisateur et génère un token JWT.
    
    - **username**: Adresse email
    - **password**: Mot de passe
    
    Retourne un token d'accès JWT avec sa durée de validité.
    
    Exemple de réponse:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "expires_in": 1800
    }
    ```
    
    Utilisez ce token dans l'en-tête d'autorisation pour accéder aux endpoints protégés:
    ```
    Authorization: Bearer {access_token}
    ```
    """
    try:
        # Recherche de l'utilisateur par email
        user = get_user_by_email_cached(form_data.username)
        if not user:
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
            
        # Vérification du mot de passe
        if not verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
            
        # Création du token JWT
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["id"]},  # Utiliser l'ID comme sujet du token
            expires_delta=access_token_expires
        )
        
        # Purger les caches périodiquement pour éviter les fuites mémoire
        purge_old_entries_from_cache()
        purge_password_cache()
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Conversion en secondes
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'authentification: {str(e)}")

@router.post("/login/json", response_model=dict, tags=["Authentication"])
async def login_json(login_data: LoginRequest):
    """
    Authentifie un utilisateur via JSON et génère un token JWT.
    
    - **email**: Adresse email de l'utilisateur
    - **password**: Mot de passe de l'utilisateur
    
    Retourne un token d'accès JWT avec sa durée de validité.
    
    Exemple de requête:
    ```json
    {
      "email": "user@example.com",
      "password": "secure_password"
    }
    ```
    
    Exemple de réponse:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "expires_in": 1800
    }
    ```
    """
    try:
        # Recherche de l'utilisateur par email
        user = get_user_by_email_cached(login_data.email)
        if not user:
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
            
        # Vérification du mot de passe
        if not verify_password(login_data.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
            
        # Création du token JWT
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["id"]},  # Utiliser l'ID comme sujet du token
            expires_delta=access_token_expires
        )
        
        # Purger les caches périodiquement pour éviter les fuites mémoire
        purge_old_entries_from_cache()
        purge_password_cache()
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Conversion en secondes
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'authentification: {str(e)}")

@router.get("/me", response_model=dict, tags=["Authentication"])
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Récupère les informations de l'utilisateur actuellement connecté.
    
    Cette route nécessite un token JWT valide et retourne les informations
    associées à l'utilisateur authentifié.
    
    Exemple de réponse:
    ```json
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "utilisateur@example.com",
      "full_name": "Nom Complet",
      "created_at": "2024-03-01T14:30:45.123456"
    }
    ```
    """
    # Supprimer le mot de passe haché de la réponse
    if "hashed_password" in current_user:
        del current_user["hashed_password"]
    
    return current_user

@router.post("/refresh-token", response_model=dict, tags=["Authentication"])
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Rafraîchit le token JWT de l'utilisateur actuellement connecté.
    
    Cette route permet de prolonger la session de l'utilisateur sans qu'il ait à se reconnecter.
    Elle nécessite un token JWT encore valide et génère un nouveau token avec une durée de validité renouvelée.
    
    Exemple de réponse:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "expires_in": 14400
    }
    ```
    """
    try:
        # Création d'un nouveau token JWT avec une durée de validité renouvelée
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": current_user["id"]},  # Utiliser l'ID comme sujet du token
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Conversion en secondes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du rafraîchissement du token: {str(e)}")

@router.get("/google", tags=["Authentication"])
async def google_auth():
    """
    Initie le processus de connexion Google OAuth.
    
    Génère un état unique et redirige directement vers Google OAuth.
    Cette route remplace l'ancien endpoint /google/login pour un flow plus simple.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Configuration Google OAuth manquante")
    
    # Générer un état unique pour la sécurité via le gestionnaire d'états
    state = oauth_state_manager.generate_state()
    
    # Paramètres OAuth Google
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "response_type": "code",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account"
    }
    
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    
    # Redirection directe vers Google
    return RedirectResponse(url=google_auth_url, status_code=302)

@router.get("/google/callback", tags=["Authentication"])
async def google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """
    Traite le callback de Google OAuth après autorisation.
    
    Google redirige ici avec les paramètres code et state.
    Traite l'authentification complète et redirige vers le frontend avec le token.
    """
    frontend_url = settings.FRONTEND_URL
    
    # Debug logging
    logger = logging.getLogger(__name__)
    logger.info(f"OAuth callback appelé - code: {'présent' if code else 'absent'}, state: {state[:8] if state else 'absent'}, error: {error}")
    
    try:
        # Vérifier s'il y a eu une erreur
        if error:
            logger.info(f"Erreur OAuth reçue: {error}")
            return RedirectResponse(url=f"{frontend_url}?error={error}")
        
        # Vérifier que code et state sont présents
        if not code or not state:
            logger.warning("Code ou state manquant dans le callback OAuth")
            return RedirectResponse(url=f"{frontend_url}?error=missing_params")
        
        # Debug: vérifier les états actifs
        states_count = oauth_state_manager.get_states_count()
        logger.info(f"États OAuth actifs avant validation: {states_count}")
        
        # Vérifier l'état de sécurité via le gestionnaire d'états
        is_valid = oauth_state_manager.validate_state(state)
        logger.info(f"Validation de l'état OAuth {state[:8]}...: {is_valid}")
        
        if not is_valid:
            logger.warning(f"État OAuth invalide: {state[:8]}...")
            return RedirectResponse(url=f"{frontend_url}?error=invalid_state")
        
        logger.info("État OAuth validé avec succès, échange du code contre token...")
        
        # Échanger le code contre un token d'accès
        token_data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GOOGLE_REDIRECT_URI
        }
        
        async with httpx.AsyncClient() as client:
            # Obtenir le token d'accès
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"Échec de l'échange de token: {token_response.status_code}")
                return RedirectResponse(url=f"{frontend_url}?error=token_exchange_failed")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            # Obtenir les informations utilisateur
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                logger.error(f"Échec de récupération des infos utilisateur: {user_response.status_code}")
                return RedirectResponse(url=f"{frontend_url}?error=user_info_failed")
            
            google_user = user_response.json()
        
        logger.info(f"Informations utilisateur Google récupérées pour: {google_user.get('email', 'email_unknown')}")
        
        # Vérifier si l'utilisateur existe déjà par OAuth
        existing_user = get_user_by_oauth("google", google_user["id"])
        
        if existing_user:
            # Utilisateur existant, créer un token JWT
            user = existing_user
            logger.info(f"Utilisateur OAuth existant trouvé: {user.get('email', 'email_unknown')}")
        else:
            # Vérifier si un utilisateur avec cet email existe déjà (compte classique)
            existing_email_user = get_user_by_email_cached(google_user["email"])
            
            if existing_email_user and not existing_email_user.get("oauth_provider"):
                logger.warning(f"Email déjà utilisé avec compte classique: {google_user['email']}")
                return RedirectResponse(url=f"{frontend_url}?error=email_already_exists")
            elif existing_email_user:
                # Utilisateur OAuth existant avec un autre provider
                logger.warning(f"Email déjà utilisé avec autre provider: {google_user['email']}")
                return RedirectResponse(url=f"{frontend_url}?error=email_exists_other_provider")
            
            # Créer un nouveau compte utilisateur
            user_data = {
                "email": google_user["email"],
                "full_name": google_user.get("name", ""),
                "profile_picture_url": google_user.get("picture", ""),
                "oauth_provider": "google",
                "oauth_id": google_user["id"]
            }
            
            user = create_user(user_data)
            logger.info(f"Nouvel utilisateur OAuth créé: {user.get('email', 'email_unknown')}")
        
        # Créer le token JWT
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(
            data={"sub": user["id"]},
            expires_delta=access_token_expires
        )
        
        # Purger les caches
        purge_old_entries_from_cache()
        purge_password_cache()
        
        logger.info(f"Token JWT créé avec succès pour l'utilisateur: {user.get('email', 'email_unknown')}")
        
        # Rediriger vers le frontend avec le token
        return RedirectResponse(url=f"{frontend_url}?token={jwt_token}&success=true", status_code=302)
        
    except Exception as e:
        logger.error(f"Erreur dans le callback OAuth: {str(e)}")
        return RedirectResponse(url=f"{frontend_url}?error=server_error", status_code=302)

@router.get("/google/login", tags=["Authentication"])
async def google_login():
    """
    DEPRECATED: Utilisez /auth/google à la place.
    
    Ancienne méthode qui retournait une URL JSON.
    Maintenant redirige vers la nouvelle méthode pour compatibilité.
    """
    return RedirectResponse(url="/auth/google", status_code=302)
