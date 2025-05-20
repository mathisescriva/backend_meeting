"""Script de test direct pour AssemblyAI avec la clu00e9 API fournie"""

import os
import sys
import time
import requests
import json

# Utiliser directement la clu00e9 API fournie
ASSEMBLYAI_API_KEY = "3419005ee6924e08a14235043cabcd4e"

def upload_file_to_assemblyai(file_path):
    """Uploade un fichier audio vers AssemblyAI"""
    print(f"Upload du fichier {file_path} vers AssemblyAI")
    
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    with open(file_path, "rb") as f:
        response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            data=f
        )
    
    if response.status_code == 200:
        upload_url = response.json()["upload_url"]
        print(f"Fichier uploadu00e9 avec succu00e8s, URL: {upload_url}")
        return upload_url
    else:
        print(f"Erreur lors de l'upload: {response.status_code} - {response.text}")
        raise Exception(f"Erreur lors de l'upload vers AssemblyAI: {response.status_code} - {response.text}")

def start_transcription(audio_url):
    """Du00e9marre une transcription avec AssemblyAI"""
    print(f"Du00e9marrage de la transcription pour l'URL: {audio_url}")
    
    headers = {
        "authorization": ASSEMBLYAI_API_KEY,
        "content-type": "application/json"
    }
    
    json_data = {
        "audio_url": audio_url,
        "speaker_labels": True,
        "language_code": "fr"
    }
    
    response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers=headers,
        json=json_data
    )
    
    if response.status_code == 200:
        transcript_id = response.json()["id"]
        print(f"Transcription du00e9marru00e9e avec succu00e8s, ID: {transcript_id}")
        return transcript_id
    else:
        print(f"Erreur lors du du00e9marrage de la transcription: {response.status_code} - {response.text}")
        raise Exception(f"Erreur lors du du00e9marrage de la transcription: {response.status_code} - {response.text}")

def check_transcription_status(transcript_id):
    """Vu00e9rifie le statut d'une transcription AssemblyAI"""
    print(f"Vu00e9rification du statut de la transcription {transcript_id}")
    
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    response = requests.get(
        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        status = result["status"]
        print(f"Statut de la transcription {transcript_id}: {status}")
        return result
    else:
        print(f"Erreur lors de la vu00e9rification du statut: {response.status_code} - {response.text}")
        raise Exception(f"Erreur lors de la vu00e9rification du statut: {response.status_code} - {response.text}")

def main():
    """Fonction principale"""
    if len(sys.argv) < 2:
        print("Usage: python test_direct_assemblyai.py <file_path>")
        print("Example: python test_direct_assemblyai.py test_audio.mp3")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"Le fichier {file_path} n'existe pas!")
        sys.exit(1)
    
    try:
        # Uploader le fichier
        upload_url = upload_file_to_assemblyai(file_path)
        
        # Du00e9marrer la transcription
        transcript_id = start_transcription(upload_url)
        
        # Vu00e9rifier le statut pu00e9riodiquement
        max_checks = 10
        for i in range(max_checks):
            print(f"\nVu00e9rification {i+1}/{max_checks}")
            result = check_transcription_status(transcript_id)
            
            status = result["status"]
            if status == "completed":
                print("\nTranscription terminu00e9e avec succu00e8s!")
                print("\nTexte de la transcription:")
                print(result["text"])
                
                # Afficher les informations sur les locuteurs si disponibles
                if "utterances" in result and result["utterances"]:
                    print("\nTexte par locuteur:")
                    for utterance in result["utterances"]:
                        print(f"Speaker {utterance['speaker']}: {utterance['text']}")
                
                break
            elif status == "error":
                print(f"\nErreur lors de la transcription: {result.get('error')}")
                break
            
            print("En attente de la transcription...")
            time.sleep(15)  # Attendre 15 secondes avant la prochaine vu00e9rification
        
        if status not in ["completed", "error"]:
            print("\nDu00e9lai d'attente du00e9passu00e9, la transcription est toujours en cours")
            print("Vous pouvez vu00e9rifier le statut plus tard avec l'ID de transcription:")
            print(transcript_id)
    
    except Exception as e:
        print(f"\nErreur: {str(e)}")

if __name__ == "__main__":
    main()
