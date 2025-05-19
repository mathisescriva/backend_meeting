from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
from ..db.database import get_user_by_email_cached, create_user, get_password_hash, purge_old_entries_from_cache
from ..models.user import UserCreate, User
from ..core.security import create_access_token, verify_password, get_current_user, purge_password_cache
from ..core.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

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
        # Log pour débogage
        print(f"Tentative de connexion pour l'email: {login_data.email}")
        
        # Connexion directe à la base de données PostgreSQL pour récupérer l'utilisateur
        import psycopg2
        import psycopg2.extras
        import os
        
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
            print(f"Exécution de la requête SQL: SELECT id, email, hashed_password, full_name, created_at FROM users WHERE email = '{login_data.email}'")
            
            cursor.execute("""
            SELECT id, email, hashed_password, full_name, created_at
            FROM users
            WHERE email = %s
            """, (login_data.email,))
            
            user_row = cursor.fetchone()
            if user_row:
                user = dict(user_row)
                print(f"Utilisateur trouvé: {user.get('email')}, ID: {user.get('id')}, Type ID: {type(user.get('id'))}")
            else:
                print(f"Aucun utilisateur trouvé avec email: {login_data.email}")
        except Exception as e:
            print(f"Erreur lors de la récupération de l'utilisateur: {str(e)}")
        finally:
            if conn:
                conn.close()
        
        if not user:
            print(f"Utilisateur non trouvé pour l'email: {login_data.email}")
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
            
        # Vérification du mot de passe
        password_valid = verify_password(login_data.password, user["hashed_password"])
        print(f"Résultat de la vérification du mot de passe: {password_valid}")
        
        if not password_valid:
            print(f"Mot de passe incorrect pour l'utilisateur: {login_data.email}")
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
            
        # Création du token JWT
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        print(f"Création du token JWT avec ID utilisateur: {user['id']}, Type: {type(user['id'])}")
        
        access_token = create_access_token(
            data={"sub": user["id"]},  # Utiliser l'ID comme sujet du token
            expires_delta=access_token_expires
        )
        
        print(f"Token JWT créé avec succès: {access_token[:10]}...")
        
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
