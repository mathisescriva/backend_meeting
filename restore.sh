#!/bin/bash

# Liste des fichiers essentiels u00e0 restaurer
essential_files=(
  # Structure principale
  "app/main.py"
  "app/core/config.py"
  "app/core/security.py"
  "app/core/__init__.py"
  "app/__init__.py"
  "app/db/database.py"
  "app/db/queries.py"
  "app/db/__init__.py"
  "app/models/meeting.py"
  "app/models/user.py"
  "app/models/__init__.py"
  
  # Routes principales
  "app/routes/__init__.py"
  "app/routes/auth.py"
  "app/routes/meetings.py"
  "app/routes/simple_meetings.py"
  "app/routes/profile.py"
  
  # Services
  "app/services/__init__.py"
  "app/services/assemblyai.py"
  "app/services/file_upload.py"
  "app/services/mistral_summary.py"
  "app/services/transcription_checker.py"
  
  # Tests essentiels
  "tests/__init__.py"
  "tests/test_endpoints.py"
  "tests/test_auth.py"
  "tests/test_summary_generation.py"
  "tests/test_transcription_process.py"
  "tests/test_api.py"
  "tests/test_simple_upload.py"
)

# Restaurer les fichiers essentiels depuis le dossier d'archive
for file in "${essential_files[@]}"; do
  if [ -f "archive/$file" ]; then
    # Cru00e9er le ru00e9pertoire parent si nu00e9cessaire
    mkdir -p "$(dirname "$file")"
    cp "archive/$file" "$file"
    echo "Restauru00e9: $file"
  else
    echo "Fichier non trouvu00e9 dans l'archive: $file"
  fi
done

# Restaurer le script de vu00e9rification des transcriptions en attente
if [ -f "archive/scheduled_transcription_checker.py" ]; then
  cp "archive/scheduled_transcription_checker.py" "scheduled_transcription_checker.py"
  echo "Restauru00e9: scheduled_transcription_checker.py"
fi

echo "Restauration terminu00e9e. Les fichiers essentiels ont u00e9tu00e9 restauru00e9s depuis le dossier 'archive'."
