#!/usr/bin/env python3
"""
Script de test pour l'implémentation Google OAuth.

Ce script teste le nouveau flux OAuth complet côté backend.
"""

import requests
import sys
import os
from urllib.parse import urlparse, parse_qs

# Configuration
API_BASE_URL = "http://localhost:8001"
EXPECTED_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

def test_google_oauth_redirect():
    """Test la redirection vers Google OAuth"""
    print("🧪 Test 1: Redirection vers Google OAuth")
    
    try:
        # Faire une requête vers l'endpoint OAuth sans suivre les redirections
        response = requests.get(f"{API_BASE_URL}/auth/google", allow_redirects=False)
        
        # Vérifier le code de statut de redirection
        if response.status_code != 302:
            print(f"❌ Erreur: Code de statut attendu 302, reçu {response.status_code}")
            return False
        
        # Vérifier la présence de l'en-tête Location
        if 'Location' not in response.headers:
            print("❌ Erreur: En-tête Location manquant")
            return False
        
        location = response.headers['Location']
        parsed_url = urlparse(location)
        
        # Vérifier que l'URL de redirection est vers Google
        if not location.startswith(EXPECTED_GOOGLE_AUTH_URL):
            print(f"❌ Erreur: URL de redirection incorrecte: {location}")
            return False
        
        # Vérifier les paramètres OAuth
        query_params = parse_qs(parsed_url.query)
        
        required_params = ['client_id', 'redirect_uri', 'scope', 'response_type', 'state']
        for param in required_params:
            if param not in query_params:
                print(f"❌ Erreur: Paramètre manquant: {param}")
                return False
        
        # Vérifier les valeurs des paramètres
        if query_params.get('response_type', [''])[0] != 'code':
            print("❌ Erreur: response_type doit être 'code'")
            return False
        
        if query_params.get('scope', [''])[0] != 'openid email profile':
            print("❌ Erreur: scope incorrect")
            return False
        
        # Vérifier que l'état n'est pas vide
        state = query_params.get('state', [''])[0]
        if not state or len(state) < 10:
            print("❌ Erreur: État OAuth invalide ou trop court")
            return False
        
        print("✅ Test 1 réussi: Redirection vers Google OAuth correcte")
        print(f"   • URL: {location[:100]}...")
        print(f"   • État: {state[:10]}...")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

def test_oauth_state_manager():
    """Test le gestionnaire d'états OAuth"""
    print("\n🧪 Test 2: Gestionnaire d'états OAuth")
    
    try:
        # Importer le gestionnaire d'états
        sys.path.append('.')
        from app.services.oauth_state_manager import oauth_state_manager
        
        # Test de génération d'état
        state1 = oauth_state_manager.generate_state()
        state2 = oauth_state_manager.generate_state()
        
        if not state1 or not state2:
            print("❌ Erreur: Impossible de générer des états")
            return False
        
        if state1 == state2:
            print("❌ Erreur: Les états ne doivent pas être identiques")
            return False
        
        if len(state1) < 32:
            print("❌ Erreur: État trop court (sécurité insuffisante)")
            return False
        
        # Test de validation d'état
        if not oauth_state_manager.validate_state(state1):
            print("❌ Erreur: État valide rejeté")
            return False
        
        # Test d'usage unique
        if oauth_state_manager.validate_state(state1):
            print("❌ Erreur: État utilisé deux fois (doit être à usage unique)")
            return False
        
        # Test d'état invalide
        if oauth_state_manager.validate_state("invalid_state"):
            print("❌ Erreur: État invalide accepté")
            return False
        
        print("✅ Test 2 réussi: Gestionnaire d'états OAuth fonctionne")
        print(f"   • États générés: {len(state1)} caractères")
        print(f"   • Usage unique: ✓")
        print(f"   • Validation: ✓")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_callback_error_handling():
    """Test la gestion d'erreurs du callback"""
    print("\n🧪 Test 3: Gestion d'erreurs du callback")
    
    try:
        # Test callback sans paramètres
        response = requests.get(f"{API_BASE_URL}/auth/google/callback", allow_redirects=False)
        
        if response.status_code != 302:
            print(f"❌ Erreur: Code de statut attendu 302, reçu {response.status_code}")
            return False
        
        location = response.headers.get('Location', '')
        if 'error=missing_params' not in location:
            print(f"❌ Erreur: Gestion d'erreur manquante dans: {location}")
            return False
        
        # Test callback avec état invalide
        response = requests.get(
            f"{API_BASE_URL}/auth/google/callback?code=test&state=invalid",
            allow_redirects=False
        )
        
        location = response.headers.get('Location', '')
        if 'error=invalid_state' not in location:
            print(f"❌ Erreur: État invalide non détecté dans: {location}")
            return False
        
        print("✅ Test 3 réussi: Gestion d'erreurs du callback")
        print(f"   • Paramètres manquants: ✓")
        print(f"   • État invalide: ✓")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

def test_configuration():
    """Test la configuration OAuth"""
    print("\n🧪 Test 4: Configuration OAuth")
    
    try:
        sys.path.append('.')
        from app.core.config import settings
        
        # Vérifier que les variables de configuration existent
        required_vars = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI', 'FRONTEND_URL']
        
        for var in required_vars:
            if not hasattr(settings, var):
                print(f"❌ Erreur: Variable de configuration manquante: {var}")
                return False
        
        # Vérifier l'URI de redirection
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        if not redirect_uri.endswith('/auth/google/callback'):
            print(f"❌ Erreur: URI de redirection incorrecte: {redirect_uri}")
            return False
        
        print("✅ Test 4 réussi: Configuration OAuth")
        print(f"   • Variables configurées: {len(required_vars)}")
        print(f"   • URI de redirection: {redirect_uri}")
        print(f"   • URL frontend: {settings.FRONTEND_URL}")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    """Fonction principale du script de test"""
    print("🔧 Test de l'implémentation Google OAuth")
    print("=" * 50)
    
    # Vérifier que le serveur est en marche
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        print(f"✅ Serveur accessible sur {API_BASE_URL}")
    except requests.exceptions.RequestException:
        print(f"❌ Serveur inaccessible sur {API_BASE_URL}")
        print("   Démarrez le serveur avec: uvicorn app.main:app --reload --port 8001")
        return False
    
    # Exécuter les tests
    tests = [
        test_configuration,
        test_oauth_state_manager,
        test_google_oauth_redirect,
        test_callback_error_handling,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Résultats: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés!")
        print("\n📋 Prochaines étapes:")
        print("1. Configurer vos variables d'environnement Google OAuth")
        print("2. Tester avec un vrai compte Google")
        print("3. Mettre à jour votre frontend pour utiliser /auth/google")
        return True
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez la configuration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 