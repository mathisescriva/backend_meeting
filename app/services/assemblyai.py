import requests
import time
import threading
import asyncio
import os
import json
import subprocess
from pathlib import Path
from ..core.config import settings
from ..db.queries import update_meeting, get_meeting
from fastapi.logger import logger
import mimetypes
import traceback
from datetime import datetime

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
    Ajoute une réunion à la file d'attente pour transcription.
    
    Args:
        meeting_id: Identifiant de la réunion
        file_url: URL ou chemin vers le fichier audio
        user_id: Identifiant de l'utilisateur
    """
    try:
        # Vérifier si le meeting existe toujours avant de lancer la transcription
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Tentative de transcription d'une réunion qui n'existe pas ou plus: {meeting_id}")
            return
            
        # Vérifier si le fichier existe avant de lancer la transcription
        if file_url.startswith("/uploads/"):
            file_path = settings.UPLOADS_DIR.parent / file_url.lstrip('/')
            if not os.path.exists(file_path):
                logger.error(f"Fichier audio introuvable pour la transcription: {file_path}")
                # Mettre à jour le statut en "error"
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "error",
                    "transcript_text": "Le fichier audio est introuvable."
                })
                return
        
        # Mettre à jour le statut immédiatement à "processing" au lieu de "pending"
        update_meeting(meeting_id, user_id, {"transcript_status": "processing"})
        logger.info(f"Statut de la réunion {meeting_id} mis à jour à 'processing'")
        
        # Créer un dossier pour la file d'attente s'il n'existe pas
        queue_dir = os.path.join(settings.UPLOADS_DIR.parent, "queue")
        if not os.path.exists(queue_dir):
            os.makedirs(queue_dir)
        
        queue_file = os.path.join(queue_dir, f"{meeting_id}.json")
        with open(queue_file, "w") as f:
            json.dump({
                "meeting_id": meeting_id,
                "file_url": file_url,
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }, f)
            
        logger.info(f"Fichier de queue créé: {queue_file}")
                
        # Lancer dans un thread pour éviter de bloquer
        logger.info(f"Création d'un thread pour la transcription de la réunion {meeting_id}")
        thread = threading.Thread(
            target=_process_transcription_wrapper,
            args=(meeting_id, file_url, user_id, queue_file)
        )
        # Définir comme non-daemon pour qu'il continue à s'exécuter même si le thread principal se termine
        thread.daemon = False
        thread.start()
        logger.info(f"Thread de transcription lancé pour la réunion {meeting_id} avec ID {thread.ident}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise en file d'attente pour transcription: {str(e)}")
        logger.error(traceback.format_exc())
        # Mettre à jour le statut en "error"
        try:
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": f"Erreur lors de la mise en file d'attente pour transcription: {str(e)}"
            })
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")

def _process_transcription(meeting_id: str, file_url: str, user_id: str):
    """Fonction principale pour traiter une transcription de réunion.
    
    Cette fonction exécute toutes les étapes:
    1. Téléchargement du fichier vers AssemblyAI si nécessaire
    2. Lancement de la transcription
    3. Vérification périodique du statut
    4. Mise à jour de la base de données avec le résultat
    """
    try:
        logger.info(f"*** DÉMARRAGE du processus de transcription pour {meeting_id} ***")
        logger.info(f"ASSEMBLY_AI_API_URL: {ASSEMBLY_AI_API_URL}")
        logger.info(f"ASSEMBLY_AI_API_KEY: {ASSEMBLY_AI_API_KEY[:4]}...{ASSEMBLY_AI_API_KEY[-4:]}")
        logger.info(f"File URL: {file_url}")
        
        # Si le fichier est local, nous devons d'abord l'uploader vers AssemblyAI
        if file_url.startswith("/uploads/"):
            # Chemin complet vers le fichier local
            logger.info(f"Fichier local détecté: {file_url}")
            
            file_path = Path(settings.UPLOADS_DIR.parent / file_url.lstrip('/'))
            
            logger.info(f"Chemin complet: {file_path}")
            logger.info(f"Le fichier existe: {os.path.exists(file_path)}")
            
            if not os.path.exists(file_path):
                error_msg = f"Le fichier audio est introuvable: {file_path}"
                logger.error(error_msg)
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "error",
                    "transcript_text": error_msg
                })
                return
            
            logger.info(f"Upload du fichier vers AssemblyAI: {file_path}")
            
            try:
                # Version synchrone de l'upload du fichier
                upload_url = _upload_file_to_assemblyai(str(file_path))
                if not upload_url:
                    raise Exception("L'upload du fichier a échoué, URL non reçue")
                    
                logger.info(f"Fichier uploadé avec succès: {upload_url}")
            except Exception as upload_error:
                error_msg = f"Erreur lors de l'upload du fichier: {str(upload_error)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "error",
                    "transcript_text": error_msg
                })
                return
                
            # Utiliser l'URL d'upload comme source pour la transcription
            audio_url = upload_url
        else:
            # Si c'est une URL externe, l'utiliser directement
            audio_url = file_url
            logger.info(f"Utilisation de l'URL externe pour la transcription: {audio_url}")
        
        # Préparer la requête pour lancer la transcription
        logger.info("Préparation de la requête de transcription")
        
        # Version synchrone du démarrage de la transcription
        try:
            transcript_id = _start_transcription_assemblyai(audio_url)
            logger.info(f"Transcription lancée avec ID: {transcript_id}")
            
            if not transcript_id:
                raise Exception("ID de transcription non reçu dans la réponse")
        except Exception as e:
            error_msg = f"Erreur lors du lancement de la transcription: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": error_msg
            })
            return
                
        # Vérifier périodiquement le statut de la transcription
        max_attempts = 60  # 30 minutes maximum (60 tentatives * 30 secondes)
        attempt = 1
        
        while attempt <= max_attempts:
            logger.info(f"Vérification du statut de la transcription (tentative {attempt}/{max_attempts})")
            status, transcript_text = check_transcription_status(transcript_id)
            
            logger.info(f"Statut actuel: {status}")
            
            # Si la transcription est terminée, mettre à jour la réunion
            if status == 'completed':
                logger.info(f"Transcription terminée avec statut: {status}")
                update_meeting(meeting_id, user_id, {
                    "transcript_status": status,
                    "transcript_text": transcript_text
                })
                logger.info(f"Statut mis à jour à '{status}' pour {meeting_id}")
                logger.info(f"*** FIN du processus de transcription pour {meeting_id} ***")
                return
            
            # Si la transcription a échoué, mettre à jour la réunion
            if status == 'error':
                logger.info(f"Transcription échouée avec statut: {status}")
                error_message = transcript_text or "Une erreur s'est produite lors de la transcription."
                update_meeting(meeting_id, user_id, {
                    "transcript_status": status,
                    "transcript_text": error_message
                })
                logger.info(f"Statut mis à jour à '{status}' pour {meeting_id}")
                logger.info(f"*** FIN du processus de transcription pour {meeting_id} ***")
                return
            
            # Attendre avant la prochaine vérification
            logger.info("Attente de 30 secondes avant la prochaine vérification...")
            time.sleep(30)
            attempt += 1
        
        # Si on a atteint le nombre maximum de tentatives sans succès
        logger.error(f"Timeout lors de la transcription (après {max_attempts} tentatives)")
        
        try:
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error", 
                "transcript_text": f"La transcription a pris trop de temps ou n'a pas abouti après {max_attempts} vérifications."
            })
            logger.info(f"Statut mis à jour à 'error' (timeout) pour {meeting_id}")
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")
                
        logger.info(f"*** FIN du processus de transcription pour {meeting_id} ***")
                
    except Exception as e:
        logger.error(f"Exception non gérée lors du traitement de la transcription: {str(e)}")
        logger.error(traceback.format_exc())
        
        try:
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": f"Exception non gérée lors de la transcription: {str(e)}"
            })
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")

def _process_transcription_wrapper(meeting_id: str, file_url: str, user_id: str, queue_file: str = None):
    """Wrapper pour _process_transcription qui gère les exceptions et supprime le fichier de queue"""
    try:
        logger.info(f"Démarrage du wrapper de transcription pour {meeting_id}")
        _process_transcription(meeting_id, file_url, user_id)
        logger.info(f"Transcription terminée avec succès pour {meeting_id}")
    except Exception as e:
        logger.error(f"Exception dans le wrapper de transcription pour {meeting_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Supprimer le fichier de queue si présent
        if queue_file and os.path.exists(queue_file):
            try:
                os.remove(queue_file)
                logger.info(f"Fichier de queue supprimé: {queue_file}")
            except Exception as e:
                logger.error(f"Impossible de supprimer le fichier de queue {queue_file}: {str(e)}")

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

def check_transcription_status(transcript_id: str, api_key: str = ASSEMBLY_AI_API_KEY):
    """Vérifie le statut d'une transcription."""
    try:
        endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        
        headers = {
            "authorization": api_key,
            "content-type": "application/json"
        }
        
        logger.info(f"Vérification du statut de la transcription {transcript_id}")
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        status = result.get('status')
        
        logger.info(f"Statut de la transcription {transcript_id}: {status}")
        
        # Si la transcription est terminée, retourner le texte
        if status == 'completed':
            transcript_text = result.get('text', '')
            return status, transcript_text
        
        # Si la transcription a échoué, retourner le message d'erreur
        if status == 'error':
            error_message = result.get('error', 'Erreur inconnue')
            return status, error_message
        
        # Transcription en cours, retourner le statut
        return status, None
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut de la transcription: {e}")
        logger.error(traceback.format_exc())
        return "error", str(e)

def _upload_file_to_assemblyai(file_path: str, api_key: str = ASSEMBLY_AI_API_KEY):
    """Version synchrone pour télécharger un fichier audio vers AssemblyAI et retourner l'URL."""
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
        
        logger.info(f"Réponse d'upload AssemblyAI: {response.status_code} - {response.text[:100]}...")
            
        if response.status_code == 200:
            upload_url = response.json()["upload_url"]
            logger.info(f"Upload réussi, URL: {upload_url}")
            return upload_url
        else:
            error_msg = response.json().get('error', 'Unknown error')
            logger.error(f"Échec de l'upload: {error_msg} (status: {response.status_code})")
            raise Exception(f"Échec de l'upload du fichier à AssemblyAI: {error_msg} (status: {response.status_code})")
    except Exception as e:
        logger.error(f"Exception lors de l'upload: {str(e)}")
        logger.error(traceback.format_exc())
        raise Exception(f"Échec de l'upload du fichier à AssemblyAI: {str(e)}")

def _start_transcription_assemblyai(audio_url: str, api_key: str = ASSEMBLY_AI_API_KEY, speaker_labels: bool = True, language_code: str = "fr"):
    """Version synchrone pour démarrer une transcription sur AssemblyAI et retourner l'ID de la transcription."""
    endpoint = f"{ASSEMBLY_AI_API_URL}/transcript"
    
    headers = {
        "authorization": api_key,
        "content-type": "application/json"
    }
    
    json_data = {
        "audio_url": audio_url,
        "language_code": language_code
    }
    
    # Ajouter uniquement les options compatibles avec le français
    if language_code == "en":
        json_data["auto_highlights"] = True
    
    # Toujours ajouter speaker_labels car disponible en français
    if speaker_labels:
        json_data["speaker_labels"] = True
    
    try:
        response = requests.post(endpoint, json=json_data, headers=headers)
        
        logger.info(f"Réponse de transcription AssemblyAI: {response.status_code} - {response.text[:100]}...")
        
        if response.status_code == 200:
            transcript_id = response.json()["id"]
            logger.info(f"Transcription démarrée avec ID: {transcript_id}")
            return transcript_id
        else:
            error_msg = response.json().get('error', 'Unknown error')
            logger.error(f"Échec du démarrage de la transcription: {error_msg} (status: {response.status_code})")
            raise Exception(f"Échec du démarrage de la transcription: {error_msg} (status: {response.status_code})")
    except Exception as e:
        logger.error(f"Exception lors du démarrage de la transcription: {str(e)}")
        logger.error(traceback.format_exc())
        raise Exception(f"Échec du démarrage de la transcription: {str(e)}")

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
