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
    
    # Vu00e9rifier les utilisateurs
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    
    # Ru00e9cupu00e9rer les noms des colonnes
    column_names = [desc[0] for desc in cursor.description]
    
    print('Colonnes de la table users:', column_names)
    print('\nUtilisateurs dans la base de donnu00e9es PostgreSQL:')
    for user in users:
        user_dict = dict(zip(column_names, user))
        print(user_dict)
    
except Exception as e:
    print(f"Erreur: {str(e)}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
