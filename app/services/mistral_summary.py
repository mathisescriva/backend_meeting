import requests
import json
import logging
import os
from typing import Optional, Dict, Any
from ..core.config import settings

# Configuration pour Mistral AI
MISTRAL_API_KEY = settings.MISTRAL_API_KEY
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Configuration du logging
logger = logging.getLogger("meeting-transcriber")

def generate_meeting_summary(transcript_text: str, meeting_title: Optional[str] = None) -> Optional[str]:
    """
    Génère un compte rendu de réunion à partir d'une transcription en utilisant l'API Mistral.
    
    Args:
        transcript_text: Texte de la transcription de la réunion
        meeting_title: Titre de la réunion (optionnel)
        
    Returns:
        str: Compte rendu généré ou None en cas d'erreur
    """
    if not MISTRAL_API_KEY:
        logger.error("Clé API Mistral non configurée. Impossible de générer le compte rendu.")
        return None
        
    try:
        # Préparer le prompt pour Mistral
        prompt = f"""Tu es un assistant spécialisé dans la création de comptes rendus de réunion.
        
        Voici la transcription d'une réunion{' intitulée "' + meeting_title + '"' if meeting_title else ''}. 
        Crée un compte rendu structuré STRICTEMENT selon les 4 parties suivantes :
        
        # Synthèse
        Une synthèse concise de la réunion en quelques lignes seulement.
        
        # Éléments discutés
        Les principaux points et sujets abordés pendant la réunion, présentés sous forme de liste à puces.
        
        # Relevé de décisions
        Toutes les décisions prises lors de la réunion, présentées sous forme de liste à puces.
        
        # Plan d'action
        Les actions à entreprendre avec leurs responsables (si mentionnés) et les échéances (si mentionnées), présentées sous forme de liste à puces.
        
        Respecte IMPÉRATIVEMENT cette structure en 4 parties avec ces titres exacts. Utilise un format clair avec des listes à puces et des paragraphes bien organisés.
        
        Transcription:
        {transcript_text}
        """
        
        # Préparer la requête pour l'API Mistral
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {MISTRAL_API_KEY}"
        }
        
        payload = {
            "model": "mistral-large-latest",  # Utiliser le modèle le plus récent et le plus performant
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # Température basse pour des résultats plus cohérents
            "max_tokens": 4000  # Limite de tokens pour la réponse
        }
        
        # Envoyer la requête à l'API Mistral
        logger.info("Envoi de la requête à l'API Mistral pour générer un compte rendu")
        response = requests.post(MISTRAL_API_URL, headers=headers, json=payload)
        
        # Vérifier la réponse
        if response.status_code == 200:
            response_data = response.json()
            summary = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if summary:
                logger.info("Compte rendu généré avec succès")
                return summary
            else:
                logger.error("La réponse de l'API Mistral ne contient pas de contenu")
                return None
        else:
            logger.error(f"Erreur lors de l'appel à l'API Mistral: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Erreur lors de la génération du compte rendu: {str(e)}")
        return None

def process_meeting_summary(meeting_id: str, user_id: str):
    """
    Traite la génération du compte rendu pour une réunion spécifique.
    
    Cette fonction récupère la transcription, génère le compte rendu et met à jour la base de données.
    
    Args:
        meeting_id: Identifiant de la réunion
        user_id: Identifiant de l'utilisateur
    
    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    from ..db.queries import get_meeting, update_meeting
    import threading
    
    try:
        # Récupérer les informations de la réunion
        meeting = get_meeting(meeting_id, user_id)
        
        if not meeting:
            logger.error(f"Réunion {meeting_id} non trouvée pour l'utilisateur {user_id}")
            return False
            
        # Vérifier que la transcription est disponible
        if not meeting.get("transcript_text") or meeting.get("transcript_status") != "completed":
            logger.error(f"La transcription n'est pas disponible pour la réunion {meeting_id}")
            update_meeting(meeting_id, user_id, {"summary_status": "error", "summary_text": "La transcription n'est pas disponible"})
            return False
            
        # Mettre à jour le statut pour indiquer que la génération est en cours
        update_meeting(meeting_id, user_id, {"summary_status": "processing"})
        
        # Stocker les données nécessaires pour le thread
        transcript_text = meeting["transcript_text"]
        meeting_title = meeting.get("title")
        
        # Lancer la génération dans un thread séparé pour ne pas bloquer
        def generate_summary_thread():
            try:
                # Générer le compte rendu
                summary = generate_meeting_summary(transcript_text, meeting_title)
                
                if summary:
                    # Mise à jour directe de la base de données en utilisant sqlite3
                    # plutôt que d'utiliser la fonction update_meeting qui utilise le pool de connexions global
                    import sqlite3
                    import os
                    from pathlib import Path
                    
                    # Chemin de la base de données
                    db_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "app.db"
                    
                    # Créer une nouvelle connexion dans ce thread
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    try:
                        # Mettre à jour la réunion avec le compte rendu
                        cursor.execute(
                            "UPDATE meetings SET summary_text = ?, summary_status = ? WHERE id = ? AND user_id = ?",
                            (summary, "completed", meeting_id, user_id)
                        )
                        conn.commit()
                        logger.info(f"Compte rendu généré et enregistré pour la réunion {meeting_id}")
                    except Exception as db_error:
                        logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")
                        return False
                    finally:
                        # Fermer la connexion
                        cursor.close()
                        conn.close()
                    
                    return True
                else:
                    # Mise à jour directe de la base de données en cas d'erreur
                    import sqlite3
                    import os
                    from pathlib import Path
                    
                    # Chemin de la base de données
                    db_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "app.db"
                    
                    # Créer une nouvelle connexion dans ce thread
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    try:
                        # Mettre à jour le statut en cas d'erreur
                        cursor.execute(
                            "UPDATE meetings SET summary_text = ?, summary_status = ? WHERE id = ? AND user_id = ?",
                            ("Erreur lors de la génération du compte rendu", "error", meeting_id, user_id)
                        )
                        conn.commit()
                    except Exception as db_error:
                        logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")
                    finally:
                        # Fermer la connexion
                        cursor.close()
                        conn.close()
                    
                    logger.error(f"Échec de la génération du compte rendu pour la réunion {meeting_id}")
                    return False
            except Exception as e:
                logger.error(f"Erreur dans le thread de génération du compte rendu: {str(e)}")
                
                # Mise à jour directe de la base de données en cas d'erreur
                try:
                    import sqlite3
                    import os
                    from pathlib import Path
                    
                    # Chemin de la base de données
                    db_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "app.db"
                    
                    # Créer une nouvelle connexion dans ce thread
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    # Mettre à jour le statut en cas d'erreur
                    cursor.execute(
                        "UPDATE meetings SET summary_text = ?, summary_status = ? WHERE id = ? AND user_id = ?",
                        (f"Erreur lors de la génération du compte rendu: {str(e)}", "error", meeting_id, user_id)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                except Exception as db_error:
                    logger.error(f"Erreur lors de la mise à jour de la base de données dans le thread: {str(db_error)}")
                return False
        
        # Démarrer le thread
        thread = threading.Thread(target=generate_summary_thread)
        thread.daemon = False
        thread.start()
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du compte rendu: {str(e)}")
        try:
            update_meeting(meeting_id, user_id, {
                "summary_status": "error",
                "summary_text": f"Erreur lors du traitement: {str(e)}"
            })
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")
        return False
