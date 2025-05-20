import psycopg2
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("check-user-table")

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
    logger.info("Structure de la table users:")
    cursor.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'users'
    ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    for col in columns:
        logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
    
    # Vu00e9rifier les utilisateurs existants
    logger.info("\nUtilisateurs existants:")
    cursor.execute("SELECT id, email, full_name FROM users")
    users = cursor.fetchall()
    for user in users:
        logger.info(f"  ID: {user[0]} (type: {type(user[0])}), Email: {user[1]}, Nom: {user[2]}")
    
    # Tester une requu00eate avec cast explicite
    logger.info("\nTest de requu00eate avec cast explicite:")
    cursor.execute("SELECT COUNT(*) FROM users WHERE id::text = %s", ('1',))
    count = cursor.fetchone()[0]
    logger.info(f"  Nombre d'utilisateurs avec ID '1' (cast en text): {count}")
    
    # Tester une requu00eate avec cast explicite inverse
    logger.info("Test de requu00eate avec cast inverse:")
    cursor.execute("SELECT COUNT(*) FROM users WHERE id = %s::integer", ('1',))
    count = cursor.fetchone()[0]
    logger.info(f"  Nombre d'utilisateurs avec ID 1 (cast en integer): {count}")
    
except Exception as e:
    logger.error(f"Erreur: {str(e)}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
