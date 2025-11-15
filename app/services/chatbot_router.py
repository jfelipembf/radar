"""Router para detectar segmento e direcionar para serviço especializado."""

import logging
from typing import Tuple
from app.services.openai_service import OpenAIService
from app.services.supabase_service import SupabaseService
from app.services.evolution_service import EvolutionService

logger = logging.getLogger(__name__)


class ChatbotRouter:
    """Detecta segmento da mensagem e roteia para serviço correto."""
    
    # Palavras-chave por segmento
    SEGMENT_KEYWORDS = {
        'bebidas': [
            'cerveja', 'refrigerante', 'coca', 'pepsi', 'skol', 'brahma',
            'heineken', 'agua', 'água', 'suco', 'vinho', 'whisky', 'vodka',
            'lata', 'garrafa', 'long neck', 'caixa de cerveja', 'budweiser',
            'stella', 'amstel', 'corona', 'guarana', 'guaraná', 'fanta',
            'sprite', 'bebida', 'drink', 'gelada', 'chopp', 'chope'
        ],
        'construcao': [
            'cimento', 'areia', 'tijolo', 'telha', 'caixa dagua', 'caixa d\'água',
            'argamassa', 'cal', 'brita', 'ferro', 'vergalhao', 'vergalhão',
            'saco', 'metro cubico', 'metro cúbico', 'm3', 'm³', 'milheiro',
            'construcao', 'construção', 'obra', 'material', 'pedra'
        ]
    }
    
    def __init__(
        self,
        openai_service: OpenAIService,
        supabase_service: SupabaseService,
        evolution_service: EvolutionService
    ):
        self.openai_service = openai_service
        self.supabase_service = supabase_service
        self.evolution_service = evolution_service
    
    def detect_segment(self, message: str) -> Tuple[str, float]:
        """
        Detecta segmento da mensagem.
        
        Args:
            message: Mensagem do usuário
        
        Returns:
            (segmento, confiança)
        """
        message_lower = message.lower()
        scores = {}
        
        for segment, keywords in self.SEGMENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                scores[segment] = score
        
        if not scores:
            return 'geral', 0.0
        
        best_segment = max(scores, key=scores.get)
        total_keywords = len(self.SEGMENT_KEYWORDS[best_segment])
        confidence = scores[best_segment] / total_keywords if total_keywords > 0 else 0.0
        
        logger.info(f"Segmento detectado: {best_segment} (confiança: {confidence:.2%})")
        
        return best_segment, confidence
    
    def get_service(self, message: str):
        """
        Retorna serviço apropriado baseado na mensagem.
        
        Args:
            message: Mensagem do usuário
            
        Returns:
            Instância do serviço apropriado
        """
        segment, confidence = self.detect_segment(message)
        
        if segment == 'bebidas':
            from app.services.bebidas import BebidasService
            logger.info("Roteando para BebidasService")
            return BebidasService(
                self.openai_service,
                self.supabase_service,
                self.evolution_service
            )
        elif segment == 'construcao':
            # TODO: Implementar ConstrucaoService
            logger.info("Segmento construção detectado, usando serviço geral")
            from app.services.chatbot_service import ChatbotService
            return ChatbotService(
                self.openai_service,
                self.supabase_service,
                self.evolution_service
            )
        else:
            # Fallback para serviço geral
            logger.info("Usando serviço geral (fallback)")
            from app.services.chatbot_service import ChatbotService
            return ChatbotService(
                self.openai_service,
                self.supabase_service,
                self.evolution_service
            )


__all__ = ["ChatbotRouter"]
