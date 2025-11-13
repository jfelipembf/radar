import os
import logging
import asyncio
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from openai import OpenAI
import requests
# from supabase import create_client

load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO').upper())
logger = logging.getLogger(__name__)

# Initialize clients
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

app = FastAPI()

EVOLUTION_URL = os.getenv('EVOLUTION_API_URL')
EVOLUTION_KEY = os.getenv('EVOLUTION_API_KEY')
EVOLUTION_INSTANCE = os.getenv('EVOLUTION_INSTANCE')

# Import Radar configuration
try:
    from app.config.radar_config import RADAR_SYSTEM_PROMPT, RADAR_CONFIG
    SYSTEM_PROMPT = RADAR_SYSTEM_PROMPT
    logger.info("Radar system prompt loaded successfully")
except ImportError:
    # Fallback to generic prompt if config not found
    SYSTEM_PROMPT = "Você é um assistente virtual amigável que conversa com o usuário pelo WhatsApp. Responda de forma breve, natural e útil."
    logger.warning("Radar config not found, using generic prompt")

# Import Radar product search
try:
    from radar_queries import RadarProductSearch
    radar_search = RadarProductSearch()
    logger.info("Radar product search loaded successfully")
except ImportError:
    radar_search = None
    logger.warning("Radar product search not available")

# Import Conversation Manager
try:
    from app.services.conversation_manager import conversation_manager
    logger.info("Conversation manager loaded successfully")
except ImportError:
    conversation_manager = None
    logger.warning("Conversation manager not available")

@app.post("/")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Received webhook: {data}")

        # Extract message details from the nested data
        if 'data' not in data:
            return {"status": "invalid_data"}

        message_data = data['data']

        # Extract message details
        key = message_data.get('key', {})
        remote_jid = key.get('remoteJid')
        from_me = key.get('fromMe', False)
        message = message_data.get('message', {})

        # Skip if message is from me to avoid loops
        if from_me:
            return {"status": "ignored"}

        # Extract text from message
        text = ""
        if 'conversation' in message:
            text = message.get('conversation', '')
        elif 'extendedTextMessage' in message:
            text = message['extendedTextMessage'].get('text', '')

        if not text:
            return {"status": "no_text"}

        # Get user phone number
        user_id = remote_jid.split('@')[0] if remote_jid else ""

        logger.info(f"Processing message from {user_id}: {text}")

        # Process incoming message with conversation manager
        if conversation_manager:
            is_first_today, context_messages = await conversation_manager.process_incoming_message(user_id, text)

            # Se for primeira mensagem do dia, enviar mensagem de boas-vindas
            if is_first_today:
                welcome_message = "🤖 *RADAR ATIVADO*\n\nOlá! Sou seu assistente inteligente de compras automotivas. Posso ajudar você a encontrar os melhores preços de peças e acessórios.\n\n💡 *Como funciona:*\n• Digite o nome da peça que procura\n• Compare preços automaticamente\n• Encontre as melhores ofertas\n\nVamos começar? O que você está procurando hoje?"
                await send_whatsapp_message(user_id, welcome_message)
                logger.info(f"Primeira mensagem do dia enviada para {user_id}")

            # Iniciar/cancelar timer de debounce
            await conversation_manager.start_debounce_timer(user_id, lambda: process_message_with_context(user_id, context_messages))
            return {"status": "debouncing"}

        else:
            # Fallback se conversation manager não estiver disponível
            response_text = await generate_ai_response(text)
            await send_whatsapp_message(user_id, response_text)
            return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

async def process_message_with_context(user_id: str, context_messages: list):
    """
    Processa mensagem após debounce, usando contexto de conversa
    """
    try:
        logger.info(f"Processando mensagem com contexto para {user_id}")

        # Obter contexto mais recente
        current_context = await conversation_manager.get_conversation_context(user_id, limit=10)

        # Gerar resposta com contexto
        response_text = await generate_ai_response_with_context("", current_context)

        # Salvar resposta no contexto
        await conversation_manager.process_outgoing_message(user_id, response_text)

        # Enviar resposta
        await send_whatsapp_message(user_id, response_text)
        logger.info(f"Resposta enviada para {user_id} após debounce")

    except Exception as e:
        logger.error(f"Erro no processamento com contexto: {e}")
        error_msg = "Desculpe, houve um erro ao processar sua mensagem. Tente novamente."
        await send_whatsapp_message(user_id, error_msg)

async def generate_ai_response_with_context(message: str, context_messages: list) -> str:
    """
    Gera resposta da IA usando contexto completo da conversa
    """
    try:
        # Pegar a última mensagem do usuário do contexto
        user_messages = [msg for msg in context_messages if msg.role == 'user']
        if user_messages:
            latest_message = user_messages[-1].content
        else:
            latest_message = message

        # Verificar se é uma consulta de produto para o RADAR
        product_query = await detect_product_query(latest_message)

        if product_query and radar_search:
            # Buscar produto no RADAR
            logger.info(f"Product query detected with context: {product_query}")
            product_result = radar_search.comparar_precos(product_query)

            if "erro" not in product_result:
                # Formatar resposta com dados do produto
                response = format_product_response(product_result)
                return response

        # Preparar mensagens para OpenAI com contexto
        messages_for_ai = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Adicionar contexto da conversa (últimas mensagens)
        for ctx_msg in context_messages[-8:]:  # Últimas 8 mensagens para não exceder limite
            messages_for_ai.append({
                "role": ctx_msg.role,
                "content": ctx_msg.content
            })

        # Adicionar mensagem atual se não estiver no contexto
        if latest_message and not any(msg['content'] == latest_message for msg in messages_for_ai):
            messages_for_ai.append({"role": "user", "content": latest_message})

        # Gerar resposta com contexto
        response = openai_client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=messages_for_ai
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"OpenAI error with context: {e}")
        return "Desculpe, houve um erro ao processar sua mensagem com contexto."

async def generate_ai_response(message: str) -> str:
    try:
        # Verificar se é uma consulta de produto para o RADAR
        product_query = await detect_product_query(message)

        if product_query and radar_search:
            # Buscar produto no RADAR
            logger.info(f"Product query detected: {product_query}")
            product_result = radar_search.comparar_precos(product_query)

            if "erro" not in product_result:
                # Formatar resposta com dados do produto
                response = format_product_response(product_result)
                return response

        # Resposta normal da IA (sem contexto)
        response = openai_client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Desculpe, houve um erro ao processar sua mensagem."

async def detect_product_query(message: str) -> str:
    """Detecta se a mensagem é uma consulta de produto"""
    message_lower = message.lower()

    # Palavras-chave que indicam busca de produto
    product_keywords = [
        'quanto custa', 'preço', 'valor', 'onde comprar', 'mais barato',
        'procurando', 'preciso de', 'quero comprar', 'buscando',
        'filtro', 'óleo', 'pastilha', 'freio', 'bateria', 'correia',
        'lâmpada', 'aditivo', 'palheta'
    ]

    # Verificar se contém palavras-chave
    for keyword in product_keywords:
        if keyword in message_lower:
            # Extrair possível nome do produto
            return extract_product_name(message)

    return None

def extract_product_name(message: str) -> str:
    """Extrai o nome do produto da mensagem"""
    # Mapeamento de termos para nomes de produtos
    product_mappings = {
        'óleo': 'óleo',
        'filtro de óleo': 'filtro de óleo',
        'filtro de ar': 'filtro de ar',
        'pastilha de freio': 'pastilha de freio',
        'fluido de freio': 'fluido de freio',
        'lâmpada': 'lâmpada',
        'aditivo': 'aditivo',
        'palheta': 'palheta',
        'bateria': 'bateria',
        'correia': 'correia'
    }

    message_lower = message.lower()

    for term, product in product_mappings.items():
        if term in message_lower:
            return product

    # Retornar a própria mensagem se não encontrar mapeamento específico
    return message.strip()

def format_product_response(product_result: dict) -> str:
    """Formata a resposta com dados do produto"""
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

async def send_whatsapp_message(number: str, text: str):
    url = f"{EVOLUTION_URL}message/sendText/{EVOLUTION_INSTANCE}"
    headers = {
        'Content-Type': 'application/json',
        'apikey': EVOLUTION_KEY
    }
    data = {
        "number": number,
        "text": text
    }
    logger.info(f"Sending message to {number}: {text}")
    try:
        response = requests.post(url, headers=headers, json=data)
        logger.info(f"Send response status: {response.status_code}, body: {response.text}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
