import psycopg2
import os
from datetime import datetime
import bcrypt

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
    
    # Vu00e9rifier si l'utilisateur avec l'ID 1 existe du00e9ju00e0
    cursor.execute("SELECT COUNT(*) FROM users WHERE id = '1'")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print("L'utilisateur avec l'ID 1 existe du00e9ju00e0 dans la base de donnu00e9es PostgreSQL.")
    else:
        # Cru00e9er un mot de passe hashu00e9
        password = "password123"
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insu00e9rer l'utilisateur avec l'ID 1
        cursor.execute("""
            INSERT INTO users (id, email, hashed_password, full_name, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, ('1', 'admin@example.com', hashed_password, 'Admin User', datetime.utcnow()))
        
        conn.commit()
        print("Utilisateur avec l'ID 1 cru00e9u00e9 avec succu00e8s dans la base de donnu00e9es PostgreSQL.")
    
except Exception as e:
    print(f"Erreur: {str(e)}")
    if 'conn' in locals() and conn:
        conn.rollback()
finally:
    if 'conn' in locals() and conn:
        conn.close()
