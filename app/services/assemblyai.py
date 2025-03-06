import requests
import time
import threading
import os
import json
import subprocess
from pathlib import Path
from ..core.config import settings
from ..db.queries import update_meeting
from fastapi.logger import logger

# API endpoints and key
ASSEMBLY_AI_API_KEY = settings.ASSEMBLYAI_API_KEY
ASSEMBLY_AI_API_URL = 'https://api.assemblyai.com/v2'

def convert_to_wav(input_path: str) -> str:
    """Convertit un fichier audio en WAV en utilisant ffmpeg"""
    try:
        # Créer un nom de fichier de sortie avec l'extension .wav
        output_path = os.path.splitext(input_path)[0] + '_converted.wav'
        
        # Commande ffmpeg pour convertir en WAV
        cmd = [
            'ffmpeg', '-i', input_path,
            '-acodec', 'pcm_s16le',  # Format PCM 16-bit
            '-ar', '44100',          # Sample rate 44.1kHz
            '-ac', '2',              # 2 canaux (stéréo)
            '-y',                    # Écraser le fichier de sortie s'il existe
            output_path
        ]
        
        logger.info(f"Conversion du fichier audio: {' '.join(cmd)}")
        
        # Exécuter la commande
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Erreur lors de la conversion: {result.stderr}")
            raise Exception(f"Échec de la conversion audio: {result.stderr}")
        
        # Vérifier que le fichier de sortie existe et a une taille non nulle
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.error(f"Le fichier converti n'existe pas ou est vide: {output_path}")
            raise Exception("Le fichier converti n'existe pas ou est vide")
            
        logger.info(f"Conversion réussie: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Erreur lors de la conversion audio: {str(e)}")
        raise Exception(f"Échec de la conversion audio: {str(e)}")

def transcribe_meeting(meeting_id: str, file_url: str, user_id: str):
    """
    Transcrit un fichier audio et met à jour la base de données avec les résultats.
    Cette fonction est exécutée dans un thread séparé.
    """
    # Lancer dans un thread pour éviter de bloquer
    thread = threading.Thread(
        target=_process_transcription,
        args=(meeting_id, file_url, user_id)
    )
    thread.daemon = True
    thread.start()
    
def _process_transcription(meeting_id: str, file_url: str, user_id: str):
    """Fonction interne pour traiter la transcription de manière asynchrone"""
    try:
        logger.info(f"Démarrage de la transcription pour la réunion {meeting_id}")
        
        # Mettre à jour le statut en "processing"
        update_meeting(meeting_id, user_id, {"transcript_status": "processing"})
        
        # Si le fichier est local, nous devons d'abord l'uploader vers AssemblyAI
        if file_url.startswith("/uploads/"):
            # Chemin complet vers le fichier local
            file_path = settings.UPLOADS_DIR.parent / file_url.lstrip('/')
            
            logger.info(f"Fichier à transcrire : {file_path}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Fichier audio introuvable: {file_path}")
            
            # Convertir le fichier en WAV si nécessaire
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext != '.wav':
                logger.info("Conversion du fichier en WAV...")
                file_path = convert_to_wav(str(file_path))
                logger.info(f"Fichier converti : {file_path}")
                
            logger.info(f"Upload du fichier local vers AssemblyAI: {file_path}")
            
            # 1. Uploader le fichier vers AssemblyAI
            upload_url = _upload_file_to_assemblyai(str(file_path))
            logger.info(f"Fichier uploadé vers AssemblyAI: {upload_url}")
        else:
            # Si c'est une URL distante, l'utiliser directement
            upload_url = file_url
            logger.info(f"Utilisation de l'URL distante: {file_url}")
        
        # 2. Démarrer la transcription
        transcript_id = _start_transcription_assemblyai(upload_url)
        logger.info(f"Transcription lancée avec ID: {transcript_id}")
        
        # 3. Attendre et récupérer le résultat
        max_retries = 30
        retry_delay = 5  # secondes
        
        for attempt in range(max_retries):
            logger.info(f"Vérification du statut, tentative {attempt+1}/{max_retries}")
            
            # Vérifier le statut
            transcript_response = _get_transcription_status_assemblyai(transcript_id)
            status = transcript_response.get('status')
            
            logger.info(f"Statut de la transcription: {status}")
            
            if status == 'completed':
                # Transcription réussie
                transcription_text = transcript_response.get('text', '')
                
                # Récupérer les informations sur les interlocuteurs si disponibles
                utterances = transcript_response.get('utterances', [])
                
                # Extraire la durée de l'audio (en secondes)
                audio_duration = transcript_response.get('audio_duration', 0)
                
                # Calculer le nombre unique de speakers
                speakers_set = set()
                if utterances:
                    # Formater le texte avec les interlocuteurs
                    formatted_text = []
                    for utterance in utterances:
                        speaker = utterance.get('speaker', 'Unknown')
                        speakers_set.add(speaker)
                        text = utterance.get('text', '')
                        formatted_text.append(f"Speaker {speaker}: {text}")
                    
                    transcription_text = "\n".join(formatted_text)
                
                speakers_count = len(speakers_set)
                
                logger.info(f"Durée audio: {audio_duration} secondes, Nombre de participants: {speakers_count}")
                
                # Mettre à jour la base de données
                update_data = {
                    "transcript_text": transcription_text,
                    "transcript_status": "completed",
                    "duration_seconds": int(audio_duration) if audio_duration else None,
                    "speakers_count": speakers_count if speakers_count > 0 else None
                }
                
                update_meeting(meeting_id, user_id, update_data)
                logger.info(f"Transcription terminée pour la réunion {meeting_id}")
                return
                
            elif status == 'error':
                # Erreur de transcription
                error_message = transcript_response.get('error', 'Unknown error')
                logger.error(f"Erreur de transcription: {error_message}")
                
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "error"
                })
                return
            
            # Sinon, attendre et réessayer
            time.sleep(retry_delay)
        
        # Si on arrive ici, c'est que le nombre maximum de tentatives a été atteint
        logger.warning(f"Nombre maximum de tentatives atteint pour la transcription {transcript_id}")
        update_meeting(meeting_id, user_id, {
            "transcript_status": "timeout"
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la transcription: {str(e)}")
        
        # Mettre à jour le statut en cas d'erreur
        try:
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error"
            })
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")

# Versions de fonctions rendues publiques pour les tests
async def upload_file_to_assemblyai(file_path: str, api_key: str = ASSEMBLY_AI_API_KEY):
    """Télécharge un fichier audio vers AssemblyAI et retourne l'URL."""
    upload_endpoint = f"{ASSEMBLY_AI_API_URL}/upload"
    
    headers = {
        "authorization": api_key
    }
    
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                upload_endpoint,
                headers=headers,
                data=f
            )
            
        if response.status_code == 200:
            return response.json()["upload_url"]
        else:
            error_msg = response.json().get('error', 'Unknown error')
            raise Exception(f"Échec de l'upload du fichier à AssemblyAI: {error_msg} (status: {response.status_code})")
    except Exception as e:
        raise Exception(f"Échec de l'upload du fichier à AssemblyAI: {str(e)}")

async def start_transcription(audio_url: str, api_key: str = ASSEMBLY_AI_API_KEY, speaker_labels: bool = True, language_code: str = "fr"):
    """Démarre une transcription sur AssemblyAI et retourne l'ID de la transcription."""
    transcript_endpoint = f"{ASSEMBLY_AI_API_URL}/transcript"
    
    headers = {
        "authorization": api_key,
        "content-type": "application/json"
    }
    
    transcript_request = {
        "audio_url": audio_url,
        "speaker_labels": speaker_labels,
        "language_code": language_code
    }
    
    try:
        response = requests.post(
            transcript_endpoint,
            json=transcript_request,
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()["id"]
        else:
            error_msg = response.json().get('error', 'Unknown error')
            raise Exception(f"Échec du démarrage de la transcription: {error_msg} (status: {response.status_code})")
    except Exception as e:
        raise Exception(f"Échec du démarrage de la transcription: {str(e)}")

async def check_transcription_status(transcript_id: str, api_key: str = ASSEMBLY_AI_API_KEY):
    """Vérifie le statut d'une transcription et retourne le statut et le texte."""
    transcript_endpoint = f"{ASSEMBLY_AI_API_URL}/transcript/{transcript_id}"
    
    headers = {
        "authorization": api_key
    }
    
    try:
        response = requests.get(transcript_endpoint, headers=headers)
        
        if response.status_code == 200:
            transcript_response = response.json()
            status = transcript_response.get('status')
            
            if status == 'completed':
                # Récupérer le texte de transcription
                transcript_text = transcript_response.get('text', '')
                
                # Récupérer la durée audio
                audio_duration = transcript_response.get('audio_duration', 0)
                
                # Récupérer les informations sur les interlocuteurs si disponibles
                utterances = transcript_response.get('utterances', [])
                
                # Calculer le nombre unique de speakers
                speakers_set = set()
                if utterances:
                    # Formater le texte avec les interlocuteurs
                    formatted_text = []
                    for utterance in utterances:
                        speaker = utterance.get('speaker', 'Unknown')
                        speakers_set.add(speaker)
                        text = utterance.get('text', '')
                        formatted_text.append(f"Speaker {speaker}: {text}")
                    
                    transcript_text = "\n".join(formatted_text)
                
                speakers_count = len(speakers_set)
                
                return status, transcript_text, int(audio_duration) if audio_duration else None, speakers_count if speakers_count > 0 else None
            
            return status, None, None, None
        else:
            error_msg = response.json().get('error', 'Unknown error')
            raise Exception(f"Échec de la vérification du statut: {error_msg} (status: {response.status_code})")
    except Exception as e:
        raise Exception(f"Échec de la vérification du statut: {str(e)}")

def _upload_file_to_assemblyai(file_path: str):
    """Version synchrone interne pour l'upload de fichier vers AssemblyAI"""
    upload_endpoint = f"{ASSEMBLY_AI_API_URL}/upload"
    
    headers = {
        "authorization": ASSEMBLY_AI_API_KEY
    }
    
    try:
        logger.info(f"Tentative d'upload du fichier: {file_path}")
        logger.info(f"Taille du fichier: {os.path.getsize(file_path)} bytes")
        logger.info(f"Headers: {headers}")
        
        # Vérifier le type MIME du fichier
        import magic
        mime = magic.Magic(mime=True)
        file_mime = mime.from_file(file_path)
        logger.info(f"Type MIME du fichier: {file_mime}")
        
        def read_file(filename):
            with open(filename, 'rb') as _file:
                while True:
                    data = _file.read(5242880)  # Lire par chunks de 5MB
                    if not data:
                        break
                    yield data
        
        # Envoyer la requête avec les données en streaming
        logger.info("Début de l'upload en streaming...")
        response = requests.post(
            upload_endpoint,
            headers=headers,
            data=read_file(file_path)
        )
        
        logger.info(f"Réponse AssemblyAI - Status: {response.status_code}")
        logger.info(f"Réponse AssemblyAI - Headers: {dict(response.headers)}")
        logger.info(f"Réponse AssemblyAI - Content: {response.text}")
        
        if response.status_code == 200:
            upload_url = response.json()["upload_url"]
            logger.info(f"Upload réussi, URL: {upload_url}")
            return upload_url
        else:
            error_msg = response.json().get('error', 'Unknown error')
            logger.error(f"Échec de l'upload - Status: {response.status_code}, Error: {error_msg}")
            raise Exception(f"Échec de l'upload du fichier: {error_msg} (status: {response.status_code})")
    except Exception as e:
        logger.error(f"Exception lors de l'upload: {str(e)}")
        raise Exception(f"Échec de l'upload du fichier à AssemblyAI: {str(e)}")

def _start_transcription_assemblyai(audio_url: str):
    """Démarre une transcription sur AssemblyAI"""
    transcript_endpoint = f"{ASSEMBLY_AI_API_URL}/transcript"
    
    headers = {
        "authorization": ASSEMBLY_AI_API_KEY,
        "content-type": "application/json"
    }
    
    transcript_request = {
        "audio_url": audio_url,
        "speaker_labels": True,
        "language_code": "fr"  # Langue française par défaut
    }
    
    response = requests.post(
        transcript_endpoint,
        json=transcript_request,
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()["id"]
    else:
        error_msg = response.json().get('error', 'Unknown error')
        raise Exception(f"Échec du démarrage de la transcription: {error_msg} (status: {response.status_code})")

def _get_transcription_status_assemblyai(transcript_id: str):
    """Récupère le statut d'une transcription sur AssemblyAI"""
    transcript_endpoint = f"{ASSEMBLY_AI_API_URL}/transcript/{transcript_id}"
    
    headers = {
        "authorization": ASSEMBLY_AI_API_KEY
    }
    
    response = requests.get(transcript_endpoint, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        error_msg = response.json().get('error', 'Unknown error')
        raise Exception(f"Échec de la récupération du statut: {error_msg} (status: {response.status_code})")
