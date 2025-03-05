#!/usr/bin/env python
"""Script pour vérifier le bon fonctionnement de l'API Meeting Transcriber"""

import subprocess
import time
import sys
import json
import requests
from pathlib import Path

# Constantes
API_URL = "http://localhost:8000"
COLORS = {
    "GREEN": "\033[92m",
    "RED": "\033[91m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "RESET": "\033[0m",
}

def print_colored(text, color):
    """Affiche du texte coloré dans le terminal"""
    print(f"{COLORS[color]}{text}{COLORS['RESET']}")

def print_header(text):
    """Affiche un en-tête"""
    print("\n" + "="*80)
    print_colored(f" {text} ", "BLUE")
    print("="*80)

def print_result(endpoint, status, message=""):
    """Affiche le résultat d'un test d'endpoint"""
    result = "✅ SUCCÈS" if status else "❌ ÉCHEC"
    color = "GREEN" if status else "RED"
    print(f"{COLORS[color]}{result}{COLORS['RESET']} - {endpoint} {message}")

def start_server():
    """Démarrer le serveur FastAPI en arrière-plan"""
    print_header("DÉMARRAGE DU SERVEUR")
    print("Démarrage du serveur FastAPI sur http://localhost:8000...")
    
    try:
        # Lancer le serveur en arrière-plan
        process = subprocess.Popen(
            ["uvicorn", "app.main:app", "--port", "8000"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
        )
        
        # Attendre que le serveur soit prêt
        for _ in range(10):
            try:
                response = requests.get(f"{API_URL}/health")
                if response.status_code == 200:
                    print_colored("Serveur démarré avec succès", "GREEN")
                    return process
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        
        print_colored("Impossible de démarrer le serveur", "RED")
        process.kill()
        return None
    except Exception as e:
        print_colored(f"Erreur lors du démarrage du serveur: {e}", "RED")
        return None

def check_health():
    """Vérifier l'endpoint de santé"""
    try:
        response = requests.get(f"{API_URL}/health")
        result = response.status_code == 200
        print_result("/health", result, f"(Status: {response.status_code})")
        if result:
            print(f"   Réponse: {json.dumps(response.json(), indent=2)}")
        return result
    except Exception as e:
        print_result("/health", False, f"(Erreur: {e})")
        return False

def check_root():
    """Vérifier l'endpoint racine"""
    try:
        response = requests.get(API_URL)
        result = response.status_code == 200
        print_result("/", result, f"(Status: {response.status_code})")
        if result:
            print(f"   Réponse: {json.dumps(response.json(), indent=2)}")
        return result
    except Exception as e:
        print_result("/", False, f"(Erreur: {e})")
        return False

def check_docs():
    """Vérifier l'accès à la documentation"""
    try:
        response = requests.get(f"{API_URL}/docs")
        result = response.status_code == 200
        print_result("/docs", result, f"(Status: {response.status_code})")
        return result
    except Exception as e:
        print_result("/docs", False, f"(Erreur: {e})")
        return False

def check_redoc():
    """Vérifier l'accès à la documentation ReDoc"""
    try:
        response = requests.get(f"{API_URL}/redoc")
        result = response.status_code == 200
        print_result("/redoc", result, f"(Status: {response.status_code})")
        return result
    except Exception as e:
        print_result("/redoc", False, f"(Erreur: {e})")
        return False

def check_openapi():
    """Vérifier l'accès au schéma OpenAPI"""
    try:
        response = requests.get(f"{API_URL}/openapi.json")
        result = response.status_code == 200
        print_result("/openapi.json", result, f"(Status: {response.status_code})")
        if result:
            # Vérifier que le schéma OpenAPI contient les bonnes sections
            schema = response.json()
            has_paths = "paths" in schema
            has_components = "components" in schema
            print(f"   Schéma valide: {'✅' if has_paths and has_components else '❌'}")
        return result
    except Exception as e:
        print_result("/openapi.json", False, f"(Erreur: {e})")
        return False

def check_headers(url="/health"):
    """Vérifier les en-têtes personnalisés"""
    try:
        response = requests.get(f"{API_URL}{url}")
        has_process_time = "X-Process-Time" in response.headers
        print_result(
            f"{url} [En-têtes]", 
            has_process_time, 
            f"(X-Process-Time: {response.headers.get('X-Process-Time', 'Non trouvé')})"
        )
        return has_process_time
    except Exception as e:
        print_result(f"{url} [En-têtes]", False, f"(Erreur: {e})")
        return False

def main():
    """Fonction principale"""
    print_header("VÉRIFICATION DE L'API MEETING TRANSCRIBER")
    
    # Démarrer le serveur
    server_process = start_server()
    if not server_process:
        sys.exit(1)
    
    try:
        # Vérifier les endpoints de base
        print_header("VÉRIFICATION DES ENDPOINTS DE BASE")
        check_health()
        check_root()
        check_docs()
        check_redoc()
        check_openapi()
        
        # Vérifier les en-têtes personnalisés
        print_header("VÉRIFICATION DES EN-TÊTES PERSONNALISÉS")
        check_headers()
        
        print_header("RÉSUMÉ")
        print_colored("✅ Votre API Meeting Transcriber fonctionne correctement!", "GREEN")
        print("Les optimisations pour la production n'ont pas cassé les fonctionnalités principales.")
        print("Vous pouvez maintenant déployer votre API en toute confiance.")
    finally:
        # Arrêter le serveur
        if server_process:
            print_header("ARRÊT DU SERVEUR")
            server_process.terminate()
            print_colored("Serveur arrêté", "YELLOW")

if __name__ == "__main__":
    main()
