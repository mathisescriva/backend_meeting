import requests
import sys

# Utiliser directement la clu00e9 API fournie
ASSEMBLYAI_API_KEY = "3419005ee6924e08a14235043cabcd4e"

def check_transcription_status(transcript_id):
    """Vu00e9rifie le statut d'une transcription AssemblyAI"""
    print(f"Vu00e9rification du statut de la transcription {transcript_id}")
    
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    try:
        response = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result["status"]
            print(f"Statut de la transcription: {status}")
            
            if status == "completed":
                print("\nTexte de la transcription:")
                print(result.get("text", ""))
                
                # Afficher les informations sur les locuteurs si disponibles
                if "utterances" in result and result["utterances"]:
                    print("\nTexte par locuteur:")
                    for utterance in result["utterances"]:
                        print(f"Speaker {utterance['speaker']}: {utterance['text']}")
            elif status == "error":
                print(f"\nErreur lors de la transcription: {result.get('error')}")
            
            return result
        else:
            print(f"Erreur: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Erreur lors de la vu00e9rification du statut: {str(e)}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_transcription_status.py <transcript_id>")
        sys.exit(1)
    
    transcript_id = sys.argv[1]
    check_transcription_status(transcript_id)

if __name__ == "__main__":
    main()
