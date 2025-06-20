import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:8001"
EMAIL = "testing.admin@gilbert.fr"  # Utilisateur par défaut
PASSWORD = "Gilbert2025!"          # Mot de passe par défaut

def login():
    """Se connecter et obtenir un token JWT"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD}
    )
    if response.status_code != 200:
        print(f"Erreur de connexion: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    return response.json()["access_token"]

def get_meetings(token):
    """Récupère la liste des réunions"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/meetings", headers=headers)
    if response.status_code != 200:
        print(f"Erreur lors de la récupération des réunions: {response.status_code}")
        print(response.text)
        return None
    
    # L'API renvoie directement une liste de réunions
    return response.json()

def get_meeting_details(token, meeting_id):
    """Récupère les détails d'une réunion spécifique"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}", headers=headers)
    if response.status_code != 200:
        print(f"Erreur lors de la récupération des détails de la réunion: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def get_meeting_speakers(token, meeting_id):
    """Récupère les noms personnalisés des locuteurs pour une réunion"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/speakers", headers=headers)
    if response.status_code != 200:
        print(f"Erreur lors de la récupération des locuteurs: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

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
    
    if response.status_code != 200:
        print(f"Erreur lors de la définition du nom personnalisé: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def update_transcript_with_custom_names(token, meeting_id):
    """Met à jour la transcription avec les noms personnalisés"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/meetings/{meeting_id}/speakers/update-transcript", headers=headers)
    if response.status_code != 200:
        print(f"Erreur lors de la mise à jour de la transcription: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def delete_meeting_speaker(token, meeting_id, speaker_id):
    """Supprime un nom personnalisé pour un locuteur"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(f"{BASE_URL}/meetings/{meeting_id}/speakers/{speaker_id}", headers=headers)
    if response.status_code != 200:
        print(f"Erreur lors de la suppression du nom personnalisé: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def main():
    # Connexion
    print("Connexion au système...")
    token = login()
    print("Connexion réussie!")
    
    # Récupérer les réunions
    print("\nRécupération des réunions...")
    meetings = get_meetings(token)
    
    if not meetings or len(meetings) == 0:
        print("Aucune réunion trouvée. Veuillez d'abord créer une réunion avec une transcription.")
        return
    
    # Afficher les réunions disponibles
    print("\nRéunions disponibles:")
    for i, meeting in enumerate(meetings):
        print(f"{i+1}. {meeting.get('title', 'Sans titre')} (ID: {meeting['id']}, Status: {meeting.get('transcript_status', 'inconnu')})")
    
    # Sélectionner automatiquement la première réunion pour les tests
    meeting_index = 0
    print(f"\nSélection automatique de la réunion {meeting_index + 1}")
    meeting_id = meetings[meeting_index]["id"]
    
    # Récupérer les détails de la réunion
    meeting_details = get_meeting_details(token, meeting_id)
    
    if not meeting_details:
        print("Impossible de récupérer les détails de la réunion.")
        return
    
    # Vérifier si la transcription est complète
    if meeting_details["transcript_status"] != "completed":
        print(f"La transcription n'est pas terminée (status: {meeting_details['transcript_status']})")
        return
    
    # Afficher un extrait de la transcription originale
    print("\nExtrait de la transcription originale:")
    transcript_text = meeting_details.get("transcript_text", "")
    print(transcript_text[:500] + "..." if len(transcript_text) > 500 else transcript_text)
    
    # Récupérer les locuteurs actuels de la réunion
    print("\nRécupération des locuteurs actuels...")
    speakers_data = get_meeting_speakers(token, meeting_id)
    
    if speakers_data and "speakers" in speakers_data:
        print("\nLocuteurs actuellement définis:")
        for speaker in speakers_data["speakers"]:
            print(f"Locuteur {speaker['speaker_id']}: {speaker['custom_name']}")
    else:
        print("Aucun nom personnalisé défini pour cette réunion.")
    
    # Analyser le texte pour trouver les locuteurs uniques
    detected_speakers = set()
    for line in transcript_text.split('\n'):
        if line.startswith("Speaker "):
            parts = line.split(":", 1)
            if len(parts) > 0:
                speaker_id = parts[0].replace("Speaker ", "").strip()
                detected_speakers.add(speaker_id)
    
    print("\nLocuteurs détectés dans la transcription:", ", ".join(detected_speakers))
    
    # Automatiser l'ajout de noms personnalisés
    print("\nAutomatisation du test de renommage des locuteurs...")
    
    # Dictionnaire de noms personnalisés pour les tests
    custom_names = {
        "A": "Monsieur le Maire",
        "B": "Conseiller Martin",
        "C": "Adjointe Dubois",
        "D": "Secrétaire Legrand"  
    }
    
    # Ajouter des noms personnalisés pour chaque locuteur détecté
    print("\nDéfinition des noms personnalisés:")
    for speaker_id in detected_speakers:
        if speaker_id in custom_names:
            custom_name = custom_names[speaker_id]
            result = set_meeting_speaker(token, meeting_id, speaker_id, custom_name)
            print(f"Nom personnalisé défini pour {speaker_id}: {custom_name}")
    
    # Mettre à jour la transcription avec les nouveaux noms
    print("\nMise à jour de la transcription avec les noms personnalisés...")
    result = update_transcript_with_custom_names(token, meeting_id)
    if result:
        print("Transcription mise à jour avec succès!")
        
        # Récupérer la version mise à jour
        meeting_details = get_meeting_details(token, meeting_id)
        print("\nExtrait de la transcription mise à jour:")
        print(meeting_details["transcript_text"][:500])
        
    # Récupérer la liste mise à jour des locuteurs
    speakers = get_meeting_speakers(token, meeting_id)
    print("\nLocuteurs personnalisés après mise à jour:")
    for speaker in speakers.get("speakers", []):
        print(f"Locuteur {speaker['speaker_id']}: {speaker['custom_name']}")
        
    # Test de suppression d'un nom personnalisé
    print("\nTest de suppression d'un nom personnalisé...")
    detected_speakers_list = list(detected_speakers)
    if detected_speakers_list:
        speaker_to_delete = detected_speakers_list[0]  # Supprimer le premier locuteur
        result = delete_meeting_speaker(token, meeting_id, speaker_to_delete)
        if result:
            print(f"Nom personnalisé supprimé pour le locuteur {speaker_to_delete}")
            
            # Mettre à jour la transcription après la suppression
            result = update_transcript_with_custom_names(token, meeting_id)
            if result:
                print("\nTranscription mise à jour après suppression!")
                
                # Vérifier les locuteurs restants
                speakers = get_meeting_speakers(token, meeting_id)
                print("\nLocuteurs personnalisés après suppression:")
                for speaker in speakers.get("speakers", []):
                    print(f"Locuteur {speaker['speaker_id']}: {speaker['custom_name']}")
                    
                # Récupérer la version finale de la transcription
                meeting_details = get_meeting_details(token, meeting_id)
                print("\nExtrait de la transcription finale:")
                print(meeting_details["transcript_text"][:500])

    print("\nTest terminé!")

if __name__ == "__main__":
    main()
