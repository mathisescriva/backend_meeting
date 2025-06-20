#!/usr/bin/env python3
"""
Test pour vérifier que la correction fonctionne et que les noms personnalisés
apparaissent maintenant dans la transcription
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8001"
EMAIL = "testing.admin@gilbert.fr"
PASSWORD = "Gilbert2025!"

def test_custom_names_display():
    print("🔍 TEST - Vérification que les noms personnalisés s'affichent maintenant")
    print("=" * 70)
    
    # 1. Se connecter
    print("1️⃣ Authentification...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD}
    )
    
    if response.status_code != 200:
        print(f"❌ Erreur de connexion: {response.status_code}")
        return False
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Connexion réussie")
    
    # 2. Récupérer les réunions
    print("\n2️⃣ Récupération des réunions...")
    response = requests.get(f"{BASE_URL}/meetings", headers=headers)
    meetings = response.json()
    
    # Trouver une réunion avec transcription complète
    test_meeting = None
    for meeting in meetings:
        if meeting.get("transcript_status") == "completed":
            test_meeting = meeting
            break
    
    if not test_meeting:
        print("❌ Aucune réunion avec transcription complète")
        return False
    
    meeting_id = test_meeting["id"]
    print(f"✅ Réunion sélectionnée: {test_meeting['title']} (ID: {meeting_id})")
    
    # 3. Vérifier les locuteurs personnalisés
    print("\n3️⃣ Vérification des locuteurs personnalisés...")
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/speakers", headers=headers)
    
    if response.status_code == 200:
        speakers_data = response.json()
        custom_speakers = speakers_data.get("speakers", [])
        
        print("Locuteurs personnalisés:")
        for speaker in custom_speakers:
            print(f"  • {speaker['speaker_id']} → {speaker['custom_name']}")
    else:
        print(f"❌ Erreur récupération locuteurs: {response.status_code}")
        return False
    
    if not custom_speakers:
        print("ℹ️ Aucun locuteur personnalisé - Test non applicable")
        return True
    
    # 4. Récupérer la transcription AVANT la correction
    print(f"\n4️⃣ Récupération de la transcription...")
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Erreur récupération réunion: {response.status_code}")
        return False
    
    meeting_details = response.json()
    transcript_text = meeting_details.get("transcript_text", "")
    
    print(f"📄 Transcription récupérée ({len(transcript_text)} caractères)")
    
    # 5. Analyser si les noms personnalisés sont maintenant présents
    print(f"\n5️⃣ Vérification des noms personnalisés dans la transcription...")
    
    success_count = 0
    total_speakers = len(custom_speakers)
    
    for speaker in custom_speakers:
        custom_name = speaker['custom_name']
        speaker_id = speaker['speaker_id']
        
        # Compter les occurrences
        count_custom = transcript_text.count(f"{custom_name}:")
        count_original = transcript_text.count(f"{speaker_id}:")
        
        print(f"\nLocuteur {speaker_id} → {custom_name}:")
        print(f"  • Occurrences de '{custom_name}:': {count_custom}")
        print(f"  • Occurrences de '{speaker_id}:': {count_original}")
        
        if count_custom > 0:
            print(f"  ✅ Le nom personnalisé '{custom_name}' apparaît dans la transcription!")
            success_count += 1
        else:
            print(f"  ❌ Le nom personnalisé '{custom_name}' n'apparaît toujours PAS")
            
            if count_original > 0:
                print(f"  ⚠️ L'ancien format 'Speaker {speaker_id}' est encore présent")
    
    # 6. Afficher le résumé
    print(f"\n6️⃣ Résumé des résultats...")
    
    if success_count == total_speakers:
        print(f"🎉 SUCCÈS COMPLET! Tous les {total_speakers} locuteurs personnalisés apparaissent dans la transcription")
        result = True
    elif success_count > 0:
        print(f"🔄 SUCCÈS PARTIEL: {success_count}/{total_speakers} locuteurs personnalisés apparaissent")
        result = True
    else:
        print(f"❌ ÉCHEC: Aucun des {total_speakers} locuteurs personnalisés n'apparaît")
        result = False
    
    # 7. Montrer un extrait de la transcription
    print(f"\n7️⃣ Extrait de la transcription actuelle:")
    lines = transcript_text.split('\n')
    speaker_lines = [line for line in lines if ':' in line and line.strip()][:5]
    
    for i, line in enumerate(speaker_lines, 1):
        print(f"  {i}. {line[:100]}{'...' if len(line) > 100 else ''}")
    
    print("\n" + "=" * 70)
    return result

if __name__ == "__main__":
    success = test_custom_names_display()
    if success:
        print("✅ Le problème semble être résolu!")
    else:
        print("❌ Le problème persiste.")
    
    print("🏁 TEST TERMINÉ") 