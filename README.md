# Meeting Transcriber API

Une API FastAPI pour la transcription automatique de réunions audio en texte avec reconnaissance des locuteurs, utilisant AssemblyAI.

## Fonctionnalités

- **Authentification sécurisée** - JWT avec optimisation des performances (mise en cache)
- **Transcription audio** - Conversion MP3/WAV en texte avec identification des locuteurs
- **API RESTful** - Interface API complète et documentée
- **Documentation OpenAPI** - Documentation interactive via Swagger UI

## Optimisations pour la Production

Cette API a été optimisée pour une utilisation en production avec:

- **Mise en cache** des vérifications de mot de passe et des données utilisateur fréquemment utilisées
- **Pool de connexions** pour la base de données SQLite
- **Gestion des erreurs** globale avec logging détaillé
- **Limitation de débit** pour éviter les abus
- **Configuration CORS** sécurisée
- **Monitoring** des temps de réponse et détection des requêtes lentes

## Prérequis

- Python 3.9+
- AssemblyAI API Key
- Environnement de déploiement (serveur Linux, Docker, etc.)

## Installation

### Installation manuelle

1. Cloner le dépôt :
```bash
git clone https://github.com/votreuser/meeting-transcriber-backend.git
cd meeting-transcriber-backend
```

2. Créer un environnement virtuel et installer les dépendances :
```bash
python -m venv venv
source venv/bin/activate  # Sous Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Créer un fichier `.env` à partir du modèle :
```bash
cp .env.example .env
```

4. Éditer le fichier `.env` avec vos configurations

5. Lancer l'application :
```bash
./start_production.sh
```

### Déploiement avec Docker

1. Créer un fichier `.env` à partir du modèle :
```bash
cp .env.example .env
```

2. Éditer le fichier `.env` avec vos configurations

3. Lancer l'application avec Docker Compose :
```bash
docker-compose up -d
```

## Structure du Projet

```
meeting-transcriber-backend/
├── app/                      # Code principal
│   ├── core/                 # Noyau de l'application
│   │   ├── config.py         # Configuration
│   │   └── security.py       # Sécurité et authentification
│   ├── db/                   # Accès à la base de données
│   │   └── database.py       # Fonctions de base de données
│   │   └── queries.py        # Requêtes SQL pour les meetings et utilisateurs
│   ├── models/               # Modèles Pydantic
│   │   └── user.py           # Modèle utilisateur
│   │   └── meeting.py        # Modèles de réunions
│   ├── routes/               # Routeurs API
│   │   ├── auth.py           # Routes d'authentification
│   │   ├── meetings.py       # Routes de gestion des réunions
│   │   └── simple_meetings.py # Routes simplifiées pour les réunions
│   ├── services/             # Services métier
│   │   ├── assemblyai.py     # Service unifié de transcription avec AssemblyAI
│   │   ├── file_upload.py    # Service de gestion des fichiers
│   │   └── queue_processor.py # Processeur de file d'attente pour les transcriptions
│   └── main.py               # Point d'entrée de l'application
├── uploads/                  # Répertoire pour stocker les fichiers
├── tests/                    # Tests
├── migrations/               # Scripts de migration SQL
├── .env.example              # Exemple de fichier de configuration
├── Dockerfile                # Configuration Docker
├── docker-compose.yml        # Configuration Docker Compose
├── check_pending_transcriptions.py # Script utilitaire pour traiter les transcriptions en attente
├── requirements.txt          # Dépendances Python
├── start_production.sh       # Script de démarrage
└── README.md                 # Documentation
```

## Variables d'Environnement

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| ENVIRONMENT | Environnement d'exécution | `development` |
| JWT_SECRET | Clé secrète pour l'authentification JWT | (valeur générée) |
| CORS_ORIGINS | Domaines autorisés pour CORS | `*` |
| DB_POOL_SIZE | Taille du pool de connexions | `10` |
| DB_POOL_TIMEOUT | Timeout pour les connexions | `30` |
| HTTP_TIMEOUT | Timeout pour les requêtes HTTP | `30` |
| ENABLE_CACHE | Activer le cache | `True` |
| CACHE_TTL | Durée de vie du cache (secondes) | `300` |
| LOG_LEVEL | Niveau de logging | `INFO` |
| MAX_UPLOAD_SIZE | Taille maximale d'upload (bytes) | `100000000` |
| ASSEMBLYAI_API_KEY | Clé API pour AssemblyAI | (requis) |
| DEFAULT_LANGUAGE | Langue par défaut pour la transcription | `fr` |
| SPEAKER_LABELS | Activer la reconnaissance des locuteurs | `True` |

## Service de Transcription

Le système utilise un service de transcription unifié basé sur AssemblyAI pour convertir les fichiers audio en texte avec identification des locuteurs.

### Fonctionnalités principales du service de transcription

- **Upload de fichier audio** - Prise en charge des formats MP3 et WAV
- **Conversion automatique** - Conversion des formats audio vers WAV compatible
- **Identification des locuteurs** - Reconnaissance et étiquetage des différents locuteurs
- **Métadonnées** - Extraction de la durée et du nombre de locuteurs
- **Traitement asynchrone** - Exécution en arrière-plan sans bloquer l'API
- **Système de file d'attente** - Gestion des transcriptions multiples
- **Reprise automatique** - Reprise des transcriptions interrompues au redémarrage

### Scripts utilitaires

- `check_pending_transcriptions.py` - Permet de vérifier et traiter manuellement les transcriptions en attente
- `transcription_service.py` - Service autonome pour traiter les transcriptions en parallèle de l'API principale

## Documentation API

Lorsque l'application est en cours d'exécution, la documentation API est disponible aux adresses suivantes:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Surveillance et Maintenance

### Logs

Les logs sont disponibles:
- En sortie standard lorsqu'exécuté directement
- Dans les logs Docker lorsqu'exécuté via Docker: `docker-compose logs -f api`

### Performance

L'API inclut des en-têtes de performance qui peuvent être surveillés:
- `X-Process-Time`: temps de traitement en secondes pour chaque requête

## Licence

Ce projet est sous licence MIT.
