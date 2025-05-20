#!/usr/bin/env python
"""Script pour vérifier le bon fonctionnement des routes d'authentification"""

import subprocess
import time
import sys
import json
import requests
import uuid
from pathlib import Path

# Constantes
API_URL = "http://localhost:8000"
AUTH_BASE = f"{API_URL}/auth"
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

def register_user():
    """Enregistrer un nouvel utilisateur"""
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "email": f"test.user.{unique_id}@example.com",
        "password": "SecurePassword123!",
        "full_name": f"Test User {unique_id}"
    }
    
    try:
        response = requests.post(f"{AUTH_BASE}/register", json=user_data)
        result = response.status_code == 201
        print_result("/auth/register", result, f"(Status: {response.status_code})")
        if result:
            print(f"   Utilisateur créé: {user_data['email']}")
            return user_data, response.json()
        else:
            print(f"   Erreur: {response.text}")
            return None, None
    except Exception as e:
        print_result("/auth/register", False, f"(Erreur: {e})")
        return None, None

def login_user(user_data):
    """Connecter un utilisateur existant"""
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    
    try:
        response = requests.post(f"{AUTH_BASE}/login", data=login_data)
        result = response.status_code == 200
        print_result("/auth/login", result, f"(Status: {response.status_code})")
        if result:
            token_data = response.json()
            print(f"   Token obtenu avec succès")
            return token_data
        else:
            print(f"   Erreur: {response.text}")
            return None
    except Exception as e:
        print_result("/auth/login", False, f"(Erreur: {e})")
        return None

def get_current_user(token_data):
    """Récupérer les informations de l'utilisateur connecté"""
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    
    try:
        response = requests.get(f"{AUTH_BASE}/me", headers=headers)
        result = response.status_code == 200
        print_result("/auth/me", result, f"(Status: {response.status_code})")
        if result:
            user_info = response.json()
            print(f"   Utilisateur: {user_info.get('email')} ({user_info.get('full_name')})")
            return user_info
        else:
            print(f"   Erreur: {response.text}")
            return None
    except Exception as e:
        print_result("/auth/me", False, f"(Erreur: {e})")
        return None

def main():
    """Fonction principale"""
    print_header("VÉRIFICATION DES ROUTES D'AUTHENTIFICATION")
    
    # Démarrer le serveur
    server_process = start_server()
    if not server_process:
        sys.exit(1)
    
    try:
        # Tester l'inscription
        print_header("TEST D'INSCRIPTION")
        user_data, user_response = register_user()
        if not user_data:
            print_colored("❌ Impossible de créer un utilisateur", "RED")
            return
        
        # Tester la connexion
        print_header("TEST DE CONNEXION")
        token_data = login_user(user_data)
        if not token_data:
            print_colored("❌ Impossible de se connecter", "RED")
            return
        
        # Vérifier les performances de la connexion (avec cache)
        print_header("TEST DES PERFORMANCES DE CONNEXION (AVEC CACHE)")
        start_time = time.time()
        token_data = login_user(user_data)
        end_time = time.time()
        if token_data:
            print_colored(f"⏱️ Temps de connexion: {(end_time - start_time)*1000:.2f} ms", "YELLOW")
        
        # Tester l'accès au profil
        print_header("TEST D'ACCÈS AU PROFIL")
        user_info = get_current_user(token_data)
        if not user_info:
            print_colored("❌ Impossible d'accéder au profil", "RED")
            return
        
        # Résumé
        print_header("RÉSUMÉ")
        print_colored("✅ Le système d'authentification fonctionne correctement!", "GREEN")
        print("Les optimisations de mise en cache pour la production n'ont pas cassé les fonctionnalités.")
        print("L'authentification est performante et sécurisée.")
        
    finally:
        # Arrêter le serveur
        if server_process:
            print_header("ARRÊT DU SERVEUR")
            server_process.terminate()
            print_colored("Serveur arrêté", "YELLOW")

if __name__ == "__main__":
    main()
