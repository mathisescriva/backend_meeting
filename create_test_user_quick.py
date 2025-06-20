#!/usr/bin/env python3

import requests
import json

# Configuration
BASE_URL = "http://localhost:8001"
TEST_USER = {
    "email": "test.rename@example.com",
    "password": "password123",
    "full_name": "Test Rename User"
}

def create_user():
    """Crée un utilisateur de test"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json=TEST_USER,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            print("✅ Utilisateur créé avec succès!")
            return True
        else:
            print(f"❌ Erreur création: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def test_login():
    """Teste la connexion"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={
                "username": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        
        if response.status_code == 200:
            print("✅ Connexion réussie!")
            token = response.json()["access_token"]
            print(f"Token: {token[:20]}...")
            return token
        else:
            print(f"❌ Erreur connexion: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

if __name__ == "__main__":
    print("Création d'un utilisateur de test...")
    if create_user():
        print("\nTest de connexion...")
        test_login() 