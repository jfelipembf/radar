#!/usr/bin/env python3
"""
Script para simular a requisição webhook que o usuário recebeu
"""
import asyncio
import json
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from fastapi.testclient import TestClient

def test_webhook_simulation():
    """Simula a requisição webhook recebida"""
    print("🧪 Simulando requisição webhook...\n")

    # Dados da requisição que o usuário recebeu
    webhook_data = {
        "event": "messages.upsert",
        "instance": "anota",
        "data": {
            "key": {
                "remoteJid": "557999371622@s.whatsapp.net",
                "fromMe": False,
                "id": "3B64E98B3C8E40852793"
            },
            "pushName": "Felipe Macedo",
            "status": "DELIVERY_ACK",
            "message": {
                "conversation": "ola, bom dia",
                "messageContextInfo": {
                    "deviceListMetadata": {
                        "senderKeyHash": "9c3FWJfpzCP69A==",
                        "senderTimestamp": "1761949562",
                        "recipientKeyHash": "FlzwxHNdQQCy4g==",
                        "recipientTimestamp": "1762372615"
                    },
                    "deviceListMetadataVersion": 2,
                    "messageSecret": "Ndite+SvoWo3PLeXhhEl99CpGmTepCCtfH1BnN6i5mg="
                }
            },
            "messageType": "conversation",
            "messageTimestamp": 1763039928,
            "instanceId": "516a733b-03da-4784-a972-eb398c8caf40",
            "source": "unknown"
        },
        "destination": "https://contrato-intelitec-radar.re1ifw.easypanel.host/",
        "date_time": "2025-11-13T10:18:48.827Z",
        "sender": "557998830315@s.whatsapp.net",
        "server_url": "https://evolution-evolution-api.re1ifw.easypanel.host",
        "apikey": "69836D24B400-44C9-A02A-FB563704833E"
    }

    print(f"📨 Enviando webhook: {json.dumps(webhook_data, indent=2)}\n")

    # Criar cliente de teste
    client = TestClient(app)

    # Enviar requisição POST
    response = client.post("/", json=webhook_data)

    print(f"📡 Resposta do servidor: {response.status_code}")
    print(f"📄 Corpo da resposta: {response.json()}\n")

    print("✅ Simulação concluída!")

if __name__ == "__main__":
    test_webhook_simulation()
