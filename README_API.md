# Documentation API MeetingTranscriberBackend

> **Note importante** : Cette API propose des endpoints simplifiés (`/simple/meetings/...`) pour la gestion des réunions. Ces endpoints sont utilisés par le frontend actuel et sont recommandés pour toute nouvelle intégration.

Ce document fournit une documentation complète des endpoints de l'API MeetingTranscriberBackend, expliquant comment les utiliser, les paramètres requis et les réponses attendues, ainsi que l'intégration avec AssemblyAI pour la transcription audio.

## Table des matières

1. [Configuration et démarrage](#configuration-et-démarrage)
2. [Intégration AssemblyAI](#intégration-assemblyai)
3. [Authentification](#authentification)
4. [Gestion des réunions - Endpoints simplifiés](#gestion-des-réunions---endpoints-simplifiés)
5. [Gestion du profil utilisateur](#gestion-du-profil-utilisateur)
6. [Exemples d'utilisation](#exemples-dutilisation)
7. [Codes d'erreur](#codes-derreur)

## Configuration et démarrage

### Prérequis

- Python 3.8 ou supérieur
- Base de données SQLite (incluse)
- Clé API AssemblyAI (à configurer dans le fichier .env)

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-nom/MeetingTranscriberBackend.git
cd MeetingTranscriberBackend

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer le fichier .env pour ajouter votre clé API AssemblyAI
```

### Démarrage du serveur

```bash
uvicorn app.main:app --reload --port 8001
```

L'API sera accessible à l'adresse : http://localhost:8001

## Intégration AssemblyAI

### Architecture de l'intégration

L'intégration avec AssemblyAI se fait en plusieurs étapes :

1. **Upload du fichier audio** : Le fichier audio est d'abord uploadé vers les serveurs d'AssemblyAI
2. **Démarrage de la transcription** : Une fois le fichier uploadé, une demande de transcription est lancée
3. **Vérification automatique du statut** : Le système vérifie automatiquement le statut de la transcription
4. **Récupération des résultats** : Une fois la transcription terminée, les résultats sont récupérés et stockés dans la base de données

### Optimisations et améliorations récentes

1. **Vérification automatique des transcriptions** : Le système vérifie automatiquement le statut des transcriptions en cours et met à jour la base de données sans intervention manuelle.

2. **Vérification périodique via thread dédié** : Lors de l'upload d'un fichier audio, un thread dédié est lancé pour vérifier périodiquement le statut de la transcription auprès d'AssemblyAI (toutes les 30 secondes pendant 10 minutes).

3. **Vérification lors des requêtes API** : Chaque fois qu'un utilisateur consulte une réunion ou la liste des réunions, le système vérifie automatiquement le statut des transcriptions en cours.

4. **Relance automatique désactivée** : Pour éviter les coûts inutiles, la relance automatique des transcriptions a été désactivée.

5. **Détection des transcriptions bloquées** : Le système détecte les transcriptions bloquées en état "processing" pendant trop longtemps et les marque comme en erreur.

6. **Gestion améliorée des erreurs** : Meilleure gestion des erreurs lors de l'upload des fichiers et du démarrage des transcriptions.

### Fichiers principaux

#### `app/services/assemblyai.py`

Contient les fonctions principales pour interagir avec l'API AssemblyAI :

- `upload_file(file_path)` : Upload un fichier audio vers AssemblyAI
- `start_transcription(audio_url)` : Démarre une transcription pour un fichier audio déjà uploadé
- `transcribe_meeting(meeting_id, file_url, user_id)` : Processus complet de transcription d'une réunion
- `check_transcription_status(transcript_id)` : Vérifie le statut d'une transcription en cours
- `get_transcript_status(transcript_id)` : Récupère le statut et les données d'une transcription
- `process_pending_transcriptions()` : Vérifie les transcriptions en attente ou en cours

#### `app/services/transcription_checker.py`

Contient les fonctions pour vérifier et mettre à jour automatiquement le statut des transcriptions :

- `check_and_update_transcription(meeting)` : Vérifie le statut d'une transcription et met à jour la base de données
- `format_transcript_text(transcript_data)` : Formate le texte de la transcription avec les locuteurs

### Scripts utilitaires

#### `update_db_transcription_status.py`

Script pour mettre à jour manuellement les statuts des transcriptions dans la base de données en vérifiant directement auprès d'AssemblyAI.

```bash
python update_db_transcription_status.py
```

#### `scheduled_transcription_checker.py`

Script à exécuter périodiquement (via cron ou un autre planificateur) pour vérifier et mettre à jour les statuts des transcriptions.

```bash
python scheduled_transcription_checker.py
```

Configuration cron recommandée (vérification toutes les 15 minutes) :
```
*/15 * * * * cd /chemin/vers/MeetingTranscriberBackend && python scheduled_transcription_checker.py >> logs/transcription_checker.log 2>&1
```

### Configuration de la clé API AssemblyAI

La clé API AssemblyAI doit être configurée dans le fichier `.env` :

```
ASSEMBLYAI_API_KEY=votre_clé_api_ici
```

Vous pouvez obtenir une clé API sur [le site d'AssemblyAI](https://www.assemblyai.com/).

## Authentification

L'API utilise l'authentification par token JWT. Vous devez d'abord vous connecter pour obtenir un token, puis inclure ce token dans l'en-tête `Authorization` de vos requêtes.

### Inscription d'un nouvel utilisateur

```
POST /auth/register
```

**Corps de la requête :**
```json
{
  "email": "utilisateur@example.com",
  "password": "motdepasse123",
  "full_name": "Nom Complet"
}
```

**Réponse :**
```json
{
  "id": "99dfd97f-a65a-4881-b917-318254285727",
  "email": "utilisateur@example.com",
  "full_name": "Nom Complet",
  "created_at": "2025-05-19T16:05:57.744623"
}
```

### Connexion (JSON)

```
POST /auth/login/json
```

**Corps de la requête :**
```json
{
  "username": "utilisateur@example.com",
  "password": "motdepasse123"
}
```

**Réponse :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 31536000
}
```

### Connexion (Formulaire)

```
POST /auth/login
```

**Corps de la requête (form-data) :**
- `username`: utilisateur@example.com
- `password`: motdepasse123

**Réponse :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 31536000
}
```

### Informations de l'utilisateur connecté

```
GET /auth/me
```

**En-têtes :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Réponse :**
```json
{
  "id": "99dfd97f-a65a-4881-b917-318254285727",
  "email": "utilisateur@example.com",
  "full_name": "Nom Complet",
  "created_at": "2025-05-19T16:05:57.744623",
  "profile_picture_url": null
}
```

## Gestion des réunions - Endpoints simplifiés

Les endpoints simplifiés offrent une interface plus simple pour interagir avec l'API, avec des vérifications automatiques des statuts de transcription. **Ces endpoints sont recommandés pour toute nouvelle intégration et sont utilisés par le frontend actuel.**

### Récupérer toutes les réunions (simplifié)

```
GET /simple/meetings/
```

**En-têtes :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Paramètres de requête (optionnels) :**
- `status`: Filtre les réunions par statut ("pending", "processing", "completed", "error")

**Réponse :**
```json
[
  {
    "id": "8bddab9d-5942-4b70-8921-9e391f165a45",
    "user_id": "99dfd97f-a65a-4881-b917-318254285727",
    "title": "Audio7min.mp3",
    "file_url": "/uploads/99dfd97f-a65a-4881-b917-318254285727/20250519_175603_tmpcvha545m.wav",
    "transcript_text": "Speaker A: Texte de la transcription...",
    "transcript_status": "completed",
    "created_at": "2025-05-19T15:56:03.367408",
    "duration_seconds": 431,
    "speakers_count": 3,
    "transcription_status": "completed"
  }
]
```

### Récupérer une réunion spécifique (simplifié)

```
GET /simple/meetings/{meeting_id}
```

**En-têtes :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Paramètres de chemin :**
- `meeting_id`: Identifiant unique de la réunion

**Réponse :**
```json
{
  "id": "8bddab9d-5942-4b70-8921-9e391f165a45",
  "user_id": "99dfd97f-a65a-4881-b917-318254285727",
  "title": "Audio7min.mp3",
  "file_url": "/uploads/99dfd97f-a65a-4881-b917-318254285727/20250519_175603_tmpcvha545m.wav",
  "transcript_text": "Speaker A: Texte de la transcription...",
  "transcript_status": "completed",
  "created_at": "2025-05-19T15:56:03.367408",
  "duration_seconds": 431,
  "speakers_count": 3,
  "summary_text": "Erreur lors de la génération du compte rendu",
  "summary_status": "error",
  "transcript_id": "9062ce77-0c69-464a-8212-4cffd42e8e8c",
  "transcription_status": "completed",
  "status": "success",
  "success": true,
  "deleted": false
}
```

### Uploader un fichier audio (simplifié)

```
POST /simple/meetings/upload
```

**En-têtes :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data
```

**Corps de la requête (form-data) :**
- `file`: Fichier audio à transcrire
- `title` (optionnel): Titre de la réunion (par défaut, le nom du fichier est utilisé)

**Fonctionnement :**
Cet endpoint a été amélioré pour inclure une vérification automatique du statut de la transcription :
1. Le fichier audio est uploadé et enregistré sur le serveur
2. Une transcription est lancée auprès d'AssemblyAI
3. Un thread dédié est lancé pour vérifier périodiquement le statut de la transcription (toutes les 30 secondes)
4. La base de données est automatiquement mise à jour lorsque la transcription est terminée

**Réponse :**
```json
{
  "id": "8bddab9d-5942-4b70-8921-9e391f165a45",
  "title": "Audio7min.mp3",
  "transcript_status": "processing",
  "success": true
}
```

### Supprimer une réunion (simplifié)

```
DELETE /simple/meetings/{meeting_id}
```

**En-têtes :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Paramètres de chemin :**
- `meeting_id`: Identifiant unique de la réunion

**Réponse :**
```json
{
  "status": "success",
  "message": "Réunion supprimée avec succès",
  "id": "8bddab9d-5942-4b70-8921-9e391f165a45",
  "success": true
}
```

## Gu00e9nu00e9ration de comptes rendus avec Mistral

Le backend intu00e8gre l'API Mistral pour gu00e9nu00e9rer des comptes rendus structuru00e9s des ru00e9unions u00e0 partir des transcriptions.

### Configuration de Mistral

La clu00e9 API Mistral doit u00eatre configuru00e9e dans le fichier `.env.local` :

```
MISTRAL_API_KEY=votre_clu00e9_api_mistral_ici
```

Vous pouvez obtenir une clu00e9 API sur [le site de Mistral](https://console.mistral.ai/).

### Gu00e9nu00e9rer un compte rendu

```
POST /meetings/{meeting_id}/generate-summary
```

**En-tu00eates :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Paramu00e8tres de chemin :**
- `meeting_id`: Identifiant unique de la ru00e9union

**Fonctionnement :**
1. L'API vu00e9rifie que la transcription est complu00e8te
2. Une demande de gu00e9nu00e9ration de compte rendu est envoyu00e9e u00e0 l'API Mistral
3. Le statut du compte rendu est mis u00e0 jour dans la base de donnu00e9es ("processing")
4. La gu00e9nu00e9ration se poursuit en arriu00e8re-plan

**Ru00e9ponse :**
```json
{
  "message": "Gu00e9nu00e9ration du compte rendu en cours",
  "meeting": {
    "id": "e0ee6308-5ac1-4abf-9c5d-5a754141ec39",
    "user_id": "99dfd97f-a65a-4881-b917-318254285727",
    "title": "audio_3h.mp3",
    "summary_status": "processing"
  },
  "success": true
}
```

### Ru00e9cupu00e9rer un compte rendu

```
GET /meetings/{meeting_id}/summary
```

**En-tu00eates :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Paramu00e8tres de chemin :**
- `meeting_id`: Identifiant unique de la ru00e9union

**Ru00e9ponse :**
```json
{
  "id": "e0ee6308-5ac1-4abf-9c5d-5a754141ec39",
  "title": "audio_3h.mp3",
  "summary_status": "completed",
  "summary_text": "# Synthu00e8se\nLa ru00e9union intitulu00e9e 'audio_3h.mp3' a abordu00e9 plusieurs points clu00e9s concernant la politique culturelle de la ville d'Orlu00e9ans...\n\n# u00c9lu00e9ments discuts\n- **Investissements culturels** : Discussion sur les investissements significatifs...\n\n# Relevu00e9 de du00e9cisions\n- **Approbation des du00e9libu00e9rations** : Plusieurs du00e9libu00e9rations ont u00e9tu00e9 approuvu00e9es...\n\n# Plan d'action\n- **Investissements culturels** : Poursuite des investissements dans les projets culturels majeurs...",
  "success": true
}
```

### Format du compte rendu

Le compte rendu gu00e9nu00e9ru00e9 par Mistral est structuru00e9 en quatre sections :

1. **Synthu00e8se** : Ru00e9sumu00e9 global de la ru00e9union
2. **u00c9lu00e9ments discuts** : Points principaux abordu00e9s lors de la ru00e9union
3. **Relevu00e9 de du00e9cisions** : Du00e9cisions prises pendant la ru00e9union
4. **Plan d'action** : Actions u00e0 entreprendre suite u00e0 la ru00e9union

Le format est en Markdown, ce qui permet un affichage structuru00e9 et formattu00e9 dans l'interface utilisateur.

## Gestion du profil utilisateur

### Obtenir les informations de profil

```
GET /profile/me
```

**En-têtes :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Réponse :**
```json
{
  "id": "99dfd97f-a65a-4881-b917-318254285727",
  "email": "utilisateur@example.com",
  "full_name": "Nom Complet",
  "created_at": "2025-05-19T16:05:57.744623",
  "profile_picture_url": null,
  "settings": {
    "theme": "light",
    "language": "fr"
  }
}
```

### Mettre à jour le profil

```
PUT /profile/update
```

**En-têtes :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

**Corps de la requête :**
```json
{
  "full_name": "Nouveau Nom",
  "settings": {
    "theme": "dark",
    "language": "en"
  }
}
```

**Réponse :**
```json
{
  "id": "99dfd97f-a65a-4881-b917-318254285727",
  "email": "utilisateur@example.com",
  "full_name": "Nouveau Nom",
  "created_at": "2025-05-19T16:05:57.744623",
  "profile_picture_url": null,
  "settings": {
    "theme": "dark",
    "language": "en"
  },
  "success": true
}
```

### Télécharger une photo de profil

```
POST /profile/upload-picture
```

**En-têtes :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data
```

**Corps de la requête (form-data) :**
- `file`: Image de profil (formats acceptés : JPG, PNG)

**Réponse :**
```json
{
  "id": "99dfd97f-a65a-4881-b917-318254285727",
  "email": "utilisateur@example.com",
  "full_name": "Nom Complet",
  "created_at": "2025-05-19T16:05:57.744623",
  "profile_picture_url": "/uploads/profile/99dfd97f-a65a-4881-b917-318254285727/profile.jpg",
  "success": true
}
```

### Changer le mot de passe

```
PUT /profile/change-password
```

**En-têtes :**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

**Corps de la requête :**
```json
{
  "current_password": "motdepasse123",
  "new_password": "nouveaumotdepasse456"
}
```

**Réponse :**
```json
{
  "message": "Mot de passe modifié avec succès",
  "success": true
}
```

## Exemples d'utilisation

### Exemple 1: Authentification et upload d'un fichier audio

```python
import requests

# Authentification
auth_response = requests.post(
    "http://localhost:8001/auth/login",
    data={"username": "test@example.com", "password": "password123"}
)
token = auth_response.json()["access_token"]

# Upload d'un fichier audio
with open("audio.mp3", "rb") as f:
    files = {"file": ("audio.mp3", f)}
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        "http://localhost:8001/simple/meetings/upload",
        headers=headers,
        files=files
    )

# Récupérer l'ID de la réunion créée
meeting_id = response.json()["id"]
print(f"Réunion créée avec l'ID: {meeting_id}")
```

### Exemple 2: Vérification du statut de la transcription

```python
import requests
import time

# Authentification
auth_response = requests.post(
    "http://localhost:8001/auth/login",
    data={"username": "test@example.com", "password": "password123"}
)
token = auth_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# ID de la réunion à vérifier
meeting_id = "8bddab9d-5942-4b70-8921-9e391f165a45"

# Vérifier le statut toutes les 10 secondes jusqu'à ce que la transcription soit terminée
for i in range(10):
    print(f"Vérification {i+1}/10")
    response = requests.get(
        f"http://localhost:8001/simple/meetings/{meeting_id}",
        headers=headers
    )
    meeting = response.json()
    print(f"Statut actuel: {meeting.get('transcript_status')}")
    
    if meeting.get("transcript_status") == "completed":
        print("Transcription terminée avec succès!")
        print(f"Début de la transcription: {meeting.get('transcript_text')[:100]}...")
        break
    elif meeting.get("transcript_status") == "error":
        print(f"Erreur lors de la transcription: {meeting.get('transcript_text')}")
        break
    
    print("En attente de la transcription...")
    time.sleep(10)
```

### Exemple 3: Script de test complet pour l'upload et la vérification automatique

```python
# test_upload_with_api_key.py
import requests
import time
import sys

# Paramètres
API_URL = "http://localhost:8001"
USERNAME = "test@example.com"
PASSWORD = "password123"

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_upload_with_api_key.py <chemin_du_fichier_audio>")
        return
        
    file_path = sys.argv[1]
    
    # 1. Connexion à l'API
    print("Connexion à l'API...")
    auth_response = requests.post(
        f"{API_URL}/auth/login",
        data={"username": USERNAME, "password": PASSWORD}
    )
    
    if auth_response.status_code != 200:
        print(f"Erreur de connexion: {auth_response.text}")
        return
        
    token = auth_response.json()["access_token"]
    print(f"Connecté avec succès, token: {token[:10]}...")
    
    # 2. Upload du fichier audio
    print(f"Upload du fichier: {file_path}")
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f)}
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{API_URL}/simple/meetings/upload",
            headers=headers,
            files=files
        )
    
    if response.status_code != 200:
        print(f"Erreur lors de l'upload: {response.text}")
        return
        
    meeting_id = response.json()["id"]
    print(f"Réunion créée avec succès, ID: {meeting_id}")
    print()
    
    # 3. Vérifier le statut de la transcription
    headers = {"Authorization": f"Bearer {token}"}
    
    for i in range(10):
        print(f"Vérification {i+1}/10")
        print(f"Vérification du statut de la réunion {meeting_id}")
        
        response = requests.get(
            f"{API_URL}/simple/meetings/{meeting_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"Erreur lors de la vérification: {response.text}")
            break
            
        meeting = response.json()
        status = meeting.get("transcript_status")
        print(f"Statut actuel: {status}")
        
        if status == "completed":
            print("Transcription terminée avec succès!")
            transcript_text = meeting.get("transcript_text", "")
            print(f"Début de la transcription: {transcript_text[:100]}...")
            break
        elif status == "error":
            print(f"Erreur lors de la transcription: {meeting.get('transcript_text')}")
            break
            
        print("En attente de la transcription...")
        print()
        time.sleep(10)
    
    print("
Fin du test")

if __name__ == "__main__":
    main()
```

## Codes d'erreur

| Code HTTP | Description |
|-----------|-------------|
| 200 | Succès |
| 400 | Requête invalide (paramètres manquants ou invalides) |
| 401 | Non autorisé (token manquant ou invalide) |
| 403 | Accès refusé (l'utilisateur n'a pas les droits nécessaires) |
| 404 | Ressource non trouvée |
| 500 | Erreur interne du serveur |

### Exemples d'erreurs

#### Erreur d'authentification

```json
{
  "detail": "Could not validate credentials"
}
```

#### Ressource non trouvée

```json
{
  "status": "not_found",
  "message": "Réunion non trouvée ou supprimée",
  "id": "8bddab9d-5942-4b70-8921-9e391f165a45",
  "deleted": true,
  "transcript_status": "deleted",
  "success": false
}
```

#### Erreur interne

```json
{
  "detail": "Une erreur s'est produite lors de l'upload: [message d'erreur]"
}
```
