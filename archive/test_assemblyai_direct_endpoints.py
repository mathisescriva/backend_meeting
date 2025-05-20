"""Script de test pour les endpoints directs d'AssemblyAI"""

import requests
import time
import sys
import json
import os
from pathlib import Path

# Configuration
API_URL = "http://localhost:8001"  # Port modifiu00e9 u00e0 8001
TEST_FILE = "test_audio.mp3"  # Fichier audio de test
EMAIL = "test@example.com"
PASSWORD = "password123"

def login():
    """Se connecte u00e0 l'API et retourne le token JWT"""
    print("\n=== Test de connexion (/auth/login) ===")
    response = requests.post(
        f"{API_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD}
    )
    
    if response.status_code != 200:
        print(f"Erreur de connexion: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    token = response.json().get("access_token")
    print(f"Connectu00e9 avec succu00e8s, token: {token[:10]}...")
    return token

def test_direct_assemblyai_upload(token, file_path):
    """Teste l'endpoint /direct-assemblyai/upload"""
    print(f"\n=== Test d'upload direct vers AssemblyAI (/direct-assemblyai/upload) ===")
    print(f"Fichier: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Le fichier {file_path} n'existe pas!")
        return None
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "title": f"Test direct upload {os.path.basename(file_path)}",
            "wait_for_result": "false"
        }
        
        response = requests.post(
            f"{API_URL}/direct-assemblyai/upload",
            files=files,
            data=data,
            headers=headers
        )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Succu00e8s! Upload direct vers AssemblyAI ru00e9ussi")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def test_assemblyai_direct_upload(token, file_path):
    """Teste l'endpoint /assemblyai-direct/upload"""
    print(f"\n=== Test d'upload via le service AssemblyAI (/assemblyai-direct/upload) ===")
    print(f"Fichier: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Le fichier {file_path} n'existe pas!")
        return None
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "title": f"Test service upload {os.path.basename(file_path)}",
            "wait_for_result": "false"
        }
        
        response = requests.post(
            f"{API_URL}/assemblyai-direct/upload",
            files=files,
            data=data,
            headers=headers
        )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Succu00e8s! Upload via le service AssemblyAI ru00e9ussi")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def test_check_transcription_status(token, transcript_id, endpoint_prefix):
    """Teste l'endpoint de vu00e9rification du statut de transcription"""
    print(f"\n=== Test de vu00e9rification du statut de transcription ({endpoint_prefix}/status/{transcript_id}) ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_URL}/{endpoint_prefix}/status/{transcript_id}", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Succu00e8s! Statut de la transcription:")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"Erreur: {response.status_code}")
        print(response.text)
        return None

def main():
    """Fonction principale"""
    # Se connecter
    token = login()
    
    # Utiliser le fichier spu00e9cifiu00e9 ou le fichier par du00e9faut
    file_path = TEST_FILE
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    # Tester l'endpoint /direct-assemblyai/upload
    direct_result = test_direct_assemblyai_upload(token, file_path)
    
    # Tester l'endpoint /assemblyai-direct/upload
    service_result = test_assemblyai_direct_upload(token, file_path)
    
    # Vu00e9rifier les statuts des transcriptions si disponibles
    if direct_result and 'transcript_id' in direct_result:
        # Attendre un peu pour laisser le temps u00e0 AssemblyAI de commencer le traitement
        print("\nAttente de 5 secondes avant de vu00e9rifier le statut...")
        time.sleep(5)
        test_check_transcription_status(token, direct_result['transcript_id'], "direct-assemblyai")
    
    if service_result and 'transcript_id' in service_result:
        # Attendre un peu pour laisser le temps u00e0 AssemblyAI de commencer le traitement
        if not direct_result or 'transcript_id' not in direct_result:
            print("\nAttente de 5 secondes avant de vu00e9rifier le statut...")
            time.sleep(5)
        test_check_transcription_status(token, service_result['transcript_id'], "assemblyai-direct")
    
    print("\nTests terminu00e9s!")

if __name__ == "__main__":
    main()
