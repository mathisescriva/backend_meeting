"""Script de test pour les endpoints du backend"""

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
    print("\n=== Test de connexion (/auth/login) ===")
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

def test_auth_me(token):
    """Teste l'endpoint /auth/me"""
    print("\n=== Test de ru00e9cupu00e9ration des informations utilisateur (/auth/me) ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/auth/me", headers=headers)
    
    if response.status_code == 200:
        print("Succu00e8s! Informations utilisateur ru00e9cupu00e9ru00e9es")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)

def test_profile_me(token):
    """Teste l'endpoint /profile/me"""
    print("\n=== Test de ru00e9cupu00e9ration du profil utilisateur (/profile/me) ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/profile/me", headers=headers)
    
    if response.status_code == 200:
        print("Succu00e8s! Profil utilisateur ru00e9cupu00e9ru00e9")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)

def test_simple_meetings(token):
    """Teste l'endpoint /simple/meetings/"""
    print("\n=== Test de ru00e9cupu00e9ration des ru00e9unions (/simple/meetings/) ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/simple/meetings/", headers=headers)
    
    if response.status_code == 200:
        meetings = response.json()
        print(f"Succu00e8s! {len(meetings)} ru00e9unions ru00e9cupu00e9ru00e9es")
        if len(meetings) > 0:
            print(f"Premiu00e8re ru00e9union: {meetings[0].get('id')} - {meetings[0].get('title')}")
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
    
    return response.json() if response.status_code == 200 else []

def test_upload_meeting(token, file_path):
    """Teste l'endpoint /simple/meetings/upload"""
    print(f"\n=== Test d'upload d'une ru00e9union (/simple/meetings/upload) ===")
    print(f"Fichier: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Le fichier {file_path} n'existe pas!")
        return None
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        headers = {"Authorization": f"Bearer {token}"}
        data = {"title": f"Test upload {os.path.basename(file_path)}"}
        
        response = requests.post(
            f"{API_URL}/simple/meetings/upload",
            files=files,
            data=data,
            headers=headers
        )
    
    if response.status_code == 200:
        meeting = response.json()
        print(f"Succu00e8s! Ru00e9union cru00e9u00e9e avec ID: {meeting.get('id')}")
        return meeting
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def test_get_meeting(token, meeting_id):
    """Teste l'endpoint /simple/meetings/{meeting_id}"""
    print(f"\n=== Test de ru00e9cupu00e9ration d'une ru00e9union (/simple/meetings/{meeting_id}) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/simple/meetings/{meeting_id}", headers=headers)
    
    if response.status_code == 200:
        meeting = response.json()
        print(f"Succu00e8s! Ru00e9union ru00e9cupu00e9ru00e9e: {meeting.get('title')}")
        print(f"Statut de la transcription: {meeting.get('transcript_status')}")
        return meeting
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def test_transcribe_meeting(token, meeting_id):
    """Teste l'endpoint /simple/meetings/{meeting_id}/transcribe"""
    print(f"\n=== Test de du00e9marrage de transcription (/simple/meetings/{meeting_id}/transcribe) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_URL}/simple/meetings/{meeting_id}/transcribe", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Succu00e8s! Transcription du00e9marru00e9e: {result}")
        return result
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def test_retry_transcription(token, meeting_id):
    """Teste l'endpoint /simple/meetings/{meeting_id}/retry-transcription"""
    print(f"\n=== Test de ru00e9essai de transcription (/simple/meetings/{meeting_id}/retry-transcription) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_URL}/simple/meetings/{meeting_id}/retry-transcription", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Succu00e8s! Transcription relance: {result}")
        return result
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def test_update_metadata(token, meeting_id):
    """Teste l'endpoint /simple/meetings/{meeting_id}/update-metadata"""
    print(f"\n=== Test de mise u00e0 jour des mu00e9tadonnu00e9es (/simple/meetings/{meeting_id}/update-metadata) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    data = {"title": f"Titre mis u00e0 jour - {time.time()}", "metadata": {"test": True}}
    
    response = requests.post(
        f"{API_URL}/simple/meetings/{meeting_id}/update-metadata", 
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Succu00e8s! Mu00e9tadonnu00e9es mises u00e0 jour: {result}")
        return result
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def test_get_audio(token, meeting_id):
    """Teste l'endpoint /simple/meetings/{meeting_id}/audio"""
    print(f"\n=== Test de ru00e9cupu00e9ration du fichier audio (/simple/meetings/{meeting_id}/audio) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/simple/meetings/{meeting_id}/audio", headers=headers)
    
    if response.status_code == 200:
        content_type = response.headers.get('Content-Type')
        content_length = len(response.content)
        print(f"Succu00e8s! Fichier audio ru00e9cupu00e9ru00e9 ({content_type}, {content_length} octets)")
        return True
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return False

def test_validate_ids(token, meeting_ids):
    """Teste l'endpoint /simple/meetings/validate-ids"""
    print(f"\n=== Test de validation des IDs de ru00e9unions (/simple/meetings/validate-ids) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    data = {"meeting_ids": meeting_ids}
    
    response = requests.post(
        f"{API_URL}/simple/meetings/validate-ids", 
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Succu00e8s! Validation des IDs: {result}")
        return result
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def test_delete_meeting(token, meeting_id):
    """Teste l'endpoint /simple/meetings/{meeting_id} (DELETE)"""
    print(f"\n=== Test de suppression d'une ru00e9union (/simple/meetings/{meeting_id}) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(f"{API_URL}/simple/meetings/{meeting_id}", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Succu00e8s! Ru00e9union supprimu00e9e: {result}")
        return result
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def main():
    """Fonction principale"""
    # Se connecter
    token = login()
    
    # Tester les endpoints d'authentification et de profil
    test_auth_me(token)
    test_profile_me(token)
    
    # Ru00e9cupu00e9rer les ru00e9unions existantes
    meetings = test_simple_meetings(token)
    
    # Uploader une nouvelle ru00e9union
    file_path = TEST_FILE
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    new_meeting = test_upload_meeting(token, file_path)
    
    if new_meeting:
        meeting_id = new_meeting.get('id')
        
        # Tester la ru00e9cupu00e9ration de la ru00e9union
        test_get_meeting(token, meeting_id)
        
        # Tester la mise u00e0 jour des mu00e9tadonnu00e9es
        test_update_metadata(token, meeting_id)
        
        # Tester la ru00e9cupu00e9ration du fichier audio
        test_get_audio(token, meeting_id)
        
        # Tester le du00e9marrage de la transcription
        test_transcribe_meeting(token, meeting_id)
        
        # Tester le ru00e9essai de la transcription
        test_retry_transcription(token, meeting_id)
        
        # Tester la validation des IDs
        if meetings and len(meetings) > 0:
            meeting_ids = [meeting.get('id') for meeting in meetings[:2]]
            meeting_ids.append(meeting_id)
            test_validate_ids(token, meeting_ids)
        
        # Attendre un peu pour voir si la transcription du00e9marre
        print("\nAttente de 5 secondes pour vu00e9rifier l'u00e9tat de la transcription...")
        time.sleep(5)
        test_get_meeting(token, meeting_id)
        
        # Ne pas supprimer la ru00e9union pour pouvoir l'examiner plus tard
        # test_delete_meeting(token, meeting_id)
    
    print("\nTests terminu00e9s!")

if __name__ == "__main__":
    main()
