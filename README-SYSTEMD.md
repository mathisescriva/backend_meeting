# Configuration du processeur de file d'attente avec systemd

Ce document explique comment configurer le processeur de file d'attente pour qu'il s'exécute automatiquement sur un serveur Linux utilisant systemd.

## Installation du service systemd

1. Modifier les fichiers de service pour spécifier les bons chemins :

```bash
# Éditer les fichiers transcription-queue.service et transcription-queue.timer
# Remplacer /path/to/MeetingTranscriberBackend par le chemin réel de l'application
# Remplacer www-data par l'utilisateur qui exécutera le service
```

2. Copier les fichiers de service dans le dossier systemd :

```bash
sudo cp transcription-queue.service /etc/systemd/system/
sudo cp transcription-queue.timer /etc/systemd/system/
```

3. Recharger la configuration systemd :

```bash
sudo systemctl daemon-reload
```

4. Activer et démarrer le timer :

```bash
sudo systemctl enable transcription-queue.timer
sudo systemctl start transcription-queue.timer
```

## Vérifier le statut du service

```bash
# Vérifier le statut du timer
sudo systemctl status transcription-queue.timer

# Vérifier le statut du service
sudo systemctl status transcription-queue.service

# Voir les logs du service
sudo journalctl -u transcription-queue.service
```

## Notes

- Le timer est configuré pour exécuter le service toutes les minutes.
- Le service vérifie les fichiers de queue et traite les transcriptions en attente.
- Si le service échoue, il redémarrera automatiquement après 30 secondes.

## Alternative : Cron

Si vous préférez utiliser cron plutôt que systemd, ajoutez la ligne suivante à votre crontab :

```bash
# Éditer le crontab
crontab -e

# Ajouter cette ligne
* * * * * cd /path/to/MeetingTranscriberBackend && python3 process_transcription_queue.py >> /var/log/transcription-queue.log 2>&1
```

Cela exécutera le script toutes les minutes et enregistrera la sortie dans le fichier de log spécifié.
