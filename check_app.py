from main import app

# Imprimer toutes les routes disponibles
print("Routes disponibles :")
for route in app.routes:
    print(f"Route : {route.path}, méthodes : {route.methods if hasattr(route, 'methods') else 'N/A'}, nom : {route.name if hasattr(route, 'name') else 'N/A'}")

# Vérifier spécifiquement les routes d'authentification
auth_routes = [route for route in app.routes if route.path.startswith("/auth")]
print("\nRoutes d'authentification :")
for route in auth_routes:
    print(f"Route : {route.path}, méthodes : {route.methods if hasattr(route, 'methods') else 'N/A'}, nom : {route.name if hasattr(route, 'name') else 'N/A'}")
