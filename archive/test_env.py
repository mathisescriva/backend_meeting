import os
from dotenv import load_dotenv
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test-env')

# Charger les variables d'environnement
os.environ['ENVIRONMENT'] = 'production'
load_dotenv('.env.local.postgres')

# Afficher les variables d'environnement pour du00e9bogage
logger.info(f"POSTGRES_DB: {os.environ.get('POSTGRES_DB')}")
logger.info(f"POSTGRES_USER: {os.environ.get('POSTGRES_USER')}")
logger.info(f"POSTGRES_PASSWORD: {os.environ.get('POSTGRES_PASSWORD')}")
logger.info(f"POSTGRES_SERVER: {os.environ.get('POSTGRES_SERVER')}")
logger.info(f"POSTGRES_PORT: {os.environ.get('POSTGRES_PORT')}")
logger.info(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")
logger.info(f"ENVIRONMENT: {os.environ.get('ENVIRONMENT')}")
