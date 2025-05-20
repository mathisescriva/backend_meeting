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
    
    # Vu00e9rifier si l'utilisateur existe
    cursor.execute("SELECT id, email, full_name FROM users")
    users = cursor.fetchall()
    
    print("\nUtilisateurs dans la base de donnu00e9es:")
    if users:
        for user in users:
            print(f"  ID: {user[0]}, Email: {user[1]}, Nom: {user[2]}")
    else:
        print("  Aucun utilisateur trouvé dans la base de données.")
    
    # Vu00e9rifier la structure de la table users
    cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'users'
    ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    print("\nStructure de la table users:")
    for col in columns:
        print(f"  {col[0]}: {col[1]}")
    
except Exception as e:
    print(f"Erreur: {str(e)}")
    if 'conn' in locals() and conn:
        conn.rollback()
finally:
    if 'conn' in locals() and conn:
        conn.close()
