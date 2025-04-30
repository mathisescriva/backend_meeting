import sqlite3
import uuid
from datetime import datetime
from .database import get_db_connection, release_db_connection
import logging

def create_meeting(meeting_data, user_id):
    """
    Créer une nouvelle réunion avec une meilleure gestion des transactions
    pour éviter les erreurs 'database is locked'
    """
    # Logger pour le débogage
    logger = logging.getLogger("fastapi")
    logger.info(f"Création d'une nouvelle réunion pour l'utilisateur {user_id}")
    
    # Récupérer une nouvelle connexion pour cette transaction
    conn = None
    meeting = None
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Obtenir une nouvelle connexion
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Générer un ID unique pour la réunion
            meeting_id = str(uuid.uuid4())
            created_at = datetime.utcnow().isoformat()
            
            # Utiliser le statut fourni ou 'pending' par défaut
            transcript_status = meeting_data.get("transcript_status", "pending")
            
            # Exécuter la requête d'insertion avec un timeout plus long
            logger.info(f"Insertion de la réunion {meeting_id} dans la base de données")
            cursor.execute(
                """
                INSERT INTO meetings (
                    id, user_id, title, file_url, 
                    transcript_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting_id, 
                    user_id, 
                    meeting_data["title"], 
                    meeting_data["file_url"], 
                    transcript_status, 
                    created_at
                )
            )
            
            # Valider la transaction immédiatement
            conn.commit()
            logger.info(f"Réunion {meeting_id} créée avec succès")
            
            # Récupérer la réunion créée dans une nouvelle transaction
            cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
            meeting = cursor.fetchone()
            
            # Si tout s'est bien passé, sortir de la boucle
            break
            
        except sqlite3.OperationalError as e:
            # Gestion spécifique de l'erreur 'database is locked'
            if "database is locked" in str(e):
                retry_count += 1
                logger.warning(f"Base de données verrouillée, tentative {retry_count}/{max_retries}")
                
                # Attendre un peu avant de réessayer
                import time
                time.sleep(1)  # Attendre 1 seconde avant de réessayer
                
                # Fermer et réinitialiser la connexion
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
            else:
                # Autres erreurs SQLite
                logger.error(f"Erreur SQLite lors de la création de la réunion: {str(e)}")
                raise
        except Exception as e:
            # Autres erreurs non SQLite
            logger.error(f"Erreur lors de la création de la réunion: {str(e)}")
            raise
        finally:
            # Libérer la connexion dans tous les cas
            if conn:
                release_db_connection(conn)
        
    return dict(meeting) if meeting else None

def get_meeting(meeting_id, user_id):
    """Récupérer les détails d'une réunion spécifique"""
    logger = logging.getLogger("fastapi")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Log pour le debugging
        logger.info(f"DB Query: Getting meeting with ID: {meeting_id} for user: {user_id}")
        
        cursor.execute(
            "SELECT * FROM meetings WHERE id = ? AND user_id = ?", 
            (meeting_id, user_id)
        )
        meeting = cursor.fetchone()
        
        if meeting:
            meeting_dict = dict(meeting)
            # Assurer la compatibilité avec le frontend qui attend transcription_status
            meeting_dict['transcription_status'] = meeting_dict.get('transcript_status', 'pending')
            
            # Log des métadonnées pour le debugging
            if 'duration_seconds' in meeting_dict:
                logger.info(f"Meeting {meeting_id} has duration_seconds: {meeting_dict.get('duration_seconds')}")
            else:
                logger.warning(f"Meeting {meeting_id} does not have duration_seconds")
                
            if 'speakers_count' in meeting_dict:
                logger.info(f"Meeting {meeting_id} has speakers_count: {meeting_dict.get('speakers_count')}")
            else:
                logger.warning(f"Meeting {meeting_id} does not have speakers_count")
            
            # Normaliser le format de la transcription
            if 'transcript_text' in meeting_dict and meeting_dict['transcript_text']:
                meeting_dict['transcript_text'] = normalize_transcript_format(meeting_dict['transcript_text'])
                
            return meeting_dict
        
        return None
    finally:
        release_db_connection(conn)

def normalize_transcript_format(text):
    """
    Normalise le format des transcriptions pour être cohérent
    Convertit tout format de transcription ('A: texte') 
    vers un format standard 'Speaker A: texte'
    """
    if not text:
        return text
        
    import re
    
    # Pattern pour détecter "X: " au début d'une ligne qui n'est pas précédé par "Speaker "
    pattern = r'(^|\n)(?!Speaker )([A-Z0-9]+): '
    replacement = r'\1Speaker \2: '
    
    # Remplacer "X: " par "Speaker X: "
    normalized_text = re.sub(pattern, replacement, text)
    
    return normalized_text

def get_meetings_by_user(user_id):
    """Récupérer toutes les réunions d'un utilisateur"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM meetings WHERE user_id = ? ORDER BY created_at DESC", 
                (user_id,)
            )
            meetings = cursor.fetchall()
            
            # Convertir les résultats en dictionnaires et renommer transcript_status en transcription_status
            result = []
            for m in meetings:
                meeting_dict = dict(m)
                meeting_dict['transcription_status'] = meeting_dict.get('transcript_status', 'pending')
                
                # Normaliser le format de la transcription si présent dans les résultats
                if 'transcript_text' in meeting_dict and meeting_dict['transcript_text']:
                    meeting_dict['transcript_text'] = normalize_transcript_format(meeting_dict['transcript_text'])
                
                result.append(meeting_dict)
            
            return result
        except Exception as e:
            logger = logging.getLogger("fastapi")
            logger.error(f"Error fetching meetings: {str(e)}")
            return []
    finally:
        release_db_connection(conn)

def update_meeting(meeting_id: str, user_id: str, update_data: dict):
    """Mettre à jour une réunion"""
    logger = logging.getLogger("fastapi")
    
    # Définir une connexion comme None pour éviter des erreurs dans le bloc finally
    conn = None
    
    try:
        # Log des données à mettre à jour
        logger.info(f"Début de mise à jour pour {meeting_id} avec data: {update_data}")
        
        # Normaliser le format du texte de transcription s'il est présent
        if 'transcript_text' in update_data and update_data['transcript_text']:
            update_data['transcript_text'] = normalize_transcript_format(update_data['transcript_text'])
        
        # Log des valeurs spécifiques pour le debugging
        if 'duration_seconds' in update_data:
            logger.info(f"DEBUG: Mise à jour duration_seconds = {update_data['duration_seconds']} (type: {type(update_data['duration_seconds'])})")
        if 'speakers_count' in update_data:
            logger.info(f"DEBUG: Mise à jour speakers_count = {update_data['speakers_count']} (type: {type(update_data['speakers_count'])})")
        
        # Construire la requête de mise à jour
        query = "UPDATE meetings SET "
        values = []
        params = []
        for key, value in update_data.items():
            query += f"{key} = ?, "
            values.append(value)
            logger.info(f"Ajout de paramètre: {key}={value} (type: {type(value)}, value_repr: {repr(value)})")
        
        # Supprimer la dernière virgule et ajouter la condition WHERE
        query = query.rstrip(", ") + " WHERE id = ? AND user_id = ?"
        values.extend([meeting_id, user_id])
        
        logger.info(f"Requête SQL: {query}")
        logger.info(f"Valeurs: {values}")
        
        # Exécuter la requête - Créer une nouvelle connexion à chaque appel
        # pour éviter les problèmes de thread avec SQLite
        try:
            # Créer une nouvelle connexion dans le thread actuel
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            
            # Log de la mise à jour
            logger.info(f"DB Update: Meeting {meeting_id} updated with data: {update_data}")
            
            # Vérifier si la mise à jour a été effectuée
            if cursor.rowcount == 0:
                logger.warning(f"DB Warning: No rows updated for meeting {meeting_id}")
                # Vérifier si la réunion existe
                cursor.execute("SELECT COUNT(*) FROM meetings WHERE id = ? AND user_id = ?", (meeting_id, user_id))
                count = cursor.fetchone()[0]
                
                if count == 0:
                    logger.error(f"DB Error: Meeting {meeting_id} does not exist for user {user_id}")
                else:
                    logger.warning(f"DB Warning: Meeting exists but no update was necessary")
                
                return False
                
            return True
        except sqlite3.Error as e:
            logger.error(f"DB Error: Failed to update meeting {meeting_id}: {str(e)}")
            logger.error(f"Traceback (most recent call last):")
            import traceback
            logger.error(traceback.format_exc())
            return False
    except Exception as e:
        logger.error(f"DB Error: Failed to update meeting {meeting_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        if conn:
            release_db_connection(conn)

def delete_meeting(meeting_id, user_id):
    """Supprimer une réunion"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Récupérer l'URL du fichier avant de supprimer
        cursor.execute(
            "SELECT file_url FROM meetings WHERE id = ? AND user_id = ?", 
            (meeting_id, user_id)
        )
        meeting = cursor.fetchone()
        
        if not meeting:
            return None
        
        file_url = meeting["file_url"]
        
        # Supprimer la réunion
        cursor.execute(
            "DELETE FROM meetings WHERE id = ? AND user_id = ?", 
            (meeting_id, user_id)
        )
        
        conn.commit()
        
        return file_url
    finally:
        release_db_connection(conn)

def get_pending_transcriptions(max_age_hours=24):
    """Récupère les transcriptions en attente qui ne sont pas trop anciennes"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM meetings 
            WHERE transcript_status = 'pending' 
            AND created_at > datetime('now', ? || ' hours')
            """,
            (f"-{max_age_hours}",)
        )
        meetings = cursor.fetchall()
        return [dict(m) for m in meetings]
    finally:
        release_db_connection(conn)

def get_meetings_by_status(status, max_age_hours=72):
    """Récupère les réunions avec un statut spécifique qui ne sont pas trop anciennes"""
    logger = logging.getLogger("fastapi")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Log pour le debugging
        logger.info(f"DB Query: Getting meetings with status: {status}, max age: {max_age_hours} hours")
        
        cursor.execute(
            """
            SELECT * FROM meetings 
            WHERE transcript_status = ? 
            AND created_at > datetime('now', ? || ' hours')
            """,
            (status, f"-{max_age_hours}")
        )
        meetings = cursor.fetchall()
        
        # Convertir en dictionnaires
        result = [dict(m) for m in meetings]
        logger.info(f"Found {len(result)} meetings with status '{status}'")
        
        return result
    except Exception as e:
        logger.error(f"Error fetching meetings with status '{status}': {str(e)}")
        return []
    finally:
        release_db_connection(conn)
