import requests
import json

# URL de l'API déployée sur Render
API_URL = "https://backend-meeting.onrender.com"

# Données de l'utilisateur à créer
user_data = {
    "email": "nicolas@gilbert.fr",
    "password": "Gilbert2025!",
    "full_name": "Nicolas Gilbert"
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

def test_login():
    """Teste la connexion avec les identifiants créés"""
    try:
        # Appel à l'API de connexion
        response = requests.post(
            f"{API_URL}/auth/login",
            data={
                "username": user_data["email"],
                "password": user_data["password"]
            }
        )
        
        # Vérifier la réponse
        if response.status_code == 200:
            print("✅ Connexion réussie!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Erreur lors de la connexion: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Création d'un nouvel utilisateur sur Render...")
    if create_user():
        print("\n🔑 Test de connexion avec les identifiants créés...")
        test_login()
