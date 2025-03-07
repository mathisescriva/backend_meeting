"""
Script de test pour l'upload et la transcription simplifiés
"""

import requests
import time
import sys
import json
import os
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000"
TEST_FILE = "test_audio.mp3"  # Assurez-vous que ce fichier existe
EMAIL = "test@example.com"
PASSWORD = "password123"

def login():
    """Se connecte à l'API et retourne le token JWT"""
    print("Connexion à l'API...")
    response = requests.post(
        f"{API_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD}
    )
    
    if response.status_code != 200:
        print(f"Erreur de connexion: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    token = response.json().get("access_token")
    print(f"Connecté avec succès, token: {token[:10]}...")
    return token

def upload_meeting(token, file_path):
    """Upload une réunion avec la nouvelle API simplifiée"""
    print(f"Upload du fichier: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Le fichier {file_path} n'existe pas!")
        sys.exit(1)
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(
            f"{API_URL}/simple/meetings/upload",
            files=files,
            headers=headers
        )
    
    if response.status_code != 200:
        print(f"Erreur lors de l'upload: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    meeting = response.json()
    print(f"Réunion créée avec succès, ID: {meeting.get('id')}")
    return meeting

def check_meeting_status(token, meeting_id):
    """Vérifie le statut d'une réunion"""
    print(f"Vérification du statut de la réunion {meeting_id}")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_URL}/simple/meetings/{meeting_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"Erreur lors de la vérification du statut: {response.status_code}")
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
    
    # Vérifier périodiquement le statut de la transcription
    max_checks = 20
    for i in range(max_checks):
        print(f"\nVérification {i+1}/{max_checks}")
        meeting = check_meeting_status(token, meeting["id"])
        
        if not meeting:
            print("Impossible de récupérer les informations de la réunion")
            break
        
        status = meeting.get("transcript_status")
        if status == "completed":
            print("Transcription terminée avec succès!")
            # Afficher les 200 premiers caractères de la transcription
            transcript = meeting.get("transcript_text", "")
            print(f"Début de la transcription: {transcript[:200]}...")
            break
        
        if status == "error":
            print("Erreur lors de la transcription")
            print(meeting.get("transcript_text", "Pas de message d'erreur"))
            break
        
        print("En attente de la transcription...")
        time.sleep(30)  # Attendre 30 secondes avant la prochaine vérification
    
    print("\nFin du test")

if __name__ == "__main__":
    main()
