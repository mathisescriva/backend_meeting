import sqlite3
import os
from pathlib import Path
import bcrypt
import uuid
from datetime import datetime
import threading
import time

# Chemin de la base de données
DB_PATH = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "app.db"

# Pool de connexions pour SQLite (simple mais efficace)
class ConnectionPool:
    def __init__(self, db_path, max_connections=10, timeout=30):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self.connections = []
        self.in_use = set()
        self.lock = threading.Lock()
        
    def get_connection(self):
        start_time = time.time()
        
        while True:
            with self.lock:
                # Vérifier les connexions disponibles
                for conn in self.connections:
                    if conn not in self.in_use:
                        self.in_use.add(conn)
                        return conn
                
                # Créer une nouvelle connexion si possible
                if len(self.connections) < self.max_connections:
                    conn = sqlite3.connect(str(self.db_path))
                    conn.row_factory = sqlite3.Row
                    self.connections.append(conn)
                    self.in_use.add(conn)
                    return conn
            
            # Attendre une connexion disponible
            if time.time() - start_time > self.timeout:
                raise TimeoutError("Impossible d'obtenir une connexion à la base de données")
            time.sleep(0.1)
    
    def release_connection(self, conn):
        with self.lock:
            if conn in self.in_use:
                self.in_use.remove(conn)
                
    def close_all(self):
        with self.lock:
            for conn in self.connections:
                try:
                    conn.close()
                except:
                    pass
            self.connections = []
            self.in_use = set()

# Créer un pool de connexions global
db_pool = ConnectionPool(DB_PATH, max_connections=50, timeout=60)

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
    """Réinitialiser le pool de connexions en cas de problème"""
    global db_pool
    db_pool.close_all()
    db_pool = ConnectionPool(DB_PATH, max_connections=50, timeout=60)
    return True

def init_db():
    """Initialiser la base de données avec les tables nécessaires"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Création de la table utilisateurs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Création d'index pour améliorer les performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_meeting_user ON meetings(user_id)')
        
        conn.commit()
        print("Database initialized successfully")
    finally:
        release_db_connection(conn)

def create_user(user_data):
    """Créer un nouvel utilisateur"""
    user_id = str(uuid.uuid4())
    email = user_data.get("email")
    hashed_password = user_data.get("hashed_password")
    full_name = user_data.get("full_name")
    created_at = datetime.utcnow().isoformat()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (id, email, hashed_password, full_name, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, hashed_password, full_name, created_at)
        )
        conn.commit()
        
        return {
            "id": user_id,
            "email": email,
            "full_name": full_name,
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

# Initialiser la base de données au démarrage
init_db()
