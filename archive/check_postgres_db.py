import psycopg2
import os

# Paramètres de connexion PostgreSQL
db_params = {
    'dbname': os.getenv('POSTGRES_DB', 'meeting_transcriber'),
    'user': os.getenv('POSTGRES_USER', 'meeting_transcriber_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'rlpb7cswwmJ5egbYXW3U1FF78g9kN308'),
    'host': os.getenv('POSTGRES_SERVER', 'dpg-d0lfghogjchc73f1mvjg-a.oregon-postgres.render.com'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

try:
    # Établir la connexion à PostgreSQL
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    
    # Vérifier les colonnes de la table users
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position")
    columns = [col[0] for col in cursor.fetchall()]
    print('Colonnes de la table users:', columns)
    
    # Vérifier les utilisateurs
    cursor.execute('SELECT id, email FROM users')
    users = cursor.fetchall()
    
    print('\nUtilisateurs dans la base de données PostgreSQL:')
    for user in users:
        print(f'ID: {user[0]}, Email: {user[1]}')
    
    # Vérifier les réunions
    cursor.execute('SELECT id, user_id, title FROM meetings LIMIT 5')
    meetings = cursor.fetchall()
    
    print('\nRéunions dans la base de données PostgreSQL (max 5):')
    for meeting in meetings:
        print(f'ID: {meeting[0]}, User ID: {meeting[1]}, Title: {meeting[2]}')
    
except Exception as e:
    print(f"Erreur: {str(e)}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
