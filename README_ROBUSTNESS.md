# Guide pour un backend robuste

Ce document du00e9crit les meilleures pratiques pour maintenir un backend robuste et fiable pour l'application MeetingTranscriberBackend.

## Table des matiu00e8res

1. [Tests automatiques](#tests-automatiques)
2. [Surveillance et logging](#surveillance-et-logging)
3. [Gestion des erreurs et ru00e9silience](#gestion-des-erreurs-et-ru00e9silience)
4. [Intu00e9gration et du00e9ploiement continus](#intu00e9gration-et-du00e9ploiement-continus)
5. [Documentation et maintenance](#documentation-et-maintenance)
6. [Su00e9curitu00e9](#su00e9curitu00e9)
7. [Workflow Git recommandu00e9](#workflow-git-recommandu00e9)

## Tests automatiques

### Tests unitaires

Les tests unitaires vu00e9rifient le comportement des fonctions individuelles.

```bash
# Exu00e9cuter les tests unitaires
python -m unittest discover tests/unit
```

### Tests d'intu00e9gration

Les tests d'intu00e9gration vu00e9rifient l'interaction entre les diffu00e9rents composants du systu00e8me.

```bash
# Exu00e9cuter les tests d'intu00e9gration
python test_all_endpoints.py
python test_summary_generation.py
```

### Tests de charge

Les tests de charge vu00e9rifient le comportement du systu00e8me sous charge importante.

```bash
# Utiliser locust pour les tests de charge
locust -f tests/load/locustfile.py
```

## Surveillance et logging

### Logs structuru00e9s

Utiliser des logs structuru00e9s avec des niveaux appropriu00e9s pour faciliter le du00e9bogage.

```python
logger.info(f"Traitement de la ru00e9union {meeting_id}", extra={"user_id": user_id})
logger.error(f"Erreur API: {e}", extra={"status_code": e.status_code})
```

### Vu00e9rifications de santu00e9

Exu00e9cuter ru00e9guliu00e8rement des vu00e9rifications de santu00e9 pour du00e9tecter les problu00e8mes avant qu'ils n'affectent les utilisateurs.

```bash
# Vu00e9rifier l'u00e9tat du backend
python health_check.py
```

## Gestion des erreurs et ru00e9silience

### Retry patterns

Implu00e9menter des retry patterns pour les opu00e9rations qui peuvent u00e9chouer temporairement.

```python
def call_with_retry(func, max_retries=3, backoff_factor=2):
    """Appelle une fonction avec retry en cas d'u00e9chec"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff_factor ** attempt)
```

### Circuit breakers

Utiliser des circuit breakers pour u00e9viter de surcharger un service externe du00e9faillant.

```python
from pybreaker import CircuitBreaker

mistral_breaker = CircuitBreaker(fail_max=3, reset_timeout=60)

@mistral_breaker
def call_mistral_api(prompt):
    # Appel u00e0 l'API Mistral
    pass
```

## Intu00e9gration et du00e9ploiement continus

### GitHub Actions

Configurer GitHub Actions pour exu00e9cuter les tests automatiquement u00e0 chaque push.

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: |
          python test_all_endpoints.py
          python test_summary_generation.py
```

### Pre-push hooks

Utiliser des pre-push hooks pour vu00e9rifier que tout fonctionne avant de pousser les modifications.

```bash
# Installer le pre-push hook
cp pre-push.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Documentation et maintenance

### Swagger/OpenAPI

Utiliser Swagger/OpenAPI pour documenter les endpoints.

```python
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(
    title="Meeting Transcriber API",
    description="API pour la transcription et l'analyse de ru00e9unions",
    version="1.0.0"
)
```

### Versionnement su00e9mantique

Utiliser le versionnement su00e9mantique pour l'API.

```
MAJOR.MINOR.PATCH
```

## Su00e9curitu00e9

### Gestion su00e9curisu00e9e des secrets

Ne jamais stocker de clu00e9s API dans le code source. Utiliser des variables d'environnement ou un gestionnaire de secrets.

```python
# Utiliser les variables d'environnement
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
```

### Validation des entru00e9es

Valider toutes les entru00e9es utilisateur pour u00e9viter les injections et autres attaques.

```python
from pydantic import BaseModel, validator

class MeetingCreate(BaseModel):
    title: str
    
    @validator("title")
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Le titre ne peut pas u00eatre vide")
        return v
```

## Workflow Git recommandu00e9

### Branches

- `main` : Code de production stable
- `develop` : Code de du00e9veloppement intu00e9gru00e9
- `feature/*` : Nouvelles fonctionnalitu00e9s
- `bugfix/*` : Corrections de bugs
- `hotfix/*` : Corrections urgentes pour la production

### Processus de validation

1. Du00e9velopper sur une branche de fonctionnalitu00e9 ou de correction
2. Exu00e9cuter les tests localement
3. Cru00e9er une pull request vers `develop`
4. Attendre la validation des tests automatiques
5. Faire une revue de code
6. Merger dans `develop`
7. Tester en environnement de staging
8. Merger dans `main` pour le du00e9ploiement en production

### Commandes Git utiles

```bash
# Cru00e9er une nouvelle branche de fonctionnalitu00e9
git checkout -b feature/nouvelle-fonctionnalite

# Pousser les modifications
git push origin feature/nouvelle-fonctionnalite

# Mettre u00e0 jour depuis develop
git checkout develop
git pull
git checkout feature/nouvelle-fonctionnalite
git merge develop
```

### Vu00e9rification avant push

Utiliser le script `pre-push.sh` pour vu00e9rifier que tout fonctionne avant de pousser les modifications.

```bash
# Vu00e9rifier manuellement
./pre-push.sh

# Installer comme hook Git
cp pre-push.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

Ce script vu00e9rifie :
1. Que le serveur est en cours d'exu00e9cution
2. Que les vu00e9rifications de santu00e9 passent
3. Que les tests des endpoints passent
4. Que les tests de gu00e9nu00e9ration de sommaire passent

Si toutes les vu00e9rifications passent, le push est autorisu00e9. Sinon, il est annulu00e9.
