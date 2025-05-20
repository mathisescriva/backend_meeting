import sqlite3
import uuid
from datetime import datetime
from .database import get_db_connection, release_db_connection
import logging

def create_client(client_data, user_id):
    """Cru00e9er un nouveau client"""
    # Logger pour le du00e9bogage
    logger = logging.getLogger("fastapi")
    logger.info(f"Cru00e9ation d'un nouveau client pour l'utilisateur {user_id}")
    
    # Gu00e9nu00e9rer un ID unique pour le client
    client_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    conn = None
    client = None
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Obtenir une nouvelle connexion
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Exu00e9cuter la requu00eate d'insertion
            cursor.execute(
                """
                INSERT INTO clients (
                    id, user_id, name, summary_template, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    user_id,
                    client_data["name"],
                    client_data.get("summary_template"),
                    created_at
                )
            )
            
            # Valider la transaction immu00e9diatement
            conn.commit()
            logger.info(f"Client {client_id} cru00e9u00e9 avec succu00e8s")
            
            # Ru00e9cupu00e9rer le client cru00e9u00e9
            cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
            client = cursor.fetchone()
            
            # Si tout s'est bien passu00e9, sortir de la boucle
            break
            
        except sqlite3.OperationalError as e:
            # Gestion spu00e9cifique de l'erreur 'database is locked'
            if "database is locked" in str(e):
                retry_count += 1
                logger.warning(f"Base de donnu00e9es verrouilu00e9e, tentative {retry_count}/{max_retries}")
                
                # Attendre un peu avant de ru00e9essayer
                import time
                time.sleep(1)  # Attendre 1 seconde avant de ru00e9essayer
                
                # Fermer et ru00e9initialiser la connexion
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
            else:
                # Autres erreurs SQLite
                logger.error(f"Erreur SQLite lors de la cru00e9ation du client: {str(e)}")
                raise
        except Exception as e:
            # Autres erreurs non SQLite
            logger.error(f"Erreur lors de la cru00e9ation du client: {str(e)}")
            raise
        finally:
            # Libu00e9rer la connexion dans tous les cas
            if conn:
                release_db_connection(conn)
    
    return dict(client) if client else None

def get_client(client_id, user_id):
    """Ru00e9cupu00e9rer un client par son ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM clients WHERE id = ? AND user_id = ?", 
            (client_id, user_id)
        )
        client = cursor.fetchone()
        return dict(client) if client else None
    finally:
        release_db_connection(conn)

def get_clients(user_id):
    """Ru00e9cupu00e9rer tous les clients d'un utilisateur"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM clients WHERE user_id = ? ORDER BY name ASC", 
            (user_id,)
        )
        clients = cursor.fetchall()
        return [dict(client) for client in clients]
    finally:
        release_db_connection(conn)

def update_client(client_id, user_id, update_data):
    """Mettre u00e0 jour un client"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Vu00e9rifier si le client existe et appartient u00e0 l'utilisateur
        cursor.execute(
            "SELECT id FROM clients WHERE id = ? AND user_id = ?", 
            (client_id, user_id)
        )
        if not cursor.fetchone():
            return None
        
        # Construire la requu00eate de mise u00e0 jour dynamiquement
        update_fields = []
        params = []
        
        if "name" in update_data and update_data["name"]:
            update_fields.append("name = ?")
            params.append(update_data["name"])
            
        if "summary_template" in update_data:
            update_fields.append("summary_template = ?")
            params.append(update_data["summary_template"])
        
        if not update_fields:
            return get_client(client_id, user_id)  # Rien u00e0 mettre u00e0 jour
        
        # Construire et exu00e9cuter la requu00eate SQL
        query = f"UPDATE clients SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?"
        params.extend([client_id, user_id])
        
        cursor.execute(query, params)
        conn.commit()
        
        # Ru00e9cupu00e9rer le client mis u00e0 jour
        return get_client(client_id, user_id)
    finally:
        release_db_connection(conn)

def delete_client(client_id, user_id):
    """Supprimer un client"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Vu00e9rifier si le client existe et appartient u00e0 l'utilisateur
        cursor.execute(
            "SELECT id FROM clients WHERE id = ? AND user_id = ?", 
            (client_id, user_id)
        )
        if not cursor.fetchone():
            return False
        
        # Supprimer le client
        cursor.execute(
            "DELETE FROM clients WHERE id = ? AND user_id = ?", 
            (client_id, user_id)
        )
        
        conn.commit()
        return True
    finally:
        release_db_connection(conn)
