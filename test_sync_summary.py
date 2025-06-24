#!/usr/bin/env python3
"""
Script pour tester directement la génération de compte rendu avec les noms personnalisés
"""

import sys
import os
import requests
from datetime import datetime

# Ajouter le répertoire de l'application au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

BASE_URL = "http://localhost:8000"

def login():
    """Se connecter et récupérer un token"""
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login/json", json=login_data)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"❌ Erreur de connexion: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Erreur lors de la connexion: {str(e)}")
        return None

def test_summary_generation():
    """Tester la génération de compte rendu directement"""
    print("=== TEST DIRECT DE GÉNÉRATION DE COMPTE RENDU ===")
    
    # Se connecter
    token = login()
    if not token:
        print("❌ Impossible de continuer sans token")
        return
    
    # ID de notre réunion de test
    meeting_id = "bc96e19f-f7df-4dba-aebb-4ce658309bc2"
    
    print(f"📋 Test avec la réunion ID: {meeting_id}")
    
    # Vérifier l'état actuel
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers=headers)
    
    if response.status_code == 200:
        meeting = response.json()
        print(f"📊 Statut actuel: {meeting.get('summary_status')}")
        
        # Vérifier les locuteurs personnalisés
        speakers_response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/speakers", headers=headers)
        if speakers_response.status_code == 200:
            speakers_data = speakers_response.json()
            if speakers_data and speakers_data.get("speakers"):
                print("👥 Locuteurs personnalisés:")
                for speaker in speakers_data["speakers"]:
                    print(f"   • {speaker['speaker_id']} → {speaker['custom_name']}")
            else:
                print("ℹ️ Aucun locuteur personnalisé")
        
        # Lancer la génération du compte rendu
        print("\n🚀 Lancement de la génération du compte rendu...")
        summary_response = requests.post(f"{BASE_URL}/meetings/{meeting_id}/generate-summary", headers=headers)
        
        if summary_response.status_code == 200:
            print("✅ Génération lancée avec succès")
            
            # Attendre un peu et vérifier le résultat
            import time
            print("⏳ Attente de la génération...")
            
            for i in range(30):  # Attendre maximum 30 secondes
                time.sleep(1)
                check_response = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers=headers)
                
                if check_response.status_code == 200:
                    updated_meeting = check_response.json()
                    status = updated_meeting.get("summary_status")
                    
                    if status == "completed":
                        print("✅ Compte rendu généré avec succès!")
                        summary_text = updated_meeting.get("summary_text", "")
                        
                        print("\n📝 Extrait du compte rendu:")
                        print("=" * 50)
                        print(summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)
                        print("=" * 50)
                        
                        # Vérifier la présence des noms personnalisés
                        if speakers_data and speakers_data.get("speakers"):
                            print("\n🔍 Vérification des noms personnalisés:")
                            for speaker in speakers_data["speakers"]:
                                custom_name = speaker["custom_name"]
                                if custom_name in summary_text:
                                    print(f"   ✅ '{custom_name}' trouvé dans le compte rendu")
                                else:
                                    print(f"   ❌ '{custom_name}' NON trouvé dans le compte rendu")
                        return
                    elif status == "error":
                        print("❌ Erreur lors de la génération du compte rendu")
                        return
                    else:
                        print(f"⏳ Statut: {status} (tentative {i+1}/30)")
                
            print("⏰ Timeout - génération trop longue")
        else:
            print(f"❌ Erreur lors du lancement: {summary_response.status_code}")
            print(f"Réponse: {summary_response.text}")
    else:
        print(f"❌ Erreur lors de la récupération de la réunion: {response.status_code}")

if __name__ == "__main__":
    test_summary_generation() 