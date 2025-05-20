import assemblyai as aai
from app.db.queries import update_meeting, get_meeting
from app.services.assemblyai import process_completed_transcript
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

# Configuration pour AssemblyAI
ASSEMBLY_AI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
aai.settings.api_key = ASSEMBLY_AI_API_KEY

# Identifiants de la réunion et de la transcription
MEETING_ID = "d4316b2d-cd64-4a2e-8848-99d2fdfaf93b"
USER_ID = "4abe545a-7a8f-4c02-9758-d44db6045ed5"
TRANSCRIPT_ID = "7a82f1d6-67d7-4f2d-a6a2-78972b1e4750"

# Récupérer la transcription depuis AssemblyAI
transcript = aai.Transcript.get_by_id(TRANSCRIPT_ID)
print(f"Statut de la transcription: {transcript.status}")

# Récupérer les informations de la réunion
meeting = get_meeting(MEETING_ID, USER_ID)
print(f"Statut actuel de la réunion: {meeting['transcript_status']}")

# Traiter la transcription complétée et mettre à jour la base de données
if transcript.status == aai.TranscriptStatus.completed:
    print("La transcription est terminée, mise à jour de la base de données...")
    process_completed_transcript(MEETING_ID, USER_ID, transcript)
    
    # Vérifier que la mise à jour a fonctionné
    updated_meeting = get_meeting(MEETING_ID, USER_ID)
    print(f"Nouveau statut de la réunion: {updated_meeting['transcript_status']}")
    print(f"Texte de transcription disponible: {updated_meeting['transcript_text'] is not None}")
    if updated_meeting['transcript_text']:
        print(f"Longueur du texte de transcription: {len(updated_meeting['transcript_text'])} caractères")
        print(f"Début du texte: {updated_meeting['transcript_text'][:200]}...")
else:
    print(f"La transcription n'est pas encore terminée, statut: {transcript.status}")
