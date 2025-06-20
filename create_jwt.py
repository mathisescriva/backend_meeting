import jwt
import datetime

# ID utilisateur obtenu précédemment
user_id = "2d53638f-d2db-4b72-9df1-d3d6817a9b08"

# Clé secrète du backend (doit être la même que celle utilisée dans le backend)
# Dans un contexte réel, ce serait stocké dans un .env et non en dur dans le code
secret_key = "super-secret-key-deve-only"

# Création des données du token
payload = {
    "sub": user_id,
    "exp": datetime.datetime.now() + datetime.timedelta(days=365)  # Expire dans 1 an
}

# Génération du token
token = jwt.encode(payload, secret_key, algorithm="HS256")

print(f"Token JWT pour l'utilisateur testing.admin@gilbert.fr:\n{token}")
