"""Script de test pour l'upload et la transcription avec la clu00e9 API AssemblyAI"""

import requests
import time
import sys
import json
import os
from pathlib import Path

# Configuration
API_URL = "http://localhost:8001"  # Port modifiu00e9 u00e0 8001
TEST_FILE = "test_audio.mp3"  # Fichier audio de test
EMAIL = "test@example.com"
PASSWORD = "password123"

def login():
    """Se connecte u00e0 l'API et retourne le token JWT"""
    print("Connexion u00e0 l'API...")
    # Utiliser le format OAuth2PasswordRequestForm (username/password)
    response = requests.post(
        f"{API_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD}
    )
    
    if response.status_code != 200:
        print(f"Erreur de connexion: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    token = response.json().get("access_token")
    print(f"Connectu00e9 avec succu00e8s, token: {token[:10]}...")
    return token

def upload_meeting(token, file_path):
    """Upload une ru00e9union avec l'API"""
    print(f"Upload du fichier: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Le fichier {file_path} n'existe pas!")
        sys.exit(1)
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        headers = {"Authorization": f"Bearer {token}"}
        data = {"title": f"Test upload {os.path.basename(file_path)}"}
        
        # Essayer d'abord avec /meetings/upload
        response = requests.post(
            f"{API_URL}/meetings/upload",
            files=files,
            data=data,
            headers=headers
        )
    
    if response.status_code != 200:
        print(f"Erreur lors de l'upload: {response.status_code}")
        print(response.text)
        print("Tentative avec un autre endpoint...")
        
        # Essayer avec /simple/upload si le premier u00e9choue
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            headers = {"Authorization": f"Bearer {token}"}
            data = {"title": f"Test upload {os.path.basename(file_path)}"}
            
            response = requests.post(
                f"{API_URL}/simple/upload",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code != 200:
            print(f"Erreur lors de l'upload (second essai): {response.status_code}")
            print(response.text)
            sys.exit(1)
    
    meeting = response.json()
    print(f"Ru00e9union cru00e9u00e9e avec succu00e8s, ID: {meeting.get('id')}")
    return meeting

def check_meeting_status(token, meeting_id):
    """Vu00e9rifie le statut d'une ru00e9union"""
    print(f"Vu00e9rification du statut de la ru00e9union {meeting_id}")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_URL}/meetings/{meeting_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"Erreur lors de la vu00e9rification du statut: {response.status_code}")
        print(response.text)
        print("Tentative avec un autre endpoint...")
        
        # Essayer avec /simple/meetings/{meeting_id} si le premier u00e9choue
        response = requests.get(
            f"{API_URL}/simple/meetings/{meeting_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"Erreur lors de la vu00e9rification du statut (second essai): {response.status_code}")
            print(response.text)
            return None
    
    meeting = response.json()
    status = meeting.get("transcript_status")
    print(f"Statut actuel: {status}")
    return meeting

def main():
    """Fonction principale"""
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = TEST_FILE
    
    token = login()
    meeting = upload_meeting(token, file_path)
    
    # Vu00e9rifier pu00e9riodiquement le statut de la transcription
    max_checks = 10  # Nombre de vu00e9rifications
    for i in range(max_checks):
        print(f"\nVu00e9rification {i+1}/{max_checks}")
        meeting = check_meeting_status(token, meeting["id"])
        
        if not meeting:
            print("Impossible de ru00e9cupu00e9rer les informations de la ru00e9union")
            break
        
        status = meeting.get("transcript_status")
        if status == "completed":
            print("Transcription terminu00e9e avec succu00e8s!")
            # Afficher les 200 premiers caractu00e8res de la transcription
            transcript = meeting.get("transcript_text", "")
            print(f"Du00e9but de la transcription: {transcript[:200]}...")
            break
        
        if status == "error":
            print("Erreur lors de la transcription")
            print(meeting.get("transcript_text", "Pas de message d'erreur"))
            break
        
        print("En attente de la transcription...")
        time.sleep(15)  # Attendre 15 secondes avant la prochaine vu00e9rification
    
    print("\nFin du test")

if __name__ == "__main__":
    main()
