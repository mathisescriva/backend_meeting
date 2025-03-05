#!/bin/bash

# Variables d'environnement pour la production
export ENVIRONMENT=production
export CORS_ORIGINS="https://app.example.com"
export DB_POOL_SIZE=20
export DB_POOL_TIMEOUT=30
export HTTP_TIMEOUT=60
export ENABLE_CACHE=true
export CACHE_TTL=600
export LOG_LEVEL=INFO
export MAX_UPLOAD_SIZE=100000000
export DEFAULT_LANGUAGE=fr
export SPEAKER_LABELS=true

# Vérifier les variables sensibles
if [ -z "$JWT_SECRET" ]; then
  echo "⚠️ JWT_SECRET non défini, utilisation d'une valeur par défaut (déconseillé en production)"
  export JWT_SECRET=$(openssl rand -base64 32)
fi

if [ -z "$ASSEMBLYAI_API_KEY" ]; then
  echo "❌ ASSEMBLYAI_API_KEY non défini, l'API de transcription ne fonctionnera pas correctement"
  echo "Veuillez définir ASSEMBLYAI_API_KEY avant de lancer l'application"
  exit 1
fi

# Créer les répertoires nécessaires
mkdir -p uploads/audio
mkdir -p logs

# Lancer l'application avec uvicorn en mode production
echo "🚀 Démarrage de l'API Meeting Transcriber en mode production"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info
