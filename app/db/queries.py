import sqlite3
import uuid
from datetime import datetime
from .database import get_db_connection

def create_meeting(meeting_data, user_id):
    """Créer une nouvelle réunion"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    meeting_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
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
            "pending", 
            created_at
        )
    )
    
    conn.commit()
    
    # Récupérer la réunion créée
    cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
    meeting = cursor.fetchone()
    
    conn.close()
    
    return dict(meeting) if meeting else None

def get_meeting(meeting_id, user_id):
    """Récupérer une réunion par son ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM meetings WHERE id = ? AND user_id = ?", 
        (meeting_id, user_id)
    )
    meeting = cursor.fetchone()
    
    conn.close()
    
    return dict(meeting) if meeting else None

def get_meetings_by_user(user_id):
    """Récupérer toutes les réunions d'un utilisateur"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM meetings WHERE user_id = ? ORDER BY created_at DESC", 
        (user_id,)
    )
    meetings = cursor.fetchall()
    
    conn.close()
    
    return [dict(m) for m in meetings]

def update_meeting(meeting_id, user_id, update_data):
    """Mettre à jour une réunion"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que la réunion existe et appartient à l'utilisateur
    cursor.execute(
        "SELECT id FROM meetings WHERE id = ? AND user_id = ?", 
        (meeting_id, user_id)
    )
    existing = cursor.fetchone()
    
    if not existing:
        return None
    
    # Construire la requête de mise à jour dynamiquement
    set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values())
    values.append(meeting_id)
    
    cursor.execute(
        f"UPDATE meetings SET {set_clause} WHERE id = ?",
        values
    )
    
    conn.commit()
    
    # Récupérer la réunion mise à jour
    cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
    meeting = cursor.fetchone()
    
    conn.close()
    
    return dict(meeting) if meeting else None

def delete_meeting(meeting_id, user_id):
    """Supprimer une réunion"""
    conn = get_db_connection()
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
    conn.close()
    
    return file_url
