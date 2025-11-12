# WhatsApp AI Automation

Este projeto configura uma automação para WhatsApp usando Evolution API e OpenAI.

## Instalação

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Certifique-se de que o arquivo `.env` está configurado com suas chaves.

## Teste

Para testar localmente, use ngrok para expor o servidor:

1. Instale ngrok: `brew install ngrok` (no macOS)

2. Execute o servidor: `python app/main.py`

3. Em outro terminal: `ngrok http 8000`

4. Copie a URL do ngrok (ex: https://abcd.ngrok.io) e configure no webhook da Evolution API para `https://abcd.ngrok.io/webhook`

5. Envie uma mensagem no WhatsApp e veja a resposta.

## Deploy no Easypanel

1. Faça upload do código para um repositório Git (GitHub, GitLab, etc.).

2. No painel do Easypanel, crie um novo projeto.

3. Selecione "Deploy from Git" e conecte seu repositório.

4. Configure as variáveis de ambiente (OPENAI_API_KEY, etc.) no painel do Easypanel.

5. O Dockerfile será usado automaticamente para build e deploy.

6. Após o deploy, copie a URL gerada e configure no webhook da Evolution API.

## Funcionamento

- Quando uma mensagem é recebida no WhatsApp, o Evolution API envia um webhook para o seu servidor.
- O servidor extrai o texto da mensagem e envia para a OpenAI para gerar uma resposta.
- A resposta é enviada de volta via WhatsApp usando a Evolution API.

## Próximos Passos

- Adicionar armazenamento de histórico de conversas no Supabase.
- Melhorar o tratamento de mensagens (mídia, etc.).
- Adicionar autenticação e validação.
