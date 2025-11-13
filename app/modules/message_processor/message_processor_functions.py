"""
Funções específicas do módulo Message Processor
"""
import logging
from .message_processor_domain import determine_processing_strategy, validate_message_context, prepare_ai_context

logger = logging.getLogger(__name__)

async def process_message_async(user_id: str, text: str, conversation_manager, ai_service: dict, whatsapp_service: dict, system_prompt: str = None, product_radar: dict = None) -> dict:
    """
    Processa mensagem de forma assíncrona

    Args:
        user_id: ID do usuário
        text: Texto da mensagem
        conversation_manager: Gerenciador de conversas
        ai_service: Serviço de IA
        whatsapp_service: Serviço WhatsApp

    Returns:
        dict: Resultado do processamento
    """
    try:
        logger.info(f"Processando mensagem async para {user_id}")

        # Processar entrada no conversation manager
        is_first_today, context_messages = await conversation_manager.process_incoming_message(user_id, text)

        # Determinar estratégia de processamento
        strategy = determine_processing_strategy(is_first_today, conversation_manager is not None)

        if strategy == 'immediate':
            # Se for primeira mensagem do dia, enviar mensagem de boas-vindas IMEDIATAMENTE
            if is_first_today:
                welcome_message = get_welcome_message()
                await whatsapp_service['send_whatsapp_message'](user_id, welcome_message)
                logger.info(f"Primeira mensagem do dia enviada para {user_id}")

                # Para primeira mensagem, responder imediatamente também
                response_text = await ai_service['generate_ai_response_with_context'](text, context_messages, system_prompt, product_radar.get('compare_prices') if product_radar else None)
                await conversation_manager.process_outgoing_message(user_id, response_text)
                await whatsapp_service['send_whatsapp_message'](user_id, response_text)
                logger.info(f"Resposta imediata enviada para primeira mensagem de {user_id}")
                return {'status': 'success', 'strategy': 'immediate'}

            # Para mensagens subsequentes, aplicar debounce
            await conversation_manager.start_debounce_timer(user_id, lambda: process_message_with_context(user_id, conversation_manager, ai_service, whatsapp_service, system_prompt, product_radar))
            logger.info(f"Debounce iniciado para {user_id}")

            return {'status': 'success', 'strategy': 'debounced'}

        else:
            # Fallback sem conversation manager
            response_text = await ai_service['generate_ai_response'](text, system_prompt, product_radar.get('compare_prices') if product_radar else None)
            await whatsapp_service['send_whatsapp_message'](user_id, response_text)

            return {'status': 'success', 'strategy': 'fallback'}

    except Exception as e:
        logger.error(f"Erro no processamento async: {e}")
        error_msg = "Desculpe, houve um erro ao processar sua mensagem. Tente novamente."
        await whatsapp_service['send_whatsapp_message'](user_id, error_msg)

        return {'status': 'error', 'error': str(e)}

async def process_message_with_context(user_id: str, conversation_manager, ai_service: dict, whatsapp_service: dict, system_prompt: str = None, product_radar: dict = None) -> dict:
    """
    Processa mensagem após debounce usando contexto

    Args:
        user_id: ID do usuário
        conversation_manager: Gerenciador de conversas
        ai_service: Serviço de IA
        whatsapp_service: Serviço WhatsApp
        system_prompt: Prompt do sistema
        product_radar: Serviço de radar de produtos

    Returns:
        dict: Resultado do processamento
    """
    try:
        logger.info(f"Processando mensagem com contexto após debounce para {user_id}")

        # Obter contexto mais recente
        current_context = await conversation_manager.get_conversation_context(user_id, limit=10)

        # Validar contexto
        validation = validate_message_context(current_context)
        if not validation['valid'] or not validation.get('needs_processing', False):
            logger.info(f"Nenhuma mensagem não processada para {user_id}")
            return {'status': 'no_action_needed'}

        # Pegar a última mensagem do usuário
        latest_user_message = validation['latest_message'].content

        # Gerar resposta com contexto
        response_text = await ai_service['generate_ai_response_with_context'](latest_user_message, current_context, system_prompt, product_radar.get('compare_prices') if product_radar else None)

        # Salvar resposta no contexto
        await conversation_manager.process_outgoing_message(user_id, response_text)

        # Enviar resposta
        await whatsapp_service['send_whatsapp_message'](user_id, response_text)
        logger.info(f"Resposta enviada para {user_id} após debounce")

        return {'status': 'success'}

    except Exception as e:
        logger.error(f"Erro no processamento com contexto: {e}")
        error_msg = "Desculpe, houve um erro ao processar sua mensagem. Tente novamente."
        await whatsapp_service['send_whatsapp_message'](user_id, error_msg)

        return {'status': 'error', 'error': str(e)}

def get_welcome_message() -> str:
    """
    Retorna mensagem de boas-vindas

    Returns:
        str: Mensagem de boas-vindas
    """
    return """🤖 *RADAR ATIVADO*

Olá! Sou seu assistente inteligente de compras automotivas. Posso ajudar você a encontrar os melhores preços de peças e acessórios.

💡 *Como funciona:*
• Digite o nome da peça que procura
• Compare preços automaticamente
• Encontre as melhores ofertas

Vamos começar? O que você está procurando hoje?"""
