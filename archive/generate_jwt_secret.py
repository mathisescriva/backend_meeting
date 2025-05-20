import secrets
import base64

# Générer une clé secrète JWT sécurisée
jwt_secret = secrets.token_hex(32)  # 32 octets = 256 bits

print(f"JWT_SECRET={jwt_secret}")
