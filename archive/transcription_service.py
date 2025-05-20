#!/usr/bin/env python3
"""
Script de service de transcription automatique qui s'exécute en arrière-plan
pour traiter les réunions en attente (pending) ou bloquées en traitement (processing).

Exécutez ce script en parallèle du serveur principal pour garantir que
toutes les transcriptions sont traitées, même en cas de problème avec 
les threads de transcription du serveur principal.
"""

import os
import sys
import time
import logging
import sqlite3
import traceback
import magic
from pathlib import Path
from datetime import datetime, timedelta
import mimetypes

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('transcription-service')

# Initialiser la base de données
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "app.db"

try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    logger.info("Base de données initialisée avec succès")
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
    sys.exit(1)

# Importer les services après l'initialisation de BASE_DIR
sys.path.insert(0, str(BASE_DIR))
# Utiliser les versions du service unifié
from app.services.assemblyai import upload_file_to_assemblyai
from app.services.assemblyai import start_transcription
from app.services.assemblyai import check_transcription_status
from app.core.config import settings

def get_pending_transcriptions(max_age_hours=24):
    """Récupère les transcriptions en attente qui ne sont pas trop anciennes"""
    cursor = conn.cursor()
    cutoff_date = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%dT%H:%M:%S")
    
    cursor.execute(
        "SELECT id, title, user_id, file_url, transcript_status, created_at FROM meetings " +
        "WHERE transcript_status IN ('pending', 'processing') AND created_at > ? " +
        "ORDER BY created_at ASC",
        (cutoff_date_str,)
    )
    
    meetings = cursor.fetchall()
    cursor.close()
    return [dict(meeting) for meeting in meetings]

def check_stalled_transcriptions():
    """Vérifie s'il y a des transcriptions bloquées en statut 'processing' depuis trop longtemps"""
    cursor = conn.cursor()
    # Considérer comme bloquée après 30 minutes en statut 'processing'
    stalled_cutoff = datetime.now() - timedelta(minutes=30)
    stalled_cutoff_str = stalled_cutoff.strftime("%Y-%m-%dT%H:%M:%S")
    
    cursor.execute(
        "SELECT id, title, user_id, file_url, transcript_status, created_at FROM meetings " +
        "WHERE transcript_status = 'processing' AND created_at < ? " +
        "ORDER BY created_at ASC",
        (stalled_cutoff_str,)
    )
    
    meetings = cursor.fetchall()
    cursor.close()
    
    if meetings:
        logger.warning(f"Détecté {len(meetings)} transcription(s) bloquée(s) en statut 'processing'")
        for meeting in meetings:
            meeting_dict = dict(meeting)
            logger.warning(f"Réinitialisation de la transcription bloquée: {meeting_dict['id']} - {meeting_dict['title']}")
            # Réinitialiser au statut 'pending' pour retenter
            update_meeting_status(meeting_dict['id'], meeting_dict['user_id'], 'pending')
    
    return [dict(meeting) for meeting in meetings]

def update_meeting_status(meeting_id, user_id, status, text=None, duration_seconds=None, speakers_count=None):
    """Met à jour le statut et le texte de transcription d'une réunion"""
    cursor = conn.cursor()
    try:
        # Log détaillé des paramètres
        logger.info(f"update_meeting_status appelé avec:")
        logger.info(f"  meeting_id: {meeting_id}")
        logger.info(f"  user_id: {user_id}")
        logger.info(f"  status: {status}")
        logger.info(f"  text: {text[:50]}..." if text else "  text: None")
        logger.info(f"  duration_seconds: {duration_seconds} (type: {type(duration_seconds)})")
        logger.info(f"  speakers_count: {speakers_count} (type: {type(speakers_count)})")
        
        update_data = {"transcript_status": status}
        if text is not None:
            update_data["transcript_text"] = text
        if duration_seconds is not None:
            update_data["duration_seconds"] = duration_seconds
            logger.info(f"Mise à jour de la durée audio: {duration_seconds} secondes pour la réunion {meeting_id}")
        if speakers_count is not None:
            update_data["speakers_count"] = speakers_count
            logger.info(f"Mise à jour du nombre de locuteurs: {speakers_count} pour la réunion {meeting_id}")
            
        placeholders = ", ".join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values())
        
        query = f"UPDATE meetings SET {placeholders} WHERE id = ? AND user_id = ?"
        params = (*values, meeting_id, user_id)
        logger.info(f"Requête SQL: {query}")
        logger.info(f"Paramètres: {params}")
        
        cursor.execute(query, params)
        conn.commit()
        
        # Vérifier si des lignes ont été modifiées
        if cursor.rowcount > 0:
            logger.info(f"Statut de la réunion {meeting_id} mis à jour avec succès: {update_data}")
        else:
            logger.warning(f"Aucune ligne modifiée pour la réunion {meeting_id}. Vérification si la réunion existe...")
            # Vérifier si la réunion existe
            cursor.execute("SELECT COUNT(*) FROM meetings WHERE id = ? AND user_id = ?", (meeting_id, user_id))
            count = cursor.fetchone()[0]
            if count == 0:
                logger.error(f"La réunion {meeting_id} n'existe pas pour l'utilisateur {user_id}")
            else:
                logger.warning(f"La réunion existe mais aucune modification n'a été effectuée (valeurs identiques?)")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du statut: {e}")
        import traceback
        logger.error(traceback.format_exc())
        conn.rollback()
        return False

def process_transcription(meeting):
    """Traite une transcription en attente"""
    meeting_id = meeting['id']
    user_id = meeting['user_id']
    file_url = meeting['file_url']
    title = meeting['title']
    created_at = meeting['created_at']
    
    logger.info(f"=== Traitement de la réunion {meeting_id} - {title} ===")
    logger.info(f"Statut actuel: {meeting['transcript_status']}")
    logger.info(f"Date de création: {created_at}")
    
    # Construire le chemin complet vers le fichier
    if file_url.startswith('/'):
        file_url = file_url[1:]  # Enlever le / initial si présent
    full_path = os.path.join(BASE_DIR, file_url)
    
    # Vérifier si le fichier existe
    if not os.path.exists(full_path):
        logger.error(f"Fichier introuvable: {full_path}")
        update_meeting_status(meeting_id, user_id, "error", "Fichier audio introuvable")
        return False
    
    logger.info(f"Vérification du fichier: {full_path}, Existe: {os.path.exists(full_path)}")
    
    # Vérifier la taille du fichier
    file_size = os.path.getsize(full_path)
    if file_size > 100 * 1024 * 1024:  # 100 MB
        error_message = f"Le fichier est trop volumineux: {file_size} bytes (max: 100MB)"
        logger.error(error_message)
        update_meeting_status(meeting_id, user_id, "error", error_message)
        return False
        
    # Vérifier le type de fichier
    mime_type, _ = mimetypes.guess_type(full_path)
    if not mime_type or not mime_type.startswith('audio/'):
        mime_type = 'audio/wav'  # Fallback par défaut
    logger.info(f"Type MIME du fichier: {mime_type}")
    
    try:
        # Si déjà en processing, vérifier si elle est bloquée
        if meeting['transcript_status'] == 'processing':
            # Si en processing depuis plus d'une heure, on considère que c'est bloqué
            created_time = datetime.fromisoformat(meeting['created_at'])
            if datetime.now() - created_time > timedelta(hours=1):
                logger.warning(f"La transcription est bloquée en processing depuis plus d'une heure, reprise du traitement")
                # On continue le traitement pour cette réunion bloquée
            else:
                logger.info(f"La transcription est déjà en processing depuis moins d'une heure, on passe à la suivante")
                return True
        
        # Marquer comme en traitement
        update_meeting_status(meeting_id, user_id, "processing")
        
        # Upload du fichier vers AssemblyAI
        logger.info(f"Upload du fichier: {full_path}")
        upload_url = upload_file_to_assemblyai(str(full_path))
        logger.info(f"Fichier uploadé: {upload_url}")
        
        # Démarrer la transcription
        logger.info("Démarrage de la transcription")
        transcript_id = start_transcription(upload_url)
        logger.info(f"Transcription démarrée avec ID: {transcript_id}")
        
        # Vérifier le statut en boucle
        max_attempts = 30
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Vérification du statut, tentative {attempt}/{max_attempts}")
            
            # Récupérer le statut de la transcription
            transcript_response = check_transcription_status(transcript_id)
            status = transcript_response.get('status')
            
            if status == "completed":
                # Récupérer le texte avec mise en forme par interlocuteur
                transcript_text = transcript_response.get('text', '')
                
                # Log la réponse complète pour le débogage
                logger.info(f"Réponse complète de l'API: {transcript_response}")
                
                # Extraire la durée de l'audio (en secondes)
                audio_duration = transcript_response.get('audio_duration')
                logger.info(f"Durée audio brute extraite: {audio_duration}")
                
                if audio_duration is not None:
                    try:
                        audio_duration = int(float(audio_duration))
                        logger.info(f"Durée audio convertie en entier: {audio_duration}")
                    except (ValueError, TypeError):
                        logger.warning(f"Impossible de convertir la durée audio en entier: {audio_duration}")
                        # Garder la valeur telle quelle, mais s'assurer qu'elle n'est pas None
                        audio_duration = audio_duration or 0
                else:
                    audio_duration = 0
                    logger.warning("Durée audio non disponible, valeur par défaut à 0")
                
                # Si des informations par interlocuteur sont disponibles
                utterances = transcript_response.get('utterances', [])
                speakers_set = set()
                
                if utterances:
                    transcript_text = ""
                    for utterance in utterances:
                        speaker = utterance.get('speaker', 'Speaker')
                        speakers_set.add(speaker)
                        text = utterance.get('text', '')
                        if text:
                            transcript_text += f"{speaker}: {text}\n"
                
                # Essayer d'abord d'obtenir le nombre de locuteurs directement de l'API
                speakers_count = transcript_response.get('speaker_count')
                logger.info(f"Nombre de locuteurs directement de l'API: {speakers_count}")
                
                # Si non disponible, calculer à partir des utterances
                if speakers_count is None:
                    # Calculer le nombre de participants à partir des utterances
                    if speakers_set:
                        speakers_count = len(speakers_set)
                        logger.info(f"Nombre de locuteurs calculé à partir des utterances: {speakers_count}")
                    else:
                        # Essayer de compter les locuteurs à partir des mots
                        words = transcript_response.get('words', [])
                        speaker_ids_from_words = set()
                        
                        for word in words:
                            if 'speaker' in word:
                                speaker_ids_from_words.add(word['speaker'])
                        
                        if speaker_ids_from_words:
                            speakers_count = len(speaker_ids_from_words)
                            logger.info(f"Nombre de locuteurs calculé à partir des mots: {speakers_count}")
                        else:
                            speakers_count = None
                            logger.warning("Impossible de déterminer le nombre de locuteurs")
                
                # Convertir en entier si possible
                if speakers_count is not None:
                    try:
                        speakers_count = int(speakers_count)
                        logger.info(f"Nombre de locuteurs converti en entier: {speakers_count}")
                    except (ValueError, TypeError):
                        logger.warning(f"Impossible de convertir le nombre de locuteurs en entier: {speakers_count}")
                        # Garder la valeur telle quelle
                
                logger.info(f"Transcription terminée avec succès. Durée: {audio_duration}s, Participants: {speakers_count}")
                update_meeting_status(
                    meeting_id, 
                    user_id, 
                    "completed", 
                    transcript_text,
                    audio_duration,
                    speakers_count
                )
                return True
            elif status == "error":
                error_message = transcript_response.get('error', 'Unknown error')
                logger.error(f"Transcription terminée avec erreur: {error_message}")
                update_meeting_status(
                    meeting_id, 
                    user_id, 
                    "error", 
                    f"Erreur lors de la transcription: {error_message}"
                )
                return False
            
            # Attendre plus longtemps entre les tentatives
            wait_time = min(10 * attempt, 60)  # Augmente progressivement, plafonne à 60s
            logger.info(f"En attente de transcription, statut actuel: {status}. Nouvelle vérification dans {wait_time}s")
            time.sleep(wait_time)
        
        # Si on arrive ici, c'est que la transcription prend trop de temps
        logger.warning("Transcription trop longue, marquée comme erreur")
        update_meeting_status(
            meeting_id, 
            user_id, 
            "error", 
            "La transcription a pris trop de temps et a été interrompue."
        )
        return False
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la transcription: {str(e)}")
        logger.error(traceback.format_exc())
        update_meeting_status(
            meeting_id, 
            user_id, 
            "error", 
            f"Erreur lors du traitement: {str(e)}"
        )
        return False

def main(single_run=False, check_interval=60):
    """Fonction principale qui vérifie régulièrement les transcriptions en attente"""
    try:
        if single_run:
            logger.info("Mode exécution unique activé")
        else:
            logger.info(f"Mode service activé (intervalle de vérification: {check_interval}s)")
        
        while True:
            logger.info("=== Vérification des transcriptions en attente ===")
            
            # Vérifier d'abord les transcriptions bloquées
            stalled_meetings = check_stalled_transcriptions()
            if stalled_meetings:
                logger.info(f"Réinitialisé {len(stalled_meetings)} transcription(s) bloquée(s)")
            
            # Récupérer les transcriptions en attente
            meetings = get_pending_transcriptions()
            logger.info(f"Trouvé {len(meetings)} transcription(s) en attente/processing")
            
            for meeting in meetings:
                try:
                    process_transcription(meeting)
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de la réunion {meeting['id']}: {e}")
                    traceback.print_exc()
            
            if single_run:
                logger.info("Exécution unique terminée")
                break
                
            logger.info(f"En attente de {check_interval} secondes avant la prochaine vérification...")
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        logger.info("Interruption clavier détectée, arrêt du service...")
    except Exception as e:
        logger.error(f"Erreur non gérée: {e}")
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Service de transcription automatique")
    parser.add_argument("--single-run", action="store_true", help="Exécuter une seule fois puis s'arrêter")
    parser.add_argument("--interval", type=int, default=60, help="Intervalle entre les vérifications (secondes)")
    
    args = parser.parse_args()
    
    main(single_run=args.single_run, check_interval=args.interval)
