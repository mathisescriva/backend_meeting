from app.services.assemblyai import check_transcription_status
from app.db.queries import update_meeting, get_meeting
import time
import sys
import json

# ID de la transcription AssemblyAI et meeting ID à vérifier
transcript_id = "4b47b5e0-b38c-4eac-a6af-c59b521fe2a9"
meeting_id = "d533975e-f991-4648-8b0b-da3dc83ab0f0"
user_id = "1"

def check_and_process():
    status = check_transcription_status(transcript_id)
    print(f"Statut: {status.get('status')}")
    
    if status.get('status') == 'completed':
        print("Transcription terminée, traitement...")
        
        # Vérifier les utterances
        utterances = status.get('utterances')
        print(f"Utterances: {utterances is not None}")
        
        if utterances:
            print(f"Nombre d'utterances: {len(utterances)}")
            print("\nLes 3 premières utterances:")
            for i, u in enumerate(utterances[:3]):
                print(f"Speaker {u.get('speaker')}: {u.get('text')[:100]}...")
        else:
            print("Pas d'utterances détectées dans la réponse")
        
        # Traiter manuellement la transcription (au lieu d'utiliser process_transcription)
        text = status.get('text', '')
        speakers_set = set()
        
        if utterances and len(utterances) > 0:
            formatted_text = []
            for utterance in utterances:
                speaker = utterance.get('speaker', 'Unknown')
                speakers_set.add(speaker)
                text_segment = utterance.get('text', '')
                # Format uniforme: "Speaker A: texte" avec préfixe "Speaker"
                formatted_text.append(f"Speaker {speaker}: {text_segment}")
            text = "\n".join(formatted_text)
        else:
            # Si pas d'utterances, utiliser le texte brut avec Speaker A
            if not text or text.strip() == "":
                text = "Speaker A: [Transcription vide]"
            else:
                text = f"Speaker A: {text}"
                speakers_set.add("A")
        
        # Mise à jour de la réunion avec les données traitées
        update_data = {
            'transcript_text': text,
            'transcript_status': 'completed',
            'speakers_count': len(speakers_set)
        }
        
        update_result = update_meeting(meeting_id, user_id, update_data)
        print(f"Base de données mise à jour: {update_result}")
        
        return True
    else:
        print("La transcription est toujours en cours...")
        return False

# Vérifier le statut toutes les 10 secondes jusqu'à ce que la transcription soit terminée
tries = 0
max_tries = 30  # 5 minutes max

while tries < max_tries:
    print(f"\n--- Vérification {tries+1}/{max_tries} ---")
    if check_and_process():
        print("Transcription terminée et traitée avec succès!")
        
        # Vérifier que la transcription a bien été enregistrée et contient les speakers
        meeting = get_meeting(meeting_id, user_id)
        if meeting:
            print("\nContenu de la transcription en base de données:")
            text = meeting.get('transcript_text', '')
            print(text[:500] + "..." if len(text) > 500 else text)
            
            # Vérifier si le texte contient des marqueurs "Speaker"
            speakers = set()
            for line in text.split('\n'):
                if line.startswith('Speaker '):
                    speaker = line.split(':')[0].strip()
                    speakers.add(speaker)
            
            if speakers:
                print(f"\nLocuteurs identifiés dans le texte: {', '.join(sorted(speakers))}")
                print(f"Nombre de locuteurs: {meeting.get('speakers_count')}")
            else:
                print("\nAucun locuteur identifié dans le texte")
        
        sys.exit(0)
    
    tries += 1
    print("Attente de 10 secondes...")
    time.sleep(10)

print("Délai d'attente dépassé. La transcription n'est pas encore terminée.")
