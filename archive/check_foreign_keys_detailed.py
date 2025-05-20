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
    
    # Vu00e9rifier les contraintes de clu00e9 u00e9trangu00e8re
    cursor.execute("""
    SELECT
        tc.constraint_name,
        tc.table_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM
        information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
    """)
    
    constraints = cursor.fetchall()
    print("\nContraintes de clu00e9 u00e9trangu00e8re:")
    for constraint in constraints:
        print(f"  {constraint[0]}: {constraint[1]}.{constraint[2]} -> {constraint[3]}.{constraint[4]}")
    
    # Vu00e9rifier les utilisateurs
    cursor.execute("SELECT id, email FROM users ORDER BY id LIMIT 10")
    users = cursor.fetchall()
    print("\nUtilisateurs (max 10):")
    for user in users:
        print(f"  ID: {user[0]} (type: {type(user[0])}), Email: {user[1]}")
    
    # Vu00e9rifier les ru00e9unions
    cursor.execute("SELECT id, user_id, title FROM meetings ORDER BY created_at DESC LIMIT 5")
    meetings = cursor.fetchall()
    print("\nRu00e9unions (max 5):")
    for meeting in meetings:
        print(f"  ID: {meeting[0]}, User ID: {meeting[1]} (type: {type(meeting[1])}), Title: {meeting[2]}")
    
    # Tester l'insertion directe d'une ru00e9union avec l'ID utilisateur 1
    print("\nTest d'insertion directe d'une ru00e9union avec l'ID utilisateur 1:")
    try:
        cursor.execute("""
        INSERT INTO meetings (id, user_id, title, file_url, transcript_status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """, ('test_id_' + os.urandom(4).hex(), 1, 'Test Meeting', '/test/file.mp3', 'pending', '2025-05-19 15:00:00'))
        
        result = cursor.fetchone()
        print(f"  Insertion ru00e9ussie avec l'ID: {result[0]}")
        conn.rollback()  # Annuler l'insertion pour ne pas modifier la base de donnu00e9es
    except Exception as e:
        print(f"  Erreur lors de l'insertion: {str(e)}")
        conn.rollback()
    
    # Tester l'insertion directe d'une ru00e9union avec l'ID utilisateur 1 (avec conversion explicite)
    print("\nTest d'insertion directe d'une ru00e9union avec l'ID utilisateur 1 (avec conversion explicite):")
    try:
        cursor.execute("""
        INSERT INTO meetings (id, user_id, title, file_url, transcript_status, created_at)
        VALUES (%s, %s::integer, %s, %s, %s, %s)
        RETURNING id
        """, ('test_id_' + os.urandom(4).hex(), '1', 'Test Meeting', '/test/file.mp3', 'pending', '2025-05-19 15:00:00'))
        
        result = cursor.fetchone()
        print(f"  Insertion ru00e9ussie avec l'ID: {result[0]}")
        conn.rollback()  # Annuler l'insertion pour ne pas modifier la base de donnu00e9es
    except Exception as e:
        print(f"  Erreur lors de l'insertion: {str(e)}")
        conn.rollback()
    
except Exception as e:
    print(f"Erreur: {str(e)}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
