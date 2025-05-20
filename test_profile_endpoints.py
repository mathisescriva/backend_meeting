import requests
import os
import json
import base64
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001"
LOG_FILE = f"test_logs/profile_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
TEST_IMAGE_PATH = "/Users/mathisescriva/CascadeProjects/MeetingTranscriberBackend/static/default-profile.png"  # Image par défaut pour tester l'upload

# Créer le dossier de logs s'il n'existe pas
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Statistiques des tests
test_stats = {
    "total": 0,
    "success": 0,
    "failure": 0,
    "skipped": 0
}

def log(message, level="INFO"):
    """Écrire un message dans le fichier de log et l'afficher dans la console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{level}] {message}"
    print(formatted_message)
    
    with open(LOG_FILE, "a") as f:
        f.write(formatted_message + "\n")

def record_test_result(test_name, success, details=None, error=None):
    """Enregistrer le résultat d'un test"""
    test_stats["total"] += 1
    
    if success:
        test_stats["success"] += 1
        log(f"\u2705 {test_name} réussi")
    else:
        test_stats["failure"] += 1
        log(f"\u274c {test_name} échoué" + (f": {error}" if error else ""), "ERROR")
    
    return success

def login():
    """Se connecter à l'API et récupérer un token"""
    log("\n===== AUTHENTIFICATION =====")
    
    url = f"{BASE_URL}/auth/login/json"
    data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "access_token" in response_data
        record_test_result("Authentification", success, response_data)
        return response_data["access_token"] if success else None
    except Exception as e:
        record_test_result("Authentification", False, error=str(e))
        return None

def test_get_profile(token):
    """Test de récupération du profil utilisateur"""
    log("\n===== TEST DE RÉCUPÉRATION DU PROFIL =====")
    
    url = f"{BASE_URL}/profile/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "id" in response_data
        record_test_result("Récupération du profil", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result("Récupération du profil", False, error=str(e))
        return None

def test_update_profile(token, profile_data):
    """Test de mise à jour du profil utilisateur"""
    log("\n===== TEST DE MISE À JOUR DU PROFIL =====")
    log(f"Données à mettre à jour: {json.dumps(profile_data, indent=2)}")
    
    url = f"{BASE_URL}/profile/update"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.put(url, json=profile_data, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "id" in response_data
        record_test_result("Mise à jour du profil", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result("Mise à jour du profil", False, error=str(e))
        return None

def test_upload_profile_picture(token):
    """Test d'upload d'une photo de profil"""
    log("\n===== TEST D'UPLOAD DE PHOTO DE PROFIL =====")
    
    if not os.path.exists(TEST_IMAGE_PATH):
        log(f"Image de test non trouvée: {TEST_IMAGE_PATH}", "WARNING")
        test_stats["skipped"] += 1
        return None
    
    url = f"{BASE_URL}/profile/upload-picture"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with open(TEST_IMAGE_PATH, "rb") as f:
            files = {"file": (os.path.basename(TEST_IMAGE_PATH), f, "image/png")}
            response = requests.post(url, files=files, headers=headers, timeout=10)
        
        response_data = response.json()
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "profile_picture_url" in response_data
        record_test_result("Upload de photo de profil", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result("Upload de photo de profil", False, error=str(e))
        return None

def test_update_email(token, new_email):
    """Test de mise à jour de l'email"""
    log("\n===== TEST DE MISE À JOUR DE L'EMAIL =====")
    log(f"Nouvel email: {new_email}")
    
    url = f"{BASE_URL}/profile/update"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {"email": new_email}
    
    try:
        response = requests.put(url, json=data, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "email" in response_data and response_data["email"] == new_email
        record_test_result("Mise à jour de l'email", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result("Mise à jour de l'email", False, error=str(e))
        return None

def test_update_password(token, current_password, new_password):
    """Test de mise à jour du mot de passe"""
    log("\n===== TEST DE MISE À JOUR DU MOT DE PASSE =====")
    
    url = f"{BASE_URL}/profile/change-password"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "current_password": current_password,
        "new_password": new_password
    }
    
    try:
        response = requests.put(url, json=data, headers=headers, timeout=10)
        
        log(f"Status code: {response.status_code}")
        
        try:
            response_data = response.json()
            log(f"Response: {json.dumps(response_data, indent=2)}")
        except:
            response_data = {"message": response.text}
            log(f"Response (text): {response.text}")
        
        success = response.status_code == 200
        record_test_result("Mise à jour du mot de passe", success, response_data)
        return success
    except Exception as e:
        record_test_result("Mise à jour du mot de passe", False, error=str(e))
        return False

def generate_report():
    """Générer un rapport HTML des résultats des tests"""
    log("\n===== GÉNÉRATION DU RAPPORT DE TEST =====")
    
    report_dir = "test_reports"
    os.makedirs(report_dir, exist_ok=True)
    
    report_file = f"{report_dir}/profile_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    with open(report_file, "w") as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rapport de test des endpoints de profil</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                .skipped {{ color: orange; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>Rapport de test des endpoints de profil</h1>
            <div class="summary">
                <h2>Résumé</h2>
                <p>Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Total des tests: {test_stats['total']}</p>
                <p class="success">Réussis: {test_stats['success']}</p>
                <p class="failure">Échoués: {test_stats['failure']}</p>
                <p class="skipped">Ignorés: {test_stats['skipped']}</p>
                <p>Taux de réussite: {(test_stats['success'] / test_stats['total'] * 100) if test_stats['total'] > 0 else 0:.2f}%</p>
            </div>
            <h2>Détails des logs</h2>
            <pre>{open(LOG_FILE, 'r').read()}</pre>
        </body>
        </html>
        """)
    
    log(f"Rapport généré: {report_file}")
    return report_file

def main():
    # Démarrer le test
    log(f"\n{'='*50}")
    log(f"DÉBUT DES TESTS DES ENDPOINTS DE PROFIL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*50}\n")
    
    # Se connecter
    token = login()
    if not token:
        log("Impossible de continuer sans token d'authentification", "ERROR")
        generate_report()
        return False
    
    # Récupérer le profil initial
    initial_profile = test_get_profile(token)
    if not initial_profile:
        log("Impossible de récupérer le profil initial", "ERROR")
        generate_report()
        return False
    
    # Mettre à jour le profil
    updated_profile = test_update_profile(token, {
        "full_name": f"Test User Updated {datetime.now().strftime('%H:%M:%S')}",
        "settings": {
            "theme": "dark",
            "language": "fr"
        }
    })
    
    # Uploader une photo de profil
    profile_with_picture = test_upload_profile_picture(token)
    
    # Mettre à jour l'email (avec un timestamp pour éviter les conflits)
    # Note: Nous utilisons le même email de base pour pouvoir nous reconnecter plus tard
    original_email = initial_profile["email"]
    email_parts = original_email.split("@")
    new_email = f"{email_parts[0]}+{datetime.now().strftime('%H%M%S')}@{email_parts[1]}"
    
    updated_email = test_update_email(token, new_email)
    
    # Remettre l'email original pour éviter les problèmes de connexion futurs
    if updated_email:
        test_update_email(token, original_email)
    
    # Tester la mise à jour du mot de passe
    # Note: Nous ne changeons pas réellement le mot de passe pour éviter les problèmes de connexion futurs
    # test_update_password(token, "password123", "newpassword123")
    # Si nous avions changé le mot de passe, il faudrait le remettre à sa valeur d'origine
    # test_update_password(token, "newpassword123", "password123")
    
    # Vérifier que le profil a bien été mis à jour
    final_profile = test_get_profile(token)
    
    # Générer le rapport
    report_path = generate_report()
    
    # Afficher le résumé
    log(f"\n{'='*50}")
    log(f"RÉSUMÉ DES TESTS:")
    log(f"  Total: {test_stats['total']}")
    log(f"  Réussis: {test_stats['success']}")
    log(f"  Échoués: {test_stats['failure']}")
    log(f"  Ignorés: {test_stats['skipped']}")
    log(f"  Taux de réussite: {(test_stats['success'] / test_stats['total'] * 100) if test_stats['total'] > 0 else 0:.2f}%")
    log(f"{'='*50}\n")
    
    log(f"Rapport détaillé: {report_path}")
    
    return test_stats['failure'] == 0

if __name__ == "__main__":
    main()
