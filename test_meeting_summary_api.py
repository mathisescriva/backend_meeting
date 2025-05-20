import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001"
LOG_FILE = f"test_logs/summary_api_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Cru00e9er le dossier de logs s'il n'existe pas
import os
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(message, level="INFO"):
    """u00c9crire un message dans le fichier de log et l'afficher dans la console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{level}] {message}"
    print(formatted_message)
    
    with open(LOG_FILE, "a") as f:
        f.write(formatted_message + "\n")

def login():
    """Se connecter u00e0 l'API et ru00e9cupu00e9rer un token"""
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
            log("u2705 Authentification ru00e9ussie")
            return response_data["access_token"]
        else:
            log("u274c u00c9chec d'authentification", "ERROR")
            return None
    except Exception as e:
        log(f"u274c Erreur lors de l'authentification: {str(e)}", "ERROR")
        return None

def get_meetings(token):
    """Ru00e9cupu00e9rer la liste des ru00e9unions"""
    log("\n===== Ru00c9CUPu00c9RATION DES Ru00c9UNIONS =====")
    
    url = f"{BASE_URL}/simple/meetings/"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Nombre de ru00e9unions: {len(response_data)}")
        
        # Trouver les ru00e9unions avec transcription complu00e8te
        completed_meetings = [m for m in response_data if m.get("transcript_status") == "completed"]
        log(f"Nombre de ru00e9unions avec transcription complu00e8te: {len(completed_meetings)}")
        
        if completed_meetings:
            # Afficher quelques du00e9tails sur la premiu00e8re ru00e9union complu00e8te
            meeting = completed_meetings[0]
            log(f"Du00e9tails de la premiu00e8re ru00e9union complu00e8te:")
            log(f"  ID: {meeting['id']}")
            log(f"  Titre: {meeting['title']}")
            log(f"  Statut de transcription: {meeting['transcript_status']}")
            log(f"  Statut de ru00e9sumu00e9: {meeting.get('summary_status', 'non disponible')}")
            log(f"  Duru00e9e: {meeting.get('duration_seconds', 'non disponible')} secondes")
        
        return completed_meetings
    except Exception as e:
        log(f"u274c Erreur lors de la ru00e9cupu00e9ration des ru00e9unions: {str(e)}", "ERROR")
        return []

def generate_summary(token, meeting_id):
    """Gu00e9nu00e9rer un compte rendu pour une ru00e9union"""
    log(f"\n===== Gu00c9Nu00c9RATION DU COMPTE RENDU (Meeting ID: {meeting_id}) =====")
    
    url = f"{BASE_URL}/meetings/{meeting_id}/generate-summary"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        
        log(f"Status code: {response.status_code}")
        
        try:
            response_data = response.json()
            log(f"Response: {json.dumps(response_data, indent=2)}")
            
            if response.status_code == 200:
                log("u2705 Demande de gu00e9nu00e9ration de compte rendu ru00e9ussie")
                return response_data
            else:
                log("u274c u00c9chec de la demande de gu00e9nu00e9ration de compte rendu", "ERROR")
                return None
        except Exception as e:
            log(f"u274c Erreur lors du parsing de la ru00e9ponse: {str(e)}", "ERROR")
            log(f"Ru00e9ponse brute: {response.text}")
            return None
    except Exception as e:
        log(f"u274c Erreur lors de la gu00e9nu00e9ration du compte rendu: {str(e)}", "ERROR")
        return None

def check_summary_status(token, meeting_id, max_checks=20, interval=5):
    """Vu00e9rifier le statut du compte rendu d'une ru00e9union"""
    log(f"\n===== SUIVI DU STATUT DU COMPTE RENDU (Meeting ID: {meeting_id}) =====")
    
    url = f"{BASE_URL}/meetings/{meeting_id}/summary"
    headers = {"Authorization": f"Bearer {token}"}
    
    for i in range(max_checks):
        try:
            log(f"Vu00e9rification {i+1}/{max_checks}...")
            response = requests.get(url, headers=headers, timeout=10)
            
            log(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                status = response_data.get("summary_status")
                log(f"Statut actuel: {status}")
                
                if status in ["completed", "error"]:
                    log(f"Statut final: {status}")
                    return status, response_data
                
                if i < max_checks - 1:
                    log(f"Attente de {interval} secondes avant la prochaine vu00e9rification...")
                    time.sleep(interval)
            else:
                log(f"Erreur lors de la vu00e9rification du statut: {response.status_code}", "ERROR")
                if i < max_checks - 1:
                    log(f"Attente de {interval} secondes avant la prochaine vu00e9rification...")
                    time.sleep(interval)
        except Exception as e:
            log(f"u274c Erreur lors de la vu00e9rification du statut: {str(e)}", "ERROR")
            if i < max_checks - 1:
                log(f"Attente de {interval} secondes avant la prochaine vu00e9rification...")
                time.sleep(interval)
    
    log("Nombre maximum de vu00e9rifications atteint sans statut final", "WARNING")
    return "timeout", None

def main():
    # Du00e9marrer le test
    log(f"\n{'='*50}")
    log(f"Du00c9BUT DU TEST DE Gu00c9Nu00c9RATION DE COMPTE RENDU VIA L'API - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*50}\n")
    
    # Se connecter
    token = login()
    if not token:
        log("Impossible de continuer sans token d'authentification", "ERROR")
        return
    
    # Ru00e9cupu00e9rer les ru00e9unions avec transcription complu00e8te
    completed_meetings = get_meetings(token)
    if not completed_meetings:
        log("Aucune ru00e9union avec transcription complu00e8te trouvu00e9e", "ERROR")
        return
    
    # Choisir la premiu00e8re ru00e9union complu00e8te pour gu00e9nu00e9rer un compte rendu
    meeting = completed_meetings[0]
    meeting_id = meeting["id"]
    
    # Gu00e9nu00e9rer un nouveau compte rendu
    generation_result = generate_summary(token, meeting_id)
    if not generation_result:
        log("u00c9chec de la demande de gu00e9nu00e9ration de compte rendu", "ERROR")
        return
    
    # Vu00e9rifier le statut du compte rendu
    status, summary_data = check_summary_status(token, meeting_id)
    
    # Afficher le ru00e9sultat final
    log(f"\n{'='*50}")
    log(f"Ru00c9SULTAT FINAL:")
    log(f"  Ru00e9union ID: {meeting_id}")
    log(f"  Titre: {meeting['title']}")
    log(f"  Statut final du compte rendu: {status}")
    
    if status == "completed" and summary_data and summary_data.get("summary_text"):
        log("\n===== COMPTE RENDU Gu00c9Nu00c9Ru00c9 =====")
        log(f"Texte du compte rendu:\n{summary_data['summary_text']}")
    elif status == "error":
        log("u274c Erreur lors de la gu00e9nu00e9ration du compte rendu", "ERROR")
    elif status == "timeout":
        log("u26a0ufe0f Timeout lors de la gu00e9nu00e9ration du compte rendu", "WARNING")
    
    log(f"{'='*50}\n")
    log(f"Rapport du00e9taillu00e9: {LOG_FILE}")

if __name__ == "__main__":
    main()
