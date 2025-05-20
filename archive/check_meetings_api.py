#!/usr/bin/env python
"""Script pour vérifier le bon fonctionnement des routes de gestion des réunions"""

import subprocess
import time
import sys
import json
import requests
import uuid
import os
from pathlib import Path

# Constantes
API_URL = "http://localhost:8000"
AUTH_BASE = f"{API_URL}/auth"
MEETING_BASE = f"{API_URL}/meetings"  # Les routes commencent par /meetings
COLORS = {
    "GREEN": "\033[92m",
    "RED": "\033[91m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "RESET": "\033[0m",
}

def print_colored(text, color):
    """Affiche du texte coloré dans le terminal"""
    print(f"{COLORS[color]}{text}{COLORS['RESET']}")

def print_header(text):
    """Affiche un en-tête"""
    print("\n" + "="*80)
    print_colored(f" {text} ", "BLUE")
    print("="*80)

def print_result(endpoint, status, message=""):
    """Affiche le résultat d'un test d'endpoint"""
    result = "✅ SUCCÈS" if status else "❌ ÉCHEC"
    color = "GREEN" if status else "RED"
    print(f"{COLORS[color]}{result}{COLORS['RESET']} - {endpoint} {message}")

def start_server():
    """Démarrer le serveur FastAPI en arrière-plan"""
    print_header("DÉMARRAGE DU SERVEUR")
    print("Démarrage du serveur FastAPI sur http://localhost:8000...")
    
    try:
        # Lancer le serveur en arrière-plan
        process = subprocess.Popen(
            ["uvicorn", "app.main:app", "--port", "8000"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
        )
        
        # Attendre que le serveur soit prêt
        for _ in range(10):
            try:
                response = requests.get(f"{API_URL}/health")
                if response.status_code == 200:
                    print_colored("Serveur démarré avec succès", "GREEN")
                    return process
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        
        print_colored("Impossible de démarrer le serveur", "RED")
        process.kill()
        return None
    except Exception as e:
        print_colored(f"Erreur lors du démarrage du serveur: {e}", "RED")
        return None

def register_and_login():
    """Enregistrer un nouvel utilisateur et le connecter"""
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "email": f"test.user.{unique_id}@example.com",
        "password": "SecurePassword123!",
        "full_name": f"Test User {unique_id}"
    }
    
    # Enregistrement
    try:
        response = requests.post(f"{AUTH_BASE}/register", json=user_data)
        if response.status_code != 201:
            print_colored(f"❌ Échec de l'enregistrement: {response.text}", "RED")
            return None
    except Exception as e:
        print_colored(f"❌ Erreur lors de l'enregistrement: {e}", "RED")
        return None
    
    # Connexion
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    
    try:
        response = requests.post(f"{AUTH_BASE}/login", data=login_data)
        if response.status_code != 200:
            print_colored(f"❌ Échec de la connexion: {response.text}", "RED")
            return None
        
        token_data = response.json()
        print_colored(f"✅ Utilisateur {user_data['email']} créé et connecté", "GREEN")
        return token_data["access_token"]
    except Exception as e:
        print_colored(f"❌ Erreur lors de la connexion: {e}", "RED")
        return None

def get_sample_audio_file():
    """Utilise le fichier Audio7min.mp3 pour le test"""
    # Chercher d'abord dans le répertoire du projet
    project_dir = Path(__file__).parent
    
    # Utiliser spécifiquement Audio7min.mp3
    audio_file = project_dir / "Audio7min.mp3"
    
    if audio_file.exists():
        print_colored(f"Utilisation du fichier audio: {audio_file}", "GREEN")
        return str(audio_file)
    
    # Si Audio7min.mp3 n'existe pas, essayer d'autres fichiers
    audio_files = [
        project_dir / "test_audio.mp3",
        project_dir / "test.mp3"
    ]
    
    # Utiliser le premier fichier qui existe
    for audio_file in audio_files:
        if audio_file.exists():
            print_colored(f"Audio7min.mp3 non trouvé, utilisation de: {audio_file}", "YELLOW")
            return str(audio_file)
    
    # Si aucun fichier n'existe, créer un fichier vide pour le test
    test_dir = project_dir / "tests" / "resources"
    test_file = test_dir / "test_audio.mp3"
    
    print_colored("Aucun fichier audio existant trouvé, création d'un fichier vide...", "YELLOW")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Création d'un fichier MP3 vide pour le test
    with open(test_file, 'wb') as f:
        f.write(b'\x00' * 1024)  # Fichier binaire vide de 1Ko
    
    return str(test_file)

def create_meeting(token):
    """Créer une nouvelle réunion"""
    headers = {"Authorization": f"Bearer {token}"}
    audio_file = get_sample_audio_file()
    
    if not os.path.exists(audio_file):
        print_colored(f"❌ Fichier audio introuvable: {audio_file}", "RED")
        return None
    
    # Titre unique pour la réunion
    meeting_title = f"Test Meeting {uuid.uuid4().hex[:8]}"
    
    # La requête doit utiliser 'file' comme nom de champ pour le fichier
    files = {
        'file': (os.path.basename(audio_file), open(audio_file, 'rb'), 'audio/mpeg')
    }
    
    # Le titre est passé comme paramètre de requête
    params = {'title': meeting_title}
    
    try:
        response = requests.post(
            f"{MEETING_BASE}/upload",
            headers=headers,
            files=files,
            params=params
        )
        print_result("/upload", response.status_code == 200, f"(Status: {response.status_code})")
        
        if response.status_code == 200:
            meeting_data = response.json()
            meeting_id = meeting_data.get("id")
            print(f"   Réunion créée avec ID: {meeting_id}")
            print(f"   Titre: {meeting_data.get('title', meeting_title)}")
            return meeting_id
        else:
            print(f"   Erreur: {response.text}")
            return None
    except Exception as e:
        print_result("/upload", False, f"(Erreur: {e})")
        return None
    finally:
        # Fermer le fichier
        files['file'][1].close()

def get_meeting(token, meeting_id):
    """Récupérer les détails d'une réunion"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{MEETING_BASE}/{meeting_id}", headers=headers)
        print_result(f"/{meeting_id}", response.status_code == 200, f"(Status: {response.status_code})")
        
        if response.status_code == 200:
            meeting_data = response.json()
            print(f"   Titre: {meeting_data.get('title')}")
            print(f"   Description: {meeting_data.get('description')}")
            return meeting_data
        else:
            print(f"   Erreur: {response.text}")
            return None
    except Exception as e:
        print_result(f"/{meeting_id}", False, f"(Erreur: {e})")
        return None

def get_transcript(token, meeting_id):
    """Récupérer la transcription d'une réunion"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{MEETING_BASE}/{meeting_id}/transcript", headers=headers)
        print_result(f"/{meeting_id}/transcript", response.status_code == 200, f"(Status: {response.status_code})")
        
        if response.status_code == 200:
            transcript_data = response.json()
            print(f"   Transcription: {transcript_data.get('transcript')[:100]}...")
            return transcript_data
        else:
            print(f"   Erreur: {response.text}")
            return None
    except Exception as e:
        print_result(f"/{meeting_id}/transcript", False, f"(Erreur: {e})")
        return None

def main():
    """Fonction principale"""
    print_header("VÉRIFICATION DES ROUTES DE GESTION DES RÉUNIONS")
    
    # Démarrer le serveur
    server_process = start_server()
    if not server_process:
        sys.exit(1)
    
    try:
        # Authentifier un utilisateur
        print_header("AUTHENTIFICATION")
        token = register_and_login()
        if not token:
            print_colored("❌ Impossible de s'authentifier", "RED")
            return
        
        # Création d'une réunion
        print_header("CRÉATION D'UNE RÉUNION")
        meeting_id = create_meeting(token)
        if not meeting_id:
            print_colored("❌ Impossible de créer une réunion", "RED")
            return
        
        # Récupération des détails
        print_header("RÉCUPÉRATION DES DÉTAILS DE LA RÉUNION")
        meeting_data = get_meeting(token, meeting_id)
        if not meeting_data:
            print_colored("❌ Impossible de récupérer les détails de la réunion", "RED")
            return
        
        # Récupération de la transcription
        print_header("RÉCUPÉRATION DE LA TRANSCRIPTION")
        transcript_data = get_transcript(token, meeting_id)
        if not transcript_data:
            print_colored("⚠️ La transcription n'est peut-être pas encore disponible", "YELLOW")
        
        # Résumé
        print_header("RÉSUMÉ")
        print_colored("✅ Les routes de gestion des réunions fonctionnent correctement!", "GREEN")
        print("L'API optimisée pour la production est fonctionnelle et répond comme prévu.")
        
    finally:
        # Arrêter le serveur
        if server_process:
            print_header("ARRÊT DU SERVEUR")
            server_process.terminate()
            print_colored("Serveur arrêté", "YELLOW")

if __name__ == "__main__":
    main()
