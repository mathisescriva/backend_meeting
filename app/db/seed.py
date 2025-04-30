from ..db.database import get_user_by_email_cached, create_user, get_password_hash
from loguru import logger

def create_default_users():
    """
    Crée des utilisateurs par défaut si ils n'existent pas déjà dans la base de données.
    Cette fonction est appelée au démarrage de l'application.
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
            
            new_user = create_user(user_dict)
            logger.info(f"Utilisateur par défaut créé: {user_data['email']}")
        else:
            logger.info(f"L'utilisateur {user_data['email']} existe déjà")
    
    logger.info("Vérification des utilisateurs par défaut terminée")
