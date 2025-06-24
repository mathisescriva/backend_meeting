# Configuration Google OAuth

## Étapes de configuration

### 1. Créer un projet Google Cloud

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez un projet existant
3. Activez l'API Google+ ou Google OAuth2

### 2. Configurer OAuth 2.0

1. Allez dans "APIs & Services" > "Credentials"
2. Cliquez sur "Create Credentials" > "OAuth 2.0 Client ID"
3. Sélectionnez "Web application"
4. Ajoutez les URI de redirection autorisées :
   - `http://localhost:8000/auth/google/callback` (développement)
   - `https://votre-domaine.com/auth/google/callback` (production)

### 3. Variables d'environnement

Ajoutez ces variables à votre fichier `.env` :

```env
# Configuration Google OAuth
GOOGLE_CLIENT_ID=votre-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=votre-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

### 4. Dépendances requises

Installez les dépendances supplémentaires :

```bash
pip install httpx
```

## Utilisation

### Côté Frontend

1. **Initier la connexion Google** :
   ```javascript
   const response = await fetch('/auth/google/login');
   const data = await response.json();
   
   // Rediriger vers Google
   window.location.href = data.auth_url;
   ```

2. **Traiter le callback** (après redirection de Google) :
   ```javascript
   // Récupérer le code et state depuis l'URL
   const urlParams = new URLSearchParams(window.location.search);
   const code = urlParams.get('code');
   const state = urlParams.get('state');
   
   // Envoyer au backend
   const response = await fetch('/auth/google/callback', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
     },
     body: JSON.stringify({
       code: code,
       state: state
     })
   });
   
   const data = await response.json();
   
   // Stocker le token JWT
   localStorage.setItem('access_token', data.access_token);
   ```

### Nouveaux endpoints disponibles

- `GET /auth/google/login` - Initie la connexion Google
- `POST /auth/google/callback` - Traite le callback de Google

## Fonctionnalités

- ✅ **Connexion automatique** : Création de compte si l'utilisateur n'existe pas
- ✅ **Gestion des conflits** : Vérifie si un compte existe déjà avec le même email
- ✅ **Récupération des données** : Email, nom, photo de profil depuis Google
- ✅ **Sécurité** : Utilisation de state tokens pour éviter les attaques CSRF
- ✅ **Compatibilité** : Fonctionne avec le système JWT existant

## Sécurité

- Les tokens d'état OAuth sont stockés temporairement en mémoire
- Pour la production, considérez l'utilisation de Redis pour le stockage des états
- Les secrets Google doivent être gardés confidentiels

## Test

Pour tester l'intégration :

1. Configurez vos variables d'environnement
2. Démarrez le serveur
3. Visitez `/auth/google/login` dans votre navigateur
4. Suivez le processus d'autorisation Google
5. Vous devriez être redirigé avec un token JWT valide 