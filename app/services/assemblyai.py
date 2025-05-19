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

# Import PostgreSQL pour le mode production
if os.getenv("ENVIRONMENT") == 'production':
    import psycopg2
    import psycopg2.extras

# Import du SDK officiel d'AssemblyAI
import assemblyai as aai

from ..core.config import settings

# Importer les fonctions de base de donnu00e9es appropriu00e9es selon l'environnement
if settings.ENVIRONMENT == 'production':
    from ..db.postgres_queries import get_pending_transcriptions, get_meetings_by_status
    from ..db.queries import update_meeting, get_meeting, normalize_transcript_format
else:
    from ..db.queries import update_meeting, get_meeting, normalize_transcript_format, get_pending_transcriptions, get_meetings_by_status

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
    À exécuter au démarrage de l'application et périodiquement.
    
    Cette fonction utilise l'API REST d'AssemblyAI pour être plus fiable.
    """
    import requests
    from ..db.queries import get_pending_transcriptions, get_meetings_by_status, get_meeting
    from ..core.config import settings
    
    # Récupérer la clé API AssemblyAI
    api_key = settings.ASSEMBLYAI_API_KEY
    if not api_key:
        logger.error("La clé API AssemblyAI n'est pas définie dans les variables d'environnement")
        return
    
    # Configuration de l'API AssemblyAI
    headers = {
        "authorization": api_key,
        "content-type": "application/json"
    }
    
    # Récupérer toutes les transcriptions en attente
    # En mode production, utiliser directement les requêtes PostgreSQL
    if settings.ENVIRONMENT == 'production':
        # Connexion PostgreSQL
        conn = None
        try:
            # Importer les fonctions PostgreSQL
            from ..db.postgres_adapter import get_db_connection, release_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Requête pour les transcriptions en attente (syntaxe PostgreSQL)
            cursor.execute(
                """
                SELECT * FROM meetings 
                WHERE transcript_status = 'pending' 
                AND created_at > NOW() - INTERVAL '%s hours'
                """,
                (24,)
            )
            pending_meetings = [dict(m) for m in cursor.fetchall()]
            logger.info(f"Transcriptions en attente: {len(pending_meetings)}")
            
            # Requête pour les transcriptions bloquées (syntaxe PostgreSQL)
            cursor.execute(
                """
                SELECT * FROM meetings 
                WHERE transcript_status = 'processing' 
                AND created_at > NOW() - INTERVAL '%s hours'
                ORDER BY created_at DESC
                """,
                (72,)
            )
            processing_meetings = [dict(m) for m in cursor.fetchall()]
            logger.info(f"Transcriptions bloquées en état 'processing': {len(processing_meetings)}")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des transcriptions: {str(e)}")
            pending_meetings = []
            processing_meetings = []
        finally:
            if conn:
                release_db_connection(conn)
    else:
        # En mode développement, utiliser les fonctions existantes
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
            
            # Si on arrive ici et que la réunion est toujours en état 'pending' ou 'processing',
            # on relance le processus de transcription depuis le début
            meeting = get_meeting(meeting_id, user_id)  # Récupérer l'état actuel
            if meeting and meeting.get('transcript_status') in ['pending', 'processing']:
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
            import traceback
            logger.error(traceback.format_exc())
