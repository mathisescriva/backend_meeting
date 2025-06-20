#!/usr/bin/env python3

import requests
import json
import time
import os

# Configuration
BASE_URL = "http://localhost:8001"
TEST_USER = {
    "email": "test.rename.api@example.com",
    "password": "password123",
    "full_name": "Test Rename API User"
}

def create_user():
    """Crée un utilisateur de test"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json=TEST_USER,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            print("✅ Utilisateur créé avec succès!")
            return True
        elif response.status_code == 400 and "already registered" in response.text:
            print("ℹ️ Utilisateur existe déjà")
            return True
        else:
            print(f"❌ Erreur création: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def login():
    """Connexion au système"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={
                "username": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("✅ Connexion réussie!")
            return token
        else:
            print(f"❌ Erreur connexion: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

def upload_test_meeting(token):
    """Upload une réunion de test (utilise un fichier audio factice)"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Créer un fichier audio factice pour le test
    test_audio_content = b"fake audio content for testing"
    
    files = {
        "file": ("test_audio.mp3", test_audio_content, "audio/mpeg")
    }
    data = {
        "title": "Test réunion pour re-renommage"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/meetings/upload",
            headers=headers,
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            meeting = response.json()
            print(f"✅ Réunion créée: {meeting.get('id')}")
            return meeting
        else:
            print(f"❌ Erreur upload: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

def create_fake_completed_meeting(token):
    """Crée une réunion factice avec transcription complétée directement en DB"""
    import sqlite3
    import uuid
    from datetime import datetime
    
    # Récupérer l'ID utilisateur
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
        if response.status_code != 200:
            print("❌ Impossible de récupérer l'ID utilisateur")
            return None
        
        user_id = response.json()["id"]
        meeting_id = str(uuid.uuid4())
        
        # Insérer directement en DB
        conn = sqlite3.connect("app.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO meetings (id, user_id, title, transcript_status, transcript_text, speakers_count, created_at)
            VALUES (?, ?, ?, 'completed', ?, 4, ?)
        """, (
            meeting_id,
            user_id,
            "Test Meeting pour Re-renommage",
            "Speaker A: Bonjour tout le monde. Speaker B: Salut! Speaker C: Comment allez-vous? Speaker D: Très bien merci!",
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Réunion factice créée: {meeting_id}")
        return {"id": meeting_id, "title": "Test Meeting pour Re-renommage"}
        
    except Exception as e:
        print(f"❌ Erreur création réunion factice: {str(e)}")
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
    print("=== Test de re-renommage via API ===\n")
    
    # 1. Créer utilisateur
    print("1. Création de l'utilisateur...")
    if not create_user():
        return
    
    # 2. Connexion
    print("\n2. Connexion...")
    token = login()
    if not token:
        return
    
    # 3. Créer une réunion factice
    print("\n3. Création d'une réunion de test...")
    meeting = create_fake_completed_meeting(token)
    if not meeting:
        return
    
    meeting_id = meeting["id"]
    speaker_id = "Speaker D"
    test_names = ["Premier nom API", "Deuxième nom API", "Troisième nom API"]
    
    # 4. État initial
    print(f"\n4. État initial des speakers pour la réunion {meeting_id}:")
    speakers = get_speakers(token, meeting_id)
    if speakers:
        for speaker in speakers.get("speakers", []):
            if speaker["speaker_id"] == speaker_id:
                print(f"   {speaker_id}: {speaker['custom_name']}")
                break
        else:
            print(f"   {speaker_id}: (pas de nom personnalisé)")
    
    # 5. Test de renommages successifs
    for i, new_name in enumerate(test_names, 1):
        print(f"\n{i+4}. Renommage en '{new_name}':")
        
        # Renommer
        result = rename_speaker(token, meeting_id, speaker_id, new_name)
        if result:
            print(f"   ✅ Renommage réussi")
            
            # Vérifier
            speakers = get_speakers(token, meeting_id)
            if speakers:
                for speaker in speakers.get("speakers", []):
                    if speaker["speaker_id"] == speaker_id:
                        current_name = speaker['custom_name']
                        print(f"   Nom actuel: {current_name}")
                        if current_name == new_name:
                            print(f"   ✅ Nom correctement mis à jour via API")
                        else:
                            print(f"   ❌ ERREUR: Nom attendu '{new_name}', obtenu '{current_name}'")
                        break
                else:
                    print(f"   ❌ ERREUR: Speaker {speaker_id} non trouvé")
        else:
            print(f"   ❌ Échec du renommage")
        
        # Attendre un peu entre les tests
        time.sleep(0.5)
    
    print(f"\n=== Test terminé ===")

if __name__ == "__main__":
    main() 