import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

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

DEBOUNCE_SECONDS = int(os.getenv("DEBOUNCE_SECONDS", "15"))
pending_tasks: Dict[str, asyncio.Task] = {}

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

        # If Supabase não está disponível, responder imediatamente
        if not supabase_service:
            response_text = await openai_service.generate_response(message=text)
            logger.info(f"Generated response: {response_text}")
            await send_whatsapp_message(user_id, response_text)
            return {"status": "processed"}

        created_at = _extract_created_at(message_data)
        message_id = key.get('id') or message_data.get('id') or ""

        await record_temp_message(
            user_id=user_id,
            content=text,
            role="user",
            message_id=message_id,
            created_at=created_at,
        )

        await schedule_user_processing(user_id)

        return {"status": "queued"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

async def send_whatsapp_message(number: str, text: str):
    try:
        await asyncio.to_thread(evolution_service.send_message, number, text)
    except Exception as e:
        logger.error(f"Error sending message: {e}")


async def log_message(user_id: str, content: str, role: str, created_at: Optional[str] = None) -> None:
    """Persist message in Supabase if service is available."""
    if not supabase_service:
        return

    try:
        payload = {
            "user_id": user_id,
            "role": role,
            "content": content,
            "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.to_thread(supabase_service.save_message, payload)
    except Exception as exc:
        logger.error("Erro ao salvar mensagem no Supabase: %s", exc)


async def record_temp_message(user_id: str, content: str, role: str, message_id: str, created_at: str) -> None:
    if not supabase_service:
        return

    payload = {
        "user_id": user_id,
        "role": role,
        "content": content,
        "message_id": message_id,
        "created_at": created_at,
    }
    await asyncio.to_thread(supabase_service.save_temp_message, payload)


async def schedule_user_processing(user_id: str) -> None:
    existing = pending_tasks.get(user_id)
    if existing and not existing.done():
        existing.cancel()

    task = asyncio.create_task(_debounce_runner(user_id))
    pending_tasks[user_id] = task


async def _debounce_runner(user_id: str) -> None:
    try:
        await asyncio.sleep(DEBOUNCE_SECONDS)
        await process_debounced_messages(user_id)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao processar debounce de %s: %s", user_id, exc)
    finally:
        pending_tasks.pop(user_id, None)


async def process_debounced_messages(user_id: str) -> None:
    if not supabase_service:
        return

    temp_messages = await asyncio.to_thread(supabase_service.get_temp_messages, user_id)
    if not temp_messages:
        return

    history: List[Dict[str, str]] = []
    recent_messages = await asyncio.to_thread(supabase_service.get_recent_messages, user_id, 20)

    for msg in sorted(recent_messages, key=_sort_key):
        if msg.get("content"):
            history.append({
                "role": msg.get("role", "user"),
                "content": msg["content"],
            })

    for temp in temp_messages:
        if temp.get("content"):
            history.append({
                "role": temp.get("role", "user"),
                "content": temp["content"],
            })

    response_text = await openai_service.generate_response(history=history)
    logger.info("Generated response after debounce for %s: %s", user_id, response_text)

    # Persist mensagens temporárias como histórico definitivo
    for temp in temp_messages:
        await log_message(
            user_id=user_id,
            content=temp.get("content", ""),
            role=temp.get("role", "user"),
            created_at=temp.get("created_at"),
        )

    await log_message(user_id, response_text, role="assistant")

    await asyncio.to_thread(supabase_service.delete_temp_messages, user_id)
    await send_whatsapp_message(user_id, response_text)


def _extract_created_at(message_data: dict) -> str:
    timestamp = message_data.get('messageTimestamp') or message_data.get('timestamp')
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc).isoformat()


def _sort_key(message: dict) -> str:
    created_at = message.get("created_at")
    if isinstance(created_at, str):
        return created_at
    return ""

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
