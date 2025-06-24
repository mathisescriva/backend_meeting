# Documentation API MeetingTranscriberBackend

> **Note importante** : Cette API propose des endpoints simplifiés (`/simple/meetings/...`) pour la gestion des réunions. Ces endpoints sont utilisés par le frontend actuel et sont recommandés pour toute nouvelle intégration.

Ce document fournit une documentation complète des endpoints de l'API MeetingTranscriberBackend, expliquant comment les utiliser, les paramètres requis et les réponses attendues, ainsi que l'intégration avec AssemblyAI pour la transcription audio.

## Table des matières

1. [Configuration et démarrage](#configuration-et-démarrage)
2. [Intégration AssemblyAI](#intégration-assemblyai)
3. [Authentification](#authentification)
4. [Gestion des réunions - Endpoints simplifiés](#gestion-des-réunions---endpoints-simplifiés)
5. [Gestion des locuteurs personnalisés](#gestion-des-locuteurs-personnalisés)
6. [Gestion du profil utilisateur](#gestion-du-profil-utilisateur)
7. [Gestion des clients et résumés personnalisés](#gestion-des-clients-et-résumés-personnalisés)
7. [Exemples d'utilisation](#exemples-dutilisation)
8. [Codes d'erreur](#codes-derreur)

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

## Authentification Google OAuth

L'API propose une authentification Google OAuth complète pour permettre aux utilisateurs de se connecter avec leur compte Google sans créer de mot de passe.

### Architecture OAuth

Le flow OAuth est entièrement géré côté backend pour éviter les problèmes de sécurité et de session. Le processus est le suivant :

1. **Redirection initiale** : L'utilisateur est redirigé vers Google OAuth
2. **Authentification Google** : L'utilisateur s'authentifie sur Google
3. **Callback automatique** : Google redirige vers le backend avec un code
4. **Traitement backend** : Le backend échange le code contre un token et crée/récupère l'utilisateur
5. **Retour frontend** : Redirection vers le frontend avec le token JWT

### Authentification Google OAuth

```
GET /auth/google
```

**Description** : Initie le processus d'authentification Google OAuth. Redirige directement vers Google.

**Paramètres** : Aucun

**Utilisation côté frontend** :
```javascript
// Simple redirection vers l'endpoint OAuth
window.location.href = 'http://localhost:8001/auth/google'
```

**Réponse** : Redirection HTTP 302 vers Google OAuth

### Callback Google OAuth

```
GET /auth/google/callback
```

**Description** : Endpoint de callback utilisé par Google après authentification. **Ne pas appeler directement.**

**Paramètres de requête automatiques** :
- `code` : Code d'autorisation fourni par Google
- `state` : État de sécurité pour prévenir les attaques CSRF
- `error` (optionnel) : Erreur si l'authentification a échoué

**Réponse** : Redirection vers le frontend avec le token JWT

### Gestion du retour côté frontend

Après l'authentification Google, l'utilisateur est redirigé vers votre frontend avec les paramètres suivants :

#### Authentification réussie
```
https://votre-frontend.com/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...&success=true
```

#### Authentification échouée
```
https://votre-frontend.com/?error=invalid_state
```

### Code JavaScript d'intégration

```javascript
// 1. Initier l'authentification Google
function loginWithGoogle() {
    window.location.href = 'http://localhost:8001/auth/google'
}

// 2. Gérer le retour de l'authentification
function handleAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search)
    const token = urlParams.get('token')
    const success = urlParams.get('success')
    const error = urlParams.get('error')
    
    if (success && token) {
        // Authentification réussie
        localStorage.setItem('access_token', token)
        
        // Nettoyer l'URL
        window.history.replaceState({}, document.title, window.location.pathname)
        
        // Rediriger vers l'application
        window.location.href = '/dashboard'
        
    } else if (error) {
        // Gérer les erreurs
        handleAuthError(error)
    }
}

// 3. Gérer les erreurs d'authentification
function handleAuthError(error) {
    const errorMessages = {
        'invalid_state': 'Session expirée, veuillez réessayer',
        'missing_params': 'Paramètres manquants, veuillez réessayer',
        'token_exchange_failed': 'Erreur lors de l\'échange de token',
        'user_info_failed': 'Impossible de récupérer les informations utilisateur',
        'email_already_exists': 'Un compte existe déjà avec cet email',
        'email_exists_other_provider': 'Cet email est associé à un autre fournisseur',
        'server_error': 'Erreur serveur, veuillez réessayer'
    }
    
    const message = errorMessages[error] || 'Erreur d\'authentification inconnue'
    alert(message) // Remplacez par votre système de notifications
}

// 4. Appeler au chargement de la page
document.addEventListener('DOMContentLoaded', handleAuthCallback)
```

### Configuration des variables d'environnement

Configurez les variables suivantes dans votre fichier `.env` :

```env
# Configuration Google OAuth
GOOGLE_CLIENT_ID=votre_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=votre_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8001/auth/google/callback
FRONTEND_URL=http://localhost:5173

# Pour la production
GOOGLE_REDIRECT_URI=https://backend-meeting.onrender.com/auth/google/callback
FRONTEND_URL=https://votre-frontend.com
```

### Configuration Google Cloud Console

1. **Créer un projet** sur [Google Cloud Console](https://console.cloud.google.com/)
2. **Activer l'API Google OAuth2**
3. **Créer des identifiants OAuth 2.0** :
   - Type d'application : Application Web
   - URI de redirection autorisées :
     - `http://localhost:8001/auth/google/callback` (développement)
     - `https://backend-meeting.onrender.com/auth/google/callback` (production)

### Gestion des erreurs OAuth

| Code d'erreur | Description | Action recommandée |
|---------------|-------------|-------------------|
| `invalid_state` | État OAuth invalide ou expiré | Recommencer le processus |
| `missing_params` | Paramètres code ou state manquants | Vérifier la configuration Google |
| `token_exchange_failed` | Échec de l'échange code → token | Vérifier les credentials Google |
| `user_info_failed` | Impossible de récupérer les infos utilisateur | Vérifier les permissions OAuth |
| `email_already_exists` | Email déjà utilisé avec un compte classique | Proposer la connexion classique |
| `email_exists_other_provider` | Email utilisé avec un autre provider OAuth | Informer l'utilisateur |
| `server_error` | Erreur interne du serveur | Réessayer plus tard |

### Sécurité implémentée

- ✅ **Protection CSRF** : États OAuth uniques et temporaires (5 minutes)
- ✅ **Usage unique** : Chaque état ne peut être utilisé qu'une seule fois
- ✅ **Validation serveur** : Toute la logique de validation côté backend
- ✅ **Gestion des conflits** : Détection des emails déjà existants
- ✅ **Logging complet** : Traçabilité des authentifications
- ✅ **Nettoyage automatique** : Suppression des états expirés

### Test de l'authentification Google

Pour tester l'implémentation :

```bash
# 1. Démarrer le serveur
uvicorn app.main:app --reload --port 8001

# 2. Ouvrir dans un navigateur
http://localhost:8001/auth/google

# 3. Suivre le processus d'authentification Google

# 4. Vérifier la redirection avec le token
```

Ou utiliser le script de test automatisé :

```bash
python test_google_oauth.py
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

## Gestion des locuteurs personnalisés

Cette section décrit les endpoints permettant de gérer les noms personnalisés des locuteurs dans les réunions transcrites. Ces endpoints permettent de renommer les locuteurs détectés automatiquement par AssemblyAI ("Speaker A", "Speaker B", etc.) avec des noms réels ou des titres (comme "Monsieur le Maire", "Secrétaire", etc.).

### Liste des locuteurs personnalisés

```
GET /meetings/{meeting_id}/speakers
```

**Description** : Récupère la liste des noms personnalisés des locuteurs pour une réunion spécifique.

**Paramètres de chemin** :
- `meeting_id` (UUID, obligatoire) : ID unique de la réunion

**En-têtes requis** :
- `Authorization: Bearer {token}`

**Réponse réussie (200 OK)** :
```json
{
  "speakers": [
    {
      "speaker_id": "A",
      "custom_name": "Monsieur le Maire"
    },
    {
      "speaker_id": "B",
      "custom_name": "Conseiller Martin"
    }
  ]
}
```

### Créer ou mettre à jour un nom personnalisé

```
POST /meetings/{meeting_id}/speakers
```

**Description** : Crée ou met à jour un nom personnalisé pour un locuteur dans une réunion.

**Paramètres de chemin** :
- `meeting_id` (UUID, obligatoire) : ID unique de la réunion

**En-têtes requis** :
- `Authorization: Bearer {token}`
- `Content-Type: application/json`

**Corps de la requête** :
```json
{
  "speaker_id": "A",
  "custom_name": "Monsieur le Maire"
}
```

**Réponse réussie (200 OK)** :
```json
{
  "speaker_id": "A",
  "custom_name": "Monsieur le Maire"
}
```

### Supprimer un nom personnalisé

```
DELETE /meetings/{meeting_id}/speakers/{speaker_id}
```

**Description** : Supprime un nom personnalisé pour un locuteur spécifique d'une réunion.

**Paramètres de chemin** :
- `meeting_id` (UUID, obligatoire) : ID unique de la réunion
- `speaker_id` (String, obligatoire) : ID du locuteur (généralement une lettre comme "A", "B", etc.)

**En-têtes requis** :
- `Authorization: Bearer {token}`

**Réponse réussie (200 OK)** :
```json
{
  "success": true,
  "message": "Nom personnalisé supprimé avec succès"
}
```

### Mettre à jour la transcription avec les noms personnalisés

```
GET /meetings/{meeting_id}/speakers/update-transcript
```

**Description** : Regénère et met à jour le texte de la transcription en remplaçant les identifiants des locuteurs ("Speaker A", etc.) par leurs noms personnalisés. Cette opération modifie le texte stocké dans la base de données.

**Paramètres de chemin** :
- `meeting_id` (UUID, obligatoire) : ID unique de la réunion

**En-têtes requis** :
- `Authorization: Bearer {token}`

**Réponse réussie (200 OK)** :
```json
{
  "success": true,
  "message": "Transcription mise à jour avec succès",
  "transcript_text": "Monsieur le Maire: Eh bien, mes chers collègues, je vous propose que nous ouvrions cette séance..."
}
```

**Erreur (404 Not Found)** :
```json
{
  "message": "Réunion non trouvée",
  "type": "NOT_FOUND"
}
```

**Erreur (400 Bad Request)** :
```json
{
  "message": "La transcription n'est pas encore terminée",
  "type": "INVALID_STATE",
  "status": "processing"
}
```

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

## Gestion des clients et résumés personnalisés

Cette API permet de gérer des clients avec des templates de résumé personnalisés. Les réunions peuvent être associées à des clients spécifiques pour générer des comptes rendus personnalisés selon le format désiré par chaque client.

### Créer un nouveau client

```
POST /clients/
```

**En-têtes requis :**
```
Authorization: Bearer votre_token_jwt
Content-Type: application/json
```

**Corps de la requête :**
```json
{
  "name": "Nom du Client",
  "summary_template": "# Compte rendu pour {meeting_title}\n\nVoici la transcription personnalisée pour ce client: {transcript_text}"
}
```

**Réponse :**
```json
{
  "id": "de269a40-2840-43e5-9e75-486d03680526",
  "user_id": "99dfd97f-a65a-4881-b917-318254285727",
  "name": "Nom du Client",
  "summary_template": "# Compte rendu pour {meeting_title}\n\nVoici la transcription personnalisée pour ce client: {transcript_text}",
  "created_at": "2025-05-20T18:46:40.452140"
}
```

### Liste des clients

```
GET /clients/
```

**En-tête requis :**
```
Authorization: Bearer votre_token_jwt
```

**Réponse :**
```json
[
  {
    "id": "de269a40-2840-43e5-9e75-486d03680526",
    "user_id": "99dfd97f-a65a-4881-b917-318254285727",
    "name": "Nom du Client",
    "summary_template": "# Compte rendu pour {meeting_title}\n\nVoici la transcription personnalisée pour ce client: {transcript_text}",
    "created_at": "2025-05-20T18:46:40.452140"
  }
]
```

### Récupérer un client spécifique

```
GET /clients/{client_id}
```

**En-tête requis :**
```
Authorization: Bearer votre_token_jwt
```

**Réponse :**
```json
{
  "id": "de269a40-2840-43e5-9e75-486d03680526",
  "user_id": "99dfd97f-a65a-4881-b917-318254285727",
  "name": "Nom du Client",
  "summary_template": "# Compte rendu pour {meeting_title}\n\nVoici la transcription personnalisée pour ce client: {transcript_text}",
  "created_at": "2025-05-20T18:46:40.452140"
}
```

### Mettre à jour un client

```
PUT /clients/{client_id}
```

**En-têtes requis :**
```
Authorization: Bearer votre_token_jwt
Content-Type: application/json
```

**Corps de la requête :**
```json
{
  "name": "Nouveau Nom du Client",
  "summary_template": "# Format personnalisé mis à jour\n\n{transcript_text}"
}
```

**Réponse :**
```json
{
  "id": "de269a40-2840-43e5-9e75-486d03680526",
  "user_id": "99dfd97f-a65a-4881-b917-318254285727",
  "name": "Nouveau Nom du Client",
  "summary_template": "# Format personnalisé mis à jour\n\n{transcript_text}",
  "created_at": "2025-05-20T18:46:40.452140"
}
```

### Supprimer un client

```
DELETE /clients/{client_id}
```

**En-tête requis :**
```
Authorization: Bearer votre_token_jwt
```

**Réponse :**
```json
{
  "message": "Client supprimé avec succès"
}
```

### Associer une réunion à un client

Pour associer une réunion à un client, utilisez la méthode PUT pour mettre à jour les informations de la réunion :

```
PUT /meetings/{meeting_id}
```

**Corps de la requête :**
```json
{
  "client_id": "de269a40-2840-43e5-9e75-486d03680526"
}
```

### Générer un résumé personnalisé

Pour générer un résumé personnalisé pour une réunion, vous pouvez spécifier le client directement lors de la génération :

```
POST /meetings/{meeting_id}/generate-summary?client_id={client_id}
```

Si la réunion est déjà associée à un client, l'API utilisera automatiquement le template de ce client pour générer le résumé.

### Variables disponibles dans les templates

Les templates de résumé peuvent utiliser les variables suivantes :

- `{meeting_title}` : Titre de la réunion
- `{transcript_text}` : Texte complet de la transcription

Exemple de template :
```
# Compte rendu de la réunion : {meeting_title}

Ci-dessous le résumé de la réunion :

{transcript_text}
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
    
    print("Fin du test")

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
