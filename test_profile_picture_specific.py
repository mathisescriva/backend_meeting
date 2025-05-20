import requests
import os
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001"
TEST_IMAGE_PATH = "/Users/mathisescriva/CascadeProjects/MeetingTranscriberBackend/logo_gilbert.png"

def log(message):
    """Afficher un message dans la console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def login():
    """Se connecter à l'API et récupérer un token"""
    log("\n===== AUTHENTIFICATION =====")
    
    url = f"{BASE_URL}/auth/login/json"
    data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        if response.status_code == 200 and "access_token" in response_data:
            log("✅ Authentification réussie")
            return response_data["access_token"]
        else:
            log("❌ Échec d'authentification")
            return None
    except Exception as e:
        log(f"❌ Erreur lors de l'authentification: {str(e)}")
        return None

def get_profile(token):
    """Récupérer le profil utilisateur"""
    log("\n===== RÉCUPÉRATION DU PROFIL =====")
    
    url = f"{BASE_URL}/profile/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        if response.status_code == 200:
            log("✅ Récupération du profil réussie")
            return response_data
        else:
            log("❌ Échec de récupération du profil")
            return None
    except Exception as e:
        log(f"❌ Erreur lors de la récupération du profil: {str(e)}")
        return None

def upload_profile_picture(token, image_path):
    """Uploader une photo de profil spécifique"""
    log(f"\n===== UPLOAD DE LA PHOTO DE PROFIL: {os.path.basename(image_path)} =====")
    log(f"Chemin de l'image: {image_path}")
    
    if not os.path.exists(image_path):
        log(f"❌ Image non trouvée: {image_path}")
        return None
    
    # Afficher la taille de l'image
    file_size = os.path.getsize(image_path) / 1024  # en KB
    log(f"Taille de l'image: {file_size:.2f} KB")
    
    url = f"{BASE_URL}/profile/upload-picture"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "image/png")}
            log("Début de l'upload...")
            response = requests.post(url, files=files, headers=headers, timeout=30)
        
        log(f"Status code: {response.status_code}")
        
        try:
            response_data = response.json()
            log(f"Response: {json.dumps(response_data, indent=2)}")
            
            if response.status_code == 200 and "profile_picture_url" in response_data:
                log("✅ Upload de la photo de profil réussi")
                log(f"URL de la photo: {response_data['profile_picture_url']}")
                return response_data
            else:
                log("❌ Échec de l'upload de la photo de profil")
                return None
        except Exception as e:
            log(f"❌ Erreur lors du parsing de la réponse: {str(e)}")
            log(f"Réponse brute: {response.text}")
            return None
    except Exception as e:
        log(f"❌ Erreur lors de l'upload: {str(e)}")
        return None

def main():
    # Vérifier que l'image existe
    if not os.path.exists(TEST_IMAGE_PATH):
        log(f"❌ Image non trouvée: {TEST_IMAGE_PATH}")
        return
    
    # Se connecter
    token = login()
    if not token:
        log("Impossible de continuer sans token d'authentification")
        return
    
    # Récupérer le profil avant upload
    profile_before = get_profile(token)
    
    # Uploader la photo de profil
    upload_result = upload_profile_picture(token, TEST_IMAGE_PATH)
    
    # Récupérer le profil après upload pour confirmer le changement
    if upload_result:
        profile_after = get_profile(token)
        
        if profile_after and profile_after.get("profile_picture_url") != profile_before.get("profile_picture_url"):
            log("\n✅ Confirmation: La photo de profil a bien été mise à jour")
            log(f"Ancienne URL: {profile_before.get('profile_picture_url')}")
            log(f"Nouvelle URL: {profile_after.get('profile_picture_url')}")
        else:
            log("\n❌ La photo de profil ne semble pas avoir été mise à jour correctement")

if __name__ == "__main__":
    main()
