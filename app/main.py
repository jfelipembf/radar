import os
import logging
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from dotenv import load_dotenv

from app.services.openai_service import OpenAIService
from app.services.evolution_service import EvolutionService
from app.services.supabase_service import SupabaseService


load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO').upper())
logger = logging.getLogger(__name__)

LOCAL_TIMEZONE = os.getenv("LOCAL_TIMEZONE", "America/Sao_Paulo")
try:
    LOCAL_ZONE = ZoneInfo(LOCAL_TIMEZONE)
except Exception:  # noqa: BLE001
    logger.warning("LOCAL_TIMEZONE inválido (%s); usando UTC", LOCAL_TIMEZONE)
    LOCAL_ZONE = timezone.utc

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

    search_source = consolidated["content"] if consolidated else _latest_user_content(history)
    catalog_context = await _build_product_context(search_source)
    catalog_message = None
    if catalog_context:
        model_context = catalog_context.get("model")
        catalog_message = catalog_context.get("user")
        if model_context:
            history.append({"role": "system", "content": model_context})

    if catalog_message:
        logger.info("Catálogo Supabase encontrado para %s; respondendo com dados estruturados", user_id)
        response_text = catalog_message
    else:
        logger.info("Nenhum catálogo disponível para %s; delegando resposta à OpenAI", user_id)
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

    now_local = datetime.now(LOCAL_ZONE)

    should_send = False
    if not latest_message:
        should_send = True
    else:
        last_created_at = latest_message.get("created_at")
        last_dt = _parse_created_at(last_created_at)
        if not last_dt:
            should_send = True
        else:
            last_local = last_dt.astimezone(LOCAL_ZONE)
            if last_local.date() != now_local.date():
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


def _extract_search_terms(text: Optional[str]) -> List[str]:
    if not text:
        return []

    normalized = text.strip().lower()
    if not normalized:
        return []

    sanitized_text = "".join(ch if ch.isalnum() or ch in {" ", "-", "_"} else " " for ch in normalized)
    words = [word for word in sanitized_text.split() if len(word) > 2]
    if not words:
        return []

    terms: List[str] = []
    seen = set()

    phrase = " ".join(words)
    if phrase and phrase not in seen:
        terms.append(phrase)
        seen.add(phrase)

    for word in words:
        if word not in seen:
            terms.append(word)
            seen.add(word)
    return terms[:10]


async def _should_search_products(message: str) -> bool:
    """Pergunta à IA se deve buscar produtos baseado na mensagem do usuário."""
    if not openai_service:
        return False

    prompt = f"""
Você é um assistente de chatbot para uma loja de materiais de construção.

Analise a seguinte mensagem do usuário e determine se ela indica interesse em:
- Comprar ou consultar preços de materiais/produtos de construção
- Perguntar sobre disponibilidade de produtos
- Buscar informações sobre itens da loja

IMPORTANTE: Responda apenas com "SIM" ou "NAO" (sem aspas).

Mensagem do usuário: "{message}"

A mensagem indica interesse em produtos de construção?
""".strip()

    try:
        response = await openai_service.generate_response(message=prompt)
        result = response.strip().upper()
        logger.debug("Catálogo → IA resposta para '%s': %s", message, result)
        return result == "SIM"
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao consultar IA sobre busca de produtos: %s", exc)
        return False


async def _extract_product_names(message: str) -> List[str]:
    """Extrai nomes de produtos específicos mencionados na mensagem usando IA."""
    if not openai_service:
        return []

    prompt = f"""
Você é um assistente especializado em identificar produtos de construção mencionados em mensagens.

Analise a seguinte mensagem do usuário e extraia APENAS os nomes dos produtos de construção mencionados especificamente.

IMPORTANTE:
- Liste apenas produtos que são claramente mencionados
- Use nomes simples e comuns de produtos de construção
- Ignore verbos, adjetivos e outras palavras que não sejam nomes de produtos
- Se não houver produtos específicos mencionados, retorne lista vazia
- Responda apenas com uma lista separada por vírgulas, sem explicações

Exemplos:
Mensagem: "Quanto custa o cimento e a areia?"
Resposta: cimento,areia

Mensagem: "Preciso de tinta acrílica branca e tijolos"
Resposta: tinta acrílica,tijolo

Mensagem: "Oi, tudo bem?"
Resposta: (lista vazia)

Mensagem: "{message}"

Quais produtos de construção são mencionados?
""".strip()

    try:
        response = await openai_service.generate_response(message=prompt)
        result = response.strip()
        if not result or result.lower() in ['nenhum', 'vazio', 'empty', 'none', '(lista vazia)']:
            return []

        # Processar a resposta em lista
        products = [p.strip().lower() for p in result.split(',') if p.strip()]
        logger.debug("Catálogo → Produtos extraídos pela IA: %s", products)
        return products
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao extrair produtos pela IA: %s", exc)
        return []


async def _build_product_context(search_text: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
    if not supabase_service or not search_text:
        return None

    # Primeiro, perguntar à IA se deve buscar produtos
    should_search = await _should_search_products(search_text)
    if not should_search:
        logger.info("Catálogo → IA decidiu não buscar produtos para: %s", search_text)
        return None

    # Extrair produtos específicos mencionados usando IA
    product_names = await _extract_product_names(search_text)
    if not product_names:
        logger.info("Catálogo → Nenhum produto específico identificado em: %s", search_text)
        return None

    logger.debug("Catálogo → produtos identificados: %s", product_names)

    try:
        # Buscar produtos específicos no Supabase
        products = await asyncio.to_thread(
            supabase_service.get_products,
            "material_construcao",
            product_names,  # Usar nomes de produtos ao invés de termos genéricos
            40,
        )

        # Filtrar apenas produtos que contenham os nomes identificados
        filtered_products = []
        for product in products:
            product_name = product.get("name", "").lower()
            if any(prod_name in product_name for prod_name in product_names):
                filtered_products.append(product)

        logger.info("Catálogo → %d produtos retornados, %d após filtro específico", len(products), len(filtered_products))

        if not filtered_products:
            logger.info("Catálogo → nenhum produto correspondente após filtro")
            return None

        model_context, user_message = _format_product_catalog(filtered_products)
        if not model_context and not user_message:
            logger.info("Catálogo → nenhum produto formatado para os termos %s", product_names)
        return {"model": model_context, "user": user_message}
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao buscar catálogo de produtos: %s", exc)
        return None


def _format_product_catalog(products: List[Dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
    instruction_lines: List[str] = [
        "INSTRUÇÕES DE CATÁLOGO:",
        "- Utilize exclusivamente as informações listadas abaixo.",
        "- Não invente lojas, preços, telefones ou condições de entrega.",
        "- Se o item solicitado não aparecer aqui, informe ao cliente que o Supabase não retornou resultados e solicite novos detalhes.",
    ]

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for product in products:
        name = product.get("name")
        if not name:
            continue
        grouped[name].append(product)

    if not grouped:
        instruction_lines.append("")
        instruction_lines.append("Nenhum produto correspondente foi encontrado no Supabase para esta consulta.")
        user_message = (
            "Não encontrei produtos correspondentes no catálogo do Supabase para essa descrição. "
            "Pode tentar informar o item com outros detalhes (ex.: nome completo, marca, unidade)?"
        )
        logger.info("Catálogo → nenhuma correspondência para a consulta atual")
        return "\n".join(instruction_lines), user_message

    instruction_lines.append("")
    instruction_lines.append("CATÁLOGO SUPABASE (ordenado por preço crescente por produto):")

    user_lines: List[str] = [
        "Encontrei as seguintes ofertas no catálogo do Supabase:",
    ]

    for product_name in sorted(grouped.keys()):
        instruction_lines.append("")
        instruction_lines.append(f"Produto: {product_name}")

        entries = []
        for product in grouped[product_name]:
            store_info = product.get("store") or {}
            store_name = store_info.get("name") or "Loja"
            phone = _format_phone(product.get("store_phone") or store_info.get("phone"))
            price_value = _coerce_price(product.get("price"))
            price_str = _format_currency(price_value)
            unit_label = product.get("unit_label") or "unidade"
            updated_at = _parse_created_at(product.get("updated_at"))
            updated_str = _format_date(updated_at)
            delivery = product.get("delivery_info") or "Entrega a combinar"

            entries.append({
                "store_name": store_name,
                "phone": phone,
                "price": price_value,
                "price_str": price_str,
                "unit_label": unit_label,
                "updated": updated_str,
                "delivery": delivery,
            })

        entries = [entry for entry in entries if entry["price"] > 0]
        if not entries:
            continue

        entries.sort(key=lambda item: item["price"])

        user_lines.append("")
        user_lines.append(f"Produto: {product_name}")

        for index, entry in enumerate(entries):
            highlight = " ← melhor preço" if index == 0 else ""
            phone_part = f" (WhatsApp: {entry['phone']})" if entry["phone"] else ""
            instruction_lines.append(
                f"• {entry['store_name']}{phone_part}: {entry['price_str']} por {entry['unit_label']} | atual. {entry['updated']} | frete: {entry['delivery']}{highlight}"
            )
            user_lines.append(
                f"  • {entry['store_name']}: {entry['price_str']} por {entry['unit_label']} (atualizado {entry['updated']}){highlight}"
            )

        if len(entries) > 1:
            economy = entries[1]["price"] - entries[0]["price"]
            if economy > 0:
                user_lines.append(
                    f"  Economia aproximada em relação à segunda opção: { _format_currency(economy) }"
                )

    if not user_lines or len(user_lines) == 1:
        logger.info("Catálogo → produtos encontrados, porém não formatados para resposta")
        return "\n".join(instruction_lines), None

    model_context = "\n".join(instruction_lines)
    user_message = "\n".join(user_lines)
    return model_context, user_message


def _coerce_price(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            cleaned = value.replace("R$", "").strip()
            cleaned = cleaned.replace(".", "").replace(",", ".")
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def _format_currency(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _format_date(dt: Optional[datetime]) -> str:
    if not dt:
        return "-"
    return dt.astimezone(LOCAL_ZONE).strftime("%d/%m/%Y")


def _format_phone(phone: Optional[str]) -> str:
    if not phone:
        return ""
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if not digits:
        return ""
    if not digits.startswith("55"):
        digits = f"55{digits}"
    return digits


def _latest_user_content(history: List[Dict[str, Any]]) -> Optional[str]:
    for message in reversed(history):
        if message.get("role") == "user" and message.get("content"):
            return str(message["content"])
    return None


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
