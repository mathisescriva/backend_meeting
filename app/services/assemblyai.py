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

# Import du SDK officiel d'AssemblyAI
import assemblyai as aai

from ..core.config import settings
from ..db.queries import update_meeting, get_meeting, normalize_transcript_format

# Configuration pour AssemblyAI
ASSEMBLY_AI_API_KEY = settings.ASSEMBLYAI_API_KEY
# Configurer le SDK AssemblyAI
aai.settings.api_key = ASSEMBLY_AI_API_KEY

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

def transcribe_meeting(meeting_id: str, file_url: str, user_id: str):
    """
    Lance la transcription d'une réunion en utilisant le SDK AssemblyAI.
    
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
        
        # Lancer dans un thread pour éviter de bloquer
        logger.info(f"Lancement de la transcription de la réunion {meeting_id} avec le SDK AssemblyAI")
        thread = threading.Thread(
            target=process_transcription,
            args=(meeting_id, file_url, user_id)
        )
        # Définir comme non-daemon pour qu'il continue à s'exécuter même si le thread principal se termine
        thread.daemon = False
        thread.start()
        logger.info(f"Thread de transcription lancé pour la réunion {meeting_id}")
        
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

# Fonction simplifiée pour soumettre une transcription avec gestion d'erreur basique
def transcribe_simple(transcriber, audio_source, config):
    """Fonction simplifiée qui tente de transcrire sans dépendance à backoff"""
    try:
        return transcriber.submit(audio_source, config)
    except Exception as e:
        logger.error(f"Erreur lors de la transcription: {str(e)}")
        # Si c'est une erreur de connexion au serveur Render, ajouter un message spécifique
        if "Cannot connect to backend server" in str(e) or "Network connection error" in str(e):
            error_msg = (
                f"Erreur de connexion au serveur. Cela peut être dû au plan Render "
                f"qui a des limitations de ressources. "
                f"Veuillez réessayer dans quelques instants."
            )
            logger.error(error_msg)
            raise Exception(error_msg) from e
        raise

def process_transcription(meeting_id: str, file_url: str, user_id: str):
    """
    Fonction principale pour traiter une transcription de réunion en utilisant le SDK AssemblyAI.
    
    Version ultra-simplifiée pour Render avec une consommation minimale de ressources.
    Cette fonction délègue le traitement à AssemblyAI et stocke uniquement l'ID de transcription.
    Le traitement réel est effectué de manière asynchrone par AssemblyAI.
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
        
        # Configuration ultra-simplifiée de la transcription
        config = aai.TranscriptionConfig(
            speaker_labels=True,  # Conserver uniquement la diarisation des locuteurs
            language_code="fr",  # Langue française par défaut
            # Désactiver toutes les fonctionnalités non essentielles
            auto_highlights=False,
            content_safety=False,
            entity_detection=False,
            iab_categories=False,
            sentiment_analysis=False
        )
        
        # Version ultra-simplifiée : juste soumettre la transcription et stocker l'ID
        logger.info(f"Soumission simplifiée de la transcription pour: {audio_source}")
        
        # Créer le transcripteur
        transcriber = aai.Transcriber()
        
        # Soumettre la transcription sans attendre le résultat
        try:
            # Utiliser directement submit sans retry complexe
            transcript_obj = transcriber.submit(audio_source, config)
            transcript_id = transcript_obj.id
            logger.info(f"Transcription soumise avec succès, ID: {transcript_id}")
            
            # Mettre à jour la base de données avec l'ID de transcription
            update_meeting(meeting_id, user_id, {
                "transcript_status": "processing",
                "transcript_text": f"Transcription en cours de traitement. ID: {transcript_id}"
            })
            
            # Terminer immédiatement sans attendre
            logger.info(f"Transcription déléguée à AssemblyAI, ID: {transcript_id}")
            return
            
        except Exception as e:
            error_msg = f"Erreur lors de la soumission de la transcription: {str(e)}"
            logger.error(error_msg)
            update_meeting(meeting_id, user_id, {
                "transcript_status": "error",
                "transcript_text": error_msg
            })
            return
            
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
    Upload un fichier vers AssemblyAI en utilisant le SDK officiel.
    Cette fonction est maintenue pour compatibilité mais n'est plus nécessaire
    car le SDK AssemblyAI gère automatiquement l'upload des fichiers locaux.
    
    Args:
        file_path: Chemin vers le fichier à uploader
        
    Returns:
        str: URL du fichier uploadé (vide car géré par le SDK)
    """
    logger.warning("La fonction upload_file_to_assemblyai est dépréciée. Le SDK AssemblyAI gère automatiquement l'upload.")
    return file_path  # Retourne simplement le chemin du fichier pour compatibilité

def start_transcription(audio_url: str, speakers_expected: Optional[int] = None, format_text: bool = False) -> str:
    """
    Démarre une transcription sur AssemblyAI.
    Cette fonction est maintenue pour compatibilité mais utilise maintenant le SDK officiel.
    
    Args:
        audio_url: URL du fichier audio à transcrire
        speakers_expected: Nombre de locuteurs attendus (optionnel)
        format_text: Si True, le texte retourné inclut les identifiants des locuteurs (Speaker A, etc.)
        
    Returns:
        str: ID de la transcription
    """
    logger.warning("La fonction start_transcription est dépréciée. Utilisez directement le SDK AssemblyAI.")
    
    # Configuration avec le SDK AssemblyAI
    config = aai.TranscriptionConfig(
        speaker_labels=True,
        language_code="fr"
    )
    
    # Optionnel: si nous avons une estimation du nombre de locuteurs
    if speakers_expected is not None and speakers_expected > 1:
        config.speakers_expected = speakers_expected
    
    try:
        # Utiliser le SDK pour démarrer la transcription
        transcriber = aai.Transcriber()
        transcript = transcriber.submit(audio_url, config)
        
        # Retourner l'ID de la transcription
        return transcript.id
    except Exception as e:
        logger.error(f"Erreur lors de la demande de transcription: {str(e)}")
        raise Exception(f"Erreur lors de la demande de transcription: {str(e)}")

def check_transcription_status(transcript_id: str) -> Dict:
    """
    Vérifie le statut d'une transcription en utilisant le SDK AssemblyAI.
    Cette fonction est maintenue pour compatibilité mais utilise maintenant le SDK officiel.
    
    Args:
        transcript_id: ID de la transcription
        
    Returns:
        dict: Réponse complète de la transcription
    """
    logger.warning("La fonction check_transcription_status est dépréciée. Utilisez directement le SDK AssemblyAI.")
    
    try:
        # Utiliser le SDK pour obtenir le statut de la transcription
        transcriber = aai.Transcriber()
        # Récupérer la transcription par son ID
        # Le SDK gère automatiquement le polling
        transcript = transcriber.get_by_id(transcript_id)
        
        # Convertir l'objet Transcript en dictionnaire pour compatibilité
        result = {
            'id': transcript.id,
            'status': transcript.status,
            'text': transcript.text,
            'audio_duration': transcript.audio_duration
        }
        
        # Ajouter les utterances si disponibles
        if hasattr(transcript, 'utterances') and transcript.utterances:
            result['utterances'] = []
            for utterance in transcript.utterances:
                result['utterances'].append({
                    'speaker': getattr(utterance, 'speaker', 'Unknown'),
                    'text': getattr(utterance, 'text', '')
                })
        
        # Ajouter l'erreur si disponible
        if hasattr(transcript, 'error') and transcript.error:
            result['error'] = transcript.error
            
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut: {str(e)}")
        raise Exception(f"Erreur lors de la vérification du statut: {str(e)}")

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
                    if speaker and text:
                        unique_speakers.add(speaker)
                        utterance_formatted = f"Speaker {speaker}: {text}"
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
        
        # Lancer la génération du résumé automatiquement
        try:
            from .mistral_summary import process_meeting_summary
            logger.info(f"Lancement de la génération du résumé pour la réunion {meeting_id}")
            import threading
            summary_thread = threading.Thread(
                target=process_meeting_summary,
                args=(meeting_id, user_id)
            )
            summary_thread.daemon = True
            summary_thread.start()
            logger.info(f"Thread de génération du résumé lancé pour la réunion {meeting_id}")
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
    Traite toutes les transcriptions en attente ou bloquées en état 'processing'.
    À exécuter au démarrage de l'application.
    
    Cette fonction utilise maintenant le SDK AssemblyAI pour un traitement plus efficace.
    """
    from ..db.queries import get_pending_transcriptions, get_meetings_by_status, get_meeting
    
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
    
    # Créer un transcriber pour réutilisation
    transcriber = aai.Transcriber()
    
    # Traiter chaque transcription
    for meeting in all_meetings_to_process:
        try:
            meeting_id = meeting['id']
            user_id = meeting['user_id']
            
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
                        
                        # Vérifier le statut de la transcription
                        # Récupérer la transcription par son ID
                        # Le SDK gère automatiquement le polling
                        transcript = transcriber.get_by_id(transcript_id)
                        logger.info(f"Statut de la transcription {transcript_id}: {transcript.status}")
                        
                        if transcript.status == 'completed':
                            # Traiter la transcription terminée
                            logger.info(f"Transcription {transcript_id} terminée, mise à jour de la base de données")
                            process_completed_transcript(meeting_id, user_id, transcript)
                            continue
                        elif transcript.status == 'error':
                            # Gérer l'erreur
                            error_message = getattr(transcript, 'error', 'Unknown error')
                            logger.error(f"Erreur de transcription pour {meeting_id}: {error_message}")
                            update_meeting(meeting_id, user_id, {
                                "transcript_status": "error",
                                "transcript_text": f"Erreur lors de la transcription: {error_message}"
                            })
                            continue
                        else:
                            # Toujours en cours, ne rien faire
                            logger.info(f"Transcription {transcript_id} toujours en cours ({transcript.status})")
                            continue
                    except Exception as e:
                        logger.error(f"Erreur lors de la vérification de la transcription {transcript_id}: {str(e)}")
                        # Continuer avec le retraitement normal
            
            # Si on arrive ici, soit il n'y a pas d'ID de transcription, soit il y a eu une erreur
            # On relance donc le processus de transcription depuis le début
            logger.info(f"Lancement/relancement de la transcription pour {meeting_id}")
            thread = threading.Thread(
                target=process_transcription,
                args=(meeting_id, meeting["file_url"], user_id)
            )
            thread.daemon = False
            thread.start()
            logger.info(f"Transcription lancée pour la réunion {meeting_id}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la transcription pour {meeting.get('id', 'unknown')}: {str(e)}")
