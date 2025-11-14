"""Aplicação principal FastAPI para o chatbot de materiais de construção."""

import logging
import os
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from dotenv import load_dotenv

from app.services.openai_service import OpenAIService
from app.services.evolution_service import EvolutionService
from app.services.supabase_service import SupabaseService
from app.services.chatbot_service import ChatbotService
from app.handlers.webhook_handler import WebhookHandler
from app.utils.formatters import LOCAL_TIMEZONE

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO').upper())
logger = logging.getLogger(__name__)

# Configurar timezone
LOCAL_TIMEZONE_STR = os.getenv("LOCAL_TIMEZONE", "America/Sao_Paulo")
try:
    LOCAL_TIMEZONE = ZoneInfo(LOCAL_TIMEZONE_STR)
except Exception:
    logger.warning("LOCAL_TIMEZONE inválido (%s); usando UTC", LOCAL_TIMEZONE_STR)
    LOCAL_TIMEZONE = None

# Inicializar serviços
openai_service = OpenAIService()
evolution_service = EvolutionService()

# Inicializar Supabase (opcional)
supabase_service = None
try:
    supabase_service = SupabaseService()
    logger.info("Supabase service iniciado")
except ValueError:
    logger.warning("Supabase não configurado; mensagens não serão persistidas")

# Inicializar serviços de negócio
chatbot_service = ChatbotService(openai_service, supabase_service, evolution_service)
webhook_handler = WebhookHandler(chatbot_service)

# Configurar aplicação FastAPI
app = FastAPI(
    title="Radar - Chatbot de Materiais de Construção",
    description="API para processamento de mensagens WhatsApp sobre materiais de construção",
    version="2.0.0"
)

# Configurações
DEBOUNCE_SECONDS = int(os.getenv("DEBOUNCE_SECONDS", "15"))

# Rota principal do webhook
@app.post("/")
async def webhook(request):
    """Endpoint principal para webhooks do WhatsApp."""
    return await webhook_handler.handle_webhook(request)

# Health check
@app.get("/health")
async def health_check():
    """Verificação de saúde da aplicação."""
    return {
        "status": "healthy",
        "services": {
            "openai": True,
            "evolution": True,
            "supabase": supabase_service is not None
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
