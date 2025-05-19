import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import logging
from .postgres_adapter import get_db_connection, release_db_connection

# Configuration du logging
logger = logging.getLogger("postgres_queries")

def get_pending_transcriptions(max_age_hours=24):
    """Ru00e9cupu00e8re les transcriptions en attente qui ne sont pas trop anciennes (PostgreSQL)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # PostgreSQL utilise INTERVAL pour les opu00e9rations de date/heure
        cursor.execute(
            """
            SELECT * FROM meetings 
            WHERE transcript_status = 'pending' 
            AND created_at > NOW() - INTERVAL '%s hours'
            """,
            (max_age_hours,)
        )
        meetings = cursor.fetchall()
        return [dict(m) for m in meetings]
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des transcriptions en attente: {str(e)}")
        return []
    finally:
        release_db_connection(conn)

def get_meetings_by_status(status, max_age_hours=72):
    """Ru00e9cupu00e8re les ru00e9unions avec un statut spu00e9cifique qui ne sont pas trop anciennes (PostgreSQL)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # PostgreSQL utilise INTERVAL pour les opu00e9rations de date/heure
        cursor.execute(
            """
            SELECT * FROM meetings 
            WHERE transcript_status = %s 
            AND created_at > NOW() - INTERVAL '%s hours'
            ORDER BY created_at DESC
            """,
            (status, max_age_hours)
        )
        meetings = cursor.fetchall()
        return [dict(m) for m in meetings]
    except Exception as e:
        logger.error(f"Erreur lors de la ru00e9cupu00e9ration des ru00e9unions par statut: {str(e)}")
        return []
    finally:
        release_db_connection(conn)
