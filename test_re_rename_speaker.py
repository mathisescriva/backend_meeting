#!/usr/bin/env python3

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8001"
MEETING_ID = "108f1bba-a7cd-49b8-9fc6-5a08db5274c6"  # Réunion de test
SPEAKER_ID = "Speaker D"
TEST_NAMES = ["Premier nom", "Deuxième nom", "Troisième nom"]

def login():
    """Connexion au système"""
    login_data = {
        "username": "test.rename@example.com",
        "password": "password123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Erreur de connexion: {response.status_code}")
        print(response.text)
        return None

def get_speakers(token, meeting_id):
    """Récupère les speakers actuels"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/speakers", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur récupération speakers: {response.status_code}")
        print(response.text)
        return None

def rename_speaker(token, meeting_id, speaker_id, new_name):
    """Renomme un speaker"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {"speaker_id": speaker_id, "custom_name": new_name}
    
    response = requests.post(f"{BASE_URL}/meetings/{meeting_id}/speakers", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur renommage: {response.status_code}")
        print(response.text)
        return None

def main():
    # Connexion
    token = login()
    if not token:
        print("Échec de connexion")
        return
    
    print(f"=== Test de re-renommage du speaker {SPEAKER_ID} ===\n")
    
    # État initial
    print("1. État initial:")
    speakers = get_speakers(token, MEETING_ID)
    if speakers:
        for speaker in speakers.get("speakers", []):
            if speaker["speaker_id"] == SPEAKER_ID:
                print(f"   {SPEAKER_ID}: {speaker['custom_name']}")
                break
        else:
            print(f"   {SPEAKER_ID}: (pas de nom personnalisé)")
    
    # Test de renommages successifs
    for i, new_name in enumerate(TEST_NAMES, 1):
        print(f"\n{i+1}. Renommage en '{new_name}':")
        
        # Renommer
        result = rename_speaker(token, MEETING_ID, SPEAKER_ID, new_name)
        if result:
            print(f"   ✓ Renommage réussi")
            
            # Vérifier
            speakers = get_speakers(token, MEETING_ID)
            if speakers:
                for speaker in speakers.get("speakers", []):
                    if speaker["speaker_id"] == SPEAKER_ID:
                        current_name = speaker['custom_name']
                        print(f"   Nom actuel: {current_name}")
                        if current_name == new_name:
                            print(f"   ✓ Nom correctement mis à jour")
                        else:
                            print(f"   ✗ ERREUR: Nom attendu '{new_name}', obtenu '{current_name}'")
                        break
                else:
                    print(f"   ✗ ERREUR: Speaker {SPEAKER_ID} non trouvé")
        else:
            print(f"   ✗ Échec du renommage")
        
        # Attendre un peu entre les tests
        time.sleep(1)
    
    print(f"\n=== Test terminé ===")

if __name__ == "__main__":
    main() 