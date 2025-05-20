"""Script de test pour vu00e9rifier la vitesse de mise u00e0 jour des transcriptions"""

import requests
import time
import sys
import os
from datetime import datetime

# Configuration
API_URL = "http://localhost:8001"
TEST_FILE = "test_audio.mp3"  # Fichier audio court pour un test rapide
EMAIL = "test@example.com"
PASSWORD = "password123"
CHECK_INTERVAL = 5  # Vu00e9rifier toutes les 5 secondes

def login():
    """Se connecte u00e0 l'API et retourne le token JWT"""
    print("\nud83dudd11 Connexion u00e0 l'API...")
    response = requests.post(
        f"{API_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        print(f"u274c Erreur de connexion: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    token = response.json().get("access_token")
    print(f"u2705 Connectu00e9 avec succu00e8s, token: {token[:10]}...")
    return token

def upload_meeting(token, file_path):
    """Upload une ru00e9union avec l'API simplifiu00e9e"""
    print(f"\nud83dudce4 Upload du fichier: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"u274c Le fichier {file_path} n'existe pas!")
        sys.exit(1)
    
    # Cru00e9er un nom unique pour la ru00e9union basu00e9 sur l'heure actuelle
    meeting_name = f"Test Meeting {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        headers = {"Authorization": f"Bearer {token}"}
        data = {"name": meeting_name}
        
        response = requests.post(
            f"{API_URL}/simple/meetings/upload",
            files=files,
            data=data,
            headers=headers
        )
    
    if response.status_code != 200:
        print(f"u274c Erreur lors de l'upload: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    meeting = response.json()
    print(f"u2705 Ru00e9union cru00e9u00e9e avec succu00e8s, ID: {meeting.get('id')}")
    print(f"ud83dudcdd Nom de la ru00e9union: {meeting.get('name')}")
    print(f"ud83dudd04 Statut initial: {meeting.get('transcript_status')}")
    return meeting

def check_meeting_status(token, meeting_id):
    """Vu00e9rifie le statut d'une ru00e9union"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_URL}/simple/meetings/{meeting_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"u274c Erreur lors de la vu00e9rification du statut: {response.status_code}")
        print(response.text)
        return None
    
    meeting = response.json()
    return meeting

def main():
    """Fonction principale"""
    print("ud83dude80 Du00e9marrage du test de vitesse de mise u00e0 jour des transcriptions")
    print(f"u23f1ufe0f Intervalle de vu00e9rification: {CHECK_INTERVAL} secondes")
    
    token = login()
    meeting = upload_meeting(token, TEST_FILE)
    meeting_id = meeting["id"]
    
    # Vu00e9rifier pu00e9riodiquement le statut de la transcription
    max_checks = 60  # Vu00e9rifier pendant 5 minutes maximum
    start_time = time.time()
    last_status = meeting.get("transcript_status")
    last_text = meeting.get("transcript_text", "")
    
    print("\nud83dudd0d Surveillance de la transcription...")
    print(f"ud83dudd04 Statut initial: {last_status}")
    
    for i in range(max_checks):
        elapsed_time = time.time() - start_time
        time.sleep(CHECK_INTERVAL)
        
        meeting = check_meeting_status(token, meeting_id)
        if not meeting:
            print("u274c Impossible de ru00e9cupu00e9rer les informations de la ru00e9union")
            break
        
        current_status = meeting.get("transcript_status")
        current_text = meeting.get("transcript_text", "")
        
        # Vu00e9rifier si le statut ou le texte a changu00e9
        if current_status != last_status or current_text != last_text:
            print(f"\nu2757 Changement du00e9tectu00e9 apru00e8s {elapsed_time:.1f} secondes:")
            print(f"ud83dudd04 Nouveau statut: {current_status} (pru00e9cu00e9dent: {last_status})")
            
            if current_text != last_text:
                # Afficher seulement les 100 premiers caractu00e8res du texte
                print(f"ud83dudcdd Nouveau texte: {current_text[:100]}...")
            
            last_status = current_status
            last_text = current_text
        else:
            print(f"Vu00e9rification {i+1}/{max_checks} ({elapsed_time:.1f}s) - Aucun changement")
        
        if current_status == "completed":
            print(f"\nu2705 Transcription terminu00e9e apru00e8s {elapsed_time:.1f} secondes!")
            break
        elif current_status == "error":
            print(f"\nu274c Erreur de transcription apru00e8s {elapsed_time:.1f} secondes")
            print(f"Message d'erreur: {current_text}")
            break
    
    print("\nud83cudfc1 Fin du test")

if __name__ == "__main__":
    main()
