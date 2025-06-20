#!/usr/bin/env python3

import sys
import os

# Ajouter le répertoire parent au path pour importer les modules de l'app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.transcription_checker import format_transcript_text

def test_speaker_formatting():
    """Test direct de la fonction format_transcript_text"""
    
    print("=== Test de formatage des locuteurs ===")
    
    # Données de test simulant une transcription AssemblyAI
    test_transcript_data = {
        "text": "Hello, this is a test transcript. How are you doing today? I'm doing well, thank you.",
        "utterances": [
            {
                "start": 0,
                "end": 2000,
                "text": "Hello, this is a test transcript.",
                "speaker": "A"
            },
            {
                "start": 2000,
                "end": 4000,
                "text": "How are you doing today?",
                "speaker": "B"
            },
            {
                "start": 4000,
                "end": 6000,
                "text": "I'm doing well, thank you.",
                "speaker": "A"
            }
        ]
    }
    
    print("1. Test sans noms personnalisés")
    print("=" * 50)
    
    formatted_text_no_names = format_transcript_text(test_transcript_data)
    print("Résultat:")
    print(formatted_text_no_names)
    
    print("\n2. Test avec noms personnalisés (format simple: 'A', 'B')")
    print("=" * 50)
    
    # Noms personnalisés avec format simple
    speaker_names_simple = {
        "A": "Alice",
        "B": "Bob"
    }
    
    formatted_text_simple = format_transcript_text(test_transcript_data, speaker_names_simple)
    print("Résultat:")
    print(formatted_text_simple)
    
    print("\n3. Test avec noms personnalisés (format complet: 'Speaker A', 'Speaker B')")
    print("=" * 50)
    
    # Noms personnalisés avec format complet
    speaker_names_full = {
        "Speaker A": "Alice",
        "Speaker B": "Bob"
    }
    
    formatted_text_full = format_transcript_text(test_transcript_data, speaker_names_full)
    print("Résultat:")
    print(formatted_text_full)
    
    print("\n4. Test avec mix de formats (certains simples, certains complets)")
    print("=" * 50)
    
    # Mix de formats
    speaker_names_mixed = {
        "A": "Alice",
        "Speaker B": "Bob"
    }
    
    formatted_text_mixed = format_transcript_text(test_transcript_data, speaker_names_mixed)
    print("Résultat:")
    print(formatted_text_mixed)
    
    print("\n5. Test avec le cas problématique: renommage de 'Speaker D' en 'Tom'")
    print("=" * 50)
    
    # Cas problématique rapporté
    test_transcript_speaker_d = {
        "text": "This is speaker D talking. Then someone else responds. Speaker D continues.",
        "utterances": [
            {
                "start": 0,
                "end": 2000,
                "text": "This is speaker D talking.",
                "speaker": "D"
            },
            {
                "start": 2000,
                "end": 4000,
                "text": "Then someone else responds.",
                "speaker": "C"
            },
            {
                "start": 4000,
                "end": 6000,
                "text": "Speaker D continues.",
                "speaker": "D"
            }
        ]
    }
    
    # Test avec le renommage problématique
    speaker_names_problem = {
        "Speaker D": "Tom"
    }
    
    formatted_text_problem = format_transcript_text(test_transcript_speaker_d, speaker_names_problem)
    print("Résultat:")
    print(formatted_text_problem)
    
    # Vérifications
    print("\n=== VÉRIFICATIONS ===")
    
    # Vérifier que "Tom" apparaît dans la transcription
    tom_count = formatted_text_problem.count("Tom:")
    print(f"✅ Nombre d'occurrences de 'Tom:': {tom_count}")
    
    # Vérifier que "Speaker D" n'apparaît plus
    speaker_d_count = formatted_text_problem.count("Speaker D:")
    print(f"✅ Nombre d'occurrences de 'Speaker D:': {speaker_d_count}")
    
    # Vérifier que "Speaker C" apparaît (non renommé)
    speaker_c_count = formatted_text_problem.count("Speaker C:")
    print(f"✅ Nombre d'occurrences de 'Speaker C:': {speaker_c_count}")
    
    if tom_count > 0 and speaker_d_count == 0:
        print("\n🎉 SUCCÈS: Le problème de renommage des locuteurs est corrigé!")
    else:
        print("\n❌ ÉCHEC: Le problème persiste")
        
    print("\n6. Test avec un cas réel (speaker_id = 'D', renommé en 'Tom')")
    print("=" * 50)
    
    # Test avec format simple uniquement
    speaker_names_real_case = {
        "D": "Tom"
    }
    
    formatted_text_real = format_transcript_text(test_transcript_speaker_d, speaker_names_real_case)
    print("Résultat:")
    print(formatted_text_real)
    
    # Vérifications pour le cas réel
    tom_count_real = formatted_text_real.count("Tom:")
    speaker_d_count_real = formatted_text_real.count("Speaker D:")
    
    print(f"\nVérifications cas réel:")
    print(f"✅ Nombre d'occurrences de 'Tom:': {tom_count_real}")
    print(f"✅ Nombre d'occurrences de 'Speaker D:': {speaker_d_count_real}")
    
    if tom_count_real > 0 and speaker_d_count_real == 0:
        print("\n🎉 SUCCÈS: Le cas réel fonctionne correctement!")
    else:
        print("\n❌ ÉCHEC: Le cas réel ne fonctionne pas")

if __name__ == "__main__":
    test_speaker_formatting() 