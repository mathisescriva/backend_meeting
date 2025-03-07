#!/usr/bin/env python3
"""
Script pour vérifier si une réunion existe dans la base de données.
"""

import sys
import sqlite3
from app.db.database import get_db_connection, release_db_connection

def check_meeting_exists(meeting_id, user_id=None):
    """Vérifie si une réunion existe, soit pour un utilisateur spécifique, soit globalement."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute(
                "SELECT * FROM meetings WHERE id = ? AND user_id = ?", 
                (meeting_id, user_id)
            )
            print(f"Recherche de la réunion {meeting_id} pour l'utilisateur {user_id}")
        else:
            cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
            print(f"Recherche de la réunion {meeting_id} globalement")
        
        meeting = cursor.fetchone()
        
        if meeting:
            print("Réunion trouvée:")
            meeting_dict = dict(meeting)
            for key, value in meeting_dict.items():
                print(f"  {key}: {value}")
            return True
        else:
            print(f"Réunion {meeting_id} non trouvée")
            
            # Liste toutes les réunions pour l'utilisateur
            if user_id:
                cursor.execute("SELECT id, title, transcript_status FROM meetings WHERE user_id = ?", (user_id,))
                meetings = cursor.fetchall()
                
                if meetings:
                    print(f"\nRéunions disponibles pour l'utilisateur {user_id}:")
                    for m in meetings:
                        print(f"  {m['id']} - {m['title']} ({m['transcript_status']})")
                else:
                    print(f"\nAucune réunion trouvée pour l'utilisateur {user_id}")
            
            return False
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_meeting.py <meeting_id> [user_id]")
        sys.exit(1)
    
    meeting_id = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    check_meeting_exists(meeting_id, user_id)
