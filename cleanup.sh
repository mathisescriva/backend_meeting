#!/bin/bash

# Créer un dossier d'archive
mkdir -p archive

# Liste des fichiers essentiels à conserver
essential_files=(
  # Structure principale
  "app/main.py"
  "app/core"
  "app/db/database.py"
  "app/db/queries.py"
  "app/models"
  
  # Routes principales
  "app/routes/auth.py"
  "app/routes/meetings.py"
  "app/routes/simple_meetings.py"
  "app/routes/profile.py"
  
  # Services
  "app/services/assemblyai.py"
  "app/services/file_upload.py"
  "app/services/mistral_summary.py"
  "app/services/transcription_checker.py"
  
  # Tests essentiels
  "test_endpoints.py"
  "test_auth.py"
  "test_summary_generation.py"
  "test_transcription_process.py"
  "test_api.py"
  "test_simple_upload.py"
  
  # Documentation
  "README_API.md"
  "README_ASSEMBLYAI.md"
  
  # Fichiers de configuration
  ".env"
  "requirements.txt"
)

# Créer un répertoire temporaire pour les fichiers essentiels
mkdir -p temp_essential

# Copier les fichiers essentiels dans le répertoire temporaire
for file in "${essential_files[@]}"; do
  if [ -f "$file" ]; then
    # Créer le répertoire parent si nécessaire
    mkdir -p "temp_essential/$(dirname "$file")"
    cp "$file" "temp_essential/$(dirname "$file")/"
    echo "Conservé: $file"
  elif [ -d "$file" ]; then
    mkdir -p "temp_essential/$file"
    cp -r "$file"/* "temp_essential/$file/"
    echo "Conservé: $file/"
  else
    echo "Fichier non trouvé: $file"
  fi
done

# Déplacer tous les autres fichiers .py dans le dossier d'archive
find . -name "*.py" -not -path "./temp_essential/*" -not -path "./archive/*" -not -path "./venv/*" | while read file; do
  # Créer le répertoire parent dans archive si nécessaire
  mkdir -p "archive/$(dirname "$file")"
  mv "$file" "archive/$(dirname "$file")/"
  echo "Archivé: $file"
done

# Restaurer les fichiers essentiels
cp -r temp_essential/* .

# Supprimer le répertoire temporaire
rm -rf temp_essential

echo "Nettoyage terminé. Les fichiers non essentiels ont été déplacés dans le dossier 'archive'."
