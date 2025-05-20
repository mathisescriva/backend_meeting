import requests
import json

# URL de l'API du00e9ployu00e9e sur Render
API_URL = "https://backend-meeting.onrender.com"

# Identifiants de test
TEST_CREDENTIALS = [
    {"email": "testing.admin@gilbert.fr", "password": "Gilbert2025!"},
    {"email": "nicolas@gilbert.fr", "password": "Gilbert2025!"}
]

def check_user_exists(email, password):
    """Vu00e9rifie si un utilisateur existe en essayant de se connecter"""
    try:
        # Appel u00e0 l'API de connexion
        response = requests.post(
            f"{API_URL}/auth/login",
            data={
                "username": email,
                "password": password
            }
        )
        
        # Vu00e9rifier la ru00e9ponse
        if response.status_code == 200:
            print(f"u2705 L'utilisateur {email} existe et peut se connecter")
            token_data = response.json()
            print(f"   u2022 Token valide pour: {token_data.get('expires_in', 'N/A')} secondes")
            return True
        else:
            print(f"u274c L'utilisateur {email} n'existe pas ou le mot de passe est incorrect")
            print(f"   u2022 Statut: {response.status_code}")
            print(f"   u2022 Du00e9tail: {response.text}")
            return False
    except Exception as e:
        print(f"u274c Erreur lors de la vu00e9rification de {email}: {str(e)}")
        return False

def check_user_info(email, password):
    """Ru00e9cupu00e8re les informations de l'utilisateur apru00e8s connexion"""
    try:
        # Se connecter pour obtenir un token
        login_response = requests.post(
            f"{API_URL}/auth/login",
            data={
                "username": email,
                "password": password
            }
        )
        
        if login_response.status_code != 200:
            return None
            
        token_data = login_response.json()
        token = token_data.get("access_token")
        
        # Ru00e9cupu00e9rer les informations de l'utilisateur
        user_response = requests.get(
            f"{API_URL}/auth/me",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )
        
        if user_response.status_code == 200:
            return user_response.json()
        else:
            return None
    except Exception as e:
        print(f"u274c Erreur lors de la ru00e9cupu00e9ration des infos pour {email}: {str(e)}")
        return None

def main():
    print("ud83dudd0e Vu00e9rification des utilisateurs dans la base de donnu00e9es Render...\n")
    
    for creds in TEST_CREDENTIALS:
        email = creds["email"]
        password = creds["password"]
        
        print(f"\nud83dudc64 Vu00e9rification de l'utilisateur: {email}")
        exists = check_user_exists(email, password)
        
        if exists:
            user_info = check_user_info(email, password)
            if user_info:
                print("   u2022 Informations utilisateur:")
                print(f"     - ID: {user_info.get('id', 'N/A')}")
                print(f"     - Nom complet: {user_info.get('full_name', 'N/A')}")
                print(f"     - Date de cru00e9ation: {user_info.get('created_at', 'N/A')}")

if __name__ == "__main__":
    main()
