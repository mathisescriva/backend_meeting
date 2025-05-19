import sqlite3
import os
import sys
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from app.core.config import settings

# Charger les variables d'environnement
load_dotenv()

# Vu00e9rifier si la variable d'environnement DATABASE_URL est du00e9finie pour PostgreSQL
if not settings.DATABASE_URL.startswith('postgresql'):
    print("Erreur: La variable d'environnement DATABASE_URL doit u00eatre configuru00e9e pour PostgreSQL.")
    print("Format attendu: postgresql://user:password@host:port/dbname")
    sys.exit(1)

# Chemin vers la base de donnu00e9es SQLite
sqlite_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")

# Vu00e9rifier si la base de donnu00e9es SQLite existe
if not os.path.exists(sqlite_db_path):
    print(f"Erreur: La base de donnu00e9es SQLite n'existe pas u00e0 l'emplacement: {sqlite_db_path}")
    sys.exit(1)

# Connexion u00e0 la base de donnu00e9es SQLite
print("Connexion u00e0 la base de donnu00e9es SQLite...")
sqlite_conn = sqlite3.connect(sqlite_db_path)
sqlite_conn.row_factory = sqlite3.Row

# Extraire les paramu00e8tres de connexion PostgreSQL de DATABASE_URL
# Format: postgresql://user:password@host:port/dbname
try:
    # Utiliser les paramu00e8tres de configuration
    pg_user = settings.POSTGRES_USER
    pg_password = settings.POSTGRES_PASSWORD
    pg_host = settings.POSTGRES_SERVER
    pg_port = settings.POSTGRES_PORT
    pg_dbname = settings.POSTGRES_DB
    
    print(f"Connexion u00e0 PostgreSQL: {pg_host}:{pg_port}/{pg_dbname}")
    
    # Connexion u00e0 PostgreSQL
    pg_conn = psycopg2.connect(
        user=pg_user,
        password=pg_password,
        host=pg_host,
        port=pg_port,
        dbname=pg_dbname
    )
    pg_cursor = pg_conn.cursor()
    
    print("Connexion u00e0 PostgreSQL u00e9tablie avec succu00e8s.")
except Exception as e:
    print(f"Erreur lors de la connexion u00e0 PostgreSQL: {e}")
    sqlite_conn.close()
    sys.exit(1)

# Fonction pour cru00e9er les tables dans PostgreSQL
def create_tables():
    try:
        # Cru00e9er la table users
        pg_cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            profile_picture_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Cru00e9er l'index sur email
        pg_cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)")
        
        # Cru00e9er la table meetings
        pg_cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            file_url TEXT NOT NULL,
            transcript_text TEXT,
            transcript_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            duration_seconds INTEGER,
            speakers_count INTEGER,
            summary_text TEXT,
            summary_status TEXT DEFAULT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        # Cru00e9er l'index sur user_id
        pg_cursor.execute("CREATE INDEX IF NOT EXISTS idx_meeting_user ON meetings(user_id)")
        
        pg_conn.commit()
        print("Tables cru00e9u00e9es avec succu00e8s dans PostgreSQL.")
    except Exception as e:
        pg_conn.rollback()
        print(f"Erreur lors de la cru00e9ation des tables: {e}")
        raise e

# Fonction pour migrer les donnu00e9es de la table users
def migrate_users():
    try:
        # Ru00e9cupu00e9rer les utilisateurs depuis SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM users")
        users = sqlite_cursor.fetchall()
        
        if not users:
            print("Aucun utilisateur u00e0 migrer.")
            return
        
        # Pru00e9parer les donnu00e9es pour l'insertion
        users_data = []
        for user in users:
            user_dict = dict(user)
            users_data.append((
                user_dict['id'],
                user_dict['email'],
                user_dict['hashed_password'],
                user_dict.get('full_name'),
                user_dict.get('profile_picture_url'),
                user_dict.get('created_at')
            ))
        
        # Insu00e9rer les utilisateurs dans PostgreSQL
        execute_values(pg_cursor, """
        INSERT INTO users (id, email, hashed_password, full_name, profile_picture_url, created_at)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
        """, users_data)
        
        pg_conn.commit()
        print(f"{len(users_data)} utilisateurs migru00e9s avec succu00e8s.")
    except Exception as e:
        pg_conn.rollback()
        print(f"Erreur lors de la migration des utilisateurs: {e}")
        raise e

# Fonction pour migrer les donnu00e9es de la table meetings
def migrate_meetings():
    try:
        # Ru00e9cupu00e9rer les ru00e9unions depuis SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM meetings")
        meetings = sqlite_cursor.fetchall()
        
        if not meetings:
            print("Aucune ru00e9union u00e0 migrer.")
            return
        
        # Ru00e9cupu00e9rer tous les utilisateurs existants dans PostgreSQL pour vu00e9rifier les clu00e9s u00e9trangu00e8res
        pg_cursor.execute("SELECT id FROM users")
        valid_user_ids = set([row[0] for row in pg_cursor.fetchall()])
        
        print(f"Utilisateurs valides dans PostgreSQL: {len(valid_user_ids)}")
        
        # Pru00e9parer les donnu00e9es pour l'insertion
        meetings_data = []
        skipped_meetings = 0
        
        for meeting in meetings:
            meeting_dict = dict(meeting)
            user_id = meeting_dict['user_id']
            
            # Vu00e9rifier si l'utilisateur existe dans PostgreSQL
            if user_id not in valid_user_ids:
                print(f"Ignoru00e9 la ru00e9union {meeting_dict['id']} car l'utilisateur {user_id} n'existe pas dans PostgreSQL")
                skipped_meetings += 1
                continue
            
            meetings_data.append((
                meeting_dict['id'],
                user_id,
                meeting_dict['title'],
                meeting_dict['file_url'],
                meeting_dict.get('transcript_text'),
                meeting_dict.get('transcript_status', 'pending'),
                meeting_dict.get('created_at'),
                meeting_dict.get('duration_seconds'),
                meeting_dict.get('speakers_count'),
                meeting_dict.get('summary_text'),
                meeting_dict.get('summary_status')
            ))
        
        if not meetings_data:
            print("Aucune ru00e9union valide u00e0 migrer apru00e8s filtrage des clu00e9s u00e9trangu00e8res.")
            return
        
        # Insu00e9rer les ru00e9unions dans PostgreSQL
        execute_values(pg_cursor, """
        INSERT INTO meetings (id, user_id, title, file_url, transcript_text, transcript_status, created_at, 
                            duration_seconds, speakers_count, summary_text, summary_status)
        VALUES %s
        ON CONFLICT (id) DO NOTHING
        """, meetings_data)
        
        pg_conn.commit()
        print(f"{len(meetings_data)} ru00e9unions migru00e9es avec succu00e8s. {skipped_meetings} ru00e9unions ignoru00e9es.")
    except Exception as e:
        pg_conn.rollback()
        print(f"Erreur lors de la migration des ru00e9unions: {e}")
        raise e

# Exu00e9cuter la migration
try:
    print("Du00e9but de la migration des donnu00e9es de SQLite vers PostgreSQL...")
    
    # Cru00e9er les tables dans PostgreSQL
    create_tables()
    
    # Migrer les utilisateurs
    migrate_users()
    
    # Migrer les ru00e9unions
    migrate_meetings()
    
    print("Migration terminu00e9e avec succu00e8s!")
except Exception as e:
    print(f"Erreur lors de la migration: {e}")
finally:
    # Fermer les connexions
    sqlite_conn.close()
    pg_cursor.close()
    pg_conn.close()
    print("Connexions fermu00e9es.")
