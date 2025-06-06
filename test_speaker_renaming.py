#!/usr/bin/env python
"""
Script de test pour la fonctionnalité de renommage des locuteurs dans les transcriptions
"""
import json
import sqlite3
from uuid import uuid4
from app.services.transcription_checker import format_transcript_text

# Exemple de données de transcription avec des locuteurs
sample_transcript_data = {
    "utterances": [
        {"speaker": "A", "text": "Bonjour à tous, je suis le premier intervenant."},
        {"speaker": "B", "text": "Bonjour, je suis le deuxième intervenant."},
        {"speaker": "A", "text": "Nous allons discuter du projet aujourd'hui."},
        {"speaker": "C", "text": "Je suis le troisième intervenant et j'ai quelques questions."},
        {"speaker": "B", "text": "Bien sûr, nous sommes là pour y répondre."}
    ]
}

# Test de formatage sans noms personnalisés
print("\n--- Test de formatage sans noms personnalisés ---")
formatted_text = format_transcript_text(sample_transcript_data)
print(formatted_text)

# Test de formatage avec noms personnalisés
print("\n--- Test de formatage avec noms personnalisés ---")
custom_speaker_names = {
    "A": "Jean Dupont",
    "B": "Marie Martin",
    "C": "Pierre Durand"
}
formatted_text_custom = format_transcript_text(sample_transcript_data, custom_speaker_names)
print(formatted_text_custom)

# Test de la base de données (si elle existe déjà)
try:
    print("\n--- Test des fonctions de base de données ---")
    from app.db.queries import get_meeting_speakers, set_meeting_speaker, delete_meeting_speaker
    from app.db.database import get_db_connection

    # Créer un ID de réunion de test et un ID utilisateur de test
    test_meeting_id = str(uuid4())
    test_user_id = str(uuid4())
    
    print(f"Test meeting ID: {test_meeting_id}")
    print(f"Test user ID: {test_user_id}")
    
    # Créer une entrée de test pour la réunion
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO meetings (id, user_id, title, transcript_status) VALUES (?, ?, ?, ?)",
        (test_meeting_id, test_user_id, "Test Meeting", "completed")
    )
    conn.commit()
    
    # Tester l'ajout de noms de locuteurs personnalisés
    print("\nAjout de noms personnalisés:")
    for speaker_id, custom_name in custom_speaker_names.items():
        success = set_meeting_speaker(test_meeting_id, test_user_id, speaker_id, custom_name)
        print(f"  - Ajout de '{custom_name}' pour locuteur '{speaker_id}': {'Succès' if success else 'Échec'}")
    
    # Récupérer les noms personnalisés
    print("\nRécupération des noms personnalisés:")
    speakers = get_meeting_speakers(test_meeting_id, test_user_id)
    if speakers:
        for speaker in speakers:
            print(f"  - Locuteur: {speaker['speaker_id']}, Nom: {speaker['custom_name']}")
    else:
        print("  Aucun locuteur personnalisé trouvé.")
    
    # Supprimer un nom personnalisé
    test_speaker_id = "B"
    print(f"\nSuppression du nom personnalisé pour le locuteur '{test_speaker_id}':")
    success = delete_meeting_speaker(test_meeting_id, test_user_id, test_speaker_id)
    print(f"  - Suppression: {'Succès' if success else 'Échec'}")
    
    # Vérifier après suppression
    print("\nRécupération des noms personnalisés après suppression:")
    speakers = get_meeting_speakers(test_meeting_id, test_user_id)
    if speakers:
        for speaker in speakers:
            print(f"  - Locuteur: {speaker['speaker_id']}, Nom: {speaker['custom_name']}")
    else:
        print("  Aucun locuteur personnalisé trouvé.")
    
    # Nettoyer les données de test
    print("\nNettoyage des données de test...")
    cursor.execute("DELETE FROM meeting_speakers WHERE meeting_id = ?", (test_meeting_id,))
    cursor.execute("DELETE FROM meetings WHERE id = ?", (test_meeting_id,))
    conn.commit()
    conn.close()
    
except Exception as e:
    print(f"Erreur lors du test des fonctions de base de données: {str(e)}")
