import requests
import json
import os
import logging
from datetime import datetime

# Configuration
LOG_FILE = f"test_logs/mistral_agent_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Créer le dossier de logs s'il n'existe pas
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(LOG_FILE),
                        logging.StreamHandler()
                    ])

logger = logging.getLogger(__name__)

# ID de l'agent spécifique pour les comptes rendus de réunion
AGENT_ID = "ag:3b67c37e:20250308:compte-rendu-meeting:131e2fe5"
MISTRAL_API_URL = "https://api.mistral.ai/v1"

def test_mistral_agent():
    """Test l'agent Mistral pour la génération de comptes rendus"""
    logger.info("=== TEST DE L'AGENT MISTRAL POUR LA GÉNÉRATION DE COMPTES RENDUS ===")
    
    # Utiliser directement la clé API Mistral fournie
    mistral_api_key = "40zsZTwSIFoAISjk1POC3rZ09GfF6WDH"
    logger.info("Utilisation de la clé API Mistral fournie")
    
    # Exemple de transcription (court pour le test)
    transcript_text = """Bonjour à tous, bienvenue à cette réunion du comité de direction. 
    Aujourd'hui, nous allons discuter de trois points principaux : 
    1. Le bilan financier du trimestre
    2. Le lancement du nouveau produit
    3. La réorganisation de l'équipe marketing
    
    Pour commencer, Jean va nous présenter le bilan financier.
    
    Jean: Merci. Les résultats du trimestre sont satisfaisants avec une croissance de 15% par rapport à l'année dernière. 
    Nous avons dépassé nos objectifs de vente de 5%. Cependant, nos coûts ont augmenté de 8%, ce qui réduit notre marge.
    
    Marie: Quelles sont les principales causes de cette augmentation des coûts?
    
    Jean: Principalement l'augmentation des matières premières et les coûts logistiques.
    
    Directeur: Merci Jean. Passons maintenant au lancement du nouveau produit. Sophie?
    
    Sophie: Le lancement est prévu pour le 15 juin. La campagne marketing débutera le 1er juin. 
    Nous avons finalisé tous les visuels et les textes. Le budget est de 50 000 euros.
    
    Directeur: Très bien. Nous validons donc le budget et la date de lancement.
    
    Pour la réorganisation de l'équipe marketing, nous avons décidé de créer deux pôles : 
    un pôle digital et un pôle traditionnel. Thomas sera responsable du pôle digital et Marie du pôle traditionnel.
    
    Thomas: J'ai déjà commencé à travailler sur la nouvelle organisation. Je présenterai un plan détaillé la semaine prochaine.
    
    Directeur: Parfait. Nous attendons ton plan pour le 25 mai au plus tard.
    
    Y a-t-il d'autres points à aborder?
    
    Marie: Juste une information : nous avons reçu le prix de l'innovation pour notre application mobile.
    
    Directeur: Excellente nouvelle! Félicitations à toute l'équipe.
    
    S'il n'y a pas d'autres points, la réunion est terminée. Merci à tous pour votre participation."""
    
    # Préparer le message pour l'agent
    message = f"Voici la transcription d'une réunion intitulée 'Comité de direction':\n\n{transcript_text}"
    
    # Préparer la requête pour l'API Mistral (appel à l'agent)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {mistral_api_key}"
    }
    
    # URL spécifique pour l'agent
    agent_url = f"{MISTRAL_API_URL}/{AGENT_ID}/chat"
    
    payload = {
        "messages": [
            {"role": "user", "content": message}
        ],
        "temperature": 0.3,
        "max_tokens": 4000
    }
    
    try:
        # Envoyer la requête à l'API Mistral (agent)
        logger.info(f"Envoi de la requête à l'agent Mistral (ID: {AGENT_ID})")
        response = requests.post(agent_url, headers=headers, json=payload)
        
        # Vérifier la réponse
        if response.status_code == 200:
            response_data = response.json()
            summary = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if summary:
                logger.info("✅ Compte rendu généré avec succès par l'agent Mistral")
                logger.info("\n=== COMPTE RENDU GÉNÉRÉ ===\n")
                logger.info(summary)
                logger.info("\n=== FIN DU COMPTE RENDU ===\n")
                return True
            else:
                logger.error("❌ La réponse de l'agent Mistral ne contient pas de contenu")
                return False
        else:
            logger.error(f"❌ Erreur lors de l'appel à l'agent Mistral: {response.status_code}")
            logger.error(f"Réponse: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du compte rendu: {str(e)}")
        return False

if __name__ == "__main__":
    test_mistral_agent()
