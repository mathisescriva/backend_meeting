#!/usr/bin/env python
"""
Test simplifié du renommage des locuteurs qui se concentre uniquement sur la 
manipulation des données dans la base de données, sans dépendre de l'API externe.
"""
import sqlite3
from app.db.database import get_db_connection
from app.db.queries import (
    get_meeting_speakers, set_meeting_speaker, delete_meeting_speaker
)
from app.services.transcription_checker import format_transcript_text

# Fonction pour afficher un titre de section
def print_section(title):
    """Affiche un titre de section formaté"""
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")

# Créez un exemple de transcription avec diarisation
sample_transcript = {
    "utterances": [
        {"speaker": "A", "text": "Bonjour à tous, bienvenue à cette réunion."},
        {"speaker": "B", "text": "Merci de nous avoir tous réunis aujourd'hui."},
        {"speaker": "A", "text": "Nous allons discuter du projet de renommage des locuteurs."},
        {"speaker": "C", "text": "J'ai quelques questions sur ce projet."},
        {"speaker": "B", "text": "Je peux peut-être y répondre après la présentation principale."}
    ]
}

try:
    print_section("CONNEXION À LA BASE DE DONNÉES")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Trouver une réunion existante
    print_section("RECHERCHE D'UNE RÉUNION EXISTANTE")
    cursor.execute(
        "SELECT id, user_id, title FROM meetings LIMIT 1"
    )
    meeting = cursor.fetchone()
    
    if not meeting:
        print("Aucune réunion trouvée dans la base de données!")
        exit(1)
    
    meeting_id = meeting[0]
    user_id = meeting[1]
    title = meeting[2]
    
    print(f"Réunion sélectionnée: {title} (ID: {meeting_id})")
    
    # Supprimer les noms personnalisés existants
    print_section("NETTOYAGE DES NOMS EXISTANTS")
    cursor.execute("DELETE FROM meeting_speakers WHERE meeting_id = ?", (meeting_id,))
    conn.commit()
    print("Suppression des noms personnalisés existants.")
    
    # Ajouter de nouveaux noms personnalisés
    print_section("AJOUT DE NOUVEAUX NOMS PERSONNALISÉS")
    speakers_to_add = {
        "A": "Jean Dupont",
        "B": "Marie Martin",
        "C": "Pierre Durand"
    }
    
    for speaker_id, name in speakers_to_add.items():
        success = set_meeting_speaker(meeting_id, user_id, speaker_id, name)
        print(f"Ajout de '{name}' pour locuteur '{speaker_id}': {'Succès' if success else 'Échec'}")
    
    # Récupérer les noms sauvegardés
    print_section("VÉRIFICATION DES NOMS SAUVEGARDÉS")
    saved_speakers = get_meeting_speakers(meeting_id, user_id)
    
    if saved_speakers:
        print("Noms personnalisés sauvegardés dans la base de données:")
        for speaker in saved_speakers:
            print(f"  - Locuteur {speaker['speaker_id']}: {speaker['custom_name']}")
        
        # Créer un dictionnaire pour le formatage
        speaker_names = {speaker['speaker_id']: speaker['custom_name'] for speaker in saved_speakers}
    else:
        print("Erreur: Aucun nom personnalisé trouvé après enregistrement!")
        speaker_names = {}
    
    # Tester le formatage
    print_section("TEST DE FORMATAGE DU TEXTE")
    # Sans noms personnalisés
    default_text = format_transcript_text(sample_transcript)
    print("Formatage par défaut:")
    print(default_text)
    
    # Avec noms personnalisés
    custom_text = format_transcript_text(sample_transcript, speaker_names)
    print("\nFormatage avec noms personnalisés:")
    print(custom_text)
    
    # Supprimer un nom personnalisé
    print_section("SUPPRESSION D'UN NOM PERSONNALISÉ")
    speaker_to_delete = "B"
    success = delete_meeting_speaker(meeting_id, user_id, speaker_to_delete)
    print(f"Suppression du nom pour '{speaker_to_delete}': {'Succès' if success else 'Échec'}")
    
    # Vérifier après suppression
    print_section("VÉRIFICATION APRÈS SUPPRESSION")
    updated_speakers = get_meeting_speakers(meeting_id, user_id)
    
    if updated_speakers:
        print("Noms personnalisés après suppression:")
        for speaker in updated_speakers:
            print(f"  - Locuteur {speaker['speaker_id']}: {speaker['custom_name']}")
        
        # Mettre à jour le dictionnaire pour le formatage
        updated_speaker_names = {speaker['speaker_id']: speaker['custom_name'] for speaker in updated_speakers}
    else:
        print("Aucun nom personnalisé trouvé après suppression!")
        updated_speaker_names = {}
    
    # Tester le formatage après suppression
    print_section("TEST DE FORMATAGE APRÈS SUPPRESSION")
    updated_text = format_transcript_text(sample_transcript, updated_speaker_names)
    print("Formatage avec noms personnalisés mis à jour:")
    print(updated_text)
    
    # Nettoyer les données de test
    print_section("NETTOYAGE FINAL")
    cursor.execute("DELETE FROM meeting_speakers WHERE meeting_id = ?", (meeting_id,))
    conn.commit()
    print("Nettoyage des données de test terminé.")
    
    print("\nTest terminé avec succès!")
    
except Exception as e:
    print(f"ERREUR: {str(e)}")
finally:
    if 'conn' in locals():
        conn.close()
