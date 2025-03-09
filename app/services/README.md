# Services de l'application Meeting Transcriber

Ce répertoire contient les différents services utilisés par l'application Meeting Transcriber.

## Service de transcription (assemblyai.py)

Le service `assemblyai.py` est responsable de la transcription des fichiers audio en texte. Il utilise l'API AssemblyAI pour effectuer cette tâche.

### Fonctions principales

- `transcribe_meeting(meeting_id, file_url, user_id)`: Lance le processus de transcription pour une réunion
- `process_transcription(meeting_id, file_url, user_id)`: Effectue le processus complet de transcription
- `upload_file_to_assemblyai(file_path)`: Télécharge un fichier audio vers AssemblyAI
- `start_transcription(audio_url)`: Démarre une transcription sur AssemblyAI
- `check_transcription_status(transcript_id)`: Vérifie le statut d'une transcription
- `process_pending_transcriptions()`: Traite toutes les transcriptions en attente
- `convert_to_wav(input_path)`: Convertit un fichier audio en format WAV

### Flux de travail

1. Un fichier audio est téléchargé via une route API
2. `transcribe_meeting` est appelé et met à jour le statut de la réunion à "processing"
3. Un thread est lancé pour exécuter `process_transcription` en arrière-plan
4. Si le fichier est local, il est d'abord téléchargé vers AssemblyAI via `upload_file_to_assemblyai`
5. La transcription est démarrée avec `start_transcription`
6. Le statut est vérifié périodiquement avec `check_transcription_status`
7. Une fois terminée, la base de données est mise à jour avec le résultat

## Processeur de file d'attente (queue_processor.py)

Le service `queue_processor.py` gère une file d'attente de transcriptions à traiter en arrière-plan.

### Fonctions principales

- `start_queue_processor()`: Démarre le processeur de file d'attente
- `stop_queue_processor()`: Arrête le processeur de file d'attente
- `QueueProcessor`: Classe principale qui gère la file d'attente

### Flux de travail

1. Le processeur s'exécute en arrière-plan et vérifie périodiquement le répertoire de queue
2. Lorsqu'un fichier de queue est trouvé, il est traité par `process_transcription_wrapper`
3. Une fois la transcription terminée, le fichier de queue est supprimé

## Service de téléchargement de fichiers (file_upload.py)

Le service `file_upload.py` gère le téléchargement et la validation des fichiers.

### Fonctions principales

- `validate_image_file(file)`: Vérifie si un fichier est une image valide
- `save_profile_picture(file, user_id)`: Sauvegarde une image de profil
- `delete_profile_picture(file_url)`: Supprime une image de profil
