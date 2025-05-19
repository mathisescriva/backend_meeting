# Intégration AssemblyAI - Documentation

Ce document décrit l'intégration du service AssemblyAI pour la transcription audio dans l'application MeetingTranscriberBackend et explique comment utiliser les endpoints de l'API.

## Architecture de l'intégration

L'intégration avec AssemblyAI se fait en plusieurs étapes :

1. **Upload du fichier audio** : Le fichier audio est d'abord uploadé vers les serveurs d'AssemblyAI
2. **Démarrage de la transcription** : Une fois le fichier uploadé, une demande de transcription est lancée
3. **Vérification automatique du statut** : Le système vérifie automatiquement le statut de la transcription
4. **Récupération des résultats** : Une fois la transcription terminée, les résultats sont récupérés et stockés dans la base de données

## Fichiers principaux

### `app/services/assemblyai.py`

Contient les fonctions principales pour interagir avec l'API AssemblyAI :

- `upload_file_to_assemblyai(file_path)` : Upload un fichier audio vers AssemblyAI
- `start_transcription(audio_url)` : Démarre une transcription pour un fichier audio déjà uploadé
- `check_transcription_status(transcript_id)` : Vérifie le statut d'une transcription en cours
- `process_transcription(meeting_id, file_url, user_id)` : Processus complet de transcription d'une réunion
- `process_pending_transcriptions()` : Vérifie les transcriptions en attente ou en cours

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

## Utilisation des endpoints de l'API

### Upload d'un fichier audio et transcription

```bash
POST /simple/meetings/upload
```

Paramètres :
- `file` : Fichier audio à transcrire (multipart/form-data)
- `title` : Titre optionnel de la réunion (par défaut, le nom du fichier est utilisé)

Exemple de requête avec curl :
```bash
curl -X POST "http://localhost:8001/simple/meetings/upload" \
  -H "Authorization: Bearer votre_token" \
  -F "file=@chemin/vers/fichier.mp3"
```

Réponse :
```json
{
  "id": "8bddab9d-5942-4b70-8921-9e391f165a45",
  "title": "fichier.mp3",
  "transcript_status": "processing",
  "success": true
}
```

### Récupération des réunions

```bash
GET /simple/meetings/
```

Paramètres :
- `status` : Filtre optionnel pour afficher uniquement les réunions avec un statut spécifique ("pending", "processing", "completed", "error")

Exemple de requête avec curl :
```bash
curl -X GET "http://localhost:8001/simple/meetings/" \
  -H "Authorization: Bearer votre_token"
```

### Récupération des détails d'une réunion

```bash
GET /simple/meetings/{meeting_id}
```

Exemple de requête avec curl :
```bash
curl -X GET "http://localhost:8001/simple/meetings/8bddab9d-5942-4b70-8921-9e391f165a45" \
  -H "Authorization: Bearer votre_token"
```

Réponse :
```json
{
  "id": "8bddab9d-5942-4b70-8921-9e391f165a45",
  "title": "fichier.mp3",
  "transcript_status": "completed",
  "transcript_text": "Speaker A: Texte de la transcription...",
  "duration_seconds": 431,
  "speakers_count": 3,
  "success": true
}
```

## Configuration

### Clé API AssemblyAI

La clé API AssemblyAI est configurée dans le fichier `.env` :

```
ASSEMBLYAI_API_KEY=votre_clé_api
```

Pour des raisons de fiabilité, la clé API est également définie directement dans le fichier `app/services/assemblyai.py` :

```python
ASSEMBLY_AI_API_KEY = "3419005ee6924e08a14235043cabcd4e"
```

## Résolution des problèmes courants

### Transcriptions bloquées en état "processing"

Si des transcriptions restent bloquées en état "processing" pendant trop longtemps, vous pouvez utiliser le script `update_db_transcription_status.py` pour forcer la mise à jour de leur statut.

### Vérification manuelle d'une transcription

Pour vérifier manuellement le statut d'une transcription sur AssemblyAI :

```python
python -c "import requests; headers = {'authorization': '3419005ee6924e08a14235043cabcd4e'}; response = requests.get('https://api.assemblyai.com/v2/transcript/TRANSCRIPT_ID', headers=headers); print(response.json())"
```

Remplacez `TRANSCRIPT_ID` par l'ID de la transcription à vérifier.

## Optimisations et améliorations récentes

1. **Vérification automatique des transcriptions** : Le système vérifie automatiquement le statut des transcriptions en cours et met à jour la base de données sans intervention manuelle.

2. **Vérification périodique via thread dédié** : Lors de l'upload d'un fichier audio, un thread dédié est lancé pour vérifier périodiquement le statut de la transcription auprès d'AssemblyAI (toutes les 30 secondes pendant 10 minutes).

3. **Vérification lors des requêtes API** : Chaque fois qu'un utilisateur consulte une réunion ou la liste des réunions, le système vérifie automatiquement le statut des transcriptions en cours.

4. **Relance automatique désactivée** : Pour éviter les coûts inutiles, la relance automatique des transcriptions a été désactivée.

5. **Détection des transcriptions bloquées** : Le système détecte les transcriptions bloquées en état "processing" pendant trop longtemps et les marque comme en erreur.

6. **Gestion améliorée des erreurs** : Meilleure gestion des erreurs lors de l'upload des fichiers et du démarrage des transcriptions.

## Recommandations

1. **Surveillance des coûts** : Surveillez régulièrement vos coûts AssemblyAI pour vous assurer qu'il n'y a pas d'utilisation excessive.

2. **Sauvegarde des fichiers audio** : Assurez-vous de sauvegarder les fichiers audio originaux en cas de problème avec la transcription.

3. **Mise à jour régulière** : Vérifiez régulièrement les mises à jour de l'API AssemblyAI et adaptez votre code en conséquence.
