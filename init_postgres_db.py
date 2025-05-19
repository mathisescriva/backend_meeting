import os
import sys
import psycopg2
from dotenv import load_dotenv
from app.core.config import settings

# Charger les variables d'environnement
load_dotenv(".env.postgres")

def init_postgres_db():
    """
    Initialise la base de donnu00e9es PostgreSQL si elle n'existe pas du00e9ju00e0.
    """
    # Extraire les paramu00e8tres de connexion
    pg_user = settings.POSTGRES_USER
    pg_password = settings.POSTGRES_PASSWORD
    pg_host = settings.POSTGRES_SERVER
    pg_port = settings.POSTGRES_PORT
    pg_dbname = settings.POSTGRES_DB
    
    print(f"Tentative de connexion u00e0 PostgreSQL: {pg_host}:{pg_port}")
    
    try:
        # Connexion u00e0 la base de donnu00e9es PostgreSQL par du00e9faut (postgres)
        conn = psycopg2.connect(
            user=pg_user,
            password=pg_password,
            host=pg_host,
            port=pg_port,
            dbname="postgres"  # Se connecter u00e0 la base de donnu00e9es par du00e9faut
        )
        conn.autocommit = True  # Activer l'autocommit pour pouvoir cru00e9er une base de donnu00e9es
        cursor = conn.cursor()
        
        # Vu00e9rifier si la base de donnu00e9es existe du00e9ju00e0
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{pg_dbname}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Cru00e9ation de la base de donnu00e9es '{pg_dbname}'...")
            cursor.execute(f"CREATE DATABASE {pg_dbname}")
            print(f"Base de donnu00e9es '{pg_dbname}' cru00e9u00e9e avec succu00e8s.")
        else:
            print(f"La base de donnu00e9es '{pg_dbname}' existe du00e9ju00e0.")
        
        # Fermer la connexion u00e0 la base de donnu00e9es postgres
        cursor.close()
        conn.close()
        
        print("Initialisation de la base de donnu00e9es terminu00e9e.")
        return True
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la base de donnu00e9es PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    # Initialiser la base de donnu00e9es PostgreSQL
    success = init_postgres_db()
    
    if success:
        print("Vous pouvez maintenant exu00e9cuter l'application avec PostgreSQL.")
        print("Pour migrer les donnu00e9es de SQLite vers PostgreSQL, exu00e9cutez le script migrate_to_postgres.py.")
    else:
        print("Impossible d'initialiser la base de donnu00e9es PostgreSQL. Vu00e9rifiez vos paramu00e8tres de connexion.")
        sys.exit(1)
