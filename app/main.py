import os
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request
from dotenv import load_dotenv

from app.services.openai_service import OpenAIService
from app.services.evolution_service import EvolutionService
from app.services.supabase_service import SupabaseService


load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO').upper())
logger = logging.getLogger(__name__)

# Initialize services
openai_service = OpenAIService()
evolution_service = EvolutionService()

try:
    supabase_service: Optional[SupabaseService] = SupabaseService()
    logger.info("Supabase service iniciado")
except ValueError:
    supabase_service = None
    logger.warning("Supabase não configurado; mensagens não serão persistidas")

app = FastAPI()

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

        # Persist incoming message
        await log_message(user_id, text, role="user")

        # Generate AI response
        response_text = await openai_service.generate_response(text)
        logger.info(f"Generated response: {response_text}")

        # Send response back
        await send_whatsapp_message(user_id, response_text)

        # Persist outgoing message
        await log_message(user_id, response_text, role="assistant")

        return {"status": "processed"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

async def send_whatsapp_message(number: str, text: str):
    try:
        evolution_service.send_message(number, text)
    except Exception as e:
        logger.error(f"Error sending message: {e}")


async def log_message(user_id: str, content: str, role: str) -> None:
    """Persist message in Supabase if service is available."""
    if not supabase_service:
        return

    try:
        supabase_service.save_message(
            {
                "user_id": user_id,
                "role": role,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:
        logger.error("Erro ao salvar mensagem no Supabase: %s", exc)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
