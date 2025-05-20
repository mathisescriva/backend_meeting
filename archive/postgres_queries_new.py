import psycopg2
import psycopg2.extras
import uuid
import re
import logging
import traceback
from datetime import datetime, timedelta
from .postgres_adapter import get_db_connection, release_db_connection

# Configuration du logging
logger = logging.getLogger("postgres_queries")

def normalize_transcript_format(text):
    """
    Normalise le format des transcriptions pour être cohérent
    Convertit tout format de transcription ('A: texte') 
    vers un format standard 'Speaker A: texte'
    """
    if not text:
        return text
        
    # Pattern pour détecter "X: " au début d'une ligne qui n'est pas précédé par "Speaker "
    pattern = r'(^|\n)(?!Speaker )([A-Z0-9]+): '
    replacement = r'\1Speaker \2: '
    
    # Remplacer "X: " par "Speaker X: "
    normalized_text = re.sub(pattern, replacement, text)
    
    return normalized_text

def create_meeting(meeting_data, user_id):
    """
    Créer une nouvelle réunion dans PostgreSQL
    """
    # Logger pour le débogage
    logger.info(f"Création d'une nouvelle réunion pour l'utilisateur {user_id}")
    
    # Convertir l'ID utilisateur en entier si nécessaire
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    # Récupérer une nouvelle connexion pour cette transaction
    conn = None
    meeting = None
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Obtenir une nouvelle connexion
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Générer un ID unique pour la réunion
            meeting_id = str(uuid.uuid4())
            created_at = datetime.utcnow()
            
            # Utiliser le statut fourni ou 'pending' par défaut
            transcript_status = meeting_data.get("transcript_status", "pending")
            
            # Exécuter la requête d'insertion
            logger.info(f"Insertion de la réunion {meeting_id} dans la base de données PostgreSQL")
            cursor.execute(
                """
                INSERT INTO meetings (
                    id, user_id, title, file_url, 
                    transcript_status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
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
            
            # Récupérer la réunion créée
            meeting = cursor.fetchone()
            
            # Valider la transaction
            conn.commit()
            logger.info(f"Réunion {meeting_id} créée avec succès dans PostgreSQL")
            
            # Si tout s'est bien passé, sortir de la boucle
            break
            
        except Exception as e:
            # Gestion des erreurs
            retry_count += 1
            logger.error(f"Erreur lors de la création de la réunion dans PostgreSQL: {str(e)}")
            
            # Annuler la transaction
            if conn:
                conn.rollback()
            
            # Si c'est la dernière tentative, lever l'exception
            if retry_count >= max_retries:
                raise
                
            # Attendre un peu avant de réessayer
            import time
            time.sleep(1)  # Attendre 1 seconde avant de réessayer
        finally:
            # Libérer la connexion dans tous les cas
            if conn:
                release_db_connection(conn)
        
    return dict(meeting) if meeting else None

def get_meeting(meeting_id, user_id):
    """Récupérer les détails d'une réunion spécifique depuis PostgreSQL"""
    logger.info(f"Récupération de la réunion {meeting_id} pour l'utilisateur {user_id} depuis PostgreSQL")
    
    # Convertir l'ID utilisateur en entier si nécessaire
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute(
            "SELECT * FROM meetings WHERE id = %s AND user_id = %s", 
            (meeting_id, user_id)
        )
        meeting = cursor.fetchone()
        
        if meeting:
            meeting_dict = dict(meeting)
            # Assurer la compatibilité avec le frontend qui attend transcription_status
            meeting_dict['transcription_status'] = meeting_dict.get('transcript_status', 'pending')
            
            # Normaliser le format de la transcription
            if 'transcript_text' in meeting_dict and meeting_dict['transcript_text']:
                meeting_dict['transcript_text'] = normalize_transcript_format(meeting_dict['transcript_text'])
                
            return meeting_dict
        
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la réunion depuis PostgreSQL: {str(e)}")
        return None
    finally:
        release_db_connection(conn)

def get_meetings_by_user(user_id):
    """Récupérer toutes les réunions d'un utilisateur depuis PostgreSQL"""
    logger.info(f"Récupération des réunions pour l'utilisateur {user_id} depuis PostgreSQL")
    
    # Convertir l'ID utilisateur en entier si nécessaire
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute(
                "SELECT * FROM meetings WHERE user_id = %s ORDER BY created_at DESC", 
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
            logger.error(f"Erreur lors de la récupération des réunions depuis PostgreSQL: {str(e)}")
            return []
    finally:
        release_db_connection(conn)

def update_meeting(meeting_id: str, user_id: str, update_data: dict):
    """Mettre à jour une réunion dans PostgreSQL"""
    logger.info(f"Mise à jour de la réunion {meeting_id} pour l'utilisateur {user_id} dans PostgreSQL")
    
    # Convertir l'ID utilisateur en entier si nécessaire
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    # Définir une connexion comme None pour éviter des erreurs dans le bloc finally
    conn = None
    
    try:
        # Log des données à mettre à jour
        logger.info(f"Données de mise à jour: {update_data}")
        
        # Normaliser le format du texte de transcription s'il est présent
        if 'transcript_text' in update_data and update_data['transcript_text']:
            update_data['transcript_text'] = normalize_transcript_format(update_data['transcript_text'])
        
        # Construire la requête de mise à jour pour PostgreSQL
        query = "UPDATE meetings SET "
        values = []
        for key, value in update_data.items():
            query += f"{key} = %s, "
            values.append(value)
            logger.info(f"Paramètre: {key}={value} (type: {type(value)})")
        
        # Supprimer la dernière virgule et ajouter la condition WHERE
        query = query.rstrip(", ") + " WHERE id = %s AND user_id = %s"
        values.extend([meeting_id, user_id])
        
        logger.info(f"Requête SQL: {query}")
        
        # Exécuter la requête
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            
            # Vérifier si la mise à jour a été effectuée
            if cursor.rowcount == 0:
                logger.warning(f"Aucune ligne mise à jour pour la réunion {meeting_id}")
                # Vérifier si la réunion existe
                cursor.execute("SELECT COUNT(*) FROM meetings WHERE id = %s AND user_id = %s", (meeting_id, user_id))
                count = cursor.fetchone()[0]
                
                if count == 0:
                    logger.error(f"La réunion {meeting_id} n'existe pas pour l'utilisateur {user_id}")
                else:
                    logger.warning(f"La réunion existe mais aucune mise à jour n'était nécessaire")
                
                return False
                
            return True
        except psycopg2.Error as e:
            logger.error(f"Erreur PostgreSQL lors de la mise à jour de la réunion {meeting_id}: {str(e)}")
            logger.error(traceback.format_exc())
            if conn:
                conn.rollback()
            return False
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la réunion {meeting_id}: {str(e)}")
        logger.error(traceback.format_exc())
        if conn and 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if conn and 'conn' in locals():
            release_db_connection(conn)

def delete_meeting(meeting_id, user_id):
    """Supprimer une réunion dans PostgreSQL"""
    logger.info(f"Suppression de la réunion {meeting_id} pour l'utilisateur {user_id} depuis PostgreSQL")
    
    # Convertir l'ID utilisateur en entier si nécessaire
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Supprimer la réunion
        cursor.execute(
            "DELETE FROM meetings WHERE id = %s AND user_id = %s", 
            (meeting_id, user_id)
        )
        
        # Valider la transaction
        conn.commit()
        
        # Vérifier si la suppression a été effectuée
        if cursor.rowcount == 0:
            logger.warning(f"Aucune réunion supprimée avec ID {meeting_id} pour l'utilisateur {user_id}")
            return False
            
        logger.info(f"Réunion {meeting_id} supprimée avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la réunion: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        release_db_connection(conn)

# Les fonctions existantes
def get_pending_transcriptions(max_age_hours=24):
    """Récupère les transcriptions en attente qui ne sont pas trop anciennes (PostgreSQL)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # PostgreSQL utilise INTERVAL pour les opérations de date/heure
        cursor.execute(
            """
            SELECT * FROM meetings 
            WHERE transcript_status = 'pending' 
            AND created_at > NOW() - INTERVAL '%s hours'
            """,
            (max_age_hours,)
        )
        meetings = cursor.fetchall()
        return [dict(m) for m in meetings]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des transcriptions en attente: {str(e)}")
        return []
    finally:
        release_db_connection(conn)

def get_meetings_by_status(status, max_age_hours=72):
    """Récupère les réunions avec un statut spécifique qui ne sont pas trop anciennes (PostgreSQL)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # PostgreSQL utilise INTERVAL pour les opérations de date/heure
        cursor.execute(
            """
            SELECT * FROM meetings 
            WHERE transcript_status = %s 
            AND created_at > NOW() - INTERVAL '%s hours'
            ORDER BY created_at DESC
            """,
            (status, max_age_hours)
        )
        meetings = cursor.fetchall()
        return [dict(m) for m in meetings]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réunions par statut: {str(e)}")
        return []
    finally:
        release_db_connection(conn)
