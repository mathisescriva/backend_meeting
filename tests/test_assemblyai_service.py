import os
import pytest
import requests
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.services.assemblyai import upload_file_to_assemblyai, start_transcription, check_transcription_status
from app.core.config import settings

# Configuration de test
TEST_API_KEY = settings.ASSEMBLYAI_API_KEY or os.getenv("ASSEMBLYAI_API_KEY", "testkey")

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
async def test_upload_file_to_assemblyai_success(test_audio_file):
    """Teste l'upload d'un fichier à AssemblyAI avec succès."""
    
    # Mock de la réponse de l'API
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"upload_url": "https://api.assemblyai.com/v2/upload/test_url"}
    
    with patch('requests.post', return_value=mock_response):
        upload_url = await upload_file_to_assemblyai(test_audio_file, TEST_API_KEY)
        
        assert upload_url == "https://api.assemblyai.com/v2/upload/test_url"

@pytest.mark.asyncio
async def test_upload_file_to_assemblyai_failure(test_audio_file):
    """Teste l'échec de l'upload d'un fichier à AssemblyAI."""
    
    # Mock de la réponse de l'API avec échec
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"error": "Bad request"}
    
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(Exception) as excinfo:
            await upload_file_to_assemblyai(test_audio_file, TEST_API_KEY)
        
        assert "Échec de l'upload du fichier à AssemblyAI" in str(excinfo.value)

@pytest.mark.asyncio
async def test_start_transcription_success():
    """Teste le démarrage d'une transcription avec succès."""
    
    # Mock de la réponse de l'API
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "transcription-123",
        "status": "queued"
    }
    
    with patch('requests.post', return_value=mock_response):
        transcription_id = await start_transcription(
            "https://example.com/audio.mp3", 
            TEST_API_KEY,
            speaker_labels=True,
            language_code="fr"
        )
        
        assert transcription_id == "transcription-123"

@pytest.mark.asyncio
async def test_start_transcription_failure():
    """Teste l'échec du démarrage d'une transcription."""
    
    # Mock de la réponse de l'API avec échec
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"error": "Bad request"}
    
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(Exception) as excinfo:
            await start_transcription("https://example.com/audio.mp3", TEST_API_KEY)
        
        assert "Échec du démarrage de la transcription" in str(excinfo.value)

@pytest.mark.asyncio
async def test_check_transcription_status_completed():
    """Teste la vérification du statut d'une transcription complétée."""
    
    # Mock de la réponse de l'API pour une transcription complétée
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "transcription-123",
        "status": "completed",
        "text": "Ceci est une transcription de test.",
        "utterances": [
            {
                "speaker": "A",
                "text": "Ceci est une transcription de test."
            }
        ]
    }
    
    with patch('requests.get', return_value=mock_response):
        status, text = await check_transcription_status("transcription-123", TEST_API_KEY)
        
        assert status == "completed"
        assert text == "Speaker A: Ceci est une transcription de test."

@pytest.mark.asyncio
async def test_check_transcription_status_error():
    """Teste la vérification du statut d'une transcription en erreur."""
    
    # Mock de la réponse de l'API pour une transcription en erreur
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "transcription-123",
        "status": "error",
        "error": "An error occurred during transcription"
    }
    
    with patch('requests.get', return_value=mock_response):
        status, text = await check_transcription_status("transcription-123", TEST_API_KEY)
        
        assert status == "error"
        assert text is None

@pytest.mark.asyncio
async def test_check_transcription_status_processing():
    """Teste la vérification du statut d'une transcription en cours."""
    
    # Mock de la réponse de l'API pour une transcription en cours
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "transcription-123",
        "status": "processing"
    }
    
    with patch('requests.get', return_value=mock_response):
        status, text = await check_transcription_status("transcription-123", TEST_API_KEY)
        
        assert status == "processing"
        assert text is None
