#!/usr/bin/env python3

import sqlite3
import uuid
from datetime import datetime

# Configuration
DB_PATH = "app.db"
MEETING_ID = "108f1bba-a7cd-49b8-9fc6-5a08db5274c6"
USER_ID = "2d53638f-d2db-4b72-9df1-d3d6817a9b08"  # User ID du propriétaire de la réunion
SPEAKER_ID = "Speaker D"
TEST_NAMES = ["Premier nom", "Deuxième nom", "Troisième nom"]

def get_db_connection():
    """Obtenir une connexion à la base de données"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def set_meeting_speaker_direct(meeting_id, user_id, speaker_id, custom_name):
    """Fonction similaire à celle dans queries.py mais directe"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Vérifier d'abord que la réunion appartient à l'utilisateur
        cursor.execute(
            "SELECT id FROM meetings WHERE id = ? AND user_id = ?",
            (meeting_id, user_id)
        )
        if not cursor.fetchone():
            print(f"❌ Réunion {meeting_id} non trouvée pour l'utilisateur {user_id}")
            return False
        
        # Vérifier si une entrée existe déjà pour ce locuteur dans cette réunion
        cursor.execute(
            "SELECT id FROM meeting_speakers WHERE meeting_id = ? AND speaker_id = ?",
            (meeting_id, speaker_id)
        )
        existing_entry = cursor.fetchone()
        
        if existing_entry:
            # Mettre à jour l'entrée existante
            print(f"🔄 Mise à jour de l'entrée existante pour {speaker_id}")
            cursor.execute(
                "UPDATE meeting_speakers SET custom_name = ? WHERE id = ?",
                (custom_name, existing_entry["id"])
            )
        else:
            # Créer une nouvelle entrée
            print(f"➕ Création d'une nouvelle entrée pour {speaker_id}")
            speaker_mapping_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO meeting_speakers (id, meeting_id, speaker_id, custom_name) VALUES (?, ?, ?, ?)",
                (speaker_mapping_id, meeting_id, speaker_id, custom_name)
            )
        
        conn.commit()
        print(f"✅ Succès: {speaker_id} -> {custom_name}")
        return True
    
    except sqlite3.Error as e:
        print(f"❌ Erreur SQLite: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_meeting_speakers_direct(meeting_id):
    """Récupère les speakers directement de la DB"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM meeting_speakers WHERE meeting_id = ? ORDER BY speaker_id",
            (meeting_id,)
        )
        
        speakers = cursor.fetchall()
        return [dict(speaker) for speaker in speakers]
    
    except sqlite3.Error as e:
        print(f"❌ Erreur récupération speakers: {str(e)}")
        return []
    finally:
        conn.close()

def main():
    print(f"=== Test de re-renommage direct en base de données ===")
    print(f"Réunion: {MEETING_ID}")
    print(f"Speaker: {SPEAKER_ID}")
    print()
    
    # État initial
    print("1. État initial des speakers:")
    speakers = get_meeting_speakers_direct(MEETING_ID)
    for speaker in speakers:
        if speaker["speaker_id"] == SPEAKER_ID:
            print(f"   {SPEAKER_ID}: {speaker['custom_name']}")
            break
    else:
        print(f"   {SPEAKER_ID}: (pas de nom personnalisé)")
    
    # Test de renommages successifs
    for i, new_name in enumerate(TEST_NAMES, 1):
        print(f"\n{i+1}. Renommage en '{new_name}':")
        
        # Renommer
        success = set_meeting_speaker_direct(MEETING_ID, USER_ID, SPEAKER_ID, new_name)
        
        if success:
            # Vérifier
            speakers = get_meeting_speakers_direct(MEETING_ID)
            for speaker in speakers:
                if speaker["speaker_id"] == SPEAKER_ID:
                    current_name = speaker['custom_name']
                    print(f"   Nom actuel en DB: {current_name}")
                    if current_name == new_name:
                        print(f"   ✅ Nom correctement mis à jour")
                    else:
                        print(f"   ❌ ERREUR: Nom attendu '{new_name}', obtenu '{current_name}'")
                    break
            else:
                print(f"   ❌ ERREUR: Speaker {SPEAKER_ID} non trouvé")
        else:
            print(f"   ❌ Échec du renommage")
    
    print(f"\n=== Test terminé ===")

if __name__ == "__main__":
    main() 