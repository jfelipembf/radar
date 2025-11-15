"""Gerenciamento de estado da conversa."""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class ConversationState:
    """Gerencia estado da conversa por usuário."""
    
    # Armazena estado em memória (em produção, usar Redis ou DB)
    _states: Dict[str, Dict[str, Any]] = {}
    
    # Tempo de expiração do estado (30 minutos)
    STATE_EXPIRATION = timedelta(minutes=30)
    
    @classmethod
    def save_budget(cls, user_id: str, budget_data: Dict[str, Any]) -> None:
        """
        Salva orçamento atual do usuário.
        
        Args:
            user_id: ID do usuário
            budget_data: Dados do orçamento (resultado de calculate_best_budget)
        """
        cls._states[user_id] = {
            "budget": budget_data,
            "timestamp": datetime.now(),
            "phase": "budget_shown"  # budget_shown, details_shown, finalized
        }
    
    @classmethod
    def get_budget(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera orçamento atual do usuário.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Dados do orçamento ou None se expirado/não existe
        """
        state = cls._states.get(user_id)
        
        if not state:
            return None
        
        # Verificar expiração
        if datetime.now() - state["timestamp"] > cls.STATE_EXPIRATION:
            cls.clear_state(user_id)
            return None
        
        return state.get("budget")
    
    @classmethod
    def get_phase(cls, user_id: str) -> Optional[str]:
        """
        Retorna fase atual da conversa.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Fase atual ou None
        """
        state = cls._states.get(user_id)
        return state.get("phase") if state else None
    
    @classmethod
    def set_phase(cls, user_id: str, phase: str) -> None:
        """
        Atualiza fase da conversa.
        
        Args:
            user_id: ID do usuário
            phase: Nova fase
        """
        if user_id in cls._states:
            cls._states[user_id]["phase"] = phase
            cls._states[user_id]["timestamp"] = datetime.now()
    
    @classmethod
    def clear_state(cls, user_id: str) -> None:
        """
        Limpa estado do usuário.
        
        Args:
            user_id: ID do usuário
        """
        if user_id in cls._states:
            del cls._states[user_id]
    
    @classmethod
    def is_option_response(cls, text: str) -> Optional[str]:
        """
        Verifica se mensagem é uma resposta de opção (1, 2, 3, 0).
        
        Args:
            text: Texto da mensagem
            
        Returns:
            Opção detectada ou None
        """
        text_clean = text.strip().lower()
        
        # Detectar apenas números
        if text_clean in ["1", "2", "3", "0"]:
            return text_clean
        
        # Detectar com emojis
        if text_clean in ["1️⃣", "2️⃣", "3️⃣", "0️⃣"]:
            return text_clean[0]
        
        return None


__all__ = ["ConversationState"]
