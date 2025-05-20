import requests
import json
import time
import os
import sys
from datetime import datetime
import logging

# Configuration
BASE_URL = "http://localhost:8001"
TEST_USER = "test@example.com"
TEST_PASSWORD = "password123"

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"logs/health_check_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("health_check")

# Créer le dossier de logs si nécessaire
os.makedirs("logs", exist_ok=True)

def check_auth():
    """Vérifie l'authentification"""
    url = f"{BASE_URL}/auth/login"
    data = {"username": TEST_USER, "password": TEST_PASSWORD}
    
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        
        if "access_token" in response_data:
            logger.info("✅ Authentification réussie")
            return response_data["access_token"]
        else:
            logger.error("❌ Échec de l'authentification: Token non trouvé dans la réponse")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erreur lors de l'authentification: {str(e)}")
        return None

def check_meetings(token):
    """Vérifie la récupération des réunions"""
    url = f"{BASE_URL}/meetings"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        
        logger.info(f"✅ Récupération des réunions réussie. Nombre de réunions: {len(response_data)}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erreur lors de la récupération des réunions: {str(e)}")
        return False

def check_transcription_service():
    """Vérifie que le service de transcription est fonctionnel"""
    token = check_auth()
    if not token:
        return False
    
    # Vérifier les réunions existantes
    if not check_meetings(token):
        return False
    
    logger.info("✅ Service de transcription fonctionnel")
    return True

def check_mistral_api():
    """Vérifie que l'API Mistral est accessible"""
    # Récupérer la clé API Mistral depuis les variables d'environnement
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_api_key:
        logger.error("❌ Clé API Mistral non trouvée dans les variables d'environnement")
        return False
    
    # Effectuer une requête simple à l'API Mistral
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {mistral_api_key}"
    }
    payload = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": "Bonjour"}],
        "temperature": 0.3,
        "max_tokens": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("✅ API Mistral accessible")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erreur lors de l'accès à l'API Mistral: {str(e)}")
        return False

def run_health_check():
    """Exécute toutes les vérifications de santé"""
    logger.info("=== DÉBUT DE LA VÉRIFICATION DE SANTÉ ===")
    
    # Vérifier que le serveur est en cours d'exécution
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        logger.info(f"✅ Serveur en cours d'exécution (status: {response.status_code})")
    except requests.exceptions.RequestException:
        logger.error("❌ Le serveur n'est pas accessible")
        return False
    
    # Vérifier l'authentification et les services
    transcription_ok = check_transcription_service()
    mistral_ok = check_mistral_api()
    
    # Résumé des vérifications
    logger.info("=== RÉSUMÉ DE LA VÉRIFICATION DE SANTÉ ===")
    logger.info(f"Service de transcription: {'✅ OK' if transcription_ok else '❌ NOK'}")
    logger.info(f"API Mistral: {'✅ OK' if mistral_ok else '❌ NOK'}")
    
    # Résultat global
    all_ok = transcription_ok and mistral_ok
    logger.info(f"Résultat global: {'✅ SYSTÈME EN BONNE SANTÉ' if all_ok else '❌ PROBLÈMES DÉTECTÉS'}")
    
    return all_ok

def main():
    """Fonction principale"""
    success = run_health_check()
    
    # Code de sortie pour l'intégration avec des scripts
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
