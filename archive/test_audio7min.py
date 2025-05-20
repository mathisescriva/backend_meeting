import requests
import json
import time
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
BASE_URL = "http://localhost:8048"
EMAIL = "test2@example.com"
PASSWORD = "password123"
FICHIER_AUDIO = "Audio7min.mp3"

# Fonction pour s'authentifier
def login():
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD}  # OAuth2 utilise username/password
    )
    print(f"Connexion: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data.get("access_token")

# Fonction pour uploader un fichier
def upload_file(token, file_path):
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "audio/mp3")}
        data = {"title": os.path.basename(file_path)}
        response = requests.post(
            f"{BASE_URL}/meetings/upload",
            headers=headers,
            files=files,
            data=data
        )
    print(f"Upload de réunion: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data.get("id")

# Fonction pour obtenir les détails d'une réunion
def get_meeting_details(token, meeting_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/meetings/{meeting_id}",
        headers=headers
    )
    return response.status_code, response.json()

# Fonction principale
def main():
    # S'authentifier
    token = login()
    if not token:
        print("Échec de l'authentification")
        return
    
    # Uploader le fichier audio
    meeting_id = upload_file(token, FICHIER_AUDIO)
    if not meeting_id:
        print("Échec de l'upload")
        return
    
    # Surveiller la transcription
    print("\nSurveillance de la transcription...")
    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        status_code, meeting = get_meeting_details(token, meeting_id)
        print(f"Détails de la réunion: {status_code}")
        print(json.dumps(meeting, indent=2))
        
        status = meeting.get("transcript_status")
        print(f"Tentative {attempt}/{max_attempts} - Statut: {status}")
        
        if status == "completed":
            print("Transcription terminée avec succès!")
            transcript_text = meeting.get("transcript_text")
            print("\nTranscription:")
            print("=" * 50)
            print(transcript_text if transcript_text else "Aucun texte de transcription disponible")
            print("=" * 50)
            break
        elif status == "error":
            print("Erreur lors de la transcription")
            break
        
        # Attendre avant la prochaine vérification
        time.sleep(5)
    
    # Afficher le résultat final
    status_code, meeting = get_meeting_details(token, meeting_id)
    print("\nRésultat final:")
    print(json.dumps(meeting, indent=2))

if __name__ == "__main__":
    main()
