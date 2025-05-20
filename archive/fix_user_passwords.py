import psycopg2
import bcrypt
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

# Fonction pour hasher un mot de passe
def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

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
    
    # Utilisateurs avec leurs mots de passe en clair
    users_to_update = [
        {"email": "admin@example.com", "password": "password123"},
        {"email": "user@example.com", "password": "password123"},
        {"email": "testing.admin@gilbert.fr", "password": "Gilbert2025!"},
        {"email": "nicolas@gilbert.fr", "password": "Gilbert2025!"}
    ]
    
    # Mettre u00e0 jour les mots de passe des utilisateurs
    for user in users_to_update:
        # Hasher le mot de passe
        hashed_password = hash_password(user["password"])
        
        # Mettre u00e0 jour l'utilisateur dans la base de donnu00e9es
        cursor.execute(
            "UPDATE users SET hashed_password = %s WHERE email = %s RETURNING id",
            (hashed_password, user["email"])
        )
        
        result = cursor.fetchone()
        if result:
            print(f"Mot de passe mis u00e0 jour pour l'utilisateur {user['email']} (ID: {result[0]})")
        else:
            print(f"Utilisateur {user['email']} non trouvé")
    
    # Valider les modifications
    conn.commit()
    
    # Vu00e9rifier les utilisateurs mis u00e0 jour
    cursor.execute("SELECT id, email FROM users")
    users = cursor.fetchall()
    print("\nListe des utilisateurs:")
    for user in users:
        print(f"ID: {user[0]}, Email: {user[1]}")
    
    print("\nMots de passe mis u00e0 jour avec succu00e8s!")
    
except Exception as e:
    print(f"Erreur: {e}")
    if 'conn' in locals():
        conn.rollback()
finally:
    # Fermer la connexion
    if 'conn' in locals():
        cursor.close()
        conn.close()
        print("Connexion fermu00e9e.")
