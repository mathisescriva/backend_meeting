"""
Module pour le traitement des transcriptions en file d'attente.
Fournit un service autonome qui s'exécute en arrière-plan au sein de l'application FastAPI.
"""

import os
import json
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from ..core.config import settings
from ..db.queries import get_meeting, update_meeting
from .assemblyai import process_transcription
from fastapi.logger import logger

class QueueProcessor:
    """
    Gestionnaire de file d'attente pour les transcriptions audio.
    S'exécute en arrière-plan et traite périodiquement les fichiers de queue.
    """
    
    def __init__(self, interval_seconds=10):
        """
        Initialise le processeur de file d'attente.
        
        Args:
            interval_seconds (int): Intervalle entre chaque traitement de la file d'attente
        """
        self.interval = interval_seconds
        self.is_running = False
        self.task = None
        self.lock = threading.Lock()
    
    async def start(self):
        """Démarre le processeur de file d'attente"""
        with self.lock:
            if self.is_running:
                logger.info("Le processeur de file d'attente est déjà en cours d'exécution")
                return
            
            self.is_running = True
            logger.info(f"Démarrage du processeur de file d'attente (intervalle: {self.interval}s)")
            self.task = asyncio.create_task(self._run_processor())
            
            # Traiter la file d'attente immédiatement au démarrage
            await asyncio.to_thread(self._process_queue)
            
            # Vérifier les transcriptions en cours au démarrage
            logger.info("Vérification des transcriptions en cours au démarrage")
            await asyncio.to_thread(self._check_pending_transcriptions)
    
    async def stop(self):
        """Arrête le processeur de file d'attente"""
        with self.lock:
            if not self.is_running:
                logger.info("Le processeur de file d'attente n'est pas en cours d'exécution")
                return
            
            self.is_running = False
            if self.task:
                logger.info("Arrêt du processeur de file d'attente")
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                self.task = None
    
    async def _run_processor(self):
        """Exécute le processeur de file d'attente en boucle"""
        while self.is_running:
            try:
                logger.info("Traitement périodique de la file d'attente de transcription")
                self._process_queue()
                
                # Vérifier les transcriptions en cours à chaque itération (toutes les 10 secondes)
                logger.info("Vérification périodique des transcriptions en cours")
                self._check_pending_transcriptions()
            except Exception as e:
                logger.error(f"Erreur lors du traitement de la file d'attente: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            await asyncio.sleep(self.interval)
    
    def _process_queue(self):
        """Traite tous les fichiers dans le répertoire de queue"""
        queue_dir = os.path.join(settings.UPLOADS_DIR.parent, "queue")
        
        if not os.path.exists(queue_dir):
            logger.info(f"Le répertoire de queue n'existe pas encore: {queue_dir}")
            os.makedirs(queue_dir, exist_ok=True)
            logger.info(f"Répertoire de queue créé: {queue_dir}")
            return
        
        queue_files = [f for f in os.listdir(queue_dir) if f.endswith('.json')]
        if queue_files:
            logger.info(f"Traitement de {len(queue_files)} fichiers dans la queue")
        
        for queue_file in queue_files:
            try:
                queue_file_path = os.path.join(queue_dir, queue_file)
                
                # Lire les données du fichier
                with open(queue_file_path, 'r') as f:
                    data = json.load(f)
                
                meeting_id = data.get('meeting_id')
                file_url = data.get('file_url')
                user_id = data.get('user_id')
                created_at = data.get('created_at')
                
                # Vérifier l'ancienneté du fichier
                if created_at:
                    created_datetime = datetime.fromisoformat(created_at)
                    age = datetime.now() - created_datetime
                    # Si le fichier a plus de 24h, considérer qu'il est obsolète
                    if age > timedelta(hours=24):
                        logger.warning(f"Fichier de queue obsolète (>24h): {queue_file}")
                        os.remove(queue_file_path)
                        continue
                
                if not all([meeting_id, file_url, user_id]):
                    logger.error(f"Données incomplètes dans le fichier de queue: {queue_file}")
                    continue
                
                # Vérifier que la réunion existe et qu'elle est toujours en attente/processing
                meeting = get_meeting(meeting_id, user_id)
                if not meeting:
                    logger.warning(f"La réunion {meeting_id} n'existe plus, suppression du fichier de queue")
                    os.remove(queue_file_path)
                    continue
                
                status = meeting.get('transcript_status')
                if status not in ['pending', 'processing']:
                    logger.info(f"La réunion {meeting_id} a déjà le statut {status}, pas besoin de retraitement")
                    os.remove(queue_file_path)
                    continue
                
                logger.info(f"Traitement de la transcription pour la réunion {meeting_id} (statut actuel: {status})")
                
                # Mettre à jour le statut en "processing" si nécessaire
                if status == 'pending':
                    update_meeting(meeting_id, user_id, {"transcript_status": "processing"})
                
                # Traiter la transcription dans un thread séparé pour ne pas bloquer la boucle principale
                thread = threading.Thread(
                    target=self.process_transcription_wrapper,
                    args=(meeting_id, file_url, user_id, queue_file_path)
                )
                thread.daemon = True
                thread.start()
                logger.info(f"Thread de transcription lancé pour {meeting_id}")
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement du fichier {queue_file}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
    
    def _check_pending_transcriptions(self):
        """Vérifie et met à jour les transcriptions en cours"""
        try:
            logger.info("Vérification des transcriptions en cours")
            from .assemblyai import process_pending_transcriptions
            
            # Utiliser un thread séparé pour ne pas bloquer la boucle principale
            thread = threading.Thread(
                target=process_pending_transcriptions
            )
            thread.daemon = True
            thread.start()
            logger.info("Thread de vérification des transcriptions lancé")
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des transcriptions en cours: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def process_transcription_wrapper(self, meeting_id, file_url, user_id, queue_file_path):
        """Wrapper pour process_transcription qui supprime le fichier de queue à la fin"""
        try:
            logger.info(f"Traitement de la transcription pour {meeting_id}")
            process_transcription(meeting_id, file_url, user_id)
            logger.info(f"Transcription terminée pour {meeting_id}")
        except Exception as e:
            logger.error(f"Erreur lors de la transcription pour {meeting_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # Supprimer le fichier de queue
            try:
                if os.path.exists(queue_file_path):
                    os.remove(queue_file_path)
                    logger.info(f"Fichier de queue supprimé: {queue_file_path}")
            except Exception as e:
                logger.error(f"Impossible de supprimer le fichier de queue {queue_file_path}: {str(e)}")

# Instance singleton du processeur de file d'attente
queue_processor = QueueProcessor()

# Fonction pour démarrer le processeur
async def start_queue_processor():
    """Démarre le processeur de file d'attente"""
    await queue_processor.start()

# Fonction pour arrêter le processeur
async def stop_queue_processor():
    """Arrête le processeur de file d'attente"""
    await queue_processor.stop()
