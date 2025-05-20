import psycopg2
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("inspect-db")

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
    
    # 1. Lister toutes les tables
    logger.info("Liste des tables dans la base de donnu00e9es:")
    cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
    """)
    tables = cursor.fetchall()
    for table in tables:
        logger.info(f"  {table[0]}")
    
    # 2. Examiner la structure de la table users
    logger.info("\nStructure de la table users:")
    cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'users'
    ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    for col in columns:
        logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
    
    # 3. Examiner la structure de la table meetings
    logger.info("\nStructure de la table meetings:")
    cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'meetings'
    ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    for col in columns:
        logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
    
    # 4. Vu00e9rifier les contraintes de la table users
    logger.info("\nContraintes de la table users:")
    cursor.execute("""
    SELECT conname, contype, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'users'::regclass
    """)
    constraints = cursor.fetchall()
    for con in constraints:
        logger.info(f"  {con[0]} ({con[1]}): {con[2]}")
    
    # 5. Vu00e9rifier les contraintes de la table meetings
    logger.info("\nContraintes de la table meetings:")
    cursor.execute("""
    SELECT conname, contype, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'meetings'::regclass
    """)
    constraints = cursor.fetchall()
    for con in constraints:
        logger.info(f"  {con[0]} ({con[1]}): {con[2]}")
    
    # 6. Vu00e9rifier les utilisateurs existants
    logger.info("\nUtilisateurs existants:")
    cursor.execute("SELECT id, email, full_name FROM users")
    users = cursor.fetchall()
    for user in users:
        logger.info(f"  ID: {user[0]} (type: {type(user[0])}), Email: {user[1]}, Nom: {user[2]}")
    
    # 7. Tester une requu00eate avec cast explicite
    logger.info("\nTest de requu00eate avec cast explicite:")
    cursor.execute("SELECT * FROM users WHERE id::text = %s", ('1',))
    user = cursor.fetchone()
    if user:
        logger.info(f"  Utilisateur trouvé avec ID '1' (cast en text): {user}")
    else:
        logger.info("  Aucun utilisateur trouvé avec ID '1' (cast en text)")
    
    # 8. Tester une requu00eate avec cast explicite inverse
    logger.info("Test de requu00eate avec cast explicite inverse:")
    try:
        cursor.execute("SELECT * FROM users WHERE id = %s::integer", ('1',))
        user = cursor.fetchone()
        if user:
            logger.info(f"  Utilisateur trouvé avec ID 1 (cast en integer): {user}")
        else:
            logger.info("  Aucun utilisateur trouvé avec ID 1 (cast en integer)")
    except Exception as e:
        logger.error(f"  Erreur lors de la requu00eate avec cast en integer: {str(e)}")
    
    # 9. Tester une requu00eate avec cast explicite des deux cu00f4tu00e9s
    logger.info("Test de requu00eate avec cast explicite des deux cu00f4tu00e9s:")
    try:
        cursor.execute("SELECT * FROM users WHERE id::text = %s::text", ('1',))
        user = cursor.fetchone()
        if user:
            logger.info(f"  Utilisateur trouvé avec ID '1' (cast des deux cu00f4tu00e9s): {user}")
        else:
            logger.info("  Aucun utilisateur trouvé avec ID '1' (cast des deux cu00f4tu00e9s)")
    except Exception as e:
        logger.error(f"  Erreur lors de la requu00eate avec cast des deux cu00f4tu00e9s: {str(e)}")
    
    # 10. Tester une requu00eate avec cast explicite en utilisant CAST
    logger.info("Test de requu00eate avec CAST:")
    try:
        cursor.execute("SELECT * FROM users WHERE CAST(id AS text) = %s", ('1',))
        user = cursor.fetchone()
        if user:
            logger.info(f"  Utilisateur trouvé avec ID '1' (CAST): {user}")
        else:
            logger.info("  Aucun utilisateur trouvé avec ID '1' (CAST)")
    except Exception as e:
        logger.error(f"  Erreur lors de la requu00eate avec CAST: {str(e)}")
    
    # 11. Tester une requu00eate avec paru00e9mu00e9trage direct
    logger.info("Test de requu00eate avec paru00e9mu00e9trage direct:")
    try:
        cursor.execute("SELECT * FROM users WHERE id = 1")
        user = cursor.fetchone()
        if user:
            logger.info(f"  Utilisateur trouvé avec ID 1 (direct): {user}")
        else:
            logger.info("  Aucun utilisateur trouvé avec ID 1 (direct)")
    except Exception as e:
        logger.error(f"  Erreur lors de la requu00eate directe: {str(e)}")
    
except Exception as e:
    logger.error(f"Erreur principale: {str(e)}")
finally:
    if 'conn' in locals() and conn:
        cursor.close()
        conn.close()
