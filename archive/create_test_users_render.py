import psycopg2
import bcrypt
import uuid
from datetime import datetime

# Informations de connexion PostgreSQL Render
PG_USER = "meeting_transcriber_user"
PG_PASSWORD = "rlpb7cswwmJ5egbYXW3U1FF78g9kN308"
PG_HOST = "dpg-d0lfghogjchc73f1mvjg-a.oregon-postgres.render.com"
PG_PORT = "5432"
PG_DBNAME = "meeting_transcriber"

# Fonction pour hasher un mot de passe
def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Utilisateurs de test
test_users = [
    {
        "email": "admin@example.com",
        "password": "password123",
        "full_name": "Admin User",
        "is_admin": True
    },
    {
        "email": "user@example.com",
        "password": "password123",
        "full_name": "Regular User",
        "is_admin": False
    }
]

# Connexion à PostgreSQL sur Render
try:
    print(f"Connexion à PostgreSQL Render: {PG_HOST}:{PG_PORT}/{PG_DBNAME}")
    
    # Connexion à PostgreSQL
    conn = psycopg2.connect(
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DBNAME
    )
    cursor = conn.cursor()
    print("Connexion à PostgreSQL établie avec succès.")
    
    # Vérifier si la table users existe, sinon la créer
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Créer la table meetings si elle n'existe pas
    cursor.execute("""
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
    
    conn.commit()
    print("Tables créées avec succès dans PostgreSQL.")
    
    # Créer les utilisateurs de test
    for user in test_users:
        # Vérifier si l'utilisateur existe déjà
        cursor.execute("SELECT id FROM users WHERE email = %s", (user["email"],))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"L'utilisateur {user['email']} existe déjà.")
        else:
            # Hasher le mot de passe
            hashed_password = hash_password(user["password"])
            
            # Insérer l'utilisateur
            cursor.execute("""
            INSERT INTO users (email, hashed_password, full_name, is_admin)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """, (
                user["email"],
                hashed_password,
                user["full_name"],
                user["is_admin"]
            ))
            
            user_id = cursor.fetchone()[0]
            print(f"Utilisateur {user['email']} créé avec l'ID {user_id}.")
    
    conn.commit()
    
    # Vérifier le nombre d'utilisateurs
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"Nombre total d'utilisateurs: {user_count}")
    
    # Lister tous les utilisateurs
    cursor.execute("SELECT id, email, full_name, is_admin FROM users")
    all_users = cursor.fetchall()
    print("\nListe des utilisateurs:")
    for user in all_users:
        print(f"ID: {user[0]}, Email: {user[1]}, Nom: {user[2]}, Admin: {user[3]}")
    
except Exception as e:
    print(f"Erreur: {e}")
finally:
    # Fermer la connexion
    if 'conn' in locals():
        cursor.close()
        conn.close()
        print("Connexion fermée.")
