#!/usr/bin/env python3
"""
Script pour tester directement la fonction process_meeting_summary
"""

import sys
import os
from datetime import datetime

# Ajouter le répertoire de l'application au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_direct_function():
    """Tester directement la fonction process_meeting_summary"""
    print("=== TEST DIRECT DE LA FONCTION process_meeting_summary ===")
    
    try:
        from app.services.mistral_summary import process_meeting_summary
        from app.db.queries import get_meeting, get_meeting_speakers
        
        # ID de notre réunion de test
        meeting_id = "bc96e19f-f7df-4dba-aebb-4ce658309bc2"
        
        # Récupérer l'utilisateur de test
        import sqlite3
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",))
        user_result = cursor.fetchone()
        conn.close()
        
        if not user_result:
            print("❌ Utilisateur test non trouvé")
            return
        
        user_id = user_result[0]
        print(f"👤 User ID: {user_id}")
        print(f"📋 Meeting ID: {meeting_id}")
        
        # Récupérer les données de la réunion
        meeting = get_meeting(meeting_id, user_id)
        if not meeting:
            print("❌ Réunion non trouvée")
            return
        
        print(f"📊 Réunion trouvée: {meeting.get('title')}")
        print(f"📄 Transcription disponible: {len(meeting.get('transcript_text', ''))} caractères")
        
        # Récupérer les locuteurs personnalisés
        speakers_data = get_meeting_speakers(meeting_id, user_id)
        if speakers_data:
            print("👥 Locuteurs personnalisés:")
            for speaker in speakers_data:
                print(f"   • {speaker['speaker_id']} → {speaker['custom_name']}")
        else:
            print("ℹ️ Aucun locuteur personnalisé")
        
        # Tester la fonction de formatage directement
        from app.services.transcription_checker import replace_speaker_names_in_text
        
        transcript_text = meeting.get("transcript_text", "")
        if speakers_data:
            speaker_names = {}
            for speaker in speakers_data:
                speaker_names[speaker['speaker_id']] = speaker['custom_name']
            
            formatted_transcript = replace_speaker_names_in_text(transcript_text, speaker_names)
            
            print(f"\n📝 Extrait de la transcription originale:")
            print(transcript_text[:200] + "...")
            
            print(f"\n📝 Extrait de la transcription formatée:")
            print(formatted_transcript[:200] + "...")
            
            # Vérifier si les noms ont été remplacés
            for speaker_id, custom_name in speaker_names.items():
                if custom_name in formatted_transcript:
                    print(f"   ✅ '{custom_name}' trouvé dans la transcription formatée")
                else:
                    print(f"   ❌ '{custom_name}' NON trouvé dans la transcription formatée")
        
        # Tester la génération de compte rendu directement
        print(f"\n🚀 Test de la génération de compte rendu...")
        
        # Importer la fonction de génération
        from app.services.mistral_summary import generate_meeting_summary
        
        # Utiliser la transcription formatée
        if speakers_data:
            speaker_names = {speaker['speaker_id']: speaker['custom_name'] for speaker in speakers_data}
            formatted_transcript = replace_speaker_names_in_text(transcript_text, speaker_names)
        else:
            formatted_transcript = transcript_text
        
        summary_text = generate_meeting_summary(formatted_transcript, meeting.get("title", "Réunion"))
        
        if summary_text:
            print("✅ Compte rendu généré avec succès!")
            print(f"📏 Longueur: {len(summary_text)} caractères")
            
            print("\n📝 Extrait du compte rendu:")
            print("=" * 50)
            print(summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)
            print("=" * 50)
            
            # Vérifier la présence des noms personnalisés
            if speakers_data:
                print("\n🔍 Vérification des noms personnalisés dans le compte rendu:")
                for speaker in speakers_data:
                    custom_name = speaker["custom_name"]
                    if custom_name in summary_text:
                        print(f"   ✅ '{custom_name}' trouvé dans le compte rendu")
                    else:
                        print(f"   ❌ '{custom_name}' NON trouvé dans le compte rendu")
        else:
            print("❌ Échec de la génération du compte rendu")
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_function() 