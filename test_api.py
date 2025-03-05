import requests
import os
import json
import time

# URL de base de l'API
BASE_URL = "http://127.0.0.1:8048"

# Fonction pour enregistrer un nouvel utilisateur
def register_user(email, password, full_name=None):
    url = f"{BASE_URL}/auth/register"
    data = {
        "email": email,
        "password": password,
        "full_name": full_name
    }
    response = requests.post(url, json=data)
    print(f"Enregistrement: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()

# Fonction pour se connecter
def login(email, password):
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": email,  # OAuth2 utilise username/password
        "password": password
    }
    response = requests.post(url, data=data)
    print(f"Connexion: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()

# Fonction pour lister les réunions
def list_meetings(token):
    url = f"{BASE_URL}/meetings"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print(f"Liste des réunions: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()

# Fonction pour télécharger un fichier audio
def upload_meeting(token, file_path, title=None):
    url = f"{BASE_URL}/meetings/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    if not title:
        title = os.path.basename(file_path)
        
    files = {"file": (os.path.basename(file_path), open(file_path, "rb"), "audio/mpeg")}
    data = {"title": title}
    
    response = requests.post(url, headers=headers, files=files, data=data)
    print(f"Upload de réunion: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()

# Fonction pour obtenir les détails d'une réunion
def get_meeting_details(token, meeting_id):
    url = f"{BASE_URL}/meetings/{meeting_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    print(f"Détails de la réunion: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()

# Fonction pour lancer manuellement la transcription
def start_transcription(token, meeting_id):
    url = f"{BASE_URL}/meetings/{meeting_id}/transcribe"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(url, headers=headers)
    print(f"Lancement transcription: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()

# Fonction pour surveiller la progression de la transcription
def monitor_transcription(token, meeting_id, max_attempts=10, delay=5):
    for attempt in range(max_attempts):
        meeting = get_meeting_details(token, meeting_id)
        status = meeting.get("transcript_status", "unknown")
        
        print(f"Tentative {attempt+1}/{max_attempts} - Statut: {status}")
        
        if status == "completed":
            print("Transcription terminée avec succès!")
            return meeting
        elif status == "error":
            print("Erreur lors de la transcription")
            return meeting
            
        # Attendre avant la prochaine vérification
        time.sleep(delay)
        
    print("Délai d'attente dépassé")
    return None

# Test principal
def main():
    # Informations utilisateur
    email = "test2@example.com"
    password = "password123"
    full_name = "Test User 2"
    
    # Chemin vers un fichier audio MP3 pour les tests
    mp3_file = "./test_audio.mp3"  # Assurez-vous d'avoir un fichier MP3 à cet emplacement
    
    # Créer un utilisateur
    try:
        register_user(email, password, full_name)
    except Exception as e:
        print(f"Erreur lors de l'enregistrement: {str(e)}")
    
    # Se connecter
    try:
        login_data = login(email, password)
        token = login_data.get("access_token")
        
        if token:
            # Lister les réunions
            meetings = list_meetings(token)
            
            # Vérifier si le fichier MP3 existe
            if os.path.exists(mp3_file):
                # Uploader une réunion
                meeting = upload_meeting(token, mp3_file, "Réunion de test avec transcription")
                meeting_id = meeting.get("id")
                
                if meeting_id:
                    # Lister à nouveau pour voir la nouvelle réunion
                    list_meetings(token)
                    
                    # Attendre et vérifier la transcription
                    print("\nSurveillance de la transcription...")
                    monitor_transcription(token, meeting_id)
                    
                    # Afficher les détails finaux
                    final_meeting = get_meeting_details(token, meeting_id)
                    
                    # Afficher le texte de la transcription
                    if final_meeting.get("transcript_text"):
                        print("\nTranscription:")
                        print(final_meeting.get("transcript_text"))
                    else:
                        print("\nAucun texte de transcription disponible")
            else:
                print(f"Le fichier {mp3_file} n'existe pas. Impossible de tester l'upload.")
    except Exception as e:
        print(f"Erreur lors des tests: {str(e)}")

if __name__ == "__main__":
    main()
