## Gestion des clients et résumés personnalisés

Cette API permet de gérer des clients avec des templates de résumé personnalisés. Les réunions peuvent être associées à des clients spécifiques pour générer des comptes rendus personnalisés selon le format désiré par chaque client.

### Créer un nouveau client

```
POST /clients/
```

**En-têtes requis :**
```
Authorization: Bearer votre_token_jwt
Content-Type: application/json
```

**Corps de la requête :**
```json
{
  "name": "Nom du Client",
  "summary_template": "# Compte rendu pour {meeting_title}\n\nVoici la transcription personnalisée pour ce client: {transcript_text}"
}
```

**Réponse :**
```json
{
  "id": "de269a40-2840-43e5-9e75-486d03680526",
  "user_id": "99dfd97f-a65a-4881-b917-318254285727",
  "name": "Nom du Client",
  "summary_template": "# Compte rendu pour {meeting_title}\n\nVoici la transcription personnalisée pour ce client: {transcript_text}",
  "created_at": "2025-05-20T18:46:40.452140"
}
```

### Liste des clients

```
GET /clients/
```

**En-tête requis :**
```
Authorization: Bearer votre_token_jwt
```

**Réponse :**
```json
[
  {
    "id": "de269a40-2840-43e5-9e75-486d03680526",
    "user_id": "99dfd97f-a65a-4881-b917-318254285727",
    "name": "Nom du Client",
    "summary_template": "# Compte rendu pour {meeting_title}\n\nVoici la transcription personnalisée pour ce client: {transcript_text}",
    "created_at": "2025-05-20T18:46:40.452140"
  }
]
```

### Récupérer un client spécifique

```
GET /clients/{client_id}
```

**En-tête requis :**
```
Authorization: Bearer votre_token_jwt
```

**Réponse :**
```json
{
  "id": "de269a40-2840-43e5-9e75-486d03680526",
  "user_id": "99dfd97f-a65a-4881-b917-318254285727",
  "name": "Nom du Client",
  "summary_template": "# Compte rendu pour {meeting_title}\n\nVoici la transcription personnalisée pour ce client: {transcript_text}",
  "created_at": "2025-05-20T18:46:40.452140"
}
```

### Mettre à jour un client

```
PUT /clients/{client_id}
```

**En-têtes requis :**
```
Authorization: Bearer votre_token_jwt
Content-Type: application/json
```

**Corps de la requête :**
```json
{
  "name": "Nouveau Nom du Client",
  "summary_template": "# Format personnalisé mis à jour\n\n{transcript_text}"
}
```

**Réponse :**
```json
{
  "id": "de269a40-2840-43e5-9e75-486d03680526",
  "user_id": "99dfd97f-a65a-4881-b917-318254285727",
  "name": "Nouveau Nom du Client",
  "summary_template": "# Format personnalisé mis à jour\n\n{transcript_text}",
  "created_at": "2025-05-20T18:46:40.452140"
}
```

### Supprimer un client

```
DELETE /clients/{client_id}
```

**En-tête requis :**
```
Authorization: Bearer votre_token_jwt
```

**Réponse :**
```json
{
  "message": "Client supprimé avec succès"
}
```

### Associer une réunion à un client

Pour associer une réunion à un client, utilisez la méthode PUT pour mettre à jour les informations de la réunion :

```
PUT /meetings/{meeting_id}
```

**Corps de la requête :**
```json
{
  "client_id": "de269a40-2840-43e5-9e75-486d03680526"
}
```

### Générer un résumé personnalisé

Pour générer un résumé personnalisé pour une réunion, vous pouvez spécifier le client directement lors de la génération :

```
POST /meetings/{meeting_id}/generate-summary?client_id={client_id}
```

Si la réunion est déjà associée à un client, l'API utilisera automatiquement le template de ce client pour générer le résumé.

### Variables disponibles dans les templates

Les templates de résumé peuvent utiliser les variables suivantes :

- `{meeting_title}` : Titre de la réunion
- `{transcript_text}` : Texte complet de la transcription

Exemple de template :
```
# Compte rendu de la réunion : {meeting_title}

Ci-dessous le résumé de la réunion :

{transcript_text}
```
