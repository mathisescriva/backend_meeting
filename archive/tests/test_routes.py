import pytest
import os
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.core.security import create_access_token
from app.models.user import User
from app.core.config import settings

# Configuration de test
client = TestClient(app)

@pytest.fixture
def test_user():
    """Fixture pour créer un utilisateur de test."""
    return {
        "id": "test-user-id",
        "username": "testuser",
        "email": "test@example.com"
    }

@pytest.fixture
def test_token(test_user):
    """Fixture pour créer un token d'authentification de test."""
    return create_access_token({"sub": test_user["id"]})

@pytest.fixture
def test_auth_header(test_token):
    """Fixture pour créer un header d'authentification de test."""
    return {"Authorization": f"Bearer {test_token}"}

@pytest.fixture
def test_audio_file():
    """Renvoie le chemin d'un fichier audio de test."""
    test_file_path = Path(__file__).parent / "resources" / "test_audio.mp3"
    
    # Si le répertoire resources n'existe pas, créez-le
    if not test_file_path.parent.exists():
        test_file_path.parent.mkdir(parents=True)
    
    # Si le fichier de test n'existe pas, créez un petit fichier MP3
    if not test_file_path.exists():
        # Créer un fichier audio de test factice
        with open(test_file_path, 'wb') as f:
            f.write(b'MOCK_AUDIO_DATA')
    
    return str(test_file_path)

@pytest.mark.asyncio
async def test_upload_meeting_endpoint(test_auth_header, test_user, test_audio_file):
    """Teste l'endpoint d'upload de réunion."""
    
    # Mock pour les dépendances
    with patch('app.routes.meetings.get_current_user', return_value=test_user), \
         patch('app.routes.meetings.save_uploaded_file', return_value="/uploads/test/file.mp3"), \
         patch('app.routes.meetings.create_meeting', return_value={"id": "meeting-123", "user_id": test_user["id"]}), \
         patch('app.routes.meetings.transcribe_meeting') as mock_transcribe:
        
        # Créer un fichier de test à envoyer
        with open(test_audio_file, "rb") as f:
            files = {"file": ("test_audio.mp3", f, "audio/mpeg")}
            response = client.post(
                "/meetings/upload",
                headers=test_auth_header,
                files=files,
                data={"title": "Test Meeting"}
            )
        
        # Vérifier la réponse
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "meeting-123"
        assert data["user_id"] == test_user["id"]
        
        # Vérifier que transcribe_meeting a été appelé
        mock_transcribe.assert_called_once()

@pytest.mark.asyncio
async def test_get_meeting_endpoint(test_auth_header, test_user):
    """Teste l'endpoint de récupération d'une réunion."""
    
    meeting_data = {
        "id": "meeting-123",
        "user_id": test_user["id"],
        "title": "Test Meeting",
        "file_url": "/uploads/test/file.mp3",
        "transcript_text": "This is a test transcript",
        "transcript_status": "completed",
        "created_at": "2023-01-01T00:00:00.000000"
    }
    
    # Mock pour les dépendances
    with patch('app.routes.meetings.get_current_user', return_value=test_user), \
         patch('app.routes.meetings.get_meeting', return_value=meeting_data):
        
        response = client.get(
            "/meetings/meeting-123",
            headers=test_auth_header
        )
        
        # Vérifier la réponse
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "meeting-123"
        assert data["user_id"] == test_user["id"]
        assert data["transcript_text"] == "This is a test transcript"
        assert data["transcript_status"] == "completed"

@pytest.mark.asyncio
async def test_get_meetings_endpoint(test_auth_header, test_user):
    """Teste l'endpoint de récupération de toutes les réunions."""
    
    meetings_data = [
        {
            "id": "meeting-123",
            "user_id": test_user["id"],
            "title": "Test Meeting 1",
            "file_url": "/uploads/test/file1.mp3",
            "transcript_status": "completed",
            "created_at": "2023-01-01T00:00:00.000000"
        },
        {
            "id": "meeting-456",
            "user_id": test_user["id"],
            "title": "Test Meeting 2",
            "file_url": "/uploads/test/file2.mp3",
            "transcript_status": "pending",
            "created_at": "2023-01-02T00:00:00.000000"
        }
    ]
    
    # Mock pour les dépendances
    with patch('app.routes.meetings.get_current_user', return_value=test_user), \
         patch('app.routes.meetings.get_user_meetings', return_value=meetings_data):
        
        response = client.get(
            "/meetings/",
            headers=test_auth_header
        )
        
        # Vérifier la réponse
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "meeting-123"
        assert data[1]["id"] == "meeting-456"
