import os
import logging
import asyncio
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Importar módulos
from app.modules.whatsapp import send_whatsapp_message, validate_webhook_data, extract_message_data, should_process_message, format_error_response
from app.modules.message_processor import process_message_async
from app.modules.ai_service import generate_ai_response, generate_ai_response_with_context
from app.modules.product_radar import compare_prices

# Carregar configurações
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO').upper())
logger = logging.getLogger(__name__)

# Inicializar serviços
try:
    from app.services.conversation_manager import conversation_manager
    logger.info("Conversation manager loaded successfully")
except ImportError:
    conversation_manager = None
    logger.warning("Conversation manager not available")

# Inicializar FastAPI
app = FastAPI()

# Configurações globais
SYSTEM_PROMPT = "Você é um assistente virtual amigável que conversa com o usuário pelo WhatsApp. Responda de forma breve, natural e útil."

@app.post("/")
async def webhook(request: Request):
    """
    Endpoint principal do webhook do WhatsApp
    """
    try:
        data = await request.json()
        logger.info(f"Received webhook: {data}")

        # Validar dados do webhook
        validation = validate_webhook_data(data)
        if not validation['valid']:
            return {"status": validation['status']}

        # Extrair informações da mensagem
        message_info = extract_message_data(data)

        # Verificar se deve processar a mensagem
        processing_decision = should_process_message(message_info)
        if not processing_decision['should_process']:
            return {"status": processing_decision['status']}

        # Processar mensagem de forma assíncrona
        asyncio.create_task(
            process_message_async(
                user_id=message_info['user_id'],
                text=message_info['text'],
                conversation_manager=conversation_manager,
                ai_service={'generate_ai_response': generate_ai_response, 'generate_ai_response_with_context': generate_ai_response_with_context},
                whatsapp_service={'send_whatsapp_message': send_whatsapp_message},
                system_prompt=SYSTEM_PROMPT,
                product_radar={'compare_prices': compare_prices}
            )
        )

        # Retornar sucesso imediatamente para Evolution API
        return {"status": "received"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return format_error_response(e)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
