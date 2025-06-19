import os
import json
import traceback
import logging
import time
import requests
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
from pathlib import Path
import mimetypes
import subprocess
import threading

from ..core.config import settings
from ..db.queries import update_meeting, get_meeting, normalize_transcript_format, get_meeting_speakers

# Configuration pour AssemblyAI
# Utiliser directement la clé API fournie au lieu de passer par settings
ASSEMBLY_AI_API_KEY = "3419005ee6924e08a14235043cabcd4e"
# URL de base de l'API AssemblyAI
ASSEMBLY_AI_BASE_URL = "https://api.assemblyai.com/v2"

# Configuration du logging
logger = logging.getLogger("meeting-transcriber")

def convert_to_wav(input_path: str) -> str:
    """Convertit un fichier audio en WAV en utilisant ffmpeg avec des paramètres optimisés pour réduire la taille"""
    try:
        # Créer un nom de fichier de sortie avec l'extension .wav
        output_path = os.path.splitext(input_path)[0] + '_converted.wav'
        
        # Commande ffmpeg optimisée pour réduire la taille et la consommation de ressources
        cmd = [
            'ffmpeg', '-i', input_path,
            '-acodec', 'pcm_s16le',  # Format PCM 16-bit
            '-ar', '16000',          # Sample rate réduit à 16kHz (suffisant pour la parole)
            '-ac', '1',              # Mono au lieu de stéréo (réduit la taille de moitié)
            '-y',                    # Écraser le fichier de sortie s'il existe
            output_path
        ]
        
        logger.info(f"Conversion optimisée du fichier audio: {' '.join(cmd)}")
        
        # Exécuter la commande avec une priorité réduite pour limiter l'utilisation CPU
        # Utiliser nice pour réduire la priorité du processus
        try:
            # Essayer d'abord avec nice si disponible
            nice_cmd = ['nice', '-n', '19'] + cmd
            result = subprocess.run(nice_cmd, capture_output=True, text=True)
        except:
            # Fallback sur la commande standard si nice n'est pas disponible
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Erreur lors de la conversion: {result.stderr}")
            raise Exception(f"Échec de la conversion audio: {result.stderr}")
        
        # Vérifier que le fichier de sortie existe et a une taille non nulle
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.error(f"Le fichier converti n'existe pas ou est vide: {output_path}")
            raise Exception("Le fichier converti n'existe pas ou est vide")
            
        logger.info(f"Conversion réussie: {output_path} (taille: {os.path.getsize(output_path) // 1024} KB)")
        return output_path
        
    except Exception as e:
        logger.error(f"Erreur lors de la conversion audio: {str(e)}")
        raise Exception(f"Échec de la conversion audio: {str(e)}")

def transcribe_meeting(meeting_id: str, file_url: str, user_id: str) -> Optional[str]:
    """
    Lance la transcription d'une réunion en utilisant le SDK AssemblyAI.
    
    Args:
        meeting_id: Identifiant de la réunion
        file_url: URL ou chemin vers le fichier audio
        user_id: Identifiant de l'utilisateur
        
    Returns:
        Optional[str]: ID de la transcription si la transcription a été lancée avec succès, None sinon
    """
    try:
        # Vérifier si le meeting existe toujours avant de lancer la transcription
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Tentative de transcription d'une réunion qui n'existe pas ou plus: {meeting_id}")
            return None
            
        # Vérifier si le fichier existe avant de lancer la transcription
        file_path = file_url.lstrip('/')
        if not os.path.exists(file_path):
            logger.error(f"Fichier audio introuvable pour la transcription: {file_path}")
            # Mettre à jour le statut en "error"
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": "Le fichier audio est introuvable."
            })
            return None
        
        # Mettre à jour le statut immédiatement à "processing" au lieu de "pending"
        update_meeting(meeting_id, user_id, {"transcript_status": "processing"})
        logger.info(f"Statut de la réunion {meeting_id} mis à jour à 'processing'")
        
        # Uploader le fichier vers AssemblyAI
        upload_url = upload_file_to_assemblyai(file_path)
        logger.info(f"Fichier {file_path} uploadé avec succès vers AssemblyAI: {upload_url}")
        
        # Démarrer la transcription
        transcript_id = start_transcription(upload_url)
        logger.info(f"Transcription démarrée avec l'ID: {transcript_id}")
        
        # Mettre à jour l'ID de transcription dans la base de données
        update_meeting(meeting_id, user_id, {"transcript_id": transcript_id})
        
        return transcript_id
        
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

# Note: La fonction transcribe_simple qui utilisait le SDK AssemblyAI a été supprimée
# Elle a été remplacée par les fonctions upload_file_to_assemblyai et start_transcription

def process_transcription(meeting_id: str, file_url: str, user_id: str):
    """
    Fonction principale pour traiter une transcription de réunion en utilisant l'API REST AssemblyAI directement.
    
    Version simplifiée qui utilise les fonctions d'API directes au lieu du SDK pour plus de fiabilité.
    """
    try:
        logger.info(f"*** DÉMARRAGE du processus de transcription simplifié pour {meeting_id} ***")
        
        # Vérifier d'abord si le meeting existe toujours et si l'utilisateur est valide
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Erreur d'authentification ou meeting introuvable: {meeting_id}, user: {user_id}")
            return
        
        # Mettre à jour le statut immédiatement à "processing"
        update_meeting(meeting_id, user_id, {
            "transcript_status": "processing",
            "transcript_text": "Transcription en cours de traitement..."
        })
        
        # Préparation du fichier audio (version simplifiée)
        audio_source = file_url
        
        # Si le fichier est local, nous utilisons le chemin complet
        if file_url.startswith("/uploads/"):
            logger.info(f"Fichier local détecté: {file_url}")
            file_path = Path(settings.UPLOADS_DIR.parent / file_url.lstrip('/'))
            
            if not os.path.exists(file_path):
                error_msg = f"Le fichier audio est introuvable: {file_path}"
                logger.error(error_msg)
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "error",
                    "transcript_text": error_msg
                })
                return
                
            audio_source = str(file_path)
            logger.info(f"Utilisation du fichier local: {audio_source}")
        else:
            logger.info(f"Utilisation de l'URL externe: {audio_source}")
        
        # Configuration de la transcription pour l'API REST directe
        # Cette configuration sera utilisée dans start_transcription
        
        # Version simplifiée utilisant directement l'API REST AssemblyAI
        logger.info(f"Soumission de la transcription via API REST pour: {audio_source}")
        
        # Uploader le fichier vers AssemblyAI (si c'est un fichier local)
        if audio_source.startswith("/") and os.path.exists(audio_source):
            logger.info(f"Upload du fichier local vers AssemblyAI: {audio_source}")
            audio_url = upload_file_to_assemblyai(audio_source)
        else:
            audio_url = audio_source
        
        # Démarrer la transcription
        logger.info(f"Démarrage de la transcription pour: {audio_url}")
        transcript_id = start_transcription(audio_url)
        
        # Mettre à jour le meeting avec l'ID de transcription
        update_meeting(meeting_id, user_id, {
            "transcript_id": transcript_id,
            "transcript_status": "processing",
            "transcript_text": f"Transcription en cours avec ID: {transcript_id}"
        })
        
        logger.info(f"Transcription démarrée avec succès pour {meeting_id}, ID: {transcript_id}")
        
        # Vérifier immédiatement le statut pour détecter les erreurs précoces
        try:
            status_result = check_transcription_status(transcript_id)
            status = status_result.get("status")
            
            if status == "error":
                error_msg = status_result.get("error", "Erreur inconnue lors de la transcription")
                logger.error(f"Erreur immédiate lors de la transcription: {error_msg}")
                
                update_meeting(meeting_id, user_id, {
                    "transcript_status": "error",
                    "transcript_text": f"Erreur lors de la transcription: {error_msg}"
                })
            else:
                logger.info(f"Statut initial de la transcription: {status}")
        except Exception as status_error:
            logger.warning(f"Impossible de vérifier le statut initial, mais la transcription continue: {str(status_error)}")
            
    except Exception as e:
        # Gestion générale des erreurs
        logger.error(f"Erreur lors du traitement de la transcription: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Mettre à jour le statut en "error"
        try:
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error", 
                "transcript_text": f"Erreur lors du traitement de la transcription: {str(e)}"
            })
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": error_msg
            })
            return
            
    except Exception as e:
        logger.error(f"Erreur non gérée lors de la transcription: {str(e)}")
        logger.error(traceback.format_exc())
        
        try:
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": f"Erreur lors de la transcription: {str(e)}"
            })
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")

def upload_file_to_assemblyai(file_path: str) -> str:
    """
    Upload un fichier vers AssemblyAI en utilisant l'API REST directement.
    
    Args:
        file_path: Chemin vers le fichier à uploader
        
    Returns:
        str: URL du fichier uploadé
    """
    logger.info(f"Upload du fichier {file_path} vers AssemblyAI")
    
    headers = {
        "authorization": ASSEMBLY_AI_API_KEY
    }
    
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers=headers,
                data=f
            )
        
        if response.status_code == 200:
            upload_url = response.json()["upload_url"]
            logger.info(f"Fichier uploadé avec succès, URL: {upload_url}")
            return upload_url
        else:
            error_msg = f"Erreur lors de l'upload: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    except Exception as e:
        logger.error(f"Erreur lors de l'upload vers AssemblyAI: {str(e)}")
        raise Exception(f"Erreur lors de l'upload vers AssemblyAI: {str(e)}")

def start_transcription(audio_url: str, speakers_expected: Optional[int] = None, format_text: bool = False) -> str:
    """
    Démarre une transcription sur AssemblyAI en utilisant l'API REST directement.
    
    Args:
        audio_url: URL du fichier audio à transcrire
        speakers_expected: Nombre de locuteurs attendus (optionnel)
        format_text: Si True, le texte retourné inclut les identifiants des locuteurs (Speaker A, etc.)
        
    Returns:
        str: ID de la transcription
    """
    logger.info(f"Démarrage de la transcription pour l'URL: {audio_url}")
    
    headers = {
        "authorization": ASSEMBLY_AI_API_KEY,
        "content-type": "application/json"
    }
    
    json_data = {
        "audio_url": audio_url,
        "speaker_labels": True,
        "language_code": "fr"
    }
    
    # Optionnel: si nous avons une estimation du nombre de locuteurs
    if speakers_expected is not None and speakers_expected > 1:
        json_data["speakers_expected"] = speakers_expected
    
    try:
        response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers=headers,
            json=json_data
        )
        
        if response.status_code == 200:
            transcript_id = response.json()["id"]
            logger.info(f"Transcription démarrée avec succès, ID: {transcript_id}")
            return transcript_id
        else:
            error_msg = f"Erreur lors du démarrage de la transcription: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    except Exception as e:
        logger.error(f"Erreur lors du démarrage de la transcription: {str(e)}")
        raise Exception(f"Erreur lors du démarrage de la transcription: {str(e)}")

def check_transcription_status(transcript_id: str) -> Dict:
    """
    Vérifie le statut d'une transcription en utilisant l'API REST AssemblyAI directement.
    
    Args:
        transcript_id: ID de la transcription
        
    Returns:
        dict: Réponse complète de la transcription
    """
    logger.info(f"Vérification du statut de la transcription {transcript_id}")
    
    headers = {
        "authorization": ASSEMBLY_AI_API_KEY
    }
    
    try:
        response = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result["status"]
            logger.info(f"Statut de la transcription {transcript_id}: {status}")
            return result
        else:
            error_msg = f"Erreur lors de la vérification du statut: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut: {str(e)}")
        raise Exception(f"Erreur lors de la vérification du statut: {str(e)}")

def get_transcript_status(transcript_id: str) -> Tuple[str, Optional[Dict]]:
    """
    Récupère le statut et les données d'une transcription.
    
    Args:
        transcript_id: ID de la transcription
        
    Returns:
        Tuple[str, Optional[Dict]]: Statut de la transcription et données associées si disponibles
    """
    try:
        transcript_data = check_transcription_status(transcript_id)
        status = transcript_data.get("status", "unknown")
        return status, transcript_data
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut de la transcription {transcript_id}: {str(e)}")
        return "error", {"error": str(e)}

def process_completed_transcript(meeting_id, user_id, transcript):
    """
    Traite une transcription terminée et met à jour la base de données.
    
    Args:
        meeting_id: ID de la réunion
        user_id: ID de l'utilisateur
        transcript: Objet Transcript du SDK AssemblyAI
    """
    try:
        # Extraction des données importantes
        audio_duration = transcript.audio_duration or 0
        logger.info(f"Durée audio: {audio_duration} secondes")
        
        # Récupérer les noms personnalisés des locuteurs s'ils existent
        speaker_names = {}
        try:
            speakers_data = get_meeting_speakers(meeting_id, user_id)
            if speakers_data:
                for speaker in speakers_data:
                    speaker_names[speaker['speaker_id']] = speaker['custom_name']
                logger.info(f"Noms personnalisés récupérés: {speaker_names}")
        except Exception as e:
            logger.warning(f"Impossible de récupérer les noms personnalisés: {str(e)}")
            speaker_names = {}
        
        # Extraction et comptage des locuteurs
        speaker_count = 0
        unique_speakers = set()
        utterances_data = []
        formatted_text = transcript.text or ""
        
        # Traitement des utterances si disponibles
        if hasattr(transcript, 'utterances') and transcript.utterances:
            try:
                utterances_text = []
                for utterance in transcript.utterances:
                    speaker = getattr(utterance, 'speaker', 'Unknown')
                    text = getattr(utterance, 'text', '').strip()
                    
                    # SAFETY: Assurer qu'on a toujours un texte, même vide
                    if text is None:
                        text = ''
                    
                    if speaker:
                        unique_speakers.add(speaker)
                        
                        # Utiliser le nom personnalisé s'il existe, sinon utiliser le format par défaut
                        speaker_name = None
                        
                        # 1. Essayer d'abord avec l'ID simple (ex: "A", "B", "C", "D")
                        if speaker in speaker_names:
                            speaker_name = speaker_names[speaker]
                            logger.debug(f"Found custom name for simple ID '{speaker}': {speaker_name}")
                        
                        # 2. Essayer avec le format "Speaker X" (ex: "Speaker A", "Speaker B")
                        full_speaker_id = f"Speaker {speaker}"
                        if speaker_name is None and full_speaker_id in speaker_names:
                            speaker_name = speaker_names[full_speaker_id]
                            logger.debug(f"Found custom name for full ID '{full_speaker_id}': {speaker_name}")
                        
                        # 3. Si aucun nom personnalisé trouvé, utiliser le format par défaut
                        if speaker_name is None:
                            speaker_name = full_speaker_id
                            logger.debug(f"No custom name found for speaker '{speaker}', using default: {speaker_name}")
                        
                        # IMPORTANT: Toujours ajouter la ligne, même si le texte est vide
                        utterance_formatted = f"{speaker_name}: {text}"
                        utterances_text.append(utterance_formatted)
                        utterances_data.append({"speaker": speaker, "text": text})
                
                if utterances_text:
                    formatted_text = "\n".join(utterances_text)
                    logger.info(f"Texte formaté avec {len(utterances_text)} segments de locuteurs")
            except Exception as e:
                logger.warning(f"Erreur lors du traitement des utterances: {str(e)}")
        else:
            logger.warning("Aucune utterance trouvée dans la transcription")
        
        # S'assurer qu'il y a au moins 1 locuteur
        speaker_count = len(unique_speakers)
        if speaker_count == 0:
            speaker_count = 1
            logger.warning("Aucun locuteur détecté, on force à 1")
        
        logger.info(f"Nombre de locuteurs détectés: {speaker_count}")
        
        # Normaliser le format du texte avant l'update
        formatted_text = normalize_transcript_format(formatted_text)
        
        # Mise à jour de la base de données
        update_data = {
            "transcript_text": formatted_text,
            "transcript_status": "completed",
            "duration_seconds": int(audio_duration),
            "speakers_count": speaker_count
        }
        
        logger.info(f"Mise à jour de la base de données pour {meeting_id}")
        update_meeting(meeting_id, user_id, update_data)
        logger.info(f"Transcription terminée avec succès pour {meeting_id}")
        
        # Lancer la génération du résumé automatiquement en mode asynchrone
        try:
            from .mistral_summary import process_meeting_summary
            logger.info(f"Lancement de la génération du résumé pour la réunion {meeting_id}")
            # Utiliser le mode asynchrone pour éviter les problèmes de threads sur Render
            process_meeting_summary(meeting_id, user_id, async_mode=True)
            logger.info(f"Génération du résumé lancée en mode asynchrone pour la réunion {meeting_id}")
        except Exception as summary_error:
            logger.error(f"Erreur lors du lancement de la génération du résumé: {str(summary_error)}")
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la transcription terminée: {str(e)}")
        logger.error(traceback.format_exc())
        update_meeting(meeting_id, user_id, {
            "transcript_status": "error",
            "transcript_text": f"Erreur lors du traitement de la transcription: {str(e)}"
        })

def normalize_transcript_format(text):
    """
    Normalise le format du texte de transcription pour qu'il soit cohérent.
    
    Args:
        text: Texte de la transcription
        
    Returns:
        str: Texte normalisé
    """
    if not text:
        return ""
        
    # Si le texte contient déjà des marqueurs de locuteurs au format 'Speaker X: ', on le laisse tel quel
    if "Speaker " in text and ": " in text:
        return text
        
    # Sinon, on le considère comme un texte brut d'un seul locuteur
    return f"Speaker A: {text}"

def process_pending_transcriptions():
    """
    Vérifie et met à jour les statuts des transcriptions en attente ou bloquées en état 'processing'.
    À exécuter au démarrage de l'application et périodiquement.
    
    Cette fonction utilise l'API REST d'AssemblyAI pour être plus fiable.
    """
    import requests
    from ..db.queries import get_pending_transcriptions, get_meetings_by_status, get_meeting
    from ..core.config import settings
    
    # Utiliser directement la clé API AssemblyAI définie en haut du fichier
    api_key = ASSEMBLY_AI_API_KEY
    if not api_key:
        logger.error("La clé API AssemblyAI n'est pas définie")
        return
    
    # Configuration de l'API AssemblyAI
    headers = {
        "authorization": api_key,
        "content-type": "application/json"
    }
    
    # Récupérer toutes les transcriptions en attente
    pending_meetings = get_pending_transcriptions()
    logger.info(f"Transcriptions en attente: {len(pending_meetings)}")
    
    # Récupérer également les transcriptions bloquées en état 'processing'
    processing_meetings = get_meetings_by_status('processing')
    logger.info(f"Transcriptions bloquées en état 'processing': {len(processing_meetings)}")
    
    # Fusionner les deux listes
    all_meetings_to_process = pending_meetings + processing_meetings
    
    if not all_meetings_to_process:
        logger.info("Aucune transcription en attente ou bloquée trouvée")
        return
    
    logger.info(f"Traitement de {len(all_meetings_to_process)} transcription(s) en attente ou bloquées")
    
    # Récupérer les transcriptions récentes d'AssemblyAI
    recent_transcripts = []
    try:
        url = "https://api.assemblyai.com/v2/transcript"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            recent_transcripts = response.json().get('transcripts', [])
            logger.info(f"Récupération de {len(recent_transcripts)} transcriptions récentes d'AssemblyAI")
        else:
            logger.error(f"Erreur lors de la récupération des transcriptions: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des transcriptions récentes: {str(e)}")
    
    # Traiter chaque transcription
    for meeting in all_meetings_to_process:
        try:
            meeting_id = meeting['id']
            user_id = meeting['user_id']
            file_url = meeting.get('file_url', '')
            file_name = os.path.basename(file_url) if file_url else ''
            
            # Vérifier si la réunion est en état 'processing'
            if meeting['transcript_status'] == 'processing':
                logger.info(f"Vérification de la réunion {meeting_id} en état 'processing'")
                
                # Essayer d'extraire l'ID de transcription AssemblyAI du texte
                transcript_id = None
                transcript_text = meeting.get('transcript_text', '')
                
                if transcript_text and 'ID:' in transcript_text:
                    try:
                        # Extraire l'ID de transcription du texte (format: 'Transcription en cours, ID: xyz')
                        transcript_id = transcript_text.split('ID:')[-1].strip()
                        logger.info(f"ID de transcription AssemblyAI extrait: {transcript_id}")
                        
                        # Vérifier le statut de la transcription via l'API REST
                        url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
                        response = requests.get(url, headers=headers)
                        
                        if response.status_code == 200:
                            transcript_data = response.json()
                            status = transcript_data.get('status')
                            logger.info(f"Statut de la transcription {transcript_id}: {status}")
                            
                            if status == 'completed':
                                # Créer un objet compatible avec process_completed_transcript
                                class TranscriptObject:
                                    def __init__(self, data):
                                        self.id = data.get('id')
                                        self.status = data.get('status')
                                        self.text = data.get('text')
                                        self.audio_duration = data.get('audio_duration')
                                        self.utterances = []
                                        
                                        # Traiter les utterances si disponibles
                                        utterances_data = data.get('utterances', [])
                                        if utterances_data and isinstance(utterances_data, list):
                                            for utterance in utterances_data:
                                                self.utterances.append(UtteranceObject(utterance))
                                
                                class UtteranceObject:
                                    def __init__(self, data):
                                        self.speaker = data.get('speaker')
                                        self.text = data.get('text')
                                
                                # Créer l'objet transcript
                                transcript = TranscriptObject(transcript_data)
                                
                                # Traiter la transcription terminée
                                logger.info(f"Transcription {transcript_id} terminée, mise à jour de la base de données")
                                process_completed_transcript(meeting_id, user_id, transcript)
                                continue
                            elif status == 'error':
                                # Gérer l'erreur
                                error_message = transcript_data.get('error', 'Unknown error')
                                logger.error(f"Erreur de transcription pour {meeting_id}: {error_message}")
                                update_meeting(meeting_id, user_id, {
                                    "transcript_status": "error",
                                    "transcript_text": f"Erreur lors de la transcription: {error_message}"
                                })
                                continue
                            else:
                                # Toujours en cours, ne rien faire
                                logger.info(f"Transcription {transcript_id} toujours en cours ({status})")
                                continue
                        else:
                            logger.error(f"Erreur lors de la vérification de la transcription {transcript_id}: {response.status_code} - {response.text}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la vérification de la transcription {transcript_id}: {str(e)}")
                        # Continuer avec la recherche dans les transcriptions récentes
                
                # Si on n'a pas pu extraire l'ID ou vérifier le statut, essayer de trouver la transcription par le nom de fichier
                if file_name:
                    logger.info(f"Recherche de transcription pour le fichier: {file_name}")
                    
                    for transcript in recent_transcripts:
                        if transcript.get('status') == 'completed':
                            # Récupérer les détails complets de la transcription
                            transcript_id = transcript.get('id')
                            url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
                            response = requests.get(url, headers=headers)
                            
                            if response.status_code == 200:
                                transcript_data = response.json()
                                audio_url = transcript_data.get('audio_url', '')
                                audio_filename = os.path.basename(audio_url) if audio_url else ''
                                
                                # Si le nom de fichier correspond
                                if file_name in audio_filename or audio_filename in file_name:
                                    logger.info(f"Transcription trouvée pour {file_name}: {transcript_id}")
                                    
                                    # Créer un objet compatible avec process_completed_transcript
                                    class TranscriptObject:
                                        def __init__(self, data):
                                            self.id = data.get('id')
                                            self.status = data.get('status')
                                            self.text = data.get('text')
                                            self.audio_duration = data.get('audio_duration')
                                            self.utterances = []
                                            
                                            # Traiter les utterances si disponibles
                                            utterances_data = data.get('utterances', [])
                                            if utterances_data and isinstance(utterances_data, list):
                                                for utterance in utterances_data:
                                                    self.utterances.append(UtteranceObject(utterance))
                                    
                                    class UtteranceObject:
                                        def __init__(self, data):
                                            self.speaker = data.get('speaker')
                                            self.text = data.get('text')
                                    
                                    # Créer l'objet transcript
                                    transcript = TranscriptObject(transcript_data)
                                    
                                    # Traiter la transcription terminée
                                    logger.info(f"Transcription {transcript_id} terminée, mise à jour de la base de données")
                                    process_completed_transcript(meeting_id, user_id, transcript)
                                    break
                    else:
                        logger.warning(f"Aucune transcription trouvée pour le fichier {file_name}")
            
            # Si on arrive ici et que la réunion est toujours en état 'processing',
            # vérifier directement auprès d'AssemblyAI si la transcription est terminée
            meeting = get_meeting(meeting_id, user_id)  # Récupérer l'état actuel
            if meeting and meeting.get('transcript_status') == 'processing' and meeting.get('transcript_id'):
                transcript_id = meeting.get('transcript_id')
                logger.info(f"Vérification du statut de la transcription {transcript_id} pour la réunion {meeting_id}")
                
                # Vérifier le statut auprès d'AssemblyAI
                try:
                    response = requests.get(
                        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        transcript_data = response.json()
                        status = transcript_data.get('status')
                        logger.info(f"Statut de la transcription {transcript_id}: {status}")
                        
                        if status == 'completed':
                            # Préparer les données de mise à jour
                            transcript_text = transcript_data.get('text', '')
                            audio_duration = transcript_data.get('audio_duration', 0)
                            
                            # Essayer de formater avec les locuteurs si disponibles
                            if 'utterances' in transcript_data and transcript_data['utterances']:
                                try:
                                    # Récupérer les noms personnalisés des locuteurs s'ils existent
                                    speaker_names = {}
                                    try:
                                        speakers_data = get_meeting_speakers(meeting_id, user_id)
                                        if speakers_data:
                                            for speaker in speakers_data:
                                                speaker_names[speaker['speaker_id']] = speaker['custom_name']
                                    except Exception as e:
                                        logger.warning(f"Impossible de récupérer les noms personnalisés: {str(e)}")
                                        speaker_names = {}
                                    
                                    formatted_text = []
                                    speakers_set = set()
                                    for utterance in transcript_data.get('utterances', []):
                                        speaker = utterance.get('speaker', 'Unknown')
                                        speakers_set.add(speaker)
                                        text = utterance.get('text', '')
                                        
                                        # SAFETY: Assurer qu'on a toujours un texte, même vide
                                        if text is None:
                                            text = ''
                                        
                                        # Utiliser le nom personnalisé s'il existe, sinon utiliser le format par défaut
                                        speaker_name = None
                                        
                                        # 1. Essayer d'abord avec l'ID simple (ex: "A", "B", "C", "D")
                                        if speaker in speaker_names:
                                            speaker_name = speaker_names[speaker]
                                            logger.debug(f"Found custom name for simple ID '{speaker}': {speaker_name}")
                                        
                                        # 2. Essayer avec le format "Speaker X" (ex: "Speaker A", "Speaker B")
                                        full_speaker_id = f"Speaker {speaker}"
                                        if speaker_name is None and full_speaker_id in speaker_names:
                                            speaker_name = speaker_names[full_speaker_id]
                                            logger.debug(f"Found custom name for full ID '{full_speaker_id}': {speaker_name}")
                                        
                                        # 3. Si aucun nom personnalisé trouvé, utiliser le format par défaut
                                        if speaker_name is None:
                                            speaker_name = full_speaker_id
                                            logger.debug(f"No custom name found for speaker '{speaker}', using default: {speaker_name}")
                                        
                                        # IMPORTANT: Toujours ajouter la ligne, même si le texte est vide
                                        formatted_text.append(f"{speaker_name}: {text}")
                                    
                                    transcript_text = "\n".join(formatted_text)
                                    speakers_count = len(speakers_set) if speakers_set else 1
                                except Exception as e:
                                    logger.error(f"Erreur lors du formatage du texte: {str(e)}")
                                    speakers_count = 1
                            else:
                                speakers_count = 1
                            
                            # Mettre à jour la base de données
                            update_data = {
                                "transcript_text": transcript_text,
                                "transcript_status": "completed",
                                "duration_seconds": int(audio_duration) if audio_duration else 0,
                                "speakers_count": speakers_count
                            }
                            
                            update_meeting(meeting_id, user_id, update_data)
                            logger.info(f"Réunion {meeting_id} mise à jour avec succès (statut: completed)")
                        elif status == 'error':
                            # Mettre à jour la base de données en cas d'erreur
                            error_message = transcript_data.get('error', 'Unknown error')
                            update_data = {
                                "transcript_status": "error",
                                "transcript_text": f"Erreur lors de la transcription: {error_message}"
                            }
                            
                            update_meeting(meeting_id, user_id, update_data)
                            logger.info(f"Réunion {meeting_id} mise à jour avec succès (statut: error)")
                        else:
                            logger.info(f"Réunion {meeting_id} toujours en cours de traitement (statut: {status})")
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification du statut de la transcription {transcript_id}: {str(e)}")
            elif meeting and meeting.get('transcript_status') == 'pending':
                logger.info(f"Réunion {meeting_id} toujours en attente")
                # Ne pas relancer automatiquement la transcription
                # Juste logger l'information pour le suivi
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la transcription pour {meeting.get('id', 'unknown')}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
