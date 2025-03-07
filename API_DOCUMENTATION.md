# Documentation API - Meeting Transcriber

## Table des matières

1. [Introduction](#introduction)
2. [Authentification](#authentification)
   - [Inscription](#inscription)
   - [Connexion](#connexion)
   - [Obtenir les informations de l'utilisateur](#obtenir-les-informations-de-lutilisateur)
3. [Gestion des réunions](#gestion-des-réunions)
   - [Récupérer toutes les réunions](#récupérer-toutes-les-réunions)
   - [Récupérer une réunion spécifique](#récupérer-une-réunion-spécifique)
   - [Uploader un fichier audio](#uploader-un-fichier-audio)
   - [Mettre à jour une réunion](#mettre-à-jour-une-réunion)
   - [Supprimer une réunion](#supprimer-une-réunion)
   - [Relancer une transcription](#relancer-une-transcription)
   - [Récupérer uniquement la transcription](#récupérer-uniquement-la-transcription)
4. [Gestion du profil utilisateur](#gestion-du-profil-utilisateur)
   - [Obtenir les informations de profil](#obtenir-les-informations-de-profil)
   - [Mettre à jour le profil](#mettre-à-jour-le-profil)
   - [Télécharger une photo de profil](#télécharger-une-photo-de-profil)
   - [Changer le mot de passe](#changer-le-mot-de-passe)
5. [Formats et structures de données](#formats-et-structures-de-données)
6. [Codes d'erreur](#codes-derreur)
7. [Bonnes pratiques](#bonnes-pratiques)

## Introduction

L'API Meeting Transcriber permet de gérer des réunions avec transcription automatique d'audio. Elle utilise AssemblyAI pour transcrire les fichiers audio en texte.

**URL de base** : `http://localhost:8000`  
**Format de réponse** : JSON  
**Authentification** : JWT (JSON Web Token)

## Authentification

L'API utilise l'authentification par token JWT. Pour accéder aux endpoints protégés, vous devez inclure le token dans l'en-tête de vos requêtes.

### Inscription

Créer un nouvel utilisateur.

**URL** : `/auth/register`  
**Méthode** : `POST`  
**Authentification requise** : Non  
**Format de la requête** :

```json
{
  "email": "utilisateur@example.com",
  "password": "MotDePasse123Secure",
  "full_name": "Nom Complet"
}
```

**Exemple de réponse réussie** :

```json
{
  "message": "Utilisateur créé avec succès",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "utilisateur@example.com",
    "full_name": "Nom Complet",
    "created_at": "2025-03-06T10:30:22.123456"
  }
}
```

### Connexion

Authentifier un utilisateur et obtenir un token JWT.

**URL** : `/auth/login/json`  
**Méthode** : `POST`  
**Authentification requise** : Non  
**Format de la requête** :

```json
{
  "email": "utilisateur@example.com",
  "password": "MotDePasse123Secure"
}
```

**Exemple de réponse réussie** :

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Alternative** : Vous pouvez également utiliser `/auth/login` avec un formulaire HTML standard.

### Obtenir les informations de l'utilisateur

Récupérer les informations de l'utilisateur connecté.

**URL** : `/auth/me`  
**Méthode** : `GET`  
**Authentification requise** : Oui  
**Headers** :

```
Authorization: Bearer votre_token_jwt
```

**Exemple de réponse réussie** :

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "utilisateur@example.com",
  "full_name": "Nom Complet",
  "created_at": "2025-03-06T10:30:22.123456"
}
```

## Gestion des réunions

### Récupérer toutes les réunions

Liste toutes les réunions de l'utilisateur connecté.

**URL** : `/meetings/`  
**Méthode** : `GET`  
**Authentification requise** : Oui  
**Paramètres de requête** :
- `status` (optionnel) : Filtrer par statut de transcription (e.g., "pending", "completed", "error")

**Exemple de réponse réussie** :

```json
[
  {
    "id": "198868c7-ba07-402c-bbba-519f376b2471",
    "user_id": "2dafc076-4cbe-4000-b62e-60b8935746c4",
    "title": "Réunion d'équipe",
    "file_url": "/uploads/2dafc076-4cbe-4000-b62e-60b8935746c4/20250306_101833_tmp3k1mtfw1.wav",
    "transcript_text": null,
    "transcript_status": "completed",
    "created_at": "2025-03-06T09:18:33.313872",
    "duration_seconds": 300,
    "speakers_count": 2
  }
]
```

### Récupérer une réunion spécifique

Récupère les détails d'une réunion, y compris sa transcription.

**URL** : `/meetings/{meeting_id}`  
**Méthode** : `GET`  
**Authentification requise** : Oui  

**Exemple de réponse réussie** :

```json
{
  "id": "198868c7-ba07-402c-bbba-519f376b2471",
  "user_id": "2dafc076-4cbe-4000-b62e-60b8935746c4",
  "title": "Réunion d'équipe",
  "file_url": "/uploads/2dafc076-4cbe-4000-b62e-60b8935746c4/20250306_101833_tmp3k1mtfw1.wav",
  "transcript_text": "Bonjour à tous, aujourd'hui nous allons discuter du projet X...",
  "transcript_status": "completed",
  "created_at": "2025-03-06T09:18:33.313872",
  "duration_seconds": 300,
  "speakers_count": 2
}
```

### Uploader un fichier audio

Télécharge un fichier audio et lance sa transcription.

**URL** : `/meetings/upload`  
**Méthode** : `POST`  
**Authentification requise** : Oui  
**Content-Type** : `multipart/form-data`  
**Paramètres de requête** :
- `file` : Fichier audio (formats supportés : MP3, WAV)
- `title` (optionnel) : Titre de la réunion

**Exemple de réponse réussie** :

```json
{
  "id": "198868c7-ba07-402c-bbba-519f376b2471",
  "user_id": "2dafc076-4cbe-4000-b62e-60b8935746c4",
  "title": "Réunion d'équipe",
  "file_url": "/uploads/2dafc076-4cbe-4000-b62e-60b8935746c4/20250306_101833_tmp3k1mtfw1.wav",
  "transcript_text": null,
  "transcript_status": "pending",
  "created_at": "2025-03-06T09:18:33.313872",
  "duration_seconds": null,
  "speakers_count": null
}
```

### Mettre à jour une réunion

Met à jour les métadonnées d'une réunion.

**URL** : `/meetings/{meeting_id}`  
**Méthode** : `PUT`  
**Authentification requise** : Oui  
**Format de la requête** :

```json
{
  "title": "Nouveau titre de la réunion"
}
```

**Exemple de réponse réussie** :

```json
{
  "id": "198868c7-ba07-402c-bbba-519f376b2471",
  "user_id": "2dafc076-4cbe-4000-b62e-60b8935746c4",
  "title": "Nouveau titre de la réunion",
  "file_url": "/uploads/2dafc076-4cbe-4000-b62e-60b8935746c4/20250306_101833_tmp3k1mtfw1.wav",
  "transcript_text": "Bonjour à tous, aujourd'hui nous allons discuter du projet X...",
  "transcript_status": "completed",
  "created_at": "2025-03-06T09:18:33.313872",
  "duration_seconds": 300,
  "speakers_count": 2
}
```

### Supprimer une réunion

Supprime une réunion et ses données associées.

**URL** : `/meetings/{meeting_id}`  
**Méthode** : `DELETE`  
**Authentification requise** : Oui  

**Exemple de réponse réussie** :

```json
{
  "message": "Réunion supprimée avec succès"
}
```

### Relancer une transcription

Relance la transcription d'une réunion, utile si la transcription initiale a échoué.

**URL** : `/meetings/{meeting_id}/transcribe`  
**Méthode** : `POST`  
**Authentification requise** : Oui  

**Exemple de réponse réussie** :

```json
{
  "message": "Transcription relancée avec succès",
  "status": "pending"
}
```

### Récupérer uniquement la transcription

Récupère uniquement la transcription d'une réunion.

**URL** : `/meetings/{meeting_id}/transcript`  
**Méthode** : `GET`  
**Authentification requise** : Oui  

**Exemple de réponse réussie** :

```json
{
  "transcript_text": "Bonjour à tous, aujourd'hui nous allons discuter du projet X...",
  "transcript_status": "completed",
  "duration_seconds": 300,
  "speakers_count": 2
}
```

## Gestion du profil utilisateur

### Obtenir les informations de profil

Récupère les informations complètes du profil de l'utilisateur connecté.

**URL** : `/profile/me`

**Méthode** : `GET`

**Authentification** : Requise

**Headers** :

```
Authorization: Bearer votre_token_jwt
```

**Exemple de réponse réussie** :

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "utilisateur@example.com",
  "full_name": "Nom Complet",
  "profile_picture_url": "/uploads/profile_pictures/550e8400-e29b-41d4-a716-446655440000/profile_12345678.jpg",
  "created_at": "2025-03-06T10:30:22.123456"
}
```

### Mettre à jour le profil

Met à jour les informations du profil de l'utilisateur connecté.

**URL** : `/profile/update`

**Méthode** : `PUT`

**Authentification** : Requise

**Headers** :

```
Authorization: Bearer votre_token_jwt
```

**Données de la requête** :

```json
{
  "full_name": "Nouveau Nom Complet",
  "email": "nouvel.email@example.com"
}
```

Tous les champs sont optionnels. Seuls les champs fournis seront mis à jour.

**Exemple de réponse réussie** :

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "nouvel.email@example.com",
  "full_name": "Nouveau Nom Complet",
  "profile_picture_url": "/uploads/profile_pictures/550e8400-e29b-41d4-a716-446655440000/profile_12345678.jpg",
  "created_at": "2025-03-06T10:30:22.123456"
}
```

### Télécharger une photo de profil

Télécharge et met à jour la photo de profil de l'utilisateur connecté.

**URL** : `/profile/upload-picture`

**Méthode** : `POST`

**Authentification** : Requise

**Headers** :

```
Authorization: Bearer votre_token_jwt
Content-Type: multipart/form-data
```

**Corps de la requête** :
- `file` : Fichier image (JPEG, PNG, GIF, WEBP) de taille inférieure à 5MB

**Exemple de réponse réussie** :

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "utilisateur@example.com",
  "full_name": "Nom Complet",
  "profile_picture_url": "/uploads/profile_pictures/550e8400-e29b-41d4-a716-446655440000/profile_87654321.jpg",
  "created_at": "2025-03-06T10:30:22.123456"
}
```

### Changer le mot de passe

Change le mot de passe de l'utilisateur connecté.

**URL** : `/profile/change-password`

**Méthode** : `PUT`

**Authentification** : Requise

**Headers** :

```
Authorization: Bearer votre_token_jwt
```

**Données de la requête** :

```json
{
  "current_password": "mot_de_passe_actuel",
  "new_password": "nouveau_mot_de_passe"
}
```

**Exemple de réponse réussie** :

```json
{
  "message": "Mot de passe mis à jour avec succès"
}
```

## Formats et structures de données

### Statuts de transcription

Les statuts possibles pour une transcription sont :
- `pending` : La transcription est en cours
- `completed` : La transcription est terminée avec succès
- `error` : Une erreur est survenue lors de la transcription
- `timeout` : La transcription a pris trop de temps et a été abandonnée

### Format de réunion

```json
{
  "id": "UUID",
  "user_id": "UUID",
  "title": "Titre de la réunion",
  "file_url": "Chemin vers le fichier audio",
  "transcript_text": "Texte de la transcription (null si non terminée)",
  "transcript_status": "État de la transcription",
  "created_at": "Date et heure de création",
  "duration_seconds": "Durée de la réunion en secondes",
  "speakers_count": "Nombre de locuteurs"
}
```

## Codes d'erreur

- `400 Bad Request` : Données de requête invalides ou incomplètes
- `401 Unauthorized` : Authentification échouée ou token invalide
- `403 Forbidden` : Accès refusé aux ressources
- `404 Not Found` : Ressource introuvable
- `500 Internal Server Error` : Erreur interne du serveur

## Bonnes pratiques

1. **Gestion des tokens** : Stockez le token JWT de manière sécurisée et renouvelez-le avant son expiration.

2. **Upload de fichiers audio** :
   - Limitez la taille des fichiers audio à 100 MB maximum
   - Préférez les formats MP3 ou WAV pour une meilleure compatibilité
   - Vérifiez le statut de transcription régulièrement après l'upload

3. **Traitement des erreurs** :
   - Implémentez une logique de retry en cas d'échec de transcription
   - Affichez des messages d'erreur explicites aux utilisateurs

4. **Polling de statut** :
   - Pour les transcriptions longues, implémentez un polling toutes les 5-10 secondes
   - Utilisez une stratégie de backoff exponentiel pour éviter de surcharger le serveur

5. **Sécurité** :
   - N'exposez jamais votre token JWT dans des URLs ou logs
   - Utilisez HTTPS en production
   - Implémentez une déconnexion automatique après expiration du token

---

**Note** : Cette API est conçue pour une utilisation en développement. Pour un environnement de production, des mesures de sécurité supplémentaires seraient nécessaires.
