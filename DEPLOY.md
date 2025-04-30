# Guide de déploiement sur Render

Ce guide explique comment déployer l'application Meeting Transcriber Backend sur Render.

## Prérequis

- Un compte Render (https://render.com)
- Un compte GitHub avec accès au dépôt
- Les clés API nécessaires (AssemblyAI, Mistral AI)

## Étapes de déploiement

1. **Connectez-vous à Render** et créez un nouveau Web Service

2. **Connectez votre dépôt GitHub**
   - Sélectionnez le dépôt `backend_meeting`
   - Choisissez la branche `production`

3. **Configurez le service**
   - Nom : `meeting-transcriber-api` (ou un nom de votre choix)
   - Environnement : Python
   - Région : Choisissez la plus proche de vos utilisateurs
   - Plan : Free (pour les tests) ou Individual (pour la production)

4. **Variables d'environnement**
   Ajoutez les variables d'environnement suivantes :
   - `ASSEMBLYAI_API_KEY` : Votre clé API AssemblyAI
   - `MISTRAL_API_KEY` : Votre clé API Mistral
   - `JWT_SECRET` : Une chaîne aléatoire pour sécuriser les tokens JWT
   - `ENVIRONMENT` : `production`

5. **Déployez !**
   - Cliquez sur "Create Web Service"
   - Render va automatiquement déployer votre application

## Limitations du plan gratuit

- Mise en veille après 15 minutes d'inactivité
- Temps de démarrage à froid (30-45 secondes) après une période d'inactivité
- 512 MB de RAM
- Stockage limité

## Adaptation du frontend

Pour que votre frontend communique avec cette API déployée :

1. Mettez à jour l'URL de base de l'API dans votre frontend :
   ```javascript
   // Exemple avec React
   const API_URL = process.env.REACT_APP_API_URL || 'https://votre-app.onrender.com';
   ```

2. Assurez-vous que CORS est correctement configuré dans le backend pour accepter les requêtes de votre frontend.

## Maintenance

Pour mettre à jour l'application déployée :

1. Fusionnez les changements de la branche principale vers la branche `production`
2. Render déploiera automatiquement les changements

## Passage à un plan payant

Si vous avez besoin de plus de performances ou de fiabilité :

1. Passez au plan "Individual" ($7/mois)
2. Envisagez d'ajouter une base de données PostgreSQL ($7/mois)
