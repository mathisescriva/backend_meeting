#!/usr/bin/env python3

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8001"
MEETING_ID = "7dff69da-0860-45f8-97b5-c2d60c7c64b7"
SPEAKER_ID = "Speaker D"
NEW_NAME = "Tom (Test Fix)"

def login():
    """Authentification pour récupérer le token"""
    login_data = {
        "email": "test.speaker@example.com",
        "password": "TestPassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login/json", json=login_data)
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"Authentification réussie. Token: {token[:20]}...")
        return token
    else:
        print(f"Échec d'authentification: {response.status_code}")
        print(response.text)
        return None

def get_meeting_details(token, meeting_id):
    """Récupère les détails d'une réunion"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur lors de la récupération de la réunion: {response.status_code}")
        print(response.text)
        return None

def get_meeting_speakers(token, meeting_id):
    """Récupère les noms personnalisés des locuteurs pour une réunion"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/speakers", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur lors de la récupération des locuteurs: {response.status_code}")
        print(response.text)
        return None

def set_meeting_speaker(token, meeting_id, speaker_id, custom_name):
    """Définit un nom personnalisé pour un locuteur"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "speaker_id": speaker_id,
        "custom_name": custom_name
    }
    
    response = requests.post(
        f"{BASE_URL}/meetings/{meeting_id}/speakers",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur lors de la définition du nom personnalisé: {response.status_code}")
        print(response.text)
        return None

def count_speaker_occurrences(transcript_text, speaker_name):
    """Compte les occurrences d'un locuteur dans la transcription"""
    if not transcript_text or not speaker_name:
        return 0
    
    # Compter les lignes qui commencent par "speaker_name:"
    lines = transcript_text.split('\n')
    count = 0
    for line in lines:
        if line.strip().startswith(f"{speaker_name}:"):
            count += 1
    
    return count

def main():
    print("=== Test de correction du problème de renommage des locuteurs ===")
    
    # 1. Authentification
    token = login()
    if not token:
        print("Échec d'authentification, impossible de continuer.")
        return
    
    # 2. État initial
    print(f"\n1. Récupération de l'état initial de la réunion {MEETING_ID}")
    meeting_data = get_meeting_details(token, MEETING_ID)
    if not meeting_data:
        print("Impossible de récupérer les données de la réunion")
        return
    
    print(f"   Statut de la transcription: {meeting_data.get('transcript_status')}")
    print(f"   Nombre de locuteurs: {meeting_data.get('speakers_count')}")
    
    # 3. Récupérer les locuteurs actuels
    print(f"\n2. Récupération des locuteurs actuels")
    speakers_data = get_meeting_speakers(token, MEETING_ID)
    if not speakers_data:
        print("Impossible de récupérer les locuteurs")
        return
    
    print(f"   Nombre de locuteurs personnalisés: {len(speakers_data.get('speakers', []))}")
    for speaker in speakers_data.get('speakers', []):
        print(f"   - {speaker['speaker_id']}: {speaker['custom_name']}")
    
    # 4. Compter les occurrences AVANT le renommage
    transcript_before = meeting_data.get('transcript_text', '')
    old_name = None
    for speaker in speakers_data.get('speakers', []):
        if speaker['speaker_id'] == SPEAKER_ID:
            old_name = speaker['custom_name']
            break
    
    if old_name:
        occurrences_before = count_speaker_occurrences(transcript_before, old_name)
        print(f"\n3. Occurrences de '{old_name}' AVANT renommage: {occurrences_before}")
    else:
        print(f"\n3. Aucun nom personnalisé trouvé pour {SPEAKER_ID}")
        occurrences_before = 0
    
    # 5. Renommer le locuteur
    print(f"\n4. Renommage du locuteur {SPEAKER_ID} en '{NEW_NAME}'")
    result = set_meeting_speaker(token, MEETING_ID, SPEAKER_ID, NEW_NAME)
    if not result:
        print("Échec du renommage")
        return
    
    print(f"   Renommage réussi: {result}")
    
    # 6. Attendre un peu pour que la mise à jour soit traitée
    print("\n5. Attente de 3 secondes pour la mise à jour...")
    time.sleep(3)
    
    # 7. Récupérer les données mises à jour
    print(f"\n6. Vérification des données mises à jour")
    updated_meeting = get_meeting_details(token, MEETING_ID)
    if not updated_meeting:
        print("Impossible de récupérer les données mises à jour")
        return
    
    # 8. Compter les occurrences APRÈS le renommage
    transcript_after = updated_meeting.get('transcript_text', '')
    occurrences_after_new = count_speaker_occurrences(transcript_after, NEW_NAME)
    occurrences_after_old = count_speaker_occurrences(transcript_after, old_name) if old_name else 0
    
    print(f"   Occurrences de '{NEW_NAME}' APRÈS renommage: {occurrences_after_new}")
    if old_name:
        print(f"   Occurrences de '{old_name}' APRÈS renommage: {occurrences_after_old}")
    
    # 9. Analyse des résultats
    print(f"\n=== RÉSULTATS ===")
    if occurrences_after_new > 0:
        print(f"✅ SUCCÈS: Le nouveau nom '{NEW_NAME}' apparaît {occurrences_after_new} fois")
        if old_name and occurrences_after_old == 0:
            print(f"✅ SUCCÈS: L'ancien nom '{old_name}' n'apparaît plus")
        elif old_name and occurrences_after_old > 0:
            print(f"⚠️  ATTENTION: L'ancien nom '{old_name}' apparaît encore {occurrences_after_old} fois")
        
        if occurrences_before > 0 and occurrences_after_new >= occurrences_before:
            print(f"✅ SUCCÈS: Le nombre d'occurrences est conservé ({occurrences_before} → {occurrences_after_new})")
        else:
            print(f"⚠️  ATTENTION: Le nombre d'occurrences a changé ({occurrences_before} → {occurrences_after_new})")
    else:
        print(f"❌ ÉCHEC: Le nouveau nom '{NEW_NAME}' n'apparaît pas dans la transcription")
        print("   Le problème de disparition des locuteurs persiste")
    
    # 10. Afficher un échantillon de la transcription pour debug
    if transcript_after:
        lines = transcript_after.split('\n')
        print(f"\n=== ÉCHANTILLON DE TRANSCRIPTION (10 premières lignes) ===")
        for i, line in enumerate(lines[:10]):
            if line.strip():
                print(f"{i+1:2d}: {line}")
    
    print(f"\n=== Test terminé ===")

if __name__ == "__main__":
    main() 