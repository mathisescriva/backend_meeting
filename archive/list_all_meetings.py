import requests

def list_meetings():
    # Connexion à l'API
    print("Connexion à l'API...")
    login_data = {
        'username': 'test@example.com',
        'password': 'password123'
    }
    login_response = requests.post('http://localhost:8001/auth/login', data=login_data)
    
    if login_response.status_code != 200:
        print(f"Erreur de connexion: {login_response.status_code} - {login_response.text}")
        return
    
    token = login_response.json()['access_token']
    print("Connecté avec succès")
    
    # Récupération des réunions
    headers = {
        'Authorization': f'Bearer {token}'
    }
    meetings_response = requests.get('http://localhost:8001/simple/meetings/', headers=headers)
    
    if meetings_response.status_code != 200:
        print(f"Erreur lors de la récupération des réunions: {meetings_response.status_code} - {meetings_response.text}")
        return
    
    meetings = meetings_response.json()
    print(f"\nNombre total de réunions: {len(meetings)}\n")
    
    # Affichage des réunions
    for i, meeting in enumerate(meetings):
        print(f"{i+1}. ID: {meeting.get('id')}")
        print(f"   Titre: {meeting.get('title')}")
        print(f"   Statut: {meeting.get('transcript_status')}")
        print(f"   ID Transcription: {meeting.get('transcript_id')}")
        print()

if __name__ == "__main__":
    list_meetings()
