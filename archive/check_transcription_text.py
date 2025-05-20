import requests
import json
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
                transcript_text = result.get("text", "")
                print(transcript_text[:500] + "..." if len(transcript_text) > 500 else transcript_text)
                
                # Sauvegarder le ru00e9sultat complet dans un fichier JSON
                with open(f"transcription_{transcript_id}.json", "w") as f:
                    json.dump(result, f, indent=2)
                print(f"\nRu00e9sultat complet sauvegardé dans transcription_{transcript_id}.json")
                
                # Afficher les informations sur les locuteurs si disponibles
                if "utterances" in result and result["utterances"]:
                    print("\nTexte par locuteur (extrait):")
                    for i, utterance in enumerate(result["utterances"][:5]):
                        print(f"Speaker {utterance.get('speaker')}: {utterance.get('text')[:100]}...")
                    if len(result["utterances"]) > 5:
                        print(f"...et {len(result['utterances']) - 5} autres segments")
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
        print("Usage: python check_transcription_text.py <transcript_id>")
        sys.exit(1)
    
    transcript_id = sys.argv[1]
    check_transcription_status(transcript_id)

if __name__ == "__main__":
    main()
