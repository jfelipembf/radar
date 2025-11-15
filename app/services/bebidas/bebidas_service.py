"""Serviço especializado em bebidas."""

import logging
from app.services.base import BaseChatbotService
from app.services.openai_service import OpenAIService
from app.services.supabase_service import SupabaseService
from app.services.evolution_service import EvolutionService
from .bebidas_prompt import BEBIDAS_PROMPT

logger = logging.getLogger(__name__)


class BebidasService(BaseChatbotService):
    """Serviço especializado em bebidas."""
    
    def __init__(
        self,
        openai_service: OpenAIService,
        supabase_service: SupabaseService,
        evolution_service: EvolutionService
    ):
        super().__init__(openai_service, supabase_service, evolution_service)
        self.system_prompt = BEBIDAS_PROMPT
        self.segment = 'bebidas'
        logger.info("BebidasService inicializado com prompt especializado")


__all__ = ["BebidasService"]
