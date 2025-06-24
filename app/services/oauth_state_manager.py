"""
Service de gestion des états OAuth pour sécuriser les flux d'authentification.

Ce service gère le stockage temporaire des états OAuth avec expiration automatique.
En développement, utilise un stockage en mémoire.
En production, peut utiliser Redis pour un stockage distribué.
"""

import time
import secrets
from typing import Dict, Optional
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class OAuthStateManager:
    """Gestionnaire des états OAuth avec expiration automatique"""
    
    def __init__(self):
        self.states: Dict[str, Dict] = {}
        self.max_age = 300  # 5 minutes
    
    def generate_state(self) -> str:
        """Génère un nouvel état OAuth unique"""
        state = secrets.token_urlsafe(32)
        self.states[state] = {
            "timestamp": time.time(),
            "valid": True
        }
        logger.info(f"État OAuth généré: {state[:8]}...")
        return state
    
    def validate_state(self, state: str) -> bool:
        """Valide et supprime un état OAuth"""
        self._cleanup_expired_states()
        
        if state in self.states:
            # Supprimer l'état après validation (usage unique)
            del self.states[state]
            logger.info(f"État OAuth validé et supprimé: {state[:8]}...")
            return True
        
        logger.warning(f"État OAuth invalide ou expiré: {state[:8]}...")
        return False
    
    def _cleanup_expired_states(self):
        """Nettoie les états OAuth expirés"""
        current_time = time.time()
        expired_states = [
            state for state, data in self.states.items()
            if current_time - data.get('timestamp', 0) > self.max_age
        ]
        
        for state in expired_states:
            del self.states[state]
            logger.debug(f"État OAuth expiré supprimé: {state[:8]}...")
        
        if expired_states:
            logger.info(f"{len(expired_states)} états OAuth expirés nettoyés")
    
    def get_states_count(self) -> int:
        """Retourne le nombre d'états OAuth actifs"""
        self._cleanup_expired_states()
        return len(self.states)

# Instance globale du gestionnaire d'états OAuth
oauth_state_manager = OAuthStateManager() 