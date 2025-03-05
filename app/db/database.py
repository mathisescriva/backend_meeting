import sqlite3
import os
from pathlib import Path
import bcrypt
import uuid
from datetime import datetime

# Chemin de la base de données
DB_PATH = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "app.db"

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def get_db_connection():
    """Créer une connexion à la base de données SQLite"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialiser la base de données avec les tables nécessaires"""
    conn = get_db_connection()
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
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def create_user(user_data):
    """Créer un nouvel utilisateur"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    cursor.execute(
        "INSERT INTO users (id, email, hashed_password, full_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, user_data["email"], user_data["hashed_password"], user_data.get("full_name", ""), created_at)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "id": user_id,
        "email": user_data["email"],
        "full_name": user_data.get("full_name", ""),
        "created_at": created_at
    }

def get_user_by_email(email):
    """Récupérer un utilisateur par son email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)
    return None

def get_user_by_id(user_id):
    """Récupérer un utilisateur par son ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)
    return None

# Initialiser la base de données au démarrage
init_db()
