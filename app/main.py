import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "40"))
PRESENCE_EXTRA_SECONDS = int(os.getenv("PRESENCE_EXTRA_SECONDS", "5"))

pending_tasks: Dict[str, Dict[str, Any]] = {}
_generation_counter: Dict[str, int] = {}

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

        await maybe_send_daily_greeting(user_id)

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


async def set_presence(user_id: str, presence: str, delay_ms: Optional[int] = None) -> None:
    try:
        await asyncio.to_thread(evolution_service.send_presence, user_id, presence, delay_ms)
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao atualizar presença (%s) para %s: %s", presence, user_id, exc)


async def schedule_user_processing(user_id: str) -> None:
    generation = _generation_counter.get(user_id, 0) + 1
    _generation_counter[user_id] = generation

    existing = pending_tasks.get(user_id)
    if existing:
        existing_task = existing.get("task")
        if existing_task and not existing_task.done():
            existing_task.cancel()

    task = asyncio.create_task(_debounce_runner(user_id, generation))
    pending_tasks[user_id] = {"task": task, "generation": generation}

    typing_window_ms = int((DEBOUNCE_SECONDS + PRESENCE_EXTRA_SECONDS) * 1000)
    asyncio.create_task(set_presence(user_id, "composing", typing_window_ms))


async def _debounce_runner(user_id: str, generation: int) -> None:
    try:
        await asyncio.sleep(DEBOUNCE_SECONDS)
        current = pending_tasks.get(user_id)
        if not current or current.get("generation") != generation:
            return
        await process_debounced_messages(user_id)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao processar debounce de %s: %s", user_id, exc)
    finally:
        current = pending_tasks.get(user_id)
        if current and current.get("generation") == generation:
            pending_tasks.pop(user_id, None)


async def process_debounced_messages(user_id: str) -> None:
    if not supabase_service:
        return

    temp_messages = await asyncio.to_thread(supabase_service.get_temp_messages, user_id)
    if not temp_messages:
        return

    history: List[Dict[str, str]] = []
    recent_messages = await asyncio.to_thread(
        supabase_service.get_recent_messages,
        user_id,
        HISTORY_LIMIT,
    )

    for msg in sorted(recent_messages, key=_sort_key):
        if msg.get("content"):
            history.append({
                "role": msg.get("role", "user"),
                "content": msg["content"],
            })

    consolidated = _consolidate_temp_messages(temp_messages)
    if consolidated:
        history.append(consolidated)

    response_text = await openai_service.generate_response(history=history)
    logger.info("Generated response after debounce for %s: %s", user_id, response_text)

    temp_ids: List[str] = []
    if consolidated:
        for temp in temp_messages:
            temp_id = temp.get("id")
            if temp_id:
                temp_ids.append(str(temp_id))

        await log_message(
            user_id=user_id,
            content=consolidated["content"],
            role=consolidated["role"],
            created_at=consolidated.get("created_at"),
        )

    await log_message(user_id, response_text, role="assistant")

    await asyncio.to_thread(supabase_service.delete_temp_messages, temp_ids)
    await send_whatsapp_message(user_id, response_text)
    await set_presence(user_id, "paused")


async def maybe_send_daily_greeting(user_id: str) -> None:
    if not supabase_service or not user_id:
        return

    try:
        latest_message = await asyncio.to_thread(supabase_service.get_latest_message, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao verificar primeira mensagem do dia para %s: %s", user_id, exc)
        return

    now_utc = datetime.now(timezone.utc)

    should_send = False
    if not latest_message:
        should_send = True
    else:
        last_created_at = latest_message.get("created_at")
        last_dt = _parse_created_at(last_created_at)
        if not last_dt or last_dt.date() != now_utc.date():
            should_send = True

    if not should_send:
        return

    greeting = "Radar ativado 🚨"
    await log_message(user_id, greeting, role="assistant")
    await send_whatsapp_message(user_id, greeting)


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


def _consolidate_temp_messages(messages: List[dict]) -> Optional[Dict[str, str]]:
    if not messages:
        return None

    ordered = sorted(messages, key=_sort_key)
    texts = [msg.get("content", "") for msg in ordered if msg.get("content")]
    if not texts:
        return None

    created_at = ordered[0].get("created_at")
    role = ordered[0].get("role", "user")
    return {
        "role": role,
        "content": " ".join(texts).strip(),
        "created_at": created_at,
    }


def _parse_created_at(value: Optional[str]) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None

    normalized = value
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
