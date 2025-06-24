#!/usr/bin/env python3
"""
Script pour tester la fonction de formatage de transcription avec noms personnalisés
"""

import sys
import os

# Ajouter le répertoire de l'application au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.transcription_checker import replace_speaker_names_in_text
from app.db.queries import get_meeting_speakers
import sqlite3

def test_format_transcript():
    """Tester le formatage de transcription"""
    
    # Récupérer les données de test
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Récupérer la réunion de test
    cursor.execute("SELECT id, transcript_text FROM meetings WHERE title LIKE '%test%' ORDER BY created_at DESC LIMIT 1")
    meeting_result = cursor.fetchone()
    
    if not meeting_result:
        print("❌ Aucune réunion de test trouvée")
        return
    
    meeting_id, original_transcript = meeting_result
    
    # Récupérer les locuteurs personnalisés
    cursor.execute("SELECT speaker_id, custom_name FROM meeting_speakers WHERE meeting_id = ?", (meeting_id,))
    speakers_results = cursor.fetchall()
    
    conn.close()
    
    print("=== TEST DE FORMATAGE DE TRANSCRIPTION ===")
    print(f"📋 Meeting ID: {meeting_id}")
    print(f"📄 Transcription originale ({len(original_transcript)} caractères):")
    print("=" * 50)
    print(original_transcript[:500] + "..." if len(original_transcript) > 500 else original_transcript)
    print("=" * 50)
    
    print("\n👥 Locuteurs personnalisés:")
    speakers_mapping = {}
    for speaker_id, custom_name in speakers_results:
        speakers_mapping[speaker_id] = custom_name
        print(f"   • {speaker_id} → {custom_name}")
    
    # Tester la fonction de formatage
    print("\n🔄 Application du formatage...")
    
    try:
        formatted_transcript = replace_speaker_names_in_text(original_transcript, speakers_mapping)
        
        print(f"✅ Formatage réussi! ({len(formatted_transcript)} caractères)")
        print("\n📝 Transcription formatée:")
        print("=" * 50)
        print(formatted_transcript[:500] + "..." if len(formatted_transcript) > 500 else formatted_transcript)
        print("=" * 50)
        
        # Vérifier si les noms personnalisés sont présents
        print("\n🔍 Vérification des remplacements:")
        for speaker_id, custom_name in speakers_mapping.items():
            if custom_name in formatted_transcript:
                print(f"   ✅ '{custom_name}' trouvé dans la transcription formatée")
            else:
                print(f"   ❌ '{custom_name}' NON trouvé dans la transcription formatée")
                
            if speaker_id in formatted_transcript:
                print(f"   ⚠️  '{speaker_id}' encore présent dans la transcription formatée")
            else:
                print(f"   ✅ '{speaker_id}' correctement remplacé")
        
        # Comparaison
        print(f"\n📊 Comparaison:")
        print(f"   Original: {len(original_transcript)} caractères")
        print(f"   Formaté:  {len(formatted_transcript)} caractères")
        print(f"   Différence: {len(formatted_transcript) - len(original_transcript)} caractères")
        
    except Exception as e:
        print(f"❌ Erreur lors du formatage: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_format_transcript() 