import requests
import json
import time
import os
import uuid
import sys
import argparse
from datetime import datetime
from colorama import init, Fore, Style
from jinja2 import Template

# Initialiser colorama pour les couleurs dans le terminal
init()

# Configuration
BASE_URL = "http://localhost:8001"
TEST_USER = "test@example.com"
TEST_PASSWORD = "password123"
AUDIO_FILE_PATH = "tests/resources/test_audio.mp3"  # Assurez-vous que ce fichier existe

# Gu00e9nu00e9rer un email unique pour les tests d'inscription
TEST_REGISTER_EMAIL = f"test_{uuid.uuid4().hex[:8]}@example.com"

# Cru00e9er les dossiers nu00e9cessaires
log_dir = "test_logs"
report_dir = "test_reports"
os.makedirs(log_dir, exist_ok=True)
os.makedirs(report_dir, exist_ok=True)

# Fichiers de log et de rapport
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = f"{log_dir}/api_test_{timestamp}.log"
report_file = f"{report_dir}/api_test_report_{timestamp}.html"

# Statistiques des tests
test_stats = {
    "total": 0,
    "success": 0,
    "failure": 0,
    "skipped": 0,
    "results": []
}

def log(message, level="INFO"):
    """Ecrire dans le fichier de log et afficher dans la console avec des couleurs"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Formater le message selon le niveau
    if level == "SUCCESS":
        formatted_message = f"{Fore.GREEN}{message}{Style.RESET_ALL}"
    elif level == "ERROR":
        formatted_message = f"{Fore.RED}{message}{Style.RESET_ALL}"
    elif level == "WARNING":
        formatted_message = f"{Fore.YELLOW}{message}{Style.RESET_ALL}"
    elif level == "INFO":
        formatted_message = f"{Fore.CYAN}{message}{Style.RESET_ALL}"
    else:
        formatted_message = message
    
    # Afficher dans la console
    print(formatted_message)
    
    # Enregistrer dans le fichier de log (sans les codes de couleur)
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {level}: {message}\n")

def record_test_result(test_name, success, response_data=None, error=None):
    """Enregistrer le ru00e9sultat d'un test"""
    test_stats["total"] += 1
    
    if success:
        test_stats["success"] += 1
        log(f"u2705 {test_name} ru00e9ussi", "SUCCESS")
    else:
        test_stats["failure"] += 1
        log(f"u274c {test_name} u00e9chouu00e9", "ERROR")
    
    # Enregistrer les du00e9tails du test
    test_stats["results"].append({
        "name": test_name,
        "success": success,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "response_data": response_data,
        "error": error
    })

def generate_report():
    """Gu00e9nu00e9rer un rapport HTML des tests"""
    log("\n===== Gu00c9Nu00c9RATION DU RAPPORT DE TEST =====")
    
    # Template HTML pour le rapport
    template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rapport de Test API - {{ timestamp }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            .summary { margin: 20px 0; padding: 10px; background-color: #f5f5f5; border-radius: 5px; }
            .success { color: green; }
            .failure { color: red; }
            .test-result { margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            .test-result.success { border-left: 5px solid green; }
            .test-result.failure { border-left: 5px solid red; }
            .details { margin-top: 10px; font-family: monospace; white-space: pre-wrap; background-color: #f9f9f9; padding: 10px; border-radius: 3px; max-height: 200px; overflow: auto; }
        </style>
    </head>
    <body>
        <h1>Rapport de Test API - {{ timestamp }}</h1>
        
        <div class="summary">
            <h2>Ru00e9sumu00e9</h2>
            <p>Tests exu00e9cutu00e9s: {{ stats.total }}</p>
            <p class="success">Ru00e9ussis: {{ stats.success }}</p>
            <p class="failure">Echouu00e9s: {{ stats.failure }}</p>
            <p>Ignoru00e9s: {{ stats.skipped }}</p>
            <p>Taux de ru00e9ussite: {{ (stats.success / stats.total * 100) | round(2) }}%</p>
        </div>
        
        <h2>Du00e9tails des Tests</h2>
        {% for result in stats.results %}
        <div class="test-result {{ 'success' if result.success else 'failure' }}">
            <h3>{{ result.name }}</h3>
            <p>Statut: {{ 'Ru00e9ussi' if result.success else 'Echouu00e9' }}</p>
            <p>Heure: {{ result.timestamp }}</p>
            {% if result.response_data %}
            <div class="details">
                <h4>Ru00e9ponse:</h4>
                <pre>{{ result.response_data | tojson(indent=2) }}</pre>
            </div>
            {% endif %}
            {% if result.error %}
            <div class="details">
                <h4>Erreur:</h4>
                <pre>{{ result.error }}</pre>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </body>
    </html>
    """
    
    # Cru00e9er le rapport
    template = Template(template_str)
    report_html = template.render(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        stats=test_stats
    )
    
    # Enregistrer le rapport
    with open(report_file, "w") as f:
        f.write(report_html)
    
    log(f"Rapport gu00e9nu00e9ru00e9: {report_file}", "SUCCESS")
    return report_file

def check_server_availability():
    """Vu00e9rifier que le serveur est disponible avant de commencer les tests"""
    log("\n===== Vu00c9RIFICATION DE LA DISPONIBILITu00c9 DU SERVEUR =====")
    
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            log(f"Serveur disponible sur {BASE_URL}", "SUCCESS")
            return True
        else:
            log(f"Serveur non disponible (code: {response.status_code})", "ERROR")
            return False
    except requests.exceptions.RequestException as e:
        log(f"Erreur de connexion au serveur: {str(e)}", "ERROR")
        return False

def test_with_retry(func, max_retries=3, retry_delay=2):
    """Exu00e9cuter une fonction de test avec retry en cas d'u00e9chec"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                log(f"Tentative {attempt+1}/{max_retries} u00e9chouu00e9e: {str(e)}", "WARNING")
                time.sleep(retry_delay)
            else:
                log(f"Toutes les tentatives ont u00e9chouu00e9: {str(e)}", "ERROR")
                raise

# ===== TESTS D'AUTHENTIFICATION =====

def test_register():
    """Test d'inscription d'un nouvel utilisateur"""
    log("\n===== TEST D'INSCRIPTION D'UN NOUVEL UTILISATEUR =====")
    
    url = f"{BASE_URL}/auth/register"
    data = {
        "email": TEST_REGISTER_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": "Utilisateur Test"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "id" in response_data
        record_test_result("Inscription d'un nouvel utilisateur", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result("Inscription d'un nouvel utilisateur", False, error=str(e))
        return None

def test_login():
    """Test de l'authentification"""
    log("\n===== TEST DE L'AUTHENTIFICATION =====")
    
    url = f"{BASE_URL}/auth/login"
    data = {"username": TEST_USER, "password": TEST_PASSWORD}
    
    try:
        response = requests.post(url, data=data, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "access_token" in response_data
        record_test_result("Authentification", success, response_data)
        return response_data["access_token"] if success else None
    except Exception as e:
        record_test_result("Authentification", False, error=str(e))
        return None

def test_login_json():
    """Test de l'authentification avec JSON"""
    log("\n===== TEST DE L'AUTHENTIFICATION (JSON) =====")
    
    url = f"{BASE_URL}/auth/login/json"
    data = {"username": TEST_USER, "password": TEST_PASSWORD}
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "access_token" in response_data
        record_test_result("Authentification (JSON)", success, response_data)
        return response_data["access_token"] if success else None
    except Exception as e:
        record_test_result("Authentification (JSON)", False, error=str(e))
        return None

def test_me(token):
    """Test de ru00e9cupu00e9ration des informations de l'utilisateur connectu00e9"""
    log("\n===== TEST DE Ru00c9CUPu00c9RATION DES INFORMATIONS DE L'UTILISATEUR =====")
    
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "id" in response_data
        record_test_result("Ru00e9cupu00e9ration des informations de l'utilisateur", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result("Ru00e9cupu00e9ration des informations de l'utilisateur", False, error=str(e))
        return None

# ===== TESTS DE GESTION DES RÉUNIONS =====

def test_get_meetings(token):
    """Test de récupération des réunions"""
    log("\n===== TEST DE RÉCUPÉRATION DES RÉUNIONS (ENDPOINT SIMPLIFIÉ) =====")
    
    url = f"{BASE_URL}/simple/meetings/"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data[:2], indent=2) if len(response_data) > 0 else '[]'}")
        
        success = response.status_code == 200 and isinstance(response_data, list)
        record_test_result("Récupération des réunions (endpoint simplifié)", success, 
                          {"count": len(response_data), "sample": response_data[:2] if len(response_data) > 0 else []})
        return response_data if success else None
    except Exception as e:
        record_test_result("Récupération des réunions (endpoint simplifié)", False, error=str(e))
        return None

# La fonction de création de réunion n'est pas disponible dans l'API simplifiée
# Les réunions sont créées uniquement via l'upload de fichiers audio

def test_get_meeting_by_id(token, meeting_id):
    """Test de récupération d'une réunion par son ID"""
    log(f"\n===== TEST DE RÉCUPÉRATION D'UNE RÉUNION PAR ID ({meeting_id}) (ENDPOINT SIMPLIFIÉ) =====")
    
    url = f"{BASE_URL}/simple/meetings/{meeting_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "id" in response_data
        record_test_result(f"Récupération d'une réunion par ID ({meeting_id}) (endpoint simplifié)", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result(f"Récupération d'une réunion par ID ({meeting_id}) (endpoint simplifié)", False, error=str(e))
        return None

# ===== TESTS DE TRANSCRIPTION =====

def test_upload_audio(token):
    """Test d'upload d'un fichier audio pour transcription"""
    log(f"\n===== TEST D'UPLOAD D'UN FICHIER AUDIO (ENDPOINT SIMPLIFIÉ) =====")
    
    url = f"{BASE_URL}/simple/meetings/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Vérifier que le fichier audio existe
    if not os.path.exists(AUDIO_FILE_PATH):
        log(f"Fichier audio non trouvé: {AUDIO_FILE_PATH}", "ERROR")
        record_test_result("Upload d'un fichier audio (endpoint simplifié)", False, error=f"Fichier non trouvé: {AUDIO_FILE_PATH}")
        return None
    
    try:
        with open(AUDIO_FILE_PATH, "rb") as f:
            files = {"file": (os.path.basename(AUDIO_FILE_PATH), f, "audio/mpeg")}
            # Ajouter un titre optionnel
            data = {"title": f"Test audio {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
            response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
            response_data = response.json()
            
            log(f"Status code: {response.status_code}")
            log(f"Response: {json.dumps(response_data, indent=2)}")
            
            success = response.status_code == 200 and "id" in response_data
            record_test_result("Upload d'un fichier audio (endpoint simplifié)", success, response_data)
            return response_data if success else None
    except Exception as e:
        record_test_result("Upload d'un fichier audio (endpoint simplifié)", False, error=str(e))
        return None

def test_get_transcription_status(token, meeting_id):
    """Test de récupération du statut de la transcription"""
    log(f"\n===== TEST DE RÉCUPÉRATION DU STATUT DE TRANSCRIPTION (Meeting ID: {meeting_id}) =====")
    
    # D'après la documentation, le statut de transcription est inclus dans la réponse de /meetings/{meeting_id}
    url = f"{BASE_URL}/meetings/{meeting_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and "transcript_status" in response_data
        record_test_result("Récupération du statut de transcription", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result("Récupération du statut de transcription", False, error=str(e))
        return None

def test_get_transcript(token, meeting_id):
    """Test de récupération de la transcription complète"""
    log(f"\n===== TEST DE RÉCUPÉRATION DE LA TRANSCRIPTION (Meeting ID: {meeting_id}) =====")
    
    url = f"{BASE_URL}/meetings/{meeting_id}/transcript"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2) if 'transcript_text' not in response_data else '[Transcription trop longue pour être affichée]'}")
        
        success = response.status_code == 200 and "transcript_status" in response_data
        record_test_result("Récupération de la transcription", success, {"status": response_data.get("transcript_status", "unknown")})
        return response_data if success else None
    except Exception as e:
        record_test_result("Récupération de la transcription", False, error=str(e))
        return None

def test_get_summary(token, meeting_id):
    """Test de récupération du résumé de la réunion"""
    log(f"\n===== TEST DE RÉCUPÉRATION DU RÉSUMÉ (Meeting ID: {meeting_id}) =====")
    
    url = f"{BASE_URL}/meetings/{meeting_id}/summary"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Vérifier si la réponse est un JSON valide
        try:
            response_data = response.json()
            log(f"Response: {json.dumps(response_data, indent=2)}")
        except:
            response_data = {"text": response.text[:200] + "..." if len(response.text) > 200 else response.text}
            log(f"Response (non-JSON): {response.text[:200]}...")
        
        log(f"Status code: {response.status_code}")
        
        success = response.status_code == 200
        record_test_result("Récupération du résumé de la réunion", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result("Récupération du résumé de la réunion", False, error=str(e))
        return None

# ===== TESTS DE GÉNÉRATION DE COMPTES RENDUS =====

def test_generate_summary(token, meeting_id):
    """Test de génération du compte rendu d'une réunion avec Mistral"""
    test_name = f"Génération du compte rendu (Meeting ID: {meeting_id})"
    log(f"\n===== TEST DE GÉNÉRATION DU COMPTE RENDU (ID: {meeting_id}) =====")
    
    url = f"{BASE_URL}/meetings/{meeting_id}/generate-summary"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(url, headers=headers)
        response_data = response.json()
        
        log(f"Status code: {response.status_code}")
        log(f"Response: {json.dumps(response_data, indent=2)}")
        
        success = response.status_code == 200 and response_data.get("success", False)
        record_test_result(test_name, success, response_data)
        
        if success:
            log("Génération du compte rendu démarrée avec succès", "SUCCESS")
            return response_data
        else:
            log("Échec du démarrage de la génération du compte rendu", "ERROR")
            return None
    except Exception as e:
        error_msg = f"Erreur lors de la génération du compte rendu: {str(e)}"
        log(error_msg, "ERROR")
        record_test_result(test_name, False, error=error_msg)
        return None

def test_wait_for_summary_completion(token, meeting_id, max_checks=10, interval=5):
    """Attendre que le compte rendu soit généré"""
    test_name = f"Attente de la fin de génération du compte rendu (Meeting ID: {meeting_id})"
    log(f"\n===== ATTENTE DE LA FIN DE GÉNÉRATION DU COMPTE RENDU (ID: {meeting_id}) =====")
    
    url = f"{BASE_URL}/meetings/{meeting_id}/summary"
    headers = {"Authorization": f"Bearer {token}"}
    
    for i in range(max_checks):
        try:
            log(f"Vérification {i+1}/{max_checks}...")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                status = response_data.get("summary_status")
                log(f"Statut actuel: {status}")
                
                if status == "completed":
                    log("Compte rendu généré avec succès", "SUCCESS")
                    record_test_result(test_name, True, response_data)
                    return response_data
                elif status == "error":
                    log("Erreur lors de la génération du compte rendu", "ERROR")
                    record_test_result(test_name, False, response_data)
                    return response_data
            
            if i < max_checks - 1:
                log(f"Attente de {interval} secondes avant la prochaine vérification...")
                time.sleep(interval)
        except Exception as e:
            error_msg = f"Erreur lors de la vérification du statut: {str(e)}"
            log(error_msg, "ERROR")
    
    log("Délai d'attente dépassé pour la génération du compte rendu", "WARNING")
    record_test_result(test_name, False, error="Timeout")
    return None

# ===== TESTS DE SANTÉ =====

def test_health_check():
    """Test de vérification de la santé du serveur"""
    log("\n===== TEST DE VÉRIFICATION DE SANTÉ =====")
    
    url = f"{BASE_URL}/health"
    
    try:
        response = requests.get(url, timeout=10)
        
        try:
            response_data = response.json()
            log(f"Response: {json.dumps(response_data, indent=2)}")
        except:
            response_data = {"text": response.text[:200] + "..." if len(response.text) > 200 else response.text}
            log(f"Response (non-JSON): {response.text[:200]}...")
        
        log(f"Status code: {response.status_code}")
        
        success = response.status_code == 200
        record_test_result("Vérification de santé", success, response_data)
        return response_data if success else None
    except Exception as e:
        record_test_result("Vérification de santé", False, error=str(e))
        return None

# ===== FONCTION PRINCIPALE =====

def run_all_tests():
    """Exécuter tous les tests d'API"""
    log(f"\n{'='*50}")
    log(f"DÉBUT DES TESTS D'API - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*50}\n")
    
    # Vérifier que le serveur est disponible
    if not check_server_availability():
        log("Le serveur n'est pas disponible. Impossible de continuer les tests.", "ERROR")
        return False
    
    # Test de santé
    test_health_check()
    
    # Test d'inscription (optionnel)
    # test_register()
    
    # Test d'authentification
    token = test_with_retry(test_login)
    if not token:
        token = test_with_retry(test_login_json)
    
    if not token:
        log("Échec d'authentification. Impossible de continuer les tests.", "ERROR")
        generate_report()
        return False
    
    # Test de récupération des informations utilisateur
    user_info = test_me(token)
    
    # Test de récupération des réunions (endpoint simplifié)
    meetings = test_get_meetings(token)
    meeting_id = None
    
    # Test d'upload d'un fichier audio (endpoint simplifié)
    if os.path.exists(AUDIO_FILE_PATH):
        upload_result = test_upload_audio(token)
        
        # Récupérer l'ID de la réunion créée par l'upload
        if upload_result and "id" in upload_result:
            meeting_id = upload_result["id"]
            log(f"Utilisation de la réunion créée par l'upload: {meeting_id}", "INFO")
    else:
        log(f"Fichier audio non trouvé: {AUDIO_FILE_PATH}. Skipping audio upload test.", "WARNING")
        test_stats["skipped"] += 1
    
    # Si on n'a pas de réunion, utiliser une existante si disponible
    if not meeting_id and meetings and len(meetings) > 0:
        meeting_id = meetings[0]["id"]
        log(f"Utilisation d'une réunion existante: {meeting_id}", "INFO")
    
    if meeting_id:
        # Test de récupération d'une réunion par ID (endpoint simplifié)
        test_get_meeting_by_id(token, meeting_id)
        
        # Test de récupération du statut de transcription (via l'endpoint de réunion)
        test_get_transcription_status(token, meeting_id)
        
        # Test de récupération de la transcription complète
        test_get_transcript(token, meeting_id)
        
        # Test de récupération du résumé existant (peut échouer si la transcription n'est pas terminée)
        summary_result = test_get_summary(token, meeting_id)
        
        # Test de génération de compte rendu avec Mistral
        if summary_result and summary_result.get("summary_status") != "completed":
            log("Test de génération de compte rendu avec Mistral", "INFO")
            # Vérifier que la transcription est complète avant de générer un compte rendu
            meeting_details = test_get_meeting_by_id(token, meeting_id)
            if meeting_details and meeting_details.get("transcript_status") == "completed":
                # Générer le compte rendu
                generation_result = test_generate_summary(token, meeting_id)
                if generation_result:
                    # Attendre que le compte rendu soit généré
                    summary = test_wait_for_summary_completion(token, meeting_id)
            else:
                log("La transcription n'est pas terminée, impossible de tester la génération du compte rendu", "WARNING")
                test_stats["skipped"] += 2  # generate_summary, wait_for_summary_completion
    else:
        log("Aucune réunion disponible pour les tests. Skipping meeting-specific tests.", "WARNING")
        test_stats["skipped"] += 4  # get_meeting_by_id, transcription_status, transcript, summary
    
    # Générer le rapport
    report_path = generate_report()
    
    # Afficher le résumé
    log(f"\n{'='*50}")
    log(f"RÉSUMÉ DES TESTS:")
    log(f"  Total: {test_stats['total']}")
    log(f"  Réussis: {Fore.GREEN}{test_stats['success']}{Style.RESET_ALL}")
    log(f"  Échoués: {Fore.RED}{test_stats['failure']}{Style.RESET_ALL}")
    log(f"  Ignorés: {Fore.YELLOW}{test_stats['skipped']}{Style.RESET_ALL}")
    log(f"  Taux de réussite: {Fore.CYAN}{(test_stats['success'] / test_stats['total'] * 100) if test_stats['total'] > 0 else 0:.2f}%{Style.RESET_ALL}")
    log(f"{'='*50}\n")
    
    log(f"Rapport détaillé: {report_path}")
    
    return test_stats['failure'] == 0

# Exécuter les tests si le script est exécuté directement
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tester les endpoints de l'API")
    parser.add_argument('--url', type=str, default=BASE_URL, help="URL de base de l'API")
    parser.add_argument('--audio', type=str, default=AUDIO_FILE_PATH, help="Chemin vers le fichier audio de test")
    parser.add_argument('--user', type=str, default=TEST_USER, help="Email de l'utilisateur de test")
    parser.add_argument('--password', type=str, default=TEST_PASSWORD, help="Mot de passe de l'utilisateur de test")
    
    args = parser.parse_args()
    
    # Mettre à jour les variables globales avec les arguments
    BASE_URL = args.url
    AUDIO_FILE_PATH = args.audio
    TEST_USER = args.user
    TEST_PASSWORD = args.password
    
    # Exécuter les tests
    success = run_all_tests()
    
    # Sortir avec un code d'erreur si les tests ont échoué
    sys.exit(0 if success else 1)
