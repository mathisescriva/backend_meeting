import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Charger les variables d'environnement
os.environ['ENVIRONMENT'] = 'production'
load_dotenv('.env.local.postgres')

# Connexion à la base de données PostgreSQL
conn = psycopg2.connect(
    dbname=os.environ.get('POSTGRES_DB'),
    user=os.environ.get('POSTGRES_USER'),
    password=os.environ.get('POSTGRES_PASSWORD'),
    host=os.environ.get('POSTGRES_SERVER'),
    port=os.environ.get('POSTGRES_PORT')
)

# Créer un curseur
cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# Exécuter la requête
cursor.execute('SELECT * FROM users')

# Récupérer les résultats
users = cursor.fetchall()

# Afficher les résultats
print('Utilisateurs dans la base de données:')
for user in users:
    print(dict(user))

# Fermer la connexion
cursor.close()
conn.close()
