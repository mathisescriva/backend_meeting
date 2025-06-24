#!/usr/bin/env python

"""
Script pour mettre à jour le statut des comptes rendus bloqués en 'processing'.

Ce script identifie les réunions dont la transcription est complétée mais dont le compte rendu
est bloqué en statut 'processing', puis déclenche manuellement la génération du compte rendu
ou met à jour leur statut.
"""

import sqlite3
import os
import sys
import logging
from pathlib import Path
import time
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("update-summary-status")

# Chemins
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
RENDER_DISK_PATH = os.environ.get("RENDER_DISK_PATH", "/data")

# Vérifier si nous sommes sur Render (disque persistant existe)
ON_RENDER = os.path.exists(RENDER_DISK_PATH)

# Chemin de la base de données
if ON_RENDER:
    DB_PATH = Path(RENDER_DISK_PATH) / "app.db"
    logger.info(f"Utilisation de la base de données sur le disque persistant: {DB_PATH}")
else:
    DB_PATH = CURRENT_DIR / "app.db"
    logger.info(f"Utilisation de la base de données locale: {DB_PATH}")

def get_stuck_summaries():
    """
    Récupère les réunions dont la transcription est complétée mais dont le compte rendu
    est bloqué en statut 'processing'.
    
    Returns:
        list: Liste des réunions bloquées
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Récupérer les réunions avec transcription complétée mais compte rendu en processing
        cursor.execute(
            """SELECT id, user_id, title, transcript_status, summary_status, created_at 
               FROM meetings 
               WHERE transcript_status = 'completed' AND summary_status = 'processing'"""
        )
        
        # Convertir en liste de dictionnaires
        columns = [col[0] for col in cursor.description]
        meetings = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return meetings
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réunions bloquées: {str(e)}")
        return []

def update_summary_status(meeting_id, user_id, status="error", message="Compte rendu non généré après un délai trop long"):
    """
    Met à jour le statut d'un compte rendu.
    
    Args:
        meeting_id (str): ID de la réunion
        user_id (str): ID de l'utilisateur
        status (str): Nouveau statut (error ou completed)
        message (str): Message à enregistrer comme texte du compte rendu
        
    Returns:
        bool: True si la mise à jour a réussi, False sinon
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Mettre à jour le statut et le texte du compte rendu
        cursor.execute(
            "UPDATE meetings SET summary_status = ?, summary_text = ? WHERE id = ? AND user_id = ?",
            (status, message, meeting_id, user_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du statut du compte rendu: {str(e)}")
        return False

def generate_summary_for_meeting(meeting_id, user_id):
    """
    Tente de générer un compte rendu pour une réunion.
    
    Args:
        meeting_id (str): ID de la réunion
        user_id (str): ID de l'utilisateur
        
    Returns:
        bool: True si la génération a été lancée, False sinon
    """
    try:
        # Importer les modules nécessaires
        sys.path.append(str(CURRENT_DIR))
        from app.services.mistral_summary import generate_meeting_summary, process_meeting_summary
        from app.db.queries import get_meeting, update_meeting, get_meeting_speakers
        from app.services.transcription_checker import get_assemblyai_transcript_details, replace_speaker_names_in_text
        
        # Récupérer les données de la réunion
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            logger.error(f"Réunion {meeting_id} non trouvée pour l'utilisateur {user_id}")
            return False
        
        # Vérifier que nous avons une transcription
        transcript_text = meeting.get("transcript_text")
        if not transcript_text:
            logger.error(f"Aucune transcription disponible pour la réunion {meeting_id}")
            return False
        
        # Récupérer les noms personnalisés des locuteurs
        speakers_data = get_meeting_speakers(meeting_id, user_id)
        speaker_names = {}
        if speakers_data:
            for speaker in speakers_data:
                speaker_names[speaker['speaker_id']] = speaker['custom_name']
            logger.info(f"Noms personnalisés des locuteurs récupérés: {speaker_names}")
        
        # Utiliser la transcription avec les noms personnalisés si disponibles
        if speaker_names:
            formatted_transcript = replace_speaker_names_in_text(transcript_text, speaker_names)
            logger.info("Transcription formatée avec les noms personnalisés")
        else:
            formatted_transcript = transcript_text
            logger.info("Aucun nom personnalisé trouvé, utilisation de la transcription originale")
        
        # Générer le compte rendu avec la transcription formatée
        logger.info(f"Génération du compte rendu pour la réunion {meeting_id}")
        summary_text = generate_meeting_summary(formatted_transcript, meeting.get("title", "Réunion"))
        
        if summary_text:
            # Mettre à jour la base de données avec le compte rendu
            update_meeting(meeting_id, user_id, {
                "summary_text": summary_text,
                "summary_status": "completed"
            })
            logger.info(f"✅ Compte rendu généré avec succès pour la réunion {meeting_id}")
            return True
        else:
            # Marquer comme erreur
            update_meeting(meeting_id, user_id, {"summary_status": "error"})
            logger.error(f"❌ Échec de la génération du compte rendu pour la réunion {meeting_id}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du compte rendu pour la réunion {meeting_id}: {str(e)}")
        try:
            update_meeting(meeting_id, user_id, {"summary_status": "error"})
        except:
            pass
        return False

def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage de la mise à jour des statuts des comptes rendus")
    
    # Récupérer les réunions bloquées
    stuck_meetings = get_stuck_summaries()
    logger.info(f"Nombre de réunions avec comptes rendus bloqués: {len(stuck_meetings)}")
    
    if not stuck_meetings:
        logger.info("Aucune réunion avec compte rendu bloqué trouvée.")
        return
    
    # Traiter chaque réunion bloquée
    for meeting in stuck_meetings:
        meeting_id = meeting["id"]
        user_id = meeting["user_id"]
        title = meeting.get("title", "Sans titre")
        created_at = meeting.get("created_at", "Date inconnue")
        
        logger.info(f"Traitement de la réunion: {title} (ID: {meeting_id}, créée le: {created_at})")
        
        # Vérifier depuis combien de temps la réunion est bloquée
        try:
            created_datetime = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now()
            delta = now - created_datetime
            hours_stuck = delta.total_seconds() / 3600
            
            logger.info(f"La réunion est bloquée depuis environ {hours_stuck:.1f} heures")
            
            # Si bloquée depuis plus de 24 heures, marquer comme erreur
            if hours_stuck > 24:
                logger.warning(f"Réunion bloquée depuis plus de 24 heures, marquage comme erreur")
                update_summary_status(meeting_id, user_id)
                continue
        except Exception as e:
            logger.warning(f"Impossible de calculer le temps de blocage: {str(e)}")
        
        # Tenter de générer le compte rendu
        success = generate_summary_for_meeting(meeting_id, user_id)
        
        if success:
            logger.info(f"Compte rendu généré avec succès pour la réunion {meeting_id}")
        else:
            logger.error(f"Échec de la génération du compte rendu pour la réunion {meeting_id}")
        
        # Attendre un peu entre chaque génération pour ne pas surcharger l'API
        time.sleep(2)
    
    logger.info("Mise à jour des statuts des comptes rendus terminée")

if __name__ == "__main__":
    main()
