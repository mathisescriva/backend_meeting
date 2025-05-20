import sqlite3
import os
import sys
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from app.core.config import settings

# Charger les variables d'environnement
load_dotenv()

# Informations de connexion PostgreSQL Render
PG_USER = "meeting_transcriber_user"
PG_PASSWORD = "rlpb7cswwmJ5egbYXW3U1FF78g9kN308"
PG_HOST = "dpg-d0lfghogjchc73f1mvjg-a.oregon-postgres.render.com"
PG_PORT = "5432"
PG_DBNAME = "meeting_transcriber"

# Chemin vers la base de données SQLite
sqlite_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")

# Vérifier si la base de données SQLite existe
if not os.path.exists(sqlite_db_path):
    print(f"Erreur: La base de données SQLite n'existe pas à l'emplacement: {sqlite_db_path}")
    sys.exit(1)

# Connexion à la base de données SQLite
print("Connexion à la base de données SQLite...")
sqlite_conn = sqlite3.connect(sqlite_db_path)
sqlite_conn.row_factory = sqlite3.Row

# Connexion à PostgreSQL sur Render
try:
    print(f"Connexion à PostgreSQL Render: {PG_HOST}:{PG_PORT}/{PG_DBNAME}")
    
    # Connexion à PostgreSQL
    pg_conn = psycopg2.connect(
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DBNAME
    )
    pg_cursor = pg_conn.cursor()
    print("Connexion à PostgreSQL établie avec succès.")
    
except Exception as e:
    print(f"Erreur lors de la connexion à PostgreSQL: {e}")
    sqlite_conn.close()
    sys.exit(1)

# Fonction pour créer les tables dans PostgreSQL
def create_tables():
    # Créer la table users
    pg_cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Créer la table meetings
    pg_cursor.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id VARCHAR(255) PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title VARCHAR(255) NOT NULL,
        file_url VARCHAR(255),
        transcript_status VARCHAR(50) DEFAULT 'pending',
        transcript_content TEXT,
        transcript_summary TEXT,
        transcript_key_points TEXT,
        transcript_action_items TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    pg_conn.commit()
    print("Tables créées avec succès dans PostgreSQL.")

# Fonction pour migrer les données de la table users
def migrate_users():
    # Récupérer les utilisateurs depuis SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT * FROM users")
    users = sqlite_cursor.fetchall()
    
    # Insérer les utilisateurs dans PostgreSQL
    for user in users:
        try:
            pg_cursor.execute("""
            INSERT INTO users (id, email, hashed_password, full_name, is_admin, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """, (
                user['id'],
                user['email'],
                user['hashed_password'],
                user['full_name'],
                user['is_admin'],
                user['created_at']
            ))
        except Exception as e:
            print(f"Erreur lors de l'insertion de l'utilisateur {user['id']}: {e}")
    
    pg_conn.commit()
    
    # Vérifier le nombre d'utilisateurs migrés
    pg_cursor.execute("SELECT COUNT(*) FROM users")
    user_count = pg_cursor.fetchone()[0]
    print(f"{user_count} utilisateurs migrés avec succès.")

# Fonction pour vérifier les utilisateurs valides dans PostgreSQL
def get_valid_user_ids():
    pg_cursor.execute("SELECT id FROM users")
    return [row[0] for row in pg_cursor.fetchall()]

# Fonction pour migrer les données de la table meetings
def migrate_meetings():
    # Récupérer les réunions depuis SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT * FROM meetings")
    meetings = sqlite_cursor.fetchall()
    
    # Récupérer les IDs d'utilisateurs valides dans PostgreSQL
    valid_user_ids = get_valid_user_ids()
    print(f"Utilisateurs valides dans PostgreSQL: {len(valid_user_ids)}")
    
    # Insérer les réunions dans PostgreSQL
    meetings_migrated = 0
    meetings_ignored = 0
    
    for meeting in meetings:
        # Vérifier si l'utilisateur existe dans PostgreSQL
        if meeting['user_id'] not in valid_user_ids:
            print(f"Ignoré la réunion {meeting['id']} car l'utilisateur {meeting['user_id']} n'existe pas dans PostgreSQL")
            meetings_ignored += 1
            continue
        
        try:
            pg_cursor.execute("""
            INSERT INTO meetings (
                id, user_id, title, file_url, transcript_status, 
                transcript_content, transcript_summary, transcript_key_points, 
                transcript_action_items, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """, (
                meeting['id'],
                meeting['user_id'],
                meeting['title'],
                meeting['file_url'],
                meeting['transcript_status'],
                meeting.get('transcript_content'),
                meeting.get('transcript_summary'),
                meeting.get('transcript_key_points'),
                meeting.get('transcript_action_items'),
                meeting['created_at']
            ))
            meetings_migrated += 1
        except Exception as e:
            print(f"Erreur lors de l'insertion de la réunion {meeting['id']}: {e}")
    
    pg_conn.commit()
    print(f"{meetings_migrated} réunions migrées avec succès. {meetings_ignored} réunions ignorées.")

# Exécuter la migration
try:
    print("Début de la migration des données de SQLite vers PostgreSQL...")
    
    # Créer les tables
    create_tables()
    
    # Migrer les utilisateurs
    migrate_users()
    
    # Migrer les réunions
    migrate_meetings()
    
    print("Migration terminée avec succès!")
    
except Exception as e:
    print(f"Erreur lors de la migration: {e}")
    pg_conn.rollback()
finally:
    # Fermer les connexions
    pg_cursor.close()
    pg_conn.close()
    sqlite_conn.close()
    print("Connexions fermées.")
