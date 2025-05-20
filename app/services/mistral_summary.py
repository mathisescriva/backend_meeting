import json
import logging
import os
from typing import Optional, Dict, Any
from ..core.config import settings
import requests

# Configuration pour Mistral AI
# Utiliser directement la clé API fournie au lieu de passer par settings
MISTRAL_API_KEY = "40zsZTwSIFoAISjk1POC3rZ09GfF6WDH"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Configuration du logging
logger = logging.getLogger("meeting-transcriber")

def get_client_template(client_id: Optional[str] = None, user_id: Optional[str] = None) -> Optional[str]:
    """
    Récupère le template de résumé associé à un client.
    
    Args:
        client_id: ID du client (optionnel)
        user_id: ID de l'utilisateur propriétaire du client (optionnel)
        
    Returns:
        str: Template de résumé ou None si aucun template n'est trouvé
    """
    if not client_id or not user_id:
        return None
        
    try:
        # Importer les fonctions ici pour éviter les imports circulaires
        from ..db.client_queries import get_client
        
        # Récupérer les informations du client
        client = get_client(client_id, user_id)
        
        if client and client.get("summary_template"):
            logger.info(f"Template de résumé trouvé pour le client {client_id}")
            return client["summary_template"]
        else:
            logger.info(f"Aucun template de résumé trouvé pour le client {client_id}")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du template client: {str(e)}")
        return None

def generate_meeting_summary(transcript_text: str, meeting_title: Optional[str] = None, client_id: Optional[str] = None, user_id: Optional[str] = None) -> Optional[str]:
    """
    Génère un compte rendu de réunion à partir d'une transcription en utilisant l'API Mistral.
    
    Args:
        transcript_text: Texte de la transcription de la réunion
        meeting_title: Titre de la réunion (optionnel)
        client_id: ID du client pour personnaliser le résumé (optionnel)
        user_id: ID de l'utilisateur qui demande le résumé (optionnel)
        
    Returns:
        str: Compte rendu généré ou None en cas d'erreur
    """
    if not MISTRAL_API_KEY:
        logger.error("Clé API Mistral non configurée. Impossible de générer le compte rendu.")
        return None
        
    try:
        # Vérifier s'il existe un template client personnalisé
        client_template = None
        if client_id and user_id:
            client_template = get_client_template(client_id, user_id)
        
        title_part = f" intitulée '{meeting_title}'" if meeting_title else ""
        
        # Utiliser le template personnalisé s'il existe, sinon utiliser le template par défaut
        if client_template:
            # Remplacer les variables dans le template client
            prompt = client_template.replace("{transcript_text}", transcript_text)
            if meeting_title:
                prompt = prompt.replace("{meeting_title}", meeting_title)
            logger.info("Utilisation d'un template client personnalisé")
        else:
            # Template par défaut
            prompt = f"""Objectif :
À partir d'une transcription brute d'une réunion, produire un compte rendu EXACTEMENT selon le format d'exemple fourni ci-dessous, intégrant précisément les emojis, les titres, les tableaux, et le style montrés.

VOICI UN EXEMPLE EXACT DU FORMAT DE SORTIE QUE TU DOIS REPRODUIRE :

# 📅 Réunion du [date inconnue ou date exacte si mentionnée] u2014 [Titre de la réunion ou sujet principal]

- 👥 **Participants** : [Liste des participants]
- ✏️ **Animateur/trice** : [Nom de l'animateur si identifiable]
- 🕒 **Durée estimée** : [Durée si mentionnée]

---

## 🧠 Résumé express
Un paragraphe de 3-4 lignes résumant l'essentiel de la réunion.

---

## 🗂️ Ordre du jour *(reconstruit)*
1. 📡 [Premier point]
2. 💰 [Deuxième point]
3. 👤 [Troisième point]
4. ⏱️ [Quatrième point]

---

## ✅ Décisions prises
- 🔒 [Décision 1] *([Nom de la personne])*
- 💰 [Décision 2] *([Nom de la personne])*
- 👥 [Décision 3] *([Nom de la personne])*

---

## 🔜 Tâches & actions à suivre

| 📌 Tâche | 👤 Responsable | ⏳ Échéance | 🔗 Liée à |
|------------------|----------------|----------------|-----------|
| [Description tâche 1] | [Responsable] | [Échéance] | [Lien] |
| [Description tâche 2] | [Responsable] | [Échéance] | [Lien] |

---

## ⚠️ Points de vigilance
- ⚠️ [Point de vigilance 1]
- 🔄 [Point de vigilance 2]

---

## 🧵 Sujets abordés

| 💬 Sujet | 🗣️ Intervenants |
|-------------|------------------------|
| [Sujet 1] | [Liste des intervenants] |
| [Sujet 2] | [Liste des intervenants] |
| [Sujet 3] | [Liste des intervenants] |
| [Sujet 4] | [Liste des intervenants] |

---

## 📚 Ressources mentionnées
- [Ressource 1]
- [Ressource 2]
- [Ressource 3]

---

## 🗓️ Prochaine réunion
📍 [Date et heure de la prochaine réunion si mentionnée]

UTILISE EXACTEMENT CE FORMAT, avec les mêmes emojis et la même mise en page, mais REMPLACE TOUS LES PLACEHOLDERS ENTRE CROCHETS par les informations réelles extraites de la transcription. Ne laisse AUCUN texte du type '[Premier point]' ou '[Sujet 1]' dans ta réponse. Si tu n'as pas l'information pour une section, indique-le clairement (ex: "Non mentionné" ou "Aucun point identifié"), mais NE CONSERVE PAS les placeholders entre crochets.

Voici la transcription d'une réunion{title_part} :

{transcript_text}
"""        
        # Préparer la requête pour l'API Mistral
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {MISTRAL_API_KEY}"
        }
        
        payload = {
            "model": "mistral-large-latest",  # Utiliser le modèle le plus récent et le plus performant
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # Température basse pour des résultats plus cohérents
            "max_tokens": 4000  # Limite de tokens pour la réponse
        }
        
        # Envoyer la requête à l'API Mistral
        logger.info("Envoi de la requête à l'API Mistral pour générer un compte rendu")
        response = requests.post(MISTRAL_API_URL, headers=headers, json=payload)
        
        # Vérifier la réponse
        if response.status_code == 200:
            response_data = response.json()
            summary = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if summary:
                logger.info("Compte rendu généré avec succès par l'API Mistral")
                return summary
            else:
                logger.error("La réponse de l'API Mistral ne contient pas de contenu")
                return None
        else:
            logger.error(f"Erreur lors de l'appel à l'API Mistral: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Erreur lors de la génération du compte rendu: {str(e)}")
        return None

def process_meeting_summary(meeting_id: str, user_id: str, client_id: Optional[str] = None):
    """
    Traite la génération du compte rendu pour une réunion spécifique.
    
    Cette fonction récupère la transcription, génère le compte rendu et met à jour la base de données.
    
    Args:
        meeting_id: Identifiant de la réunion
        user_id: Identifiant de l'utilisateur
        client_id: Identifiant du client pour personnaliser le résumé (optionnel)
    
    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    from ..db.queries import get_meeting, update_meeting
    import threading
    
    try:
        # Récupérer les informations de la réunion
        meeting = get_meeting(meeting_id, user_id)
        
        if not meeting:
            logger.error(f"Réunion {meeting_id} non trouvée pour l'utilisateur {user_id}")
            return False
            
        # Vérifier que la transcription est disponible
        if not meeting.get("transcript_text") or meeting.get("transcript_status") != "completed":
            logger.error(f"La transcription n'est pas disponible pour la réunion {meeting_id}")
            update_meeting(meeting_id, user_id, {"summary_status": "error", "summary_text": "La transcription n'est pas disponible"})
            return False
            
        # Récupérer le client_id depuis la réunion si pas fourni en paramètre
        if not client_id and "client_id" in meeting:
            client_id = meeting.get("client_id")
            
        # Mettre à jour le statut pour indiquer que la génération est en cours
        update_data = {"summary_status": "processing"}
        if client_id:
            update_data["client_id"] = client_id
        update_meeting(meeting_id, user_id, update_data)
        
        # Stocker les données nécessaires pour le thread
        transcript_text = meeting["transcript_text"]
        meeting_title = meeting.get("title")
        
        # Lancer la génération dans un thread séparé pour ne pas bloquer
        def generate_summary_thread():
            try:
                # Générer le compte rendu avec le paramètre client_id
                summary = generate_meeting_summary(transcript_text, meeting_title, client_id, user_id)
                
                if summary:
                    # Mise à jour directe de la base de données en utilisant sqlite3
                    # plutôt que d'utiliser la fonction update_meeting qui utilise le pool de connexions global
                    import sqlite3
                    import os
                    from pathlib import Path
                    
                    # Chemin de la base de données
                    db_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "app.db"
                    
                    # Créer une nouvelle connexion dans ce thread
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    try:
                        # Mettre à jour la réunion avec le compte rendu
                        cursor.execute(
                            "UPDATE meetings SET summary_text = ?, summary_status = ? WHERE id = ? AND user_id = ?",
                            (summary, "completed", meeting_id, user_id)
                        )
                        conn.commit()
                        logger.info(f"Compte rendu généré et enregistré pour la réunion {meeting_id}")
                    except Exception as db_error:
                        logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")
                        return False
                    finally:
                        # Fermer la connexion
                        cursor.close()
                        conn.close()
                    
                    return True
                else:
                    # Mise à jour directe de la base de données en cas d'erreur
                    import sqlite3
                    import os
                    from pathlib import Path
                    
                    # Chemin de la base de données
                    db_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "app.db"
                    
                    # Créer une nouvelle connexion dans ce thread
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    try:
                        # Mettre à jour le statut en cas d'erreur
                        cursor.execute(
                            "UPDATE meetings SET summary_text = ?, summary_status = ? WHERE id = ? AND user_id = ?",
                            ("Erreur lors de la génération du compte rendu", "error", meeting_id, user_id)
                        )
                        conn.commit()
                    except Exception as db_error:
                        logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")
                    finally:
                        # Fermer la connexion
                        cursor.close()
                        conn.close()
                    
                    logger.error(f"Échec de la génération du compte rendu pour la réunion {meeting_id}")
                    return False
            except Exception as e:
                logger.error(f"Erreur dans le thread de génération du compte rendu: {str(e)}")
                
                # Mise à jour directe de la base de données en cas d'erreur
                try:
                    import sqlite3
                    import os
                    from pathlib import Path
                    
                    # Chemin de la base de données
                    db_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "app.db"
                    
                    # Créer une nouvelle connexion dans ce thread
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    # Mettre à jour le statut en cas d'erreur
                    cursor.execute(
                        "UPDATE meetings SET summary_text = ?, summary_status = ? WHERE id = ? AND user_id = ?",
                        (f"Erreur lors de la génération du compte rendu: {str(e)}", "error", meeting_id, user_id)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                except Exception as db_error:
                    logger.error(f"Erreur lors de la mise à jour de la base de données dans le thread: {str(db_error)}")
                return False
        
        # Démarrer le thread
        thread = threading.Thread(target=generate_summary_thread)
        thread.daemon = False
        thread.start()
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du compte rendu: {str(e)}")
        try:
            update_meeting(meeting_id, user_id, {
                "summary_status": "error",
                "summary_text": f"Erreur lors du traitement: {str(e)}"
            })
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour de la base de données: {str(db_error)}")
        return False
