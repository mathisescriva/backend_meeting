import requests
import json

# Configuration
BASE_URL = "http://localhost:8001"
TEST_USER = "test@example.com"
TEST_PASSWORD = "password123"

def test_login():
    """Test de l'authentification"""
    print("\n===== TEST DE L'AUTHENTIFICATION =====")
    
    url = f"{BASE_URL}/auth/login"
    data = {"username": TEST_USER, "password": TEST_PASSWORD}
    
    try:
        print(f"Envoi de la requu00eate u00e0 {url}")
        print(f"Donnu00e9es: {data}")
        
        response = requests.post(url, data=data)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Ru00e9ponse: {json.dumps(response_data, indent=2)}")
            
            if "access_token" in response_data:
                print("\nu2705 Authentification ru00e9ussie")
                return response_data["access_token"]
            else:
                print("\nu274c Pas de token dans la ru00e9ponse")
                return None
        else:
            print(f"\nu274c u00c9chec de l'authentification (code {response.status_code})")
            try:
                error_data = response.json()
                print(f"Du00e9tails de l'erreur: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Contenu de la ru00e9ponse: {response.text}")
            return None
    except Exception as e:
        print(f"\nu274c Erreur lors de l'authentification: {str(e)}")
        return None

if __name__ == "__main__":
    token = test_login()
    if token:
        print(f"\nToken obtenu: {token[:20]}...")
    else:
        print("\nImpossible d'obtenir un token d'authentification")
