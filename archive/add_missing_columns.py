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
    
    # Vu00e9rifier si la colonne transcript_content existe du00e9ju00e0
    cursor.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'meetings' AND column_name = 'transcript_content'
    """)
    column_exists = cursor.fetchone()
    
    if column_exists:
        print("La colonne 'transcript_content' existe du00e9ju00e0 dans la table 'meetings'.")
    else:
        # Ajouter la colonne manquante
        cursor.execute("ALTER TABLE meetings ADD COLUMN transcript_content TEXT")
        conn.commit()
        print("La colonne 'transcript_content' a u00e9tu00e9 ajoutu00e9e u00e0 la table 'meetings'.")
    
    # Vu00e9rifier si la colonne transcript_summary existe du00e9ju00e0
    cursor.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'meetings' AND column_name = 'transcript_summary'
    """)
    column_exists = cursor.fetchone()
    
    if column_exists:
        print("La colonne 'transcript_summary' existe du00e9ju00e0 dans la table 'meetings'.")
    else:
        # Ajouter la colonne manquante
        cursor.execute("ALTER TABLE meetings ADD COLUMN transcript_summary TEXT")
        conn.commit()
        print("La colonne 'transcript_summary' a u00e9tu00e9 ajoutu00e9e u00e0 la table 'meetings'.")
    
    # Vu00e9rifier si la colonne transcript_key_points existe du00e9ju00e0
    cursor.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'meetings' AND column_name = 'transcript_key_points'
    """)
    column_exists = cursor.fetchone()
    
    if column_exists:
        print("La colonne 'transcript_key_points' existe du00e9ju00e0 dans la table 'meetings'.")
    else:
        # Ajouter la colonne manquante
        cursor.execute("ALTER TABLE meetings ADD COLUMN transcript_key_points TEXT")
        conn.commit()
        print("La colonne 'transcript_key_points' a u00e9tu00e9 ajoutu00e9e u00e0 la table 'meetings'.")
    
    # Vu00e9rifier si la colonne transcript_action_items existe du00e9ju00e0
    cursor.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'meetings' AND column_name = 'transcript_action_items'
    """)
    column_exists = cursor.fetchone()
    
    if column_exists:
        print("La colonne 'transcript_action_items' existe du00e9ju00e0 dans la table 'meetings'.")
    else:
        # Ajouter la colonne manquante
        cursor.execute("ALTER TABLE meetings ADD COLUMN transcript_action_items TEXT")
        conn.commit()
        print("La colonne 'transcript_action_items' a u00e9tu00e9 ajoutu00e9e u00e0 la table 'meetings'.")
    
    # Vu00e9rifier la structure finale de la table meetings
    cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'meetings'
    ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    print("\nStructure finale de la table meetings:")
    for col in columns:
        print(f"  {col[0]}: {col[1]}")
    
except Exception as e:
    print(f"Erreur: {str(e)}")
    if 'conn' in locals() and conn:
        conn.rollback()
finally:
    if 'conn' in locals() and conn:
        conn.close()
