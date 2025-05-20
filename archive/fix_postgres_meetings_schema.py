#!/usr/bin/env python3
"""
Script pour vérifier et corriger la structure de la table meetings dans PostgreSQL
"""

import psycopg2
import os
import logging
from app.core.config import settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('postgres-schema-fixer')

# Paramètres de connexion PostgreSQL
db_params = {
    'dbname': settings.POSTGRES_DB,
    'user': settings.POSTGRES_USER,
    'password': settings.POSTGRES_PASSWORD,
    'host': settings.POSTGRES_SERVER,
    'port': settings.POSTGRES_PORT
}

def get_postgres_connection():
    try:
        conn = psycopg2.connect(**db_params)
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion à PostgreSQL: {str(e)}")
        raise e

def check_and_fix_meetings_schema():
    """Vérifie et corrige la structure de la table meetings dans PostgreSQL"""
    conn = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Vérifier les colonnes existantes dans la table meetings
        cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'meetings'
        ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        logger.info("Structure actuelle de la table 'meetings':")
        existing_columns = {}
        for col in columns:
            column_name, data_type = col
            existing_columns[column_name] = data_type
            logger.info(f"- {column_name} ({data_type})")
        
        # Définir les colonnes requises avec leurs types
        required_columns = {
            "id": "character varying",
            "user_id": "integer",
            "title": "character varying",
            "file_url": "character varying",
            "transcript_status": "character varying",
            "transcript_text": "text",
            "transcript_content": "text",
            "transcript_summary": "text",
            "transcript_key_points": "text",
            "transcript_action_items": "text",
            "created_at": "timestamp without time zone",
            "duration_seconds": "integer",
            "speakers_count": "integer",
            "summary_text": "text",
            "summary_status": "character varying"
        }
        
        # Vérifier et ajouter les colonnes manquantes
        for column_name, data_type in required_columns.items():
            if column_name not in existing_columns:
                logger.warning(f"❌ La colonne '{column_name}' n'existe PAS dans la table")
                
                # Ajouter la colonne manquante
                try:
                    logger.info(f"Ajout de la colonne '{column_name}' avec le type '{data_type}'")
                    cursor.execute(f"""
                    ALTER TABLE meetings
                    ADD COLUMN {column_name} {data_type}
                    """)
                    conn.commit()
                    logger.info(f"✅ Colonne '{column_name}' ajoutée avec succès")
                except Exception as e:
                    logger.error(f"Erreur lors de l'ajout de la colonne '{column_name}': {str(e)}")
                    conn.rollback()
            else:
                # Vérifier si le type de données correspond
                if existing_columns[column_name] != data_type:
                    logger.warning(f"⚠️ La colonne '{column_name}' a un type différent: {existing_columns[column_name]} (attendu: {data_type})")
                else:
                    logger.info(f"✅ La colonne '{column_name}' existe avec le bon type")
        
        # Vérifier à nouveau la structure après les modifications
        cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'meetings'
        ORDER BY ordinal_position
        """)
        updated_columns = cursor.fetchall()
        
        logger.info("\nStructure mise à jour de la table 'meetings':")
        for col in updated_columns:
            logger.info(f"- {col[0]} ({col[1]})")
            
    except Exception as e:
        logger.error(f"Erreur lors de la vérification/correction du schéma: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Vérification et correction de la structure de la table meetings dans PostgreSQL...")
    check_and_fix_meetings_schema()
    logger.info("Opération terminée")
