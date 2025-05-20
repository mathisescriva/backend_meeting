from app.db.queries import get_meetings_by_user, get_meeting
import json
import sys

def list_user_meetings(user_id="1"):  # Utiliser un user_id par défaut pour les tests
    meetings = get_meetings_by_user(user_id)
    print(f"Transcriptions disponibles pour l'utilisateur {user_id}:")
    for m in meetings:
        print(f"ID: {m['id']}, Titre: {m['title']}, Statut: {m['transcript_status']}")
    return meetings

def get_meeting_details(meeting_id, user_id="1"):
    meeting = get_meeting(meeting_id, user_id)
    if meeting:
        print(f"\nDétails de la réunion {meeting_id}:")
        print(f"Titre: {meeting['title']}")
        print(f"Statut: {meeting['transcript_status']}")
        print(f"Nombre de locuteurs: {meeting.get('speakers_count', 'Non spécifié')}")
        
        # Afficher les premiers 500 caractères de la transcription
        if meeting.get('transcript_text'):
            text = meeting['transcript_text']
            print(f"\nDébut de la transcription:")
            print(text[:500] + "..." if len(text) > 500 else text)
            
            # Vérifier si le texte contient des marqueurs "Speaker"
            speakers = set()
            for line in text.split('\n'):
                if line.startswith('Speaker '):
                    speaker = line.split(':')[0].strip()
                    speakers.add(speaker)
            
            if speakers:
                print(f"\nLocuteurs identifiés dans le texte: {', '.join(sorted(speakers))}")
            else:
                print("\nAucun locuteur identifié dans le texte")
        else:
            print("\nPas de transcription disponible")
    else:
        print(f"Réunion avec ID {meeting_id} non trouvée")

if __name__ == "__main__":
    user_id = "1"  # Utiliser un user_id par défaut pour les tests
    meetings = list_user_meetings(user_id)
    
    if len(meetings) > 0:
        print("\nPour voir les détails d'une réunion, entrez son ID:")
        meeting_id = input("> ")
        if meeting_id:
            get_meeting_details(meeting_id, user_id)
    else:
        print("Aucune réunion trouvée pour cet utilisateur")
