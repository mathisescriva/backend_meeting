#!/usr/bin/env python3
"""
Script pour retraiter manuellement une réunion en attente.
"""
import sys
import sqlite3
import os
from app.services.assemblyai import _process_transcription

def reprocess_meeting(meeting_id):
    """Retraite une réunion specifique depuis la base de données"""
    print(f"Retraitement de la réunion: {meeting_id}")
    
    # Connexion à la base de données
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Récupération des données de la réunion
    cursor.execute("""
        SELECT id, user_id, file_url, transcript_status FROM meetings
        WHERE id = ?
    """, (meeting_id,))
    
    meeting = cursor.fetchone()
    
    if not meeting:
        print(f"Réunion non trouvée: {meeting_id}")
        return
    
    print(f"Statut actuel: {meeting['transcript_status']}")
    print(f"URL du fichier: {meeting['file_url']}")
    
    # Appel direct à _process_transcription
    try:
        print("Lancement du traitement...")
        _process_transcription(meeting['id'], meeting['file_url'], meeting['user_id'])
        print("Traitement terminé avec succès!")
    except Exception as e:
        print(f"Erreur lors du traitement: {str(e)}")
        import traceback
        print(traceback.format_exc())

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <meeting_id>")
        sys.exit(1)
    
    meeting_id = sys.argv[1]
    reprocess_meeting(meeting_id)

if __name__ == "__main__":
    main()
