import requests
import json

# URL de l'API locale
API_URL = "http://localhost:8001"

# Données de l'utilisateur à créer
user_data = {
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User"
}

def create_user():
    """Crée un nouvel utilisateur via l'API d'enregistrement"""
    try:
        # Appel à l'API d'enregistrement
        response = requests.post(
            f"{API_URL}/auth/register",
            json=user_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Vérifier la réponse
        if response.status_code == 201:
            print("✅ Utilisateur créé avec succès!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Erreur lors de la création de l'utilisateur: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Création d'un nouvel utilisateur local...")
    create_user()
