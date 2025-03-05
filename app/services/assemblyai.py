import requests
import time
import threading
import os
import json
from pathlib import Path
from ..core.config import settings
from ..db.queries import update_meeting
from fastapi.logger import logger

# API endpoints and key
ASSEMBLY_AI_API_KEY = settings.ASSEMBLYAI_API_KEY
ASSEMBLY_AI_API_URL = 'https://api.assemblyai.com/v2'

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
                if utterances:
                    # Formater le texte avec les interlocuteurs
                    formatted_text = []
                    for utterance in utterances:
                        speaker = utterance.get('speaker', 'Unknown')
                        text = utterance.get('text', '')
                        formatted_text.append(f"Speaker {speaker}: {text}")
                    
                    transcription_text = "\n".join(formatted_text)
                
                # Mettre à jour la base de données
                update_data = {
                    "transcript_text": transcription_text,
                    "transcript_status": "completed"
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
                
                # Récupérer les informations sur les interlocuteurs si disponibles
                utterances = transcript_response.get('utterances', [])
                if utterances:
                    # Formater le texte avec les interlocuteurs
                    formatted_text = []
                    for utterance in utterances:
                        speaker = utterance.get('speaker', 'Unknown')
                        text = utterance.get('text', '')
                        formatted_text.append(f"Speaker {speaker}: {text}")
                    
                    transcript_text = "\n".join(formatted_text)
                
                return status, transcript_text
            
            return status, None
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
        raise Exception(f"Échec de l'upload du fichier: {error_msg} (status: {response.status_code})")

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
