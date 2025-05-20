import requests
import json
import logging
from datetime import datetime

# Configuration
LOG_FILE = f"test_logs/mistral_standard_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Cru00e9er le dossier de logs s'il n'existe pas
import os
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(LOG_FILE),
                        logging.StreamHandler()
                    ])

logger = logging.getLogger(__name__)

# Configuration pour Mistral AI
MISTRAL_API_KEY = "40zsZTwSIFoAISjk1POC3rZ09GfF6WDH"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

def test_mistral_standard():
    """Test de l'API standard de Mistral pour la gu00e9nu00e9ration de comptes rendus"""
    logger.info("=== TEST DE L'API STANDARD DE MISTRAL POUR LA Gu00c9Nu00c9RATION DE COMPTES RENDUS ===")
    
    # Exemple de transcription (court pour le test)
    transcript_text = """Bonjour u00e0 tous, bienvenue u00e0 cette ru00e9union du comitu00e9 de direction. 
    Aujourd'hui, nous allons discuter de trois points principaux : 
    1. Le bilan financier du trimestre
    2. Le lancement du nouveau produit
    3. La ru00e9organisation de l'u00e9quipe marketing
    
    Pour commencer, Jean va nous pru00e9senter le bilan financier.
    
    Jean: Merci. Les ru00e9sultats du trimestre sont satisfaisants avec une croissance de 15% par rapport u00e0 l'annu00e9e derniu00e8re. 
    Nous avons du00e9passu00e9 nos objectifs de vente de 5%. Cependant, nos cou00fbts ont augmentu00e9 de 8%, ce qui ru00e9duit notre marge.
    
    Marie: Quelles sont les principales causes de cette augmentation des cou00fbts?
    
    Jean: Principalement l'augmentation des matiu00e8res premiu00e8res et les cou00fbts logistiques.
    
    Directeur: Merci Jean. Passons maintenant au lancement du nouveau produit. Sophie?
    
    Sophie: Le lancement est pru00e9vu pour le 15 juin. La campagne marketing du00e9butera le 1er juin. 
    Nous avons finalisu00e9 tous les visuels et les textes. Le budget est de 50 000 euros.
    
    Directeur: Tru00e8s bien. Nous validons donc le budget et la date de lancement.
    
    Pour la ru00e9organisation de l'u00e9quipe marketing, nous avons du00e9cidu00e9 de cru00e9er deux pu00f4les : 
    un pu00f4le digital et un pu00f4le traditionnel. Thomas sera responsable du pu00f4le digital et Marie du pu00f4le traditionnel.
    
    Thomas: J'ai du00e9ju00e0 commencu00e9 u00e0 travailler sur la nouvelle organisation. Je pru00e9senterai un plan du00e9taillu00e9 la semaine prochaine.
    
    Directeur: Parfait. Nous attendons ton plan pour le 25 mai au plus tard.
    
    Y a-t-il d'autres points u00e0 aborder?
    
    Marie: Juste une information : nous avons reu00e7u le prix de l'innovation pour notre application mobile.
    
    Directeur: Excellente nouvelle! Fu00e9licitations u00e0 toute l'u00e9quipe.
    
    S'il n'y a pas d'autres points, la ru00e9union est terminu00e9e. Merci u00e0 tous pour votre participation."""
    
    # Pru00e9parer le prompt pour Mistral
    title_part = " intitulu00e9e 'Comitu00e9 de direction'"
    
    prompt = f"""Tu es un assistant spu00e9cialisu00e9 dans la cru00e9ation de comptes rendus de ru00e9union.
    
    Voici la transcription d'une ru00e9union{title_part}.
    Cru00e9e un compte rendu structuru00e9 STRICTEMENT selon les 4 parties suivantes :
    
    # Synthu00e8se
    Une synthu00e8se concise de la ru00e9union en quelques lignes seulement.
    
    # u00c9lu00e9ments discut\u00e9s
    Les principaux points et sujets abordu00e9s pendant la ru00e9union, pru00e9sentu00e9s sous forme de liste u00e0 puces.
    
    # Relevu00e9 de du00e9cisions
    Toutes les du00e9cisions prises lors de la ru00e9union, pru00e9sentu00e9es sous forme de liste u00e0 puces.
    
    # Plan d'action
    Les actions u00e0 entreprendre avec leurs responsables (si mentionnu00e9s) et les u00e9chu00e9ances (si mentionnu00e9es), pru00e9sentu00e9es sous forme de liste u00e0 puces.
    
    Respecte IMPu00c9RATIVEMENT cette structure en 4 parties avec ces titres exacts. Utilise un format clair avec des listes u00e0 puces et des paragraphes bien organisu00e9s.
    
    Transcription:
    {transcript_text}
    """
    
    # Pru00e9parer la requu00eate pour l'API Mistral
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    payload = {
        "model": "mistral-large-latest",  # Utiliser le modu00e8le le plus ru00e9cent et le plus performant
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # Tempu00e9rature basse pour des ru00e9sultats plus cohu00e9rents
        "max_tokens": 4000  # Limite de tokens pour la ru00e9ponse
    }
    
    try:
        # Envoyer la requu00eate u00e0 l'API Mistral
        logger.info("Envoi de la requu00eate u00e0 l'API Mistral")
        logger.info(f"URL: {MISTRAL_API_URL}")
        response = requests.post(MISTRAL_API_URL, headers=headers, json=payload)
        
        # Vu00e9rifier la ru00e9ponse
        logger.info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            summary = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if summary:
                logger.info("u2705 Compte rendu gu00e9nu00e9ru00e9 avec succu00e8s par l'API Mistral")
                logger.info("\n=== COMPTE RENDU Gu00c9Nu00c9Ru00c9 ===\n")
                logger.info(summary)
                logger.info("\n=== FIN DU COMPTE RENDU ===\n")
                return True
            else:
                logger.error("u274c La ru00e9ponse de l'API Mistral ne contient pas de contenu")
                logger.error(f"Ru00e9ponse compu00e8te: {json.dumps(response_data, indent=2)}")
                return False
        else:
            logger.error(f"u274c Erreur lors de l'appel u00e0 l'API Mistral: {response.status_code}")
            logger.error(f"Ru00e9ponse: {response.text}")
            return False
    except Exception as e:
        logger.error(f"u274c Erreur lors de la gu00e9nu00e9ration du compte rendu: {str(e)}")
        return False

if __name__ == "__main__":
    test_mistral_standard()
