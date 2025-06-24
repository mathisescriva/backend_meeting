#!/usr/bin/env python3
"""
Script pour créer une réunion de test avec transcription et locuteurs personnalisés
"""

import requests
import json
import sqlite3
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"

def login():
    """Se connecter et récupérer un token"""
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login/json", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Erreur de connexion: {response.status_code}")
        return None

def create_test_meeting_in_db():
    """Créer directement une réunion de test dans la base de données"""
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # Récupérer l'ID de l'utilisateur test
    cursor.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",))
    user_result = cursor.fetchone()
    if not user_result:
        print("Utilisateur test non trouvé")
        return None
    
    user_id = user_result[0]
    meeting_id = str(uuid.uuid4())
    
    # Créer la réunion
    meeting_data = {
        'id': meeting_id,
        'user_id': user_id,
        'title': 'Réunion de test - Compte rendu avec noms personnalisés',
        'file_url': 'test://meeting-file-url',
        'transcript_status': 'completed',
        'transcript_text': '''Speaker A: Bonjour à tous, je suis ravi de vous retrouver pour cette réunion importante.

Speaker B: Merci de nous avoir organisé cette rencontre. J'ai plusieurs points à aborder concernant le projet.

Speaker A: Parfait, nous allons commencer par faire le point sur l'avancement des développements.

Speaker C: De mon côté, j'ai terminé l'implémentation des nouvelles fonctionnalités que nous avions discutées la semaine dernière.

Speaker B: Excellent travail ! Pouvez-vous nous donner plus de détails sur les performances ?

Speaker C: Bien sûr, les tests montrent une amélioration de 30% par rapport à la version précédente.

Speaker A: C'est formidable ! Qu'en est-il de la sécurité ?

Speaker B: J'ai effectué un audit complet et tout semble conforme aux standards requis.

Speaker C: Parfait, nous pouvons donc procéder au déploiement la semaine prochaine.

Speaker A: Très bien, je vais préparer la documentation pour l'équipe de production.

Speaker B: N'oubliez pas de prévoir une session de formation pour les utilisateurs finaux.

Speaker C: Bien noté, je m'en occupe dès demain.

Speaker A: Excellent, merci à tous pour votre travail. À bientôt !''',
        'summary_status': 'pending',
        'duration_seconds': 300,
        'speakers_count': 3,
        'created_at': datetime.now().isoformat()
    }
    
    # Insérer la réunion
    cursor.execute('''
        INSERT INTO meetings (id, user_id, title, file_url, transcript_status, transcript_text, summary_status, duration_seconds, speakers_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        meeting_data['id'],
        meeting_data['user_id'],
        meeting_data['title'],
        meeting_data['file_url'],
        meeting_data['transcript_status'],
        meeting_data['transcript_text'],
        meeting_data['summary_status'],
        meeting_data['duration_seconds'],
        meeting_data['speakers_count'],
        meeting_data['created_at']
    ))
    
    # Créer les locuteurs personnalisés
    speakers = [
        {'speaker_id': 'Speaker A', 'custom_name': 'Marie Dupont (CEO)'},
        {'speaker_id': 'Speaker B', 'custom_name': 'Jean Martin (CTO)'},
        {'speaker_id': 'Speaker C', 'custom_name': 'Sophie Leclerc (Dev Lead)'}
    ]
    
    for speaker in speakers:
        cursor.execute('''
            INSERT INTO meeting_speakers (id, meeting_id, speaker_id, custom_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            meeting_id,
            speaker['speaker_id'],
            speaker['custom_name'],
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Réunion de test créée avec l'ID: {meeting_id}")
    print("👥 Locuteurs personnalisés:")
    for speaker in speakers:
        print(f"   • {speaker['speaker_id']} → {speaker['custom_name']}")
    
    return meeting_id

def main():
    print("=== CRÉATION D'UNE RÉUNION DE TEST ===")
    
    # Créer la réunion de test
    meeting_id = create_test_meeting_in_db()
    
    if meeting_id:
        print(f"\n✅ Réunion de test créée avec succès!")
        print(f"📋 ID de la réunion: {meeting_id}")
        print(f"🔗 Vous pouvez maintenant tester avec: python test_mistral_with_custom_names.py")
    else:
        print("❌ Erreur lors de la création de la réunion de test")

if __name__ == "__main__":
    main() 