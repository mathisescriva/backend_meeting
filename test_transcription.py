from app.services.assemblyai import check_transcription_status, process_transcription
import json
import time
from unittest.mock import patch, MagicMock

# ID de la transcription déjà créée
transcript_id = '6918d380-0d67-46aa-a5fb-95d20b69d9e1'

# Récupérer le statut
status = check_transcription_status(transcript_id)

# Infos de base
print(f"Statut: {status.get('status')}")
print(f"Durée audio: {status.get('audio_duration')} secondes")
print(f"Nombre de mots: {len(status.get('words', []))}")

# Vérifier les utterances
utterances = status.get('utterances', [])
if utterances:
    print(f"Nombre d'utterances: {len(utterances)}")
    print("\nLes 3 premières utterances:")
    for i, u in enumerate(utterances[:3]):
        print(f"Speaker {u.get('speaker')}: {u.get('text')[:100]}...")
else:
    print("Pas d'utterances détectées")

# Test de process_transcription
print("\nTest de process_transcription:")

# URL du fichier audio utilisé précédemment
audio_url = "https://cdn.assemblyai.com/upload/f1c2d390-e381-4c3c-9c90-84b2fe4958a4"

# Fonction pour capturer les appels à update_meeting
captured_text = None
def mock_update_meeting(meeting_id, **kwargs):
    global captured_text
    captured_text = kwargs.get('text', '')
    print(f"Mise à jour de la base de données simulée pour meeting_id: {meeting_id}")
    return True

# Création d'un mock pour la fonction start_transcription qui retourne notre transcript_id
def mock_start_transcription(*args, **kwargs):
    return transcript_id

# Application des mocks
with patch('app.services.assemblyai.start_transcription', side_effect=mock_start_transcription):
    with patch('app.services.assemblyai.update_meeting', side_effect=mock_update_meeting):
        # Appel de process_transcription avec un faux meeting_id
        process_transcription(meeting_id="test-meeting", file_url=audio_url, user_id="testuser")

# Afficher le texte formaté qui aurait été enregistré en BDD
print("\nTexte formaté résultant (premiers 500 caractères):")
if captured_text:
    print(captured_text[:500] + "..." if len(captured_text) > 500 else captured_text)
else:
    print("Aucun texte capturé")
