from supabase.client import Client, create_client, ClientOptions
from ..core.config import settings
from typing import Dict, Any
import json
from fastapi.logger import logger
import traceback
import httpx

# Initialize the Supabase client
supabase: Client = create_client(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_KEY
)

# Ensure the audio bucket exists
try:
    # Create the bucket if it doesn't exist
    try:
        supabase.storage.create_bucket("audio", {"public": True})
        logger.info("Created 'audio' bucket")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            logger.info("Audio bucket already exists")
        else:
            # Bucket might already exist
            logger.error(f"Error creating bucket: {str(e)}")
except Exception as e:
    logger.error(f"Error managing storage bucket: {str(e)}")

def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crée un nouvel utilisateur en utilisant l'API REST Supabase.
    """
    try:
        # Création de l'utilisateur via l'API REST
        url = f"{settings.SUPABASE_URL}/auth/v1/admin/users"
        headers = {
            "apikey": settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        user_payload = {
            "email": user_data["email"],
            "password": user_data["hashed_password"],
            "email_confirm": True,
            "user_metadata": {
                "full_name": user_data.get("full_name", "")
            }
        }
        
        response = httpx.post(url, headers=headers, json=user_payload)
        if response.status_code >= 400:
            raise Exception(f"API Error: {response.text}")
            
        user = response.json()
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user.get("user_metadata", {}).get("full_name", ""),
            "created_at": user["created_at"]
        }
            
    except Exception as e:
        raise Exception(f"Error creating user: {str(e)}")

def get_user_by_email(email: str) -> Dict[str, Any]:
    """
    Récupère un utilisateur par son email.
    """
    try:
        url = f"{settings.SUPABASE_URL}/auth/v1/admin/users"
        headers = {
            "apikey": settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_KEY}"
        }
        
        response = httpx.get(url, headers=headers)
        if response.status_code >= 400:
            logger.error(f"API Error: {response.text}")
            return None
            
        users = response.json()
        for user in users:
            if user.get("email") == email:
                return {
                    "id": user["id"],
                    "email": user["email"],
                    "full_name": user.get("user_metadata", {}).get("full_name", ""),
                    "created_at": user["created_at"]
                }
        return None
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return None
