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
    
    # Vu00e9rifier la structure de la table users
    cursor.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'users'
    ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    print("Structure de la table users:")
    for col in columns:
        print(f"  {col[0]}: {col[1]}" + (f" (max length: {col[2]})" if col[2] else ""))
    
    # Vu00e9rifier les utilisateurs avec l'ID 1 (avec diffeu00e9rentes approches)
    print("\nRecherche d'utilisateurs avec ID = 1:")
    
    # Approche 1: ID comme entier
    cursor.execute("SELECT id, email FROM users WHERE id = 1")
    users = cursor.fetchall()
    print(f"  Approche 1 (id = 1): {users}")
    
    # Approche 2: ID comme chau00eene
    cursor.execute("SELECT id, email FROM users WHERE id = '1'")
    users = cursor.fetchall()
    print(f"  Approche 2 (id = '1'): {users}")
    
    # Approche 3: ID avec conversion explicite
    cursor.execute("SELECT id, email FROM users WHERE id::text = '1'")
    users = cursor.fetchall()
    print(f"  Approche 3 (id::text = '1'): {users}")
    
    # Approche 4: Tous les utilisateurs
    cursor.execute("SELECT id, email FROM users LIMIT 5")
    users = cursor.fetchall()
    print(f"  Approche 4 (tous les utilisateurs, max 5): {users}")
    
    # Vu00e9rifier la structure de la table meetings
    cursor.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_name = 'meetings'
    ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    print("\nStructure de la table meetings:")
    for col in columns:
        print(f"  {col[0]}: {col[1]}" + (f" (max length: {col[2]})" if col[2] else ""))
    
except Exception as e:
    print(f"Erreur: {str(e)}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
