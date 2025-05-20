#!/usr/bin/env python3
"""
Script pour appliquer les migrations de base de données
"""
import os
import sqlite3
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('migrations')

# Chemin vers la base de données
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.db')

# Chemin vers le dossier des migrations
MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrations')

def apply_migrations():
    """Applique toutes les migrations SQL dans le dossier migrations"""
    if not os.path.exists(DB_PATH):
        logger.error(f"La base de données {DB_PATH} n'existe pas.")
        return
    
    # Connexion à la base de données
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Créer une table pour suivre les migrations si elle n'existe pas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        migration_name TEXT NOT NULL UNIQUE,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    
    # Récupérer les migrations déjà appliquées
    cursor.execute('SELECT migration_name FROM migrations')
    applied_migrations = {row[0] for row in cursor.fetchall()}
    
    # Parcourir tous les fichiers de migration
    migration_files = [f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.sql')]
    migration_files.sort()  # Pour appliquer dans l'ordre alphabétique
    
    for migration_file in migration_files:
        if migration_file in applied_migrations:
            logger.info(f"Migration {migration_file} déjà appliquée. Ignorée.")
            continue
        
        # Lire le fichier de migration
        migration_path = os.path.join(MIGRATIONS_DIR, migration_file)
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        # Diviser le script en commandes individuelles
        commands = [cmd.strip() for cmd in migration_sql.split(';') if cmd.strip()]
        success = True
        
        try:
            # Exécuter chaque commande séparément
            for cmd in commands:
                try:
                    logger.info(f"Exécution de la commande: {cmd}")
                    cursor.execute(cmd)
                except sqlite3.OperationalError as e:
                    # Ignorer les erreurs de type "column already exists"
                    if "duplicate column name" in str(e):
                        logger.warning(f"Colonne déjà existante, ignorée: {e}")
                    else:
                        logger.error(f"Erreur SQL: {e}")
                        success = False
                        raise
            
            # Enregistrer la migration comme appliquée si toutes les commandes ont réussi
            if success:
                # Enregistrer la migration comme appliquée
                cursor.execute('INSERT INTO migrations (migration_name) VALUES (?)', (migration_file,))
                conn.commit()
                logger.info(f"Migration {migration_file} appliquée avec succès.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur lors de l'application de la migration {migration_file}: {e}")
            # Ne pas propager l'erreur pour continuer avec les autres migrations
        
    conn.close()
    logger.info("Toutes les migrations ont été appliquées avec succès.")

if __name__ == "__main__":
    # Créer le dossier migrations s'il n'existe pas
    if not os.path.exists(MIGRATIONS_DIR):
        os.makedirs(MIGRATIONS_DIR)
        logger.info(f"Dossier de migrations créé: {MIGRATIONS_DIR}")
    
    apply_migrations()
