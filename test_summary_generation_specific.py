import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001"
LOG_FILE = f"test_logs/summary_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Créer le dossier de logs s'il n'existe pas
import os
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(message, level="INFO"):
    """Écrire un message dans le fichier de log et l'afficher dans la console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{level}] {message}"
    print(formatted_message)
    
    with open(LOG_FILE, "a") as f:
        f.write(formatted_message + "\n")

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
            log("❌ Échec d'authentification", "ERROR")
            return None
    except Exception as e:
        log(f"❌ Erreur lors de l'authentification: {str(e)}", "ERROR")
        return None

def get_meetings(token):
    """Récupérer la liste des réunions"""
    log("\n===== RÉCUPÉRATION DES RÉUNIONS =====")
    
    url = f"{BASE_URL}/simple/meetings/"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Nombre de réunions: {len(response_data)}")
        
        # Trouver les réunions avec transcription complète
        completed_meetings = [m for m in response_data if m.get("transcript_status") == "completed"]
        log(f"Nombre de réunions avec transcription complète: {len(completed_meetings)}")
        
        if completed_meetings:
            # Afficher quelques détails sur la première réunion complète
            meeting = completed_meetings[0]
            log(f"Détails de la première réunion complète:")
            log(f"  ID: {meeting['id']}")
            log(f"  Titre: {meeting['title']}")
            log(f"  Statut de transcription: {meeting['transcript_status']}")
            log(f"  Statut de résumé: {meeting.get('summary_status', 'non disponible')}")
            log(f"  Durée: {meeting.get('duration_seconds', 'non disponible')} secondes")
        
        return completed_meetings
    except Exception as e:
        log(f"❌ Erreur lors de la récupération des réunions: {str(e)}", "ERROR")
        return []

def generate_summary(token, meeting_id):
    """Générer un compte rendu pour une réunion"""
    log(f"\n===== GÉNÉRATION DU COMPTE RENDU (Meeting ID: {meeting_id}) =====")
    
    url = f"{BASE_URL}/meetings/{meeting_id}/generate-summary"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        
        log(f"Status code: {response.status_code}")
        
        try:
            response_data = response.json()
            log(f"Response: {json.dumps(response_data, indent=2)}")
            
            if response.status_code == 200:
                log("✅ Demande de génération de compte rendu réussie")
                return response_data
            else:
                log("❌ Échec de la demande de génération de compte rendu", "ERROR")
                return None
        except Exception as e:
            log(f"❌ Erreur lors du parsing de la réponse: {str(e)}", "ERROR")
            log(f"Réponse brute: {response.text}")
            return None
    except Exception as e:
        log(f"❌ Erreur lors de la génération du compte rendu: {str(e)}", "ERROR")
        return None

def check_summary_status(token, meeting_id, max_checks=20, interval=30):
    """Vérifier le statut du compte rendu d'une réunion"""
    log(f"\n===== SUIVI DU STATUT DU COMPTE RENDU (Meeting ID: {meeting_id}) =====")
    
    url = f"{BASE_URL}/meetings/{meeting_id}/summary"
    headers = {"Authorization": f"Bearer {token}"}
    
    for i in range(max_checks):
        try:
            log(f"Vérification {i+1}/{max_checks}...")
            response = requests.get(url, headers=headers, timeout=10)
            
            log(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                log(f"Response: {json.dumps(response_data, indent=2)}")
                
                status = response_data.get("summary_status")
                log(f"Statut actuel: {status}")
                
                if status in ["completed", "error"]:
                    log(f"Statut final: {status}")
                    return status, response_data
                
                if i < max_checks - 1:
                    log(f"Attente de {interval} secondes avant la prochaine vérification...")
                    time.sleep(interval)
            else:
                log(f"Erreur lors de la vérification du statut: {response.status_code}", "ERROR")
                if i < max_checks - 1:
                    log(f"Attente de {interval} secondes avant la prochaine vérification...")
                    time.sleep(interval)
        except Exception as e:
            log(f"❌ Erreur lors de la vérification du statut: {str(e)}", "ERROR")
            if i < max_checks - 1:
                log(f"Attente de {interval} secondes avant la prochaine vérification...")
                time.sleep(interval)
    
    log("Nombre maximum de vérifications atteint sans statut final", "WARNING")
    return "timeout", None

def main():
    # Démarrer le test
    log(f"\n{'='*50}")
    log(f"DÉBUT DU TEST DE GÉNÉRATION DE COMPTE RENDU - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*50}\n")
    
    # Se connecter
    token = login()
    if not token:
        log("Impossible de continuer sans token d'authentification", "ERROR")
        return
    
    # Récupérer les réunions avec transcription complète
    completed_meetings = get_meetings(token)
    if not completed_meetings:
        log("Aucune réunion avec transcription complète trouvée", "ERROR")
        return
    
    # Choisir la première réunion complète pour générer un compte rendu
    meeting = completed_meetings[0]
    meeting_id = meeting["id"]
    
    # Vérifier si un compte rendu existe déjà
    if meeting.get("summary_status") == "completed":
        log(f"Un compte rendu existe déjà pour cette réunion (ID: {meeting_id})")
        log("Vérification du compte rendu existant...")
        status, summary_data = check_summary_status(token, meeting_id, max_checks=1)
        
        if summary_data and summary_data.get("summary_text"):
            log("\n===== COMPTE RENDU EXISTANT =====")
            log(f"Texte du compte rendu:\n{summary_data['summary_text']}")
            return
    
    # Générer un nouveau compte rendu
    generation_result = generate_summary(token, meeting_id)
    if not generation_result:
        log("Échec de la demande de génération de compte rendu", "ERROR")
        return
    
    # Vérifier le statut du compte rendu
    status, summary_data = check_summary_status(token, meeting_id)
    
    # Afficher le résultat final
    log(f"\n{'='*50}")
    log(f"RÉSULTAT FINAL:")
    log(f"  Réunion ID: {meeting_id}")
    log(f"  Titre: {meeting['title']}")
    log(f"  Statut final du compte rendu: {status}")
    
    if status == "completed" and summary_data and summary_data.get("summary_text"):
        log("\n===== COMPTE RENDU GÉNÉRÉ =====")
        log(f"Texte du compte rendu:\n{summary_data['summary_text']}")
    elif status == "error":
        log("❌ Erreur lors de la génération du compte rendu", "ERROR")
    elif status == "timeout":
        log("⚠️ Timeout lors de la génération du compte rendu", "WARNING")
    
    log(f"{'='*50}\n")
    log(f"Rapport détaillé: {LOG_FILE}")

if __name__ == "__main__":
    main()
