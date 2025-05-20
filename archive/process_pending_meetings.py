#!/usr/bin/env python3
"""
Script pour vérifier et traiter automatiquement les réunions en statut 'processing'.
Ce script s'exécute en continu à un intervalle régulier.
"""
import sqlite3
import time
import sys
import os
import logging
from app.services.assemblyai import _process_transcription
import traceback
import argparse

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('processing_meetings.log')
    ]
)
logger = logging.getLogger('meeting-processor')

def get_processing_meetings():
    """Récupère toutes les réunions en statut 'processing' ou 'pending'"""
    try:
        # Connexion à la base de données
        conn = sqlite3.connect('app.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Récupération des réunions en processing ou pending
        cursor.execute("""
            SELECT id, user_id, file_url, title, created_at
            FROM meetings
            WHERE transcript_status IN ('processing', 'pending')
            ORDER BY created_at DESC
        """)
        
        meetings = cursor.fetchall()
        conn.close()
        
        return [dict(meeting) for meeting in meetings]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réunions: {str(e)}")
        return []

def process_meeting(meeting):
    """Traite une réunion spécifique"""
    meeting_id = meeting['id']
    file_url = meeting['file_url']
    user_id = meeting['user_id']
    
    logger.info(f"Traitement de la réunion: {meeting_id} - {meeting['title']}")
    
    try:
        # Appel direct de la fonction de traitement
        _process_transcription(meeting_id, file_url, user_id)
        logger.info(f"Réunion {meeting_id} traitée avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la réunion {meeting_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def run_continuous(interval=60):
    """Exécute le processus en continu avec un intervalle spécifié"""
    logger.info(f"Démarrage du service de traitement avec un intervalle de {interval} secondes")
    
    while True:
        try:
            # Enregistrer l'heure de début pour calculer précisément l'intervalle
            start_time = time.time()
            
            # Vérifier et traiter les réunions
            check_and_process()
            
            # Calculer le temps restant à attendre
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)  # Éviter les valeurs négatives
            
            logger.info(f"Traitement terminé en {elapsed:.2f} secondes. Prochain cycle dans {sleep_time:.2f} secondes")
            time.sleep(sleep_time)
        except KeyboardInterrupt:
            logger.info("Arrêt du service demandé. Fermeture propre...")
            break
        except Exception as e:
            logger.error(f"Erreur dans la boucle principale: {str(e)}")
            logger.error(traceback.format_exc())
            # Attendre quand même avant de réessayer
            time.sleep(interval)

def check_and_process():
    """Vérifie et traite les réunions en attente"""
    logger.info("Vérification des réunions en attente")
    
    # Récupérer les réunions en processing ou pending
    meetings = get_processing_meetings()
    
    if not meetings:
        logger.info("Aucune réunion en attente à traiter")
        return
    
    logger.info(f"Nombre de réunions à traiter: {len(meetings)}")
    
    # Traiter chaque réunion
    for meeting in meetings:
        logger.info(f"Traitement de la réunion {meeting['id']} - {meeting['title']}")
        success = process_meeting(meeting)
        
        if success:
            logger.info(f"Réunion {meeting['id']} traitée avec succès")
        else:
            logger.error(f"Échec du traitement de la réunion {meeting['id']}")
        
        # Attendre un peu entre chaque traitement pour éviter de surcharger l'API
        time.sleep(1)
    
    logger.info("Cycle de traitement des réunions terminé")

def main():
    # Analyser les arguments
    parser = argparse.ArgumentParser(description="Service de traitement des transcriptions en attente")
    parser.add_argument('--once', action='store_true', help="Exécuter le script une seule fois puis quitter")
    parser.add_argument('--interval', type=int, default=60, help="Intervalle en secondes entre chaque vérification")
    args = parser.parse_args()
    
    if args.once:
        # Exécution unique
        logger.info("Mode d'exécution unique")
        check_and_process()
    else:
        # Exécution continue
        run_continuous(args.interval)

if __name__ == "__main__":
    main()
