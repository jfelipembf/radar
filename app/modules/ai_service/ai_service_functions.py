"""
Funções específicas do módulo AI Service
"""
import os
import logging
from openai import OpenAI
from .ai_service_domain import detect_product_query, validate_ai_response, prepare_messages_for_ai, extract_latest_user_message, should_use_context
from .ai_service_types import AI_CONFIG, AI_STATUS

logger = logging.getLogger(__name__)

# Cliente OpenAI será inicializado sob demanda
_openai_client = None

def get_openai_client():
    """Obtém cliente OpenAI inicializado sob demanda"""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client

async def generate_ai_response(message: str, system_prompt: str = None, product_radar = None) -> str:
    """
    Gera resposta da IA sem contexto

    Args:
        message: Mensagem do usuário
        system_prompt: Prompt do sistema (opcional)
        product_radar: Serviço de radar de produtos (opcional)

    Returns:
        str: Resposta da IA
    """
    try:
        # Verificar se é uma consulta de produto para o RADAR
        product_query = detect_product_query(message)

        if product_query and product_radar:
            logger.info(f"Product query detected: {product_query}")
            product_result = product_radar.comparar_precos(product_query)

            if "erro" not in product_result:
                # Formatar resposta com dados do produto
                response = format_product_response(product_result)
                return response

        # Resposta normal da IA (sem contexto)
        messages = [
            {"role": "system", "content": system_prompt or "Você é um assistente virtual amigável que conversa com o usuário pelo WhatsApp. Responda de forma breve, natural e útil."},
            {"role": "user", "content": message}
        ]

        client = get_openai_client()
        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', AI_CONFIG['default_model']),
            messages=messages,
            max_tokens=AI_CONFIG['max_tokens'],
            temperature=AI_CONFIG['temperature']
        )

        ai_response = response.choices[0].message.content.strip()

        # Validar resposta
        validation = validate_ai_response(ai_response)
        if not validation['valid']:
            logger.warning(f"Invalid AI response: {validation['error']}")
            return "Desculpe, houve um erro ao processar sua mensagem."

        return ai_response

    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Desculpe, houve um erro ao processar sua mensagem."

async def generate_ai_response_with_context(message: str, context_messages: list, system_prompt: str = None, product_radar = None) -> str:
    """
    Gera resposta da IA usando contexto completo da conversa

    Args:
        message: Mensagem do usuário
        context_messages: Mensagens do contexto
        system_prompt: Prompt do sistema (opcional)
        product_radar: Serviço de radar de produtos (opcional)

    Returns:
        str: Resposta da IA
    """
    try:
        # Pegar a última mensagem do usuário do contexto
        latest_message = extract_latest_user_message(context_messages, message)

        # Verificar se é uma consulta de produto para o RADAR
        product_query = detect_product_query(latest_message)

        if product_query and product_radar:
            logger.info(f"Product query detected with context: {product_query}")
            product_result = product_radar.comparar_precos(product_query)

            if "erro" not in product_result:
                # Formatar resposta com dados do produto
                response = format_product_response(product_result)
                return response

        # Preparar mensagens para OpenAI com contexto
        system_msg = system_prompt or "Você é um assistente virtual amigável que conversa com o usuário pelo WhatsApp. Responda de forma breve, natural e útil."
        messages_for_ai = prepare_messages_for_ai(system_msg, context_messages, latest_message)

        # Gerar resposta com contexto
        client = get_openai_client()
        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', AI_CONFIG['default_model']),
            messages=messages_for_ai,
            max_tokens=AI_CONFIG['max_tokens'],
            temperature=AI_CONFIG['temperature']
        )

        ai_response = response.choices[0].message.content.strip()

        # Validar resposta
        validation = validate_ai_response(ai_response)
        if not validation['valid']:
            logger.warning(f"Invalid AI response with context: {validation['error']}")
            return "Desculpe, houve um erro ao processar sua mensagem com contexto."

        return ai_response

    except Exception as e:
        logger.error(f"OpenAI error with context: {e}")
        return "Desculpe, houve um erro ao processar sua mensagem com contexto."

def format_product_response(product_result: dict) -> str:
    """
    Formata a resposta com dados do produto

    Args:
        product_result: Resultado da busca do produto

    Returns:
        str: Resposta formatada
    """
    melhor = product_result['melhor_opcao']

    resposta = f"""🎯 **{melhor['produto'].upper()}**

💰 **MELHOR OPÇÃO ENCONTRADA**
🏪 **{melhor['loja']}**
📍 [Localização da loja]
💵 **Preço: R$ {melhor['preco']}** ({melhor['unidade']})
⭐ **Marca:** {melhor['marca']}
📊 **Economia:** R$ {product_result['economia_total']['valor']} ({product_result['economia_total']['percentual']}%) mais barato

🔍 **COMPARAÇÃO DETALHADA**
"""

    for item in product_result['comparacao']:
        resposta += f"🏪 {item['loja']}: R$ {item['preco']}"
        if item['diferenca'] > 0:
            resposta += f" (+R$ {item['diferenca']})"
        resposta += "\n"

    resposta += f"""
💡 **DICAS PARA ECONOMIA**
✅ Verifique compatibilidade com seu veículo
✅ Compare marcas e garantias
✅ Consulte a loja sobre disponibilidade

🛒 **PRÓXIMOS PASSOS**
📞 Ligue para consultar disponibilidade
🕒 Horário: Seg-Sex 8h-18h
"""

    return resposta
