import sqlite3
import os
from pathlib import Path
import bcrypt
import uuid
from datetime import datetime
import threading
import time

# Chemin de la base de données
# Utiliser le disque persistant Render si disponible, sinon utiliser le chemin par défaut
# Utilisation de /data comme chemin vers le disque persistant monté sur Render
RENDER_DISK_PATH = os.environ.get("RENDER_DISK_PATH", "/data")
DB_PATH = Path(RENDER_DISK_PATH) / "app.db" if os.path.exists(RENDER_DISK_PATH) else Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "app.db"

# Gestionnaire de connexions par thread pour SQLite
class ThreadLocalConnectionManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.local = threading.local()
        
    def get_connection(self):
        # Vérifier si ce thread a déjà une connexion
        if not hasattr(self.local, 'connection'):
            # Créer une nouvelle connexion pour ce thread avec un timeout plus long
            # et une configuration pour améliorer la gestion des verrous
            self.local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=60.0,  # Attendre jusqu'à 60 secondes pour les verrous
                isolation_level='IMMEDIATE'  # Réduire les conflits de verrous
            )
            self.local.connection.row_factory = sqlite3.Row
            
            # Configuration pour améliorer la performance et la stabilité
            self.local.connection.execute('PRAGMA journal_mode = WAL')  # Write-Ahead Logging pour de meilleures performances
            self.local.connection.execute('PRAGMA synchronous = NORMAL')  # Bon équilibre entre performance et sécurité
            self.local.connection.execute('PRAGMA busy_timeout = 30000')  # Attendre 30 secondes si la BD est occupée
            
        return self.local.connection
    
    def release_connection(self, conn):
        # Ne rien faire - la connexion reste attachée au thread
        pass
    
    def close_all(self):
        # Cette méthode n'est pas vraiment utilisée, mais on la garde pour compatibilité
        pass
        
    def close_thread_connection(self):
        # Fermer la connexion du thread actuel si elle existe
        if hasattr(self.local, 'connection'):
            try:
                self.local.connection.close()
            except Exception as e:
                print(f"Erreur lors de la fermeture de la connexion: {e}")
            finally:
                del self.local.connection

# Créer un gestionnaire de connexions par thread global
db_pool = ThreadLocalConnectionManager(DB_PATH)

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def get_db_connection():
    """Obtenir une connexion depuis le pool"""
    return db_pool.get_connection()

def release_db_connection(conn):
    """Libérer une connexion pour la réutiliser"""
    db_pool.release_connection(conn)

def reset_db_pool():
    """Réinitialiser le gestionnaire de connexions en cas de problème"""
    global db_pool
    db_pool.close_all()
    db_pool = ThreadLocalConnectionManager(DB_PATH)
    return True

def init_db():
    """Initialiser la base de données avec les tables nécessaires"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier si le chemin de la base de données est sur le disque persistant Render
        is_render_disk = os.path.exists(RENDER_DISK_PATH) and str(DB_PATH).startswith(RENDER_DISK_PATH)
        if is_render_disk:
            print(f"Base de données sur disque persistant Render: {DB_PATH}")
        else:
            print(f"Base de données locale: {DB_PATH}")
        
        # Vérifier si les tables existent déjà
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_table_exists = cursor.fetchone() is not None
        
        if not users_table_exists:
            cursor.execute("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT,
                full_name TEXT,
                profile_picture_url TEXT,
                oauth_provider TEXT,
                oauth_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("CREATE INDEX idx_user_email ON users(email)")
            cursor.execute("CREATE INDEX idx_user_oauth ON users(oauth_provider, oauth_id)")
            
        else:
            # Vérifier les colonnes existantes
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'profile_picture_url' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN profile_picture_url TEXT")
                print("Colonne profile_picture_url ajoutée à la table users")
                
            if 'oauth_provider' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN oauth_provider TEXT")
                print("Colonne oauth_provider ajoutée à la table users")
                
            if 'oauth_id' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN oauth_id TEXT")
                print("Colonne oauth_id ajoutée à la table users")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_oauth ON users(oauth_provider, oauth_id)")
                
            # Modifier la colonne hashed_password pour qu'elle soit nullable (pour les utilisateurs OAuth)
            # SQLite ne supporte pas ALTER COLUMN, on doit recréer la table si nécessaire
            cursor.execute("PRAGMA table_info(users)")
            columns_info = cursor.fetchall()
            hashed_password_nullable = False
            for col in columns_info:
                if col[1] == 'hashed_password' and col[3] == 0:  # col[3] est notnull (0 = nullable, 1 = not null)
                    hashed_password_nullable = True
                    break
            
            if not hashed_password_nullable:
                print("La colonne hashed_password doit être rendue nullable pour les utilisateurs OAuth")
                print("Veuillez exécuter une migration si nécessaire")
        
        # Création de la table meetings
        cursor.execute('''
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
        ''')
        
        # Vérifier si les colonnes summary_text et summary_status existent déjà
        cursor.execute("PRAGMA table_info(meetings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Ajouter les colonnes manquantes si nécessaire
        if 'summary_text' not in columns:
            cursor.execute("ALTER TABLE meetings ADD COLUMN summary_text TEXT")
            print("Colonne summary_text ajoutée à la table meetings")
            
        if 'summary_status' not in columns:
            cursor.execute("ALTER TABLE meetings ADD COLUMN summary_status TEXT DEFAULT NULL")
            print("Colonne summary_status ajoutée à la table meetings")
        
        # Création d'index pour améliorer les performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_meeting_user ON meetings(user_id)')
        
        # Vérifier si la colonne client_id existe déjà dans meetings
        cursor.execute("PRAGMA table_info(meetings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Ajouter la colonne client_id si elle n'existe pas
        if 'client_id' not in columns:
            cursor.execute("ALTER TABLE meetings ADD COLUMN client_id TEXT")
            print("Colonne client_id ajoutée à la table meetings")
            
        # Création de la table clients
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                summary_template TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Création d'index pour la table clients
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_client_user ON clients(user_id)')
        
        # Création de la table meeting_speakers pour les noms personnalisés des locuteurs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meeting_speakers (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                speaker_id TEXT NOT NULL,
                custom_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE,
                UNIQUE(meeting_id, speaker_id)
            )
        ''')
        
        # Création d'index pour la table meeting_speakers
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_speaker_meeting ON meeting_speakers(meeting_id)')
        
        conn.commit()
        print("Database initialized successfully")
    finally:
        if conn:
            release_db_connection(conn)

def create_user(user_data):
    """Créer un nouvel utilisateur (classique ou OAuth)"""
    user_id = str(uuid.uuid4())
    email = user_data.get("email")
    hashed_password = user_data.get("hashed_password")  # Peut être None pour OAuth
    full_name = user_data.get("full_name")
    profile_picture_url = user_data.get("profile_picture_url")
    oauth_provider = user_data.get("oauth_provider")
    oauth_id = user_data.get("oauth_id")
    created_at = datetime.utcnow().isoformat()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (id, email, hashed_password, full_name, profile_picture_url, 
               oauth_provider, oauth_id, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, email, hashed_password, full_name, profile_picture_url, 
             oauth_provider, oauth_id, created_at)
        )
        conn.commit()
        
        return {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "profile_picture_url": profile_picture_url,
            "oauth_provider": oauth_provider,
            "oauth_id": oauth_id,
            "created_at": created_at
        }
    finally:
        release_db_connection(conn)

def get_user_by_email(email):
    """Récupérer un utilisateur par son email"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if user:
            return dict(user)
        return None
    finally:
        release_db_connection(conn)

def get_user_by_id(user_id):
    """Récupérer un utilisateur par son ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            return dict(user)
        return None
    finally:
        release_db_connection(conn)

def update_user(user_id, update_data):
    """Mettre à jour les informations d'un utilisateur"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construire la requête de mise à jour dynamiquement
        placeholders = ", ".join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values())
        
        query = f"UPDATE users SET {placeholders} WHERE id = ?"
        cursor.execute(query, (*values, user_id))
        conn.commit()
        
        # Vider le cache pour cet utilisateur
        cache_key = f"user_id_{user_id}"
        if cache_key in user_cache:
            del user_cache[cache_key]
        
        # Récupérer l'utilisateur mis à jour
        return get_user_by_id(user_id)
    except Exception as e:
        print(f"Erreur lors de la mise à jour de l'utilisateur: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            release_db_connection(conn)

# Cache utilisateur (pour limiter les requêtes à la base de données)
user_cache = {}

# Fonctions avec cache pour les utilisateurs
def get_user_by_email_cached(email, max_age_seconds=60):
    """Version mise en cache de get_user_by_email"""
    current_time = time.time()
    cache_key = f"email:{email}"
    
    # Vérifier si l'utilisateur est dans le cache et si le cache est encore valide
    if cache_key in user_cache:
        timestamp, user = user_cache[cache_key]
        if current_time - timestamp < max_age_seconds:
            return user
    
    # Si pas dans le cache ou expiré, interroger la base de données
    user = get_user_by_email(email)
    
    # Mettre en cache si l'utilisateur existe
    if user:
        user_cache[cache_key] = (current_time, user)
    
    return user

def get_user_by_id_cached(user_id, max_age_seconds=300):
    """Version mise en cache de get_user_by_id"""
    current_time = time.time()
    cache_key = f"id:{user_id}"
    
    # Vérifier si l'utilisateur est dans le cache et si le cache est encore valide
    if cache_key in user_cache:
        timestamp, user = user_cache[cache_key]
        if current_time - timestamp < max_age_seconds:
            return user
    
    # Si pas dans le cache ou expiré, interroger la base de données
    user = get_user_by_id(user_id)
    
    # Mettre en cache si l'utilisateur existe
    if user:
        user_cache[cache_key] = (current_time, user)
    
    return user

def clear_user_cache():
    """Vider le cache utilisateur"""
    global user_cache
    user_cache = {}

def purge_old_entries_from_cache(max_age_seconds=600):
    """Purger les entrées de cache trop anciennes"""
    global user_cache
    current_time = time.time()
    
    user_cache = {
        k: v for k, v in user_cache.items() 
        if current_time - v[0] < max_age_seconds
    }

def get_user_by_oauth(oauth_provider, oauth_id):
    """Récupérer un utilisateur par ses identifiants OAuth"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE oauth_provider = ? AND oauth_id = ?", 
            (oauth_provider, oauth_id)
        )
        user = cursor.fetchone()
        
        if user:
            return dict(user)
        return None
    finally:
        release_db_connection(conn)

# Initialiser la base de données au démarrage
init_db()
