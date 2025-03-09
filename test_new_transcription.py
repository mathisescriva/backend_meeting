from app.services.assemblyai import check_transcription_status, process_transcription
import json
import time
import sys

# ID de la transcription
transcript_id = "a7a0c22f-9f49-42e5-9612-7d7b85d5f14f"

def check_status():
    status = check_transcription_status(transcript_id)
    print(f"Statut: {status.get('status')}")
    
    if status.get('status') == 'completed':
        print(f"Durée audio: {status.get('audio_duration')} secondes")
        
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
            
        # Afficher notre implémentation du formatage
        print("\nFormatage du texte selon notre implémentation:")
        
        if utterances:
            formatted_text = []
            for utterance in utterances:
                speaker = utterance.get('speaker', 'Unknown')
                text_segment = utterance.get('text', '')
                formatted_text.append(f"Speaker {speaker}: {text_segment}")
            result = "\n".join(formatted_text)
        else:
            text = status.get('text', '')
            if text and text.strip():
                result = f"Speaker A: {text}"
            else:
                result = "Speaker A: [Transcription vide]"
        
        print(result[:500] + "..." if len(result) > 500 else result)
        
        return True
    else:
        print("La transcription est toujours en cours...")
        return False

# Vérifier le statut toutes les 10 secondes jusqu'à ce que la transcription soit terminée
while True:
    print("\n--- Vérification du statut ---")
    if check_status():
        break
    print("Attente de 10 secondes...")
    time.sleep(10)
