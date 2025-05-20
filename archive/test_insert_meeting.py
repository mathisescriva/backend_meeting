import psycopg2
import os
import uuid
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-insert")

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
    
    # Vu00e9rifier les utilisateurs existants
    logger.info("Utilisateurs existants:")
    cursor.execute("SELECT id, email, full_name FROM users")
    users = cursor.fetchall()
    for user in users:
        logger.info(f"  ID: {user[0]} (type: {type(user[0])}), Email: {user[1]}, Nom: {user[2]}")
    
    # Choisir l'utilisateur avec l'ID 1
    user_id = 1
    logger.info(f"\nTentative d'insertion d'une ru00e9union pour l'utilisateur avec ID: {user_id}")
    
    # Gu00e9nu00e9rer un ID unique pour la ru00e9union
    meeting_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    title = "Test Meeting Insert"
    file_url = "/test/path/to/file.wav"
    transcript_status = "pending"
    
    # Exu00e9cuter la requu00eate d'insertion
    logger.info(f"Insertion de la ru00e9union {meeting_id} dans la base de donnu00e9es PostgreSQL")
    cursor.execute(
        """
        INSERT INTO meetings (
            id, user_id, title, file_url, 
            transcript_status, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, user_id, title
        """,
        (
            meeting_id, 
            user_id, 
            title, 
            file_url, 
            transcript_status, 
            created_at
        )
    )
    
    # Ru00e9cupu00e9rer la ru00e9union cru00e9u00e9e
    meeting = cursor.fetchone()
    
    # Valider la transaction
    conn.commit()
    logger.info(f"Ru00e9union {meeting_id} cru00e9u00e9e avec succu00e8s dans PostgreSQL")
    logger.info(f"Ru00e9union cru00e9u00e9e: ID: {meeting[0]}, User ID: {meeting[1]}, Title: {meeting[2]}")
    
except Exception as e:
    logger.error(f"Erreur: {str(e)}")
    if 'conn' in locals() and conn:
        conn.rollback()
    
    # Vu00e9rifier si c'est une erreur de contrainte de clu00e9 u00e9trangu00e8re
    if "violates foreign key constraint" in str(e):
        logger.error("Erreur de contrainte de clu00e9 u00e9trangu00e8re. Vu00e9rification des utilisateurs...")
        
        # Vu00e9rifier si l'utilisateur existe
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE id = %s", (user_id,))
            count = cursor.fetchone()[0]
            logger.info(f"Nombre d'utilisateurs avec ID {user_id}: {count}")
            
            # Vu00e9rifier les contraintes de la table meetings
            cursor.execute("""
            SELECT conname, contype, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'meetings'::regclass
            """)
            constraints = cursor.fetchall()
            logger.info("Contraintes de la table meetings:")
            for con in constraints:
                logger.info(f"  {con[0]} ({con[1]}): {con[2]}")
                
            # Vu00e9rifier le type de la colonne user_id dans la table meetings
            cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'meetings' AND column_name = 'user_id'
            """)
            column = cursor.fetchone()
            logger.info(f"Type de la colonne user_id dans meetings: {column[1]}")
        except Exception as inner_e:
            logger.error(f"Erreur lors de la vu00e9rification: {str(inner_e)}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
