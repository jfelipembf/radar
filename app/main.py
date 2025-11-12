import os
import logging
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

        # Generate AI response
        response_text = await generate_ai_response(text)
        logger.info(f"Generated response: {response_text}")

        # Send response back
        await send_whatsapp_message(user_id, response_text)

        return {"status": "processed"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

async def generate_ai_response(message: str) -> str:
    try:
        response = openai_client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL'),
            messages=[{"role": "user", "content": message}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Desculpe, houve um erro ao processar sua mensagem."

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
