#!/usr/bin/env python3
"""
Script pour tester directement l'envoi d'une transcription à AssemblyAI.
"""
import os
import sys
import requests
import json
import time
from pathlib import Path

# Configuration
API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "3419005ee6924e08a14235043cabcd4e")
API_URL = "https://api.assemblyai.com/v2"

def upload_file(file_path):
    """Upload un fichier audio directement à AssemblyAI"""
    print(f"Chargement du fichier: {file_path}")
    
    headers = {
        "authorization": API_KEY
    }
    
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{API_URL}/upload",
                headers=headers,
                data=f
            )
        
        print(f"Réponse du serveur: {response.status_code}")
        print(f"Contenu de la réponse: {response.text}")
        
        if response.status_code == 200:
            upload_url = response.json()["upload_url"]
            print(f"URL d'upload: {upload_url}")
            return upload_url
        else:
            print(f"Erreur dans la réponse: {response.text}")
            return None
    except Exception as e:
        print(f"Erreur lors de l'upload: {str(e)}")
        return None

def start_transcription(audio_url):
    """Démarre une transcription avec AssemblyAI"""
    print(f"Démarrage de la transcription pour: {audio_url}")
    
    headers = {
        "authorization": API_KEY,
        "content-type": "application/json"
    }
    
    json_data = {
        "audio_url": audio_url,
        "language_code": "fr",
        "speaker_labels": True
    }
    
    try:
        response = requests.post(
            f"{API_URL}/transcript",
            headers=headers,
            json=json_data
        )
        
        print(f"Réponse du serveur: {response.status_code}")
        print(f"Contenu de la réponse: {response.text}")
        
        if response.status_code == 200:
            transcript_id = response.json()["id"]
            print(f"ID de transcription: {transcript_id}")
            return transcript_id
        else:
            print(f"Erreur dans la réponse: {response.text}")
            return None
    except Exception as e:
        print(f"Erreur lors du démarrage de la transcription: {str(e)}")
        return None

def check_transcription_status(transcript_id):
    """Vérifie le statut d'une transcription"""
    print(f"Vérification du statut pour: {transcript_id}")
    
    headers = {
        "authorization": API_KEY
    }
    
    try:
        response = requests.get(
            f"{API_URL}/transcript/{transcript_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            status = response.json()["status"]
            print(f"Statut: {status}")
            return status
        else:
            print(f"Erreur dans la réponse: {response.text}")
            return None
    except Exception as e:
        print(f"Erreur lors de la vérification du statut: {str(e)}")
        return None

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <audio_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"Le fichier {file_path} n'existe pas.")
        sys.exit(1)
    
    # 1. Upload du fichier
    upload_url = upload_file(file_path)
    if not upload_url:
        print("Échec de l'upload. Arrêt.")
        sys.exit(1)
    
    # 2. Démarrage de la transcription
    transcript_id = start_transcription(upload_url)
    if not transcript_id:
        print("Échec du démarrage de la transcription. Arrêt.")
        sys.exit(1)
    
    # 3. Vérification du statut toutes les 5 secondes pendant 30 secondes
    for _ in range(6):
        status = check_transcription_status(transcript_id)
        if status == "completed":
            print("Transcription terminée!")
            break
        elif status in ["error", "failed"]:
            print("La transcription a échoué.")
            break
        
        print("En attente...")
        time.sleep(5)
    
    print("Test terminé.")

if __name__ == "__main__":
    main()
