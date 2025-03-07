import sqlite3
import uuid
from datetime import datetime
from .database import get_db_connection, release_db_connection

def create_meeting(meeting_data, user_id):
    """Créer une nouvelle réunion"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        meeting_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        # Utiliser le statut fourni ou 'pending' par défaut
        transcript_status = meeting_data.get("transcript_status", "pending")
        
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
        
        conn.commit()
        
        # Récupérer la réunion créée
        cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
        meeting = cursor.fetchone()
        
        return dict(meeting) if meeting else None
    finally:
        release_db_connection(conn)

def get_meeting(meeting_id, user_id):
    """Récupérer une réunion par son ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Log pour le debugging
        print(f"DB Query: Getting meeting with ID: {meeting_id} for user: {user_id}")
        
        cursor.execute(
            "SELECT * FROM meetings WHERE id = ? AND user_id = ?", 
            (meeting_id, user_id)
        )
        meeting = cursor.fetchone()
        
        if meeting:
            meeting_dict = dict(meeting)
            # Assurer la compatibilité avec le frontend qui attend transcription_status
            meeting_dict['transcription_status'] = meeting_dict.get('transcript_status', 'pending')
            return meeting_dict
        
        return None
    finally:
        release_db_connection(conn)

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
                result.append(meeting_dict)
            
            return result
        except Exception as e:
            print(f"Error fetching meetings: {str(e)}")
            return []
    finally:
        release_db_connection(conn)

def update_meeting(meeting_id: str, user_id: str, update_data: dict):
    """Mettre à jour une réunion"""
    try:
        # Construire la requête de mise à jour
        query = "UPDATE meetings SET "
        values = []
        params = []
        for key, value in update_data.items():
            query += f"{key} = ?, "
            values.append(value)
        
        # Supprimer la dernière virgule et ajouter la condition WHERE
        query = query.rstrip(", ") + " WHERE id = ? AND user_id = ?"
        values.extend([meeting_id, user_id])
        
        # Exécuter la requête
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        
        # Log de la mise à jour
        print(f"DB Update: Meeting {meeting_id} updated with data: {update_data}")
        
        # Vérifier si la mise à jour a été effectuée
        if cursor.rowcount == 0:
            print(f"DB Warning: No rows updated for meeting {meeting_id}")
            return False
            
        return True
    except Exception as e:
        print(f"DB Error: Failed to update meeting {meeting_id}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False
    finally:
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
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(hours=max_age_hours)
        cutoff_date_str = cutoff_date.strftime("%Y-%m-%dT%H:%M:%S")
        
        cursor.execute(
            "SELECT id, title, user_id, file_url, transcript_status, created_at FROM meetings " +
            "WHERE transcript_status IN ('pending', 'processing') AND created_at > ? " +
            "ORDER BY created_at ASC",
            (cutoff_date_str,)
        )
        
        meetings = cursor.fetchall()
        return [dict(meeting) for meeting in meetings]
    finally:
        release_db_connection(conn)
