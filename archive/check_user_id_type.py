import psycopg2
import os

# Paramu00e8tres de connexion PostgreSQL
db_params = {
    'dbname': os.getenv('POSTGRES_DB', 'meeting_transcriber'),
    'user': os.getenv('POSTGRES_USER', 'meeting_transcriber_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'rlpb7cswwmJ5egbYXW3U1FF78g9kN308'),
    'host': os.getenv('POSTGRES_SERVER', 'dpg-d0lfghogjchc73f1mvjg-a.oregon-postgres.render.com'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

try:
    # u00c9tablir la connexion u00e0 PostgreSQL
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    
    # Vu00e9rifier le type de donnu00e9es de la colonne id dans la table users
    cursor.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'id'
    """)
    column_info = cursor.fetchone()
    print(f"Colonne: {column_info[0]}, Type: {column_info[1]}, Longueur max: {column_info[2]}")
    
    # Vu00e9rifier l'utilisateur avec l'ID 1
    cursor.execute("SELECT id, email, full_name FROM users WHERE id = '1'")
    user = cursor.fetchone()
    if user:
        print(f"Utilisateur trouvé: ID={user[0]} (type: {type(user[0])}), Email={user[1]}, Nom={user[2]}")
    else:
        print("Aucun utilisateur avec l'ID '1' trouvé.")
    
    # Essayer avec une conversion explicite
    cursor.execute("SELECT id, email, full_name FROM users WHERE id::text = '1'")
    user = cursor.fetchone()
    if user:
        print(f"Utilisateur trouvé avec conversion explicite: ID={user[0]} (type: {type(user[0])}), Email={user[1]}, Nom={user[2]}")
    else:
        print("Aucun utilisateur avec l'ID '1' trouvé avec conversion explicite.")
    
except Exception as e:
    print(f"Erreur: {str(e)}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
