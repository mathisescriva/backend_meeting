import psycopg2
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Informations de connexion PostgreSQL Render
PG_USER = "meeting_transcriber_user"
PG_PASSWORD = "rlpb7cswwmJ5egbYXW3U1FF78g9kN308"
PG_HOST = "dpg-d0lfghogjchc73f1mvjg-a.oregon-postgres.render.com"
PG_PORT = "5432"
PG_DBNAME = "meeting_transcriber"

# Connexion u00e0 PostgreSQL sur Render
try:
    print(f"Connexion u00e0 PostgreSQL Render: {PG_HOST}:{PG_PORT}/{PG_DBNAME}")
    
    # Connexion u00e0 PostgreSQL
    conn = psycopg2.connect(
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DBNAME
    )
    cursor = conn.cursor()
    print("Connexion u00e0 PostgreSQL u00e9tablie avec succu00e8s.")
    
    # Vu00e9rifier si les tables existent et les supprimer
    print("Suppression des tables existantes...")
    cursor.execute("DROP TABLE IF EXISTS meetings CASCADE")
    cursor.execute("DROP TABLE IF EXISTS users CASCADE")
    conn.commit()
    print("Tables supprimu00e9es avec succu00e8s.")
    
    # Cru00e9er la table users avec id comme SERIAL
    print("Cru00e9ation de la table users...")
    cursor.execute("""
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Cru00e9er la table meetings
    print("Cru00e9ation de la table meetings...")
    cursor.execute("""
    CREATE TABLE meetings (
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
    
    # Cru00e9er des utilisateurs de test
    print("Cru00e9ation des utilisateurs de test...")
    cursor.execute("""
    INSERT INTO users (email, hashed_password, full_name)
    VALUES 
    ('admin@example.com', '$2b$12$1YGSl6.3o/DpXQvZ/O8jdeyLYU5XXxD1ZyVQmM4Y4VIQsOo/CKbIa', 'Admin User'),
    ('user@example.com', '$2b$12$1YGSl6.3o/DpXQvZ/O8jdeyLYU5XXxD1ZyVQmM4Y4VIQsOo/CKbIa', 'Regular User'),
    ('testing.admin@gilbert.fr', '$2b$12$1YGSl6.3o/DpXQvZ/O8jdeyLYU5XXxD1ZyVQmM4Y4VIQsOo/CKbIa', 'Admin Test'),
    ('nicolas@gilbert.fr', '$2b$12$1YGSl6.3o/DpXQvZ/O8jdeyLYU5XXxD1ZyVQmM4Y4VIQsOo/CKbIa', 'Nicolas Gilbert')
    """)
    
    conn.commit()
    print("Utilisateurs de test cru00e9u00e9s avec succu00e8s.")
    
    # Lister les utilisateurs
    cursor.execute("SELECT id, email, full_name FROM users")
    users = cursor.fetchall()
    print("\nListe des utilisateurs:")
    for user in users:
        print(f"ID: {user[0]}, Email: {user[1]}, Nom: {user[2]}")
    
    print("\nStructure de la base de donnu00e9es corrigu00e9e avec succu00e8s!")
    
except Exception as e:
    print(f"Erreur: {e}")
finally:
    # Fermer la connexion
    if 'conn' in locals():
        cursor.close()
        conn.close()
        print("Connexion fermu00e9e.")
