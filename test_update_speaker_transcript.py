"""
Script de test pour mettre à jour un nom de speaker et vérifier la mise à jour de la transcription.
"""

import requests
import json
import os
import time

# Configuration
BASE_URL = "http://localhost:8001"
MEETING_ID = "13698611-9bbc-4ef5-90ba-155e09a5fb3e"  # Changez-le par l'ID de votre réunion
SPEAKER_ID = "Speaker A"  # Speaker à renommer
NEW_NAME = "Mathis Test"  # Nouveau nom

# Fonction d'authentification
def login():
    response = requests.post(
        f"{BASE_URL}/auth/login",  # Endpoint corrigé
        data={"username": "mathis", "password": "password"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Erreur de login: {response.status_code}")
        print(response.text)
        return None

# 1. Authentification
token = login()
if not token:
    print("Échec d'authentification, impossible de continuer.")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 2. Obtenir l'état actuel
print("Récupération des données actuelles...")
response = requests.get(f"{BASE_URL}/meetings/{MEETING_ID}", headers=headers)
if response.status_code == 200:
    meeting_data = response.json()
    print(f"Statut de la transcription: {meeting_data.get('transcript_status')}")
else:
    print(f"Erreur lors de la récupération de la réunion: {response.status_code}")
    print(response.text)
    exit(1)

# 3. Récupérer les speakers actuels
response = requests.get(f"{BASE_URL}/meetings/{MEETING_ID}/speakers", headers=headers)
if response.status_code == 200:
    speakers_data = response.json()
    print(f"Speakers actuels: {json.dumps(speakers_data, indent=2)}")
else:
    print(f"Erreur lors de la récupération des speakers: {response.status_code}")
    print(response.text)
    exit(1)

# 4. Renommer un speaker
print(f"Renommage du speaker {SPEAKER_ID} en {NEW_NAME}...")
response = requests.post(
    f"{BASE_URL}/meetings/{MEETING_ID}/speakers",
    headers=headers,
    json={"speaker_id": SPEAKER_ID, "custom_name": NEW_NAME}
)
if response.status_code == 200:
    created_speaker = response.json()
    print(f"Speaker créé/mis à jour: {json.dumps(created_speaker, indent=2)}")
else:
    print(f"Erreur lors de la création/mise à jour du speaker: {response.status_code}")
    print(response.text)
    exit(1)

# 5. Attendre un peu pour s'assurer que la mise à jour est traitée
print("Attente de quelques secondes...")
time.sleep(2)

# 6. Vérifier si la transcription a été mise à jour
print("Vérification de la mise à jour de la transcription...")
response = requests.get(f"{BASE_URL}/meetings/{MEETING_ID}", headers=headers)
if response.status_code == 200:
    updated_meeting = response.json()
    
    # Vérifier si le nom est dans la transcription
    if NEW_NAME in updated_meeting.get("transcript_text", ""):
        print(f"SUCCÈS: La transcription a été mise à jour avec le nouveau nom '{NEW_NAME}'")
    else:
        print(f"ÉCHEC: La transcription ne contient pas le nouveau nom '{NEW_NAME}'")
        print("Essai avec /simple/meetings/...")
        
        # Essayer avec l'endpoint simple
        response = requests.get(f"{BASE_URL}/simple/meetings/{MEETING_ID}", headers=headers)
        if response.status_code == 200:
            simple_meeting = response.json()
            
            if NEW_NAME in simple_meeting.get("transcript_text", ""):
                print(f"SUCCÈS via /simple: La transcription a été mise à jour avec le nouveau nom '{NEW_NAME}'")
            else:
                print(f"ÉCHEC via /simple: La transcription ne contient pas le nouveau nom '{NEW_NAME}'")
                
                # Forcer la mise à jour explicite
                print("Forçage de la mise à jour de la transcription via l'endpoint dédié...")
                response = requests.get(f"{BASE_URL}/meetings/{MEETING_ID}/speakers/update-transcript", headers=headers)
                if response.status_code == 200:
                    transcript_update = response.json()
                    
                    if NEW_NAME in transcript_update.get("transcript_text", ""):
                        print(f"SUCCÈS via update-transcript: La mise à jour forcée a fonctionné!")
                    else:
                        print(f"ÉCHEC total: Même la mise à jour forcée n'a pas fonctionné.")
                else:
                    print(f"Erreur lors de la mise à jour forcée: {response.status_code}")
                    print(response.text)
        else:
            print(f"Erreur lors de la récupération via /simple: {response.status_code}")
            print(response.text)
else:
    print(f"Erreur lors de la récupération de la réunion mise à jour: {response.status_code}")
    print(response.text)
