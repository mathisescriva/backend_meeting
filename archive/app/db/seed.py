from ..db.database import get_user_by_email_cached, create_user, get_password_hash
from loguru import logger
import sqlite3

def create_default_users():
    """
    Crée des utilisateurs par défaut si ils n'existent pas déjà dans la base de données.
    Cette fonction est appelée au démarrage de l'application.
    Gère les erreurs de contrainte d'unicité qui peuvent se produire lors du démarrage
    de plusieurs workers simultanément.
    """
    default_users = [
        {
            "email": "testing.admin@gilbert.fr",
            "password": "Gilbert2025!",
            "full_name": "Admin Test"
        },
        {
            "email": "nicolas@gilbert.fr",
            "password": "Gilbert2025!",
            "full_name": "Nicolas Gilbert"
        }
        # Ajoutez d'autres utilisateurs par défaut ici
    ]
    
    for user_data in default_users:
        try:
            # Vérifier si l'utilisateur existe déjà
            existing_user = get_user_by_email_cached(user_data["email"])
            
            if not existing_user:
                # Créer l'utilisateur
                hashed_password = get_password_hash(user_data["password"])
                
                user_dict = {
                    "email": user_data["email"],
                    "hashed_password": hashed_password,
                    "full_name": user_data["full_name"]
                }
                
                try:
                    new_user = create_user(user_dict)
                    logger.info(f"Utilisateur par défaut créé: {user_data['email']}")
                except sqlite3.IntegrityError:
                    # Un autre worker a probablement créé l'utilisateur entre temps
                    logger.info(f"L'utilisateur {user_data['email']} a déjà été créé par un autre processus")
            else:
                logger.info(f"L'utilisateur {user_data['email']} existe déjà")
        except Exception as e:
            # Ne pas faire échouer le démarrage de l'application si la création d'un utilisateur échoue
            logger.error(f"Erreur lors de la création de l'utilisateur {user_data['email']}: {str(e)}")
    
    logger.info("Vérification des utilisateurs par défaut terminée")
