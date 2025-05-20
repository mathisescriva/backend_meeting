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
    
    # Vu00e9rifier les contraintes de clu00e9 u00e9trangu00e8re pour la table meetings
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
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name='meetings'
    """)
    
    constraints = cursor.fetchall()
    print('Contraintes de clu00e9 u00e9trangu00e8re pour la table meetings:')
    for constraint in constraints:
        print(f'Contrainte: {constraint[0]}')
        print(f'Table: {constraint[1]}')
        print(f'Colonne: {constraint[2]}')
        print(f'Table u00e9trangu00e8re: {constraint[3]}')
        print(f'Colonne u00e9trangu00e8re: {constraint[4]}')
        print('---')
    
    # Vu00e9rifier le type de donnu00e9es des colonnes id dans les tables users et meetings
    cursor.execute("""
    SELECT
        table_name,
        column_name,
        data_type
    FROM
        information_schema.columns
    WHERE
        (table_name = 'users' AND column_name = 'id')
        OR (table_name = 'meetings' AND column_name = 'user_id')
    """)
    
    columns = cursor.fetchall()
    print('\nTypes de donnu00e9es des colonnes id:')
    for column in columns:
        print(f'Table: {column[0]}, Colonne: {column[1]}, Type: {column[2]}')
    
except Exception as e:
    print(f"Erreur: {str(e)}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
