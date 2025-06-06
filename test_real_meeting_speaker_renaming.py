#!/usr/bin/env python
"""
Script de test pour renommer les intervenants d'une réunion existante et vérifier
que les modifications sont bien sauvegardées dans la base de données.
"""
import json
import sqlite3
import sys
from uuid import uuid4
from app.db.database import get_db_connection
from app.db.queries import (
    get_meeting, get_meeting_speakers, 
    set_meeting_speaker, delete_meeting_speaker
)
from app.services.transcription_checker import (
    get_assemblyai_transcript_details, format_transcript_text
)

def print_section(title):
    """Affiche un titre de section formaté"""
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")

# Trouver une réunion existante avec une transcription terminée
print_section("LISTE DES RÉUNIONS")
print("Recherche d'une réunion avec une transcription terminée...")

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer la liste des meetings avec transcription terminée
    cursor.execute(
        "SELECT id, user_id, title, transcript_status, transcript_id FROM meetings "
        "WHERE transcript_status = 'completed' AND transcript_id IS NOT NULL"
    )
    meetings = cursor.fetchall()
    
    if not meetings:
        print("Aucune réunion avec transcription terminée trouvée!")
        sys.exit(1)
        
    # Afficher les réunions disponibles
    print(f"Trouvé {len(meetings)} réunion(s) avec transcription terminée:")
    for i, meeting in enumerate(meetings):
        print(f"{i+1}. ID: {meeting[0]}, Titre: {meeting[2]}")
    
    # Sélectionner la première réunion
    selected_meeting = meetings[0]
    meeting_id = selected_meeting[0]
    user_id = selected_meeting[1]
    meeting_title = selected_meeting[2]
    transcript_id = selected_meeting[4]
    
    print(f"\nRéunion sélectionnée: {meeting_title} (ID: {meeting_id})")
    
    # Vérifier si des noms personnalisés existent déjà
    print_section("NOMS PERSONNALISÉS EXISTANTS")
    cursor.execute(
        "SELECT speaker_id, custom_name FROM meeting_speakers WHERE meeting_id = ?",
        (meeting_id,)
    )
    existing_speakers = cursor.fetchall()
    
    if existing_speakers:
        print("Noms personnalisés existants:")
        for speaker in existing_speakers:
            print(f"  - Locuteur {speaker[0]}: {speaker[1]}")
        
        # Suppression des noms existants pour un test propre
        print("\nSuppression des noms personnalisés existants pour un test propre...")
        cursor.execute(
            "DELETE FROM meeting_speakers WHERE meeting_id = ?",
            (meeting_id,)
        )
        conn.commit()
    else:
        print("Aucun nom personnalisé existant.")
    
    # Récupérer le contenu de la transcription
    print_section("CONTENU DE LA TRANSCRIPTION ORIGINALE")
    cursor.execute(
        "SELECT transcript_text FROM meetings WHERE id = ?",
        (meeting_id,)
    )
    result = cursor.fetchone()
    original_transcript = result[0] if result else "Aucune transcription trouvée"
    print(original_transcript[:500] + "..." if len(original_transcript) > 500 else original_transcript)
    
    # Récupérer les détails de la transcription depuis AssemblyAI
    print_section("IDENTIFICATION DES LOCUTEURS")
    transcript_data = get_assemblyai_transcript_details(transcript_id)
    
    if not transcript_data or 'utterances' not in transcript_data or not transcript_data['utterances']:
        print("Impossible de récupérer les détails de la transcription ou pas de diarisation.")
        sys.exit(1)
    
    # Identifier les locuteurs uniques
    unique_speakers = set()
    for utterance in transcript_data['utterances']:
        unique_speakers.add(utterance.get('speaker', 'Unknown'))
    
    print(f"Locuteurs identifiés: {', '.join(sorted(unique_speakers))}")
    
    # Créer des noms personnalisés pour chaque locuteur
    custom_names = {}
    for speaker in sorted(unique_speakers):
        if speaker == 'A':
            custom_names[speaker] = "Jean Dupont"
        elif speaker == 'B':
            custom_names[speaker] = "Marie Martin"
        elif speaker == 'C':
            custom_names[speaker] = "Pierre Durand"
        else:
            custom_names[speaker] = f"Personne {speaker}"
    
    print("\nNoms personnalisés à appliquer:")
    for speaker_id, name in custom_names.items():
        print(f"  - Locuteur {speaker_id}: {name}")
    
    # Ajouter les noms personnalisés à la base de données
    print_section("AJOUT DES NOMS PERSONNALISÉS")
    for speaker_id, custom_name in custom_names.items():
        success = set_meeting_speaker(meeting_id, user_id, speaker_id, custom_name)
        print(f"Ajout de '{custom_name}' pour locuteur '{speaker_id}': {'Succès' if success else 'Échec'}")
    
    # Vérifier les noms sauvegardés
    print_section("VÉRIFICATION DES NOMS SAUVEGARDÉS")
    saved_speakers = get_meeting_speakers(meeting_id, user_id)
    
    if saved_speakers:
        print("Noms personnalisés sauvegardés dans la base de données:")
        for speaker in saved_speakers:
            print(f"  - Locuteur {speaker['speaker_id']}: {speaker['custom_name']}")
    else:
        print("Erreur: Aucun nom personnalisé trouvé après enregistrement!")
    
    # Récupérer la réunion complète et vérifier la transcription
    print_section("MISE À JOUR DE LA TRANSCRIPTION")
    
    # Formater la transcription avec les noms personnalisés
    formatted_transcript = format_transcript_text(transcript_data, {s['speaker_id']: s['custom_name'] for s in saved_speakers})
    
    print("Transcription avec noms personnalisés (extrait):")
    print(formatted_transcript[:500] + "..." if len(formatted_transcript) > 500 else formatted_transcript)
    
    # Mise à jour de la transcription dans la base de données
    cursor.execute(
        "UPDATE meetings SET transcript_text = ? WHERE id = ?",
        (formatted_transcript, meeting_id)
    )
    conn.commit()
    
    # Vérifier que la transcription a été mise à jour
    print_section("VÉRIFICATION FINALE")
    cursor.execute(
        "SELECT transcript_text FROM meetings WHERE id = ?",
        (meeting_id,)
    )
    updated_transcript = cursor.fetchone()[0]
    
    print("Transcription mise à jour dans la base de données (extrait):")
    print(updated_transcript[:500] + "..." if len(updated_transcript) > 500 else updated_transcript)
    
    print("\nTest terminé avec succès!")
    
except Exception as e:
    print(f"ERREUR: {str(e)}")
finally:
    if 'conn' in locals():
        conn.close()
