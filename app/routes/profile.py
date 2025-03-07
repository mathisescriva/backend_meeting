from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from fastapi.security import OAuth2PasswordBearer
from ..core.security import get_current_user, verify_password
from ..db.database import get_user_by_id, update_user, get_password_hash
from ..models.user import User, UserUpdate, UserPasswordUpdate
from ..services.file_upload import save_profile_picture, delete_profile_picture
from typing import Optional
import logging

# Configurer le logging
logger = logging.getLogger("profile")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("/me", response_model=User)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """
    Récupère le profil de l'utilisateur actuellement connecté.
    
    Retourne les informations complètes sur l'utilisateur.
    
    Exemple de réponse:
    ```json
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "utilisateur@example.com",
      "full_name": "Nom Complet",
      "profile_picture_url": "/uploads/profile_pictures/550e8400-e29b-41d4-a716-446655440000/profile_123456.jpg",
      "created_at": "2024-03-01T14:30:45.123456"
    }
    ```
    """
    # L'utilisateur est déjà récupéré par la dépendance get_current_user
    return current_user

@router.put("/update", response_model=User)
async def update_profile(
    user_data: UserUpdate = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Met à jour les informations du profil utilisateur.
    
    - **full_name**: Nouveau nom complet (optionnel)
    - **email**: Nouvelle adresse email (optionnel)
    
    Retourne les informations mises à jour sur l'utilisateur.
    
    Exemple de requête:
    ```json
    {
      "full_name": "Nouveau Nom",
      "email": "nouvel.email@example.com"
    }
    ```
    """
    user_id = current_user["id"]
    update_fields = {}
    
    # Ne mettre à jour que les champs qui sont fournis
    if user_data.full_name is not None:
        update_fields["full_name"] = user_data.full_name
    
    if user_data.email is not None:
        update_fields["email"] = user_data.email
    
    # Si l'URL de la photo de profil est fournie, la mettre à jour
    if user_data.profile_picture_url is not None:
        update_fields["profile_picture_url"] = user_data.profile_picture_url
    
    # Si aucun champ n'est fourni, ne rien faire
    if not update_fields:
        return current_user
    
    # Mettre à jour l'utilisateur en base
    updated_user = update_user(user_id, update_fields)
    
    if not updated_user:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la mise à jour du profil"
        )
    
    return updated_user

@router.post("/upload-picture", response_model=User)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Télécharge et met à jour la photo de profil de l'utilisateur.
    
    Le fichier doit être une image (JPEG, PNG, GIF, WEBP) de taille inférieure à 5MB.
    
    Retourne les informations mises à jour sur l'utilisateur, incluant l'URL de la nouvelle photo de profil.
    """
    user_id = current_user["id"]
    
    try:
        # Supprimer l'ancienne photo si elle existe
        if current_user.get("profile_picture_url"):
            delete_profile_picture(current_user["profile_picture_url"])
        
        # Sauvegarder la nouvelle photo
        profile_picture_url = await save_profile_picture(file, user_id)
        
        # Mettre à jour l'utilisateur
        updated_user = update_user(user_id, {"profile_picture_url": profile_picture_url})
        
        if not updated_user:
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de la mise à jour de la photo de profil"
            )
        
        return updated_user
        
    except HTTPException as e:
        # Propager l'exception si c'est une HTTPException
        raise e
    except Exception as e:
        logger.error(f"Erreur lors de l'upload de la photo de profil: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'upload de la photo de profil"
        )

@router.put("/change-password", response_model=dict)
async def change_password(
    password_data: UserPasswordUpdate = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Change le mot de passe de l'utilisateur.
    
    - **current_password**: Mot de passe actuel
    - **new_password**: Nouveau mot de passe
    
    Vérifie que le mot de passe actuel est correct avant de mettre à jour.
    
    Exemple de requête:
    ```json
    {
      "current_password": "ancien_mot_de_passe",
      "new_password": "nouveau_mot_de_passe"
    }
    ```
    
    Exemple de réponse:
    ```json
    {
      "message": "Mot de passe mis à jour avec succès"
    }
    ```
    """
    user_id = current_user["id"]
    
    # Vérifier le mot de passe actuel
    if not verify_password(password_data.current_password, current_user["hashed_password"]):
        raise HTTPException(
            status_code=400,
            detail="Le mot de passe actuel est incorrect"
        )
    
    # Hasher le nouveau mot de passe
    hashed_password = get_password_hash(password_data.new_password)
    
    # Mettre à jour le mot de passe
    updated_user = update_user(user_id, {"hashed_password": hashed_password})
    
    if not updated_user:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la mise à jour du mot de passe"
        )
    
    return {"message": "Mot de passe mis à jour avec succès"}
