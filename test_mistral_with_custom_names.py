#!/usr/bin/env python3
"""
Script de test pour vérifier que la génération de comptes rendus avec Mistral AI 
utilise bien les noms personnalisés des participants.
"""

import os
import sys
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
LOG_FILE = f"test_logs/mistral_custom_names_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Créer le dossier de logs s'il n'existe pas
os.makedirs("test_logs", exist_ok=True)

def log(message, level="INFO"):
    """Log un message avec timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    
    # Écrire dans le fichier de log
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def login():
    """Se connecter et récupérer un token d'authentification"""
    log("Tentative de connexion...")
    
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login/json", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            log("✅ Connexion réussie")
            return token
        else:
            log(f"❌ Erreur de connexion: {response.status_code}", "ERROR")
            log(f"Réponse: {response.text}", "ERROR")
            return None
    except Exception as e:
        log(f"❌ Erreur lors de la connexion: {str(e)}", "ERROR")
        return None

def get_meetings_with_transcripts(token):
    """Récupérer les réunions avec transcription complète"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/meetings", headers=headers)
        
        if response.status_code == 200:
            meetings = response.json()
            
            # Filtrer les réunions avec transcription complète
            completed_meetings = [
                meeting for meeting in meetings 
                if meeting.get("transcript_status") == "completed" and meeting.get("transcript_text")
            ]
            
            log(f"✅ {len(completed_meetings)} réunions avec transcription complète trouvées")
            return completed_meetings
        else:
            log(f"❌ Erreur récupération réunions: {response.status_code}", "ERROR")
            return []
    except Exception as e:
        log(f"❌ Erreur lors de la récupération des réunions: {str(e)}", "ERROR")
        return []

def get_meeting_speakers(token, meeting_id):
    """Récupérer les locuteurs personnalisés d'une réunion"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/speakers", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            log(f"❌ Erreur récupération locuteurs: {response.status_code}", "ERROR")
            return None
    except Exception as e:
        log(f"❌ Erreur lors de la récupération des locuteurs: {str(e)}", "ERROR")
        return None

def generate_summary(token, meeting_id):
    """Générer un compte rendu pour une réunion"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(f"{BASE_URL}/meetings/{meeting_id}/generate-summary", headers=headers)
        
        if response.status_code == 200:
            log("✅ Génération de compte rendu lancée")
            return True
        else:
            log(f"❌ Erreur génération compte rendu: {response.status_code}", "ERROR")
            log(f"Réponse: {response.text}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Erreur lors de la génération du compte rendu: {str(e)}", "ERROR")
        return False

def wait_for_summary_completion(token, meeting_id, max_wait_time=300):
    """Attendre que la génération du compte rendu soit terminée"""
    headers = {"Authorization": f"Bearer {token}"}
    start_time = datetime.now()
    
    log(f"⏳ Attente de la génération du compte rendu (max {max_wait_time}s)...")
    
    while True:
        try:
            response = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers=headers)
            
            if response.status_code == 200:
                meeting = response.json()
                summary_status = meeting.get("summary_status")
                
                if summary_status == "completed":
                    log("✅ Compte rendu généré avec succès")
                    return meeting.get("summary_text")
                elif summary_status == "error":
                    log("❌ Erreur lors de la génération du compte rendu", "ERROR")
                    return None
                
                # Vérifier le timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > max_wait_time:
                    log("⏰ Timeout lors de l'attente du compte rendu", "WARNING")
                    return None
                
                # Attendre 5 secondes avant de vérifier à nouveau
                import time
                time.sleep(5)
            else:
                log(f"❌ Erreur lors de la vérification du statut: {response.status_code}", "ERROR")
                return None
        except Exception as e:
            log(f"❌ Erreur lors de la vérification du statut: {str(e)}", "ERROR")
            return None

def main():
    """Fonction principale du test"""
    log("=== DÉBUT DU TEST DE GÉNÉRATION DE COMPTE RENDU AVEC NOMS PERSONNALISÉS ===")
    
    # Se connecter
    token = login()
    if not token:
        log("❌ Impossible de continuer sans token", "ERROR")
        return
    
    # Récupérer les réunions avec transcription
    meetings = get_meetings_with_transcripts(token)
    if not meetings:
        log("❌ Aucune réunion avec transcription trouvée", "ERROR")
        return
    
    # Prendre la première réunion
    meeting = meetings[0]
    meeting_id = meeting["id"]
    meeting_title = meeting.get("title", "Sans titre")
    
    log(f"📋 Test avec la réunion: {meeting_title} (ID: {meeting_id})")
    
    # Vérifier s'il y a des locuteurs personnalisés
    speakers_data = get_meeting_speakers(token, meeting_id)
    if speakers_data and speakers_data.get("speakers"):
        log("👥 Locuteurs personnalisés trouvés:")
        for speaker in speakers_data["speakers"]:
            log(f"   • {speaker['speaker_id']} → {speaker['custom_name']}")
    else:
        log("ℹ️ Aucun locuteur personnalisé défini pour cette réunion")
    
    # Afficher un extrait de la transcription actuelle
    transcript_text = meeting.get("transcript_text", "")
    log(f"📄 Extrait de la transcription ({len(transcript_text)} caractères):")
    log(f"   {transcript_text[:200]}...")
    
    # Générer le compte rendu
    log("\n🚀 Lancement de la génération du compte rendu...")
    if generate_summary(token, meeting_id):
        # Attendre la completion
        summary_text = wait_for_summary_completion(token, meeting_id)
        
        if summary_text:
            log("\n✅ COMPTE RENDU GÉNÉRÉ AVEC SUCCÈS!")
            log("📝 Contenu du compte rendu:")
            log("=" * 50)
            log(summary_text)
            log("=" * 50)
            
            # Vérifier si les noms personnalisés apparaissent dans le compte rendu
            if speakers_data and speakers_data.get("speakers"):
                log("\n🔍 Vérification de la présence des noms personnalisés dans le compte rendu:")
                for speaker in speakers_data["speakers"]:
                    custom_name = speaker["custom_name"]
                    if custom_name in summary_text:
                        log(f"   ✅ '{custom_name}' trouvé dans le compte rendu")
                    else:
                        log(f"   ❌ '{custom_name}' NON trouvé dans le compte rendu")
        else:
            log("❌ Échec de la génération du compte rendu", "ERROR")
    else:
        log("❌ Impossible de lancer la génération du compte rendu", "ERROR")
    
    log(f"\n=== FIN DU TEST ===")
    log(f"📄 Rapport détaillé: {LOG_FILE}")

if __name__ == "__main__":
    main() 