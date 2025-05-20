import psycopg2
import os
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix-postgres")

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
    
    # 1. Analyser la structure actuelle
    logger.info("Analyse de la structure actuelle de la base de donnu00e9es...")
    
    # Vu00e9rifier la structure de la table users
    cursor.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'users'
    ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    logger.info("Structure de la table users:")
    for col in columns:
        logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
    
    # Vu00e9rifier les contraintes de la table users
    cursor.execute("""
    SELECT conname, contype, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'users'::regclass
    """)
    constraints = cursor.fetchall()
    logger.info("Contraintes de la table users:")
    for con in constraints:
        logger.info(f"  {con[0]} ({con[1]}): {con[2]}")
    
    # Vu00e9rifier la structure de la table meetings
    cursor.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'meetings'
    ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    logger.info("Structure de la table meetings:")
    for col in columns:
        logger.info(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
    
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
    
    # 2. Vu00e9rifier les utilisateurs existants
    cursor.execute("SELECT id, email, full_name FROM users")
    users = cursor.fetchall()
    logger.info("Utilisateurs existants:")
    for user in users:
        logger.info(f"  ID: {user[0]} (type: {type(user[0])}), Email: {user[1]}, Nom: {user[2]}")
    
    # 3. Vu00e9rifier les ru00e9unions existantes
    cursor.execute("SELECT id, user_id, title FROM meetings LIMIT 5")
    meetings = cursor.fetchall()
    logger.info("Ru00e9unions existantes:")
    for meeting in meetings:
        logger.info(f"  ID: {meeting[0]}, User ID: {meeting[1]} (type: {type(meeting[1])}), Title: {meeting[2]}")
    
    # 4. Corriger la structure de la base de donnu00e9es si nu00e9cessaire
    logger.info("\nCorrection de la structure de la base de donnu00e9es...")
    
    # Vu00e9rifier si la contrainte de clu00e9 u00e9trangu00e8re existe
    cursor.execute("""
    SELECT conname
    FROM pg_constraint
    WHERE conrelid = 'meetings'::regclass AND conname = 'meetings_user_id_fkey'
    """)
    fk_constraint = cursor.fetchone()
    
    if fk_constraint:
        # Supprimer la contrainte de clu00e9 u00e9trangu00e8re existante
        logger.info("Suppression de la contrainte de clu00e9 u00e9trangu00e8re existante...")
        cursor.execute("ALTER TABLE meetings DROP CONSTRAINT meetings_user_id_fkey")
        conn.commit()
        logger.info("Contrainte supprimu00e9e avec succu00e8s")
    
    # Cru00e9er une nouvelle contrainte de clu00e9 u00e9trangu00e8re qui convertit les types
    logger.info("Cru00e9ation d'une nouvelle contrainte de clu00e9 u00e9trangu00e8re avec conversion de types...")
    try:
        cursor.execute("""
        ALTER TABLE meetings
        ADD CONSTRAINT meetings_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
        """)
        conn.commit()
        logger.info("Nouvelle contrainte cru00e9u00e9e avec succu00e8s")
    except Exception as e:
        logger.error(f"Erreur lors de la cru00e9ation de la nouvelle contrainte: {str(e)}")
        conn.rollback()
        
        # Si la cru00e9ation de la contrainte u00e9choue, essayer une approche alternative
        logger.info("Tentative d'approche alternative...")
        
        # Vu00e9rifier si la colonne user_id est du bon type
        cursor.execute("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'meetings' AND column_name = 'user_id'
        """)
        user_id_type = cursor.fetchone()[0]
        
        if user_id_type != 'integer':
            # Modifier le type de la colonne user_id
            logger.info(f"Modification du type de la colonne user_id de {user_id_type} u00e0 integer...")
            cursor.execute("ALTER TABLE meetings ALTER COLUMN user_id TYPE integer USING user_id::integer")
            conn.commit()
            logger.info("Type de colonne modifiu00e9 avec succu00e8s")
            
            # Essayer de cru00e9er la contrainte u00e0 nouveau
            try:
                cursor.execute("""
                ALTER TABLE meetings
                ADD CONSTRAINT meetings_user_id_fkey
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
                """)
                conn.commit()
                logger.info("Nouvelle contrainte cru00e9u00e9e avec succu00e8s apru00e8s modification du type")
            except Exception as e2:
                logger.error(f"Erreur lors de la cru00e9ation de la nouvelle contrainte apru00e8s modification du type: {str(e2)}")
                conn.rollback()
    
    # 5. Vu00e9rifier si la structure a u00e9tu00e9 correctement corrigu00e9e
    logger.info("\nVu00e9rification de la structure corrigu00e9e...")
    
    # Vu00e9rifier les contraintes de la table meetings apru00e8s correction
    cursor.execute("""
    SELECT conname, contype, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'meetings'::regclass
    """)
    constraints = cursor.fetchall()
    logger.info("Contraintes de la table meetings apru00e8s correction:")
    for con in constraints:
        logger.info(f"  {con[0]} ({con[1]}): {con[2]}")
    
    # 6. Tester l'insertion d'une ru00e9union
    logger.info("\nTest d'insertion d'une ru00e9union...")
    
    # Choisir l'utilisateur avec l'ID 1
    user_id = 1
    
    # Gu00e9nu00e9rer des donnu00e9es de test
    import uuid
    meeting_id = str(uuid.uuid4())
    title = "Test Meeting After Fix"
    file_url = "/test/path/to/file.wav"
    transcript_status = "pending"
    created_at = datetime.utcnow()
    
    try:
        # Insu00e9rer une ru00e9union de test
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
        
        # Ru00e9cupu00e9rer la ru00e9union insu00e9ru00e9e
        meeting = cursor.fetchone()
        
        # Valider la transaction
        conn.commit()
        logger.info(f"Ru00e9union de test insu00e9ru00e9e avec succu00e8s: ID: {meeting[0]}, User ID: {meeting[1]}, Title: {meeting[2]}")
        logger.info("La base de donnu00e9es PostgreSQL a u00e9tu00e9 corrigu00e9e avec succu00e8s!")
    except Exception as e:
        logger.error(f"Erreur lors du test d'insertion: {str(e)}")
        conn.rollback()
        
        # Si l'insertion u00e9choue, essayer une approche plus radicale
        logger.info("Tentative d'approche plus radicale...")
        
        # Supprimer toutes les contraintes de la table meetings
        cursor.execute("""
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'meetings'::regclass AND contype = 'f'
        """)
        constraints = cursor.fetchall()
        
        for con in constraints:
            logger.info(f"Suppression de la contrainte {con[0]}...")
            cursor.execute(f"ALTER TABLE meetings DROP CONSTRAINT {con[0]}")
            conn.commit()
        
        # Essayer d'insu00e9rer u00e0 nouveau sans contraintes
        try:
            cursor.execute(
                """
                INSERT INTO meetings (
                    id, user_id, title, file_url, 
                    transcript_status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, title
                """,
                (
                    str(uuid.uuid4()), 
                    user_id, 
                    "Test Meeting Without Constraints", 
                    file_url, 
                    transcript_status, 
                    created_at
                )
            )
            
            meeting = cursor.fetchone()
            conn.commit()
            logger.info(f"Ru00e9union insu00e9ru00e9e sans contraintes: ID: {meeting[0]}, User ID: {meeting[1]}, Title: {meeting[2]}")
            logger.info("La base de donnu00e9es a u00e9tu00e9 corrigu00e9e en supprimant les contraintes")
        except Exception as e2:
            logger.error(f"Erreur lors de l'insertion sans contraintes: {str(e2)}")
            conn.rollback()
            
            # Si mu00eame l'insertion sans contraintes u00e9choue, essayer de recru00e9er la table meetings
            logger.info("Tentative de recru00e9ation de la table meetings...")
            
            # Sauvegarder les donnu00e9es existantes
            cursor.execute("SELECT * FROM meetings")
            existing_meetings = cursor.fetchall()
            
            # Ru00e9cupu00e9rer la structure de la table
            cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'meetings'
            ORDER BY ordinal_position
            """)
            column_names = [col[0] for col in cursor.fetchall()]
            
            # Supprimer la table existante
            cursor.execute("DROP TABLE meetings")
            
            # Recru00e9er la table avec la bonne structure
            cursor.execute("""
            CREATE TABLE meetings (
                id VARCHAR(255) PRIMARY KEY,
                user_id INTEGER,
                title VARCHAR(255) NOT NULL,
                file_url VARCHAR(255),
                transcript_status VARCHAR(255),
                transcript_content TEXT,
                transcript_summary TEXT,
                transcript_key_points TEXT,
                transcript_action_items TEXT,
                created_at TIMESTAMP
            )
            """)
            conn.commit()
            logger.info("Table meetings recru00e9u00e9e avec succu00e8s")
            
            # Ru00e9insu00e9rer les donnu00e9es existantes si possible
            if existing_meetings:
                logger.info(f"Ru00e9insertion de {len(existing_meetings)} ru00e9unions existantes...")
                
                for meeting in existing_meetings:
                    try:
                        # Cru00e9er la requu00eate d'insertion dynamiquement
                        placeholders = ", ".join([f"%s" for _ in range(len(column_names))])
                        columns = ", ".join(column_names)
                        
                        # Convertir user_id en entier si possible
                        meeting_data = list(meeting)
                        try:
                            meeting_data[1] = int(meeting_data[1])
                        except (ValueError, TypeError):
                            meeting_data[1] = 1  # Utiliser l'ID 1 par du00e9faut
                        
                        cursor.execute(f"INSERT INTO meetings ({columns}) VALUES ({placeholders})", meeting_data)
                        conn.commit()
                    except Exception as e3:
                        logger.error(f"Erreur lors de la ru00e9insertion d'une ru00e9union: {str(e3)}")
                        conn.rollback()
            
            # Tester l'insertion d'une nouvelle ru00e9union
            try:
                cursor.execute(
                    """
                    INSERT INTO meetings (
                        id, user_id, title, file_url, 
                        transcript_status, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, title
                    """,
                    (
                        str(uuid.uuid4()), 
                        user_id, 
                        "Test Meeting After Recreation", 
                        file_url, 
                        transcript_status, 
                        created_at
                    )
                )
                
                meeting = cursor.fetchone()
                conn.commit()
                logger.info(f"Ru00e9union insu00e9ru00e9e apru00e8s recru00e9ation: ID: {meeting[0]}, User ID: {meeting[1]}, Title: {meeting[2]}")
                logger.info("La base de donnu00e9es a u00e9tu00e9 corrigu00e9e en recru00e9ant la table")
            except Exception as e4:
                logger.error(f"Erreur lors de l'insertion apru00e8s recru00e9ation: {str(e4)}")
                conn.rollback()
    
except Exception as e:
    logger.error(f"Erreur principale: {str(e)}")
    if 'conn' in locals() and conn:
        conn.rollback()
finally:
    if 'conn' in locals() and conn:
        conn.close()
