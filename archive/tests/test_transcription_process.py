"""Script de test pour suivre le processus complet de transcription d'une réunion"""

import requests
import time
import sys
import json
import os
from datetime import datetime

# Configuration
API_URL = "http://localhost:8001"
TEST_FILE = "test_audio.mp3"  # Fichier audio court pour un test rapide
# TEST_FILE = "Audio7min.mp3"  # Fichier audio plus long pour un test plus réaliste
EMAIL = "test@example.com"
PASSWORD = "password123"
CHECK_INTERVAL = 10  # Vérifier toutes les 10 secondes (au lieu de 30)

def login():
    """Se connecte à l'API et retourne le token JWT"""
    print("\n🔑 Connexion à l'API...")
    response = requests.post(
        f"{API_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        print(f"❌ Erreur de connexion: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    token = response.json().get("access_token")
    print(f"✅ Connecté avec succès, token: {token[:10]}...")
    return token

def upload_meeting(token, file_path):
    """Upload une réunion avec l'API simplifiée"""
    print(f"\n📤 Upload du fichier: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ Le fichier {file_path} n'existe pas!")
        sys.exit(1)
    
    # Créer un nom unique pour la réunion basé sur l'heure actuelle
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
        print(f"❌ Erreur lors de l'upload: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    meeting = response.json()
    print(f"✅ Réunion créée avec succès, ID: {meeting.get('id')}")
    print(f"📝 Nom de la réunion: {meeting.get('name')}")
    print(f"🔄 Statut initial: {meeting.get('transcript_status')}")
    return meeting

def check_meeting_status(token, meeting_id):
    """Vérifie le statut d'une réunion"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_URL}/simple/meetings/{meeting_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Erreur lors de la vérification du statut: {response.status_code}")
        print(response.text)
        return None
    
    meeting = response.json()
    status = meeting.get("transcript_status")
    return meeting

def check_assemblyai_status(token, meeting):
    """Vérifie directement le statut sur AssemblyAI si possible"""
    # Essayer d'extraire l'ID de transcription AssemblyAI du texte
    transcript_id = None
    transcript_text = meeting.get('transcript_text', '')
    
    if transcript_text and 'ID:' in transcript_text:
        try:
            # Extraire l'ID de transcription du texte (format: 'Transcription en cours, ID: xyz')
            transcript_id = transcript_text.split('ID:')[-1].strip()
            print(f"🔍 ID de transcription AssemblyAI extrait: {transcript_id}")
            return transcript_id
        except Exception as e:
            print(f"⚠️ Impossible d'extraire l'ID de transcription: {str(e)}")
    
    return None

def main():
    """Fonction principale"""
    print("🚀 Démarrage du test de transcription")
    print(f"⏱️ Intervalle de vérification: {CHECK_INTERVAL} secondes")
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = TEST_FILE
    
    token = login()
    meeting = upload_meeting(token, file_path)
    meeting_id = meeting["id"]
    
    # Vérifier périodiquement le statut de la transcription
    max_checks = 30
    start_time = time.time()
    assemblyai_id = None
    
    for i in range(max_checks):
        elapsed_time = time.time() - start_time
        print(f"\n⏱️ Vérification {i+1}/{max_checks} (temps écoulé: {elapsed_time:.1f}s)")
        
        meeting = check_meeting_status(token, meeting_id)
        
        if not meeting:
            print("❌ Impossible de récupérer les informations de la réunion")
            break
        
        status = meeting.get("transcript_status")
        print(f"🔄 Statut actuel: {status}")
        
        # Si nous n'avons pas encore l'ID AssemblyAI et que le statut est 'processing', essayer de l'extraire
        if not assemblyai_id and status == "processing":
            assemblyai_id = check_assemblyai_status(token, meeting)
        
        if status == "completed":
            print("✅ Transcription terminée avec succès!")
            print(f"⏱️ Temps total: {elapsed_time:.1f} secondes")
            # Afficher les 200 premiers caractères de la transcription
            transcript = meeting.get("transcript_text", "")
            print(f"📝 Début de la transcription: {transcript[:200]}...")
            break
        
        if status == "error":
            print("❌ Erreur lors de la transcription")
            print(meeting.get("transcript_text", "Pas de message d'erreur"))
            break
        
        print(f"⏳ En attente de la transcription... (vérification dans {CHECK_INTERVAL}s)")
        time.sleep(CHECK_INTERVAL)
    
    print("\n🏁 Fin du test")

if __name__ == "__main__":
    main()
