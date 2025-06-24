#!/usr/bin/env python3
"""
Script pour tester la fonction process_meeting_summary complète
"""

import sys
import os
import sqlite3

# Ajouter le répertoire de l'application au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_complete_process():
    """Tester la fonction process_meeting_summary complète"""
    print("=== TEST COMPLET DE process_meeting_summary ===")
    
    try:
        from app.services.mistral_summary import process_meeting_summary
        
        # ID de notre réunion de test
        meeting_id = "bc96e19f-f7df-4dba-aebb-4ce658309bc2"
        
        # Récupérer l'utilisateur de test
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
        
        # Remettre le statut à pending
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE meetings SET summary_status = 'pending', summary_text = NULL WHERE id = ?", (meeting_id,))
        conn.commit()
        conn.close()
        print("🔄 Statut remis à 'pending'")
        
        # Appeler la fonction complète en mode synchrone (async_mode=False)
        print("\n🚀 Lancement de process_meeting_summary...")
        success = process_meeting_summary(meeting_id, user_id, async_mode=False)
        
        if success:
            print("✅ process_meeting_summary a réussi!")
            
            # Vérifier le résultat dans la base de données
            conn = sqlite3.connect('app.db')
            cursor = conn.cursor()
            cursor.execute("SELECT summary_status, summary_text FROM meetings WHERE id = ?", (meeting_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                status, summary_text = result
                print(f"📊 Statut final: {status}")
                print(f"📏 Longueur du texte: {len(summary_text) if summary_text else 0} caractères")
                
                if summary_text:
                    print("\n📝 Extrait du compte rendu:")
                    print("=" * 50)
                    print(summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)
                    print("=" * 50)
                    
                    # Vérifier la présence des noms personnalisés
                    custom_names = ["Marie Dupont (CEO)", "Jean Martin (CTO)", "Sophie Leclerc (Dev Lead)"]
                    print("\n🔍 Vérification des noms personnalisés:")
                    for name in custom_names:
                        if name in summary_text:
                            print(f"   ✅ '{name}' trouvé dans le compte rendu")
                        else:
                            print(f"   ❌ '{name}' NON trouvé dans le compte rendu")
                else:
                    print("❌ Aucun texte de compte rendu généré")
            else:
                print("❌ Impossible de récupérer le résultat de la base de données")
        else:
            print("❌ process_meeting_summary a échoué")
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complete_process() 