"""Aplicação principal FastAPI para o chatbot de vendas."""

import logging
import os
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from dotenv import load_dotenv

from app.services.openai_service import OpenAIService
from app.services.evolution_service import EvolutionService
from app.services.supabase_service import SupabaseService
from app.services.chatbot_router import ChatbotRouter
from app.handlers.webhook_handler import WebhookHandler

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO').upper())
logger = logging.getLogger(__name__)

# Configurar timezone
LOCAL_TIMEZONE = None
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

# Inicializar router (detecta segmento e roteia)
chatbot_router = ChatbotRouter(openai_service, supabase_service, evolution_service)
webhook_handler = WebhookHandler(chatbot_router)

# Configurar aplicação FastAPI
app = FastAPI(
    title="Radar - Chatbot de Vendas",
    description="API para processamento de mensagens WhatsApp para comparação de preços",
    version="2.0.0"
)

# Rota principal do webhook
@app.post("/")
async def webhook(request: Request):
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
