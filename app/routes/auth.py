from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
from ..db.database import get_user_by_email, create_user, get_password_hash
from ..models.user import UserCreate, User
from ..core.config import settings
from ..core.security import verify_password, create_access_token

router = APIRouter()

@router.post("/register", response_model=dict, status_code=201, tags=["Authentication"])
async def register(user_data: UserCreate = Body(..., description="Informations de l'utilisateur à créer")):
    """
    Enregistre un nouvel utilisateur.
    
    - **email**: Adresse email valide
    - **password**: Mot de passe (minimum 8 caractères)
    - **full_name**: Nom complet
    
    Retourne les informations de l'utilisateur créé sans le mot de passe.
    """
    try:
        # Vérifier si l'email existe déjà
        existing_user = get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
        
        # Hashage du mot de passe
        hashed_password = get_password_hash(user_data.password)
        
        # Préparation des données utilisateur
        user_dict = {
            "email": user_data.email,
            "hashed_password": hashed_password,
            "full_name": user_data.full_name
        }
        
        # Création de l'utilisateur dans la base de données
        new_user = create_user(user_dict)
        return {"message": "Utilisateur créé avec succès", "user": new_user}
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
        user = get_user_by_email(form_data.username)
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
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Conversion en secondes
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

@router.get("/me", response_model=dict, tags=["Authentication"])
async def get_current_user_info(current_user: dict = Depends(verify_password)):
    """
    Récupère les informations de l'utilisateur actuellement connecté.
    
    Cette route nécessite un token JWT valide et retourne les informations
    associées à l'utilisateur authentifié.
    """
    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"]
    }
