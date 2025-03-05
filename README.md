# Meeting Transcriber Backend

Une API FastAPI pour transcrire des enregistrements audio de réunions en texte, avec identification des interlocuteurs, en utilisant AssemblyAI.

## Fonctionnalités

- 🔐 **Authentification JWT** : Système sécurisé d'inscription et de connexion
- 🎙️ **Transcription Audio** : Convertit les fichiers audio en texte avec identification des locuteurs
- 📊 **Gestion des Réunions** : API complète pour créer, lire, mettre à jour et supprimer des réunions
- 📄 **Documentation API** : Documentation interactive via Swagger UI
- 🧪 **Tests Automatisés** : Tests unitaires et d'intégration

## Prérequis

- Python 3.9+
- [AssemblyAI API Key](https://www.assemblyai.com/) (pour la transcription)

## Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/username/meeting-transcriber-backend.git
cd meeting-transcriber-backend
```

2. Créer et activer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Créer un fichier `.env` à la racine du projet :
```
ASSEMBLYAI_API_KEY=votre_cle_api_assemblyai
JWT_SECRET_KEY=une_cle_secrete_aleatoire
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Démarrage

1. Lancer le serveur de développement :
```bash
uvicorn app.main:app --reload --port 8048
```

2. Accéder à la documentation API :
   - Documentation Swagger : http://localhost:8048/docs
   - Documentation ReDoc : http://localhost:8048/redoc

## Tests

Pour exécuter les tests automatisés :

```bash
python -m pytest tests/
```

## Structure de l'API

### Authentification

- `POST /auth/register` : Inscription d'un utilisateur
- `POST /auth/login` : Connexion et obtention d'un token JWT

### Gestion des Réunions

- `POST /meetings/upload` : Téléchargement d'un fichier audio et création d'une réunion
- `GET /meetings/` : Liste des réunions de l'utilisateur
- `GET /meetings/{meeting_id}` : Détails d'une réunion spécifique
- `PUT /meetings/{meeting_id}` : Mise à jour des métadonnées d'une réunion
- `DELETE /meetings/{meeting_id}` : Suppression d'une réunion

### Transcription

- `POST /meetings/{meeting_id}/transcribe` : Relance la transcription d'une réunion
- `GET /meetings/{meeting_id}/transcript` : Récupère uniquement la transcription d'une réunion

## Intégration AssemblyAI

Le service utilise l'API REST AssemblyAI v2 pour la transcription audio avec les fonctionnalités suivantes :

- Identification des interlocuteurs (speaker labels)
- Support multilingue (français par défaut)
- Upload direct des fichiers vers AssemblyAI
- Gestion asynchrone du processus de transcription

## Déploiement en production

Pour un déploiement en production, prenez en compte les points suivants :

1. Utilisez un serveur WSGI comme Gunicorn :
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

2. Sécurisez vos variables d'environnement
3. Mettez en place une base de données robuste (PostgreSQL recommandé)
4. Configurez les permissions de fichiers appropriées pour le stockage local
5. Ajustez les paramètres CORS pour limiter l'accès aux domaines autorisés

## Licence

MIT
