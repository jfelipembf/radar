"""Regras de negócio específicas para materiais de construção."""

import logging

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.openai_service import OpenAIService
    from app.services.supabase_service import SupabaseService

from app.business.message_templates import format_interactive_catalog

logger = logging.getLogger(__name__)


async def should_search_products(message: str, openai_service: "OpenAIService") -> bool:
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
        return result == "SIM"
    except Exception:
        return False


async def extract_product_names(message: str, openai_service: "OpenAIService") -> List[str]:
    """Extrai nomes de produtos específicos mencionados na mensagem usando IA melhorada."""
    if not openai_service:
        return []

    prompt = f"""
Você é um assistente especializado em identificar produtos de construção mencionados em mensagens.

Analise a seguinte mensagem do usuário e extraia APENAS os nomes dos produtos de construção mencionados especificamente.

IMPORTANTE:
- Liste apenas produtos que são claramente mencionados
- Use nomes simples e comuns de produtos de construção
- Corrija automaticamente erros de digitação comuns
- Ignore verbos, adjetivos e outras palavras que não sejam nomes de produtos
- Se não houver produtos específicos mencionados, retorne lista vazia
- Responda apenas com uma lista separada por vírgulas, sem explicações

EXEMPLOS DE CORREÇÃO:
- "caida dagua" → "caixa d'água"
- "cimento" → "cimento"
- "tinta" → "tinta"
- "massa acrilica" → "massa acrílica"
- "areia" → "areia"
- "tijolo" → "tijolo"
- "argamassa" → "argamassa"

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
        return products
    except Exception:
        return []


def format_product_catalog(products: List[dict], supabase_service: "SupabaseService") -> tuple[Optional[str], Optional[str]]:
    """Formata catálogo de produtos para exibição com opções interativas."""
    instruction_lines: List[str] = [
        "INSTRUÇÕES DE CATÁLOGO:",
        "- Utilize exclusivamente as informações listadas abaixo.",
        "- Não invente lojas, preços, telefones ou condições de entrega.",
        "- Se o item solicitado não aparecer aqui, informe ao cliente que o Supabase não retornou resultados e solicite novos detalhes.",
    ]

    # Usar o novo template interativo
    user_message = format_interactive_catalog(products, supabase_service)

    if not user_message:
        instruction_lines.append("")
        instruction_lines.append("Nenhum produto correspondente foi encontrado no Supabase para esta consulta.")
        user_message = (
            "Não encontrei produtos correspondentes no catálogo do Supabase para essa descrição. "
            "Pode tentar informar o item com outros detalhes (ex.: nome completo, marca, unidade)?"
        )
        return "\n".join(instruction_lines), user_message

    # Para o contexto do modelo, manter informações básicas
    instruction_lines.append("")
    instruction_lines.append("CATÁLOGO INTERATIVO - O usuário pode escolher opções 1, 2 ou 3.")

    model_context = "\n".join(instruction_lines)
    return model_context, user_message


async def analyze_product_variations(products: List[Dict[str, Any]], openai_service, conversation_history: Optional[List[Dict[str, str]]] = None, clarified_categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """Analisa variações dos produtos encontrados usando IA pura com contexto conversacional."""

    if not products or len(products) <= 1:
        return {"needs_clarification": False, "variations": {}, "message": ""}

    # Preparar contexto conversacional
    conversation_context = ""
    if conversation_history:
        recent_messages = conversation_history[-10:]  # Últimas 10 mensagens para contexto
        conversation_context = "\n".join([
            f"{'Cliente' if msg.get('role') == 'user' else 'Sistema'}: {msg.get('content', '')}"
            for msg in recent_messages
        ])

    # Usar IA pura para categorizar e analisar variações baseadas nas descrições reais
    clarified_text = f"CATEGORIAS JÁ ESCLARECIDAS: {', '.join(clarified_categories) if clarified_categories else 'nenhuma'}"

    prompt = f"""
Você é um assistente inteligente de compras de materiais de construção. Analise TODOS os produtos encontrados e identifique o que o usuário está pedindo.

{clarified_text}

LISTA COMPLETA DE TODOS OS PRODUTOS ENCONTRADOS:
{chr(10).join(f"• {p.get('name', '')} - Descrição: {p.get('description', '')} - Preço: R$ {p.get('price', 'N/A')}" for i, p in enumerate(products))}

TAREFA PRINCIPAL:
Analise todos os produtos acima e determine se há ALGUM produto que ainda precisa de esclarecimento do usuário.

INSTRUÇÕES DETALHADAS:
1. OLHE todos os produtos da lista acima
2. IDENTIFIQUE produtos que são muito similares mas têm diferenças importantes
3. IGNORE produtos que já foram esclarecidos: {', '.join(clarified_categories) if clarified_categories else 'nenhuma'}
4. Se encontrar produtos similares que precisam distinção, pergunte sobre o PRIMEIRO grupo encontrado
5. Seja ESPECÍFICO nas suas perguntas - mencione as opções reais encontradas

EXEMPLOS DE QUANDO PERGUNTAR:
- Vários tipos de cimento (CP-II, CP-III, CP-V) → "Qual tipo de cimento você quer?"
- Várias capacidades de caixa d'água (500L, 1000L, 2000L) → "Qual capacidade da caixa d'água?"
- Vários tipos de areia (lavada, grossa) → "Qual tipo de areia?"

EXEMPLOS DE QUANDO NÃO PERGUNTAR:
- Mesmo produto em lojas diferentes (não é variação)
- Diferenças só de preço (não é variação)
- Todos os produtos são claramente distintos
- Categoria já foi esclarecida

ANÁLISE LIVRE:
Baseie sua decisão APENAS nos produtos listados acima. Não assuma variações que não existem nos dados.

RESPONDA APENAS com JSON:
{{
    "needs_clarification": true/false,
    "clarification_message": "Pergunta específica sobre as variações encontradas nos produtos",
    "category_to_clarify": "categoria identificada que precisa esclarecimento",
    "detected_options": ["opção real 1", "opção real 2", "opção real 3"],
    "reasoning": "breve explicação de quais produtos similares foram encontrados"
}}

Se NÃO HÁ NENHUMA variação significativa a esclarecer, retorne:
{{"needs_clarification": false, "clarification_message": "", "category_to_clarify": "", "detected_options": [], "reasoning": "todos os produtos são claramente distintos ou categorias já esclarecidas"}}
"""

    try:
        response = await openai_service.generate_response(message=prompt)
        result = response.strip()
        logger.info(f"IA análise de variações - Resposta completa: {result}")
        logger.info(f"IA análise de variações - Tamanho da resposta: {len(result)} caracteres")

        # Tentar fazer parse do JSON
        import json
        try:
            analysis = json.loads(result)
            logger.info(f"IA análise de variações - Parsed: needs_clarification={analysis.get('needs_clarification')}, category={analysis.get('category_to_clarify')}")
        except json.JSONDecodeError:
            logger.warning(f"Falha no parse JSON da análise de variações: {result}")
            return {"needs_clarification": False, "variations": {}, "message": ""}

        # Adaptar para o formato esperado
        if analysis.get("needs_clarification"):
            # Para compatibilidade, criar o formato antigo baseado no novo
            category_indices = []  # IA agora não retorna índices, trabalha com descrições
            category_products = products  # Mantém todos os produtos, IA filtrará depois

            return {
                "needs_clarification": True,
                "variations": {analysis.get("category_to_clarify", "produto"): {
                    "products": category_products,
                    "detected_variations": analysis.get("detected_options", [])
                }},
                "message": analysis.get("clarification_message", ""),
                "current_category": analysis.get("category_to_clarify", ""),
                "total_products": len(products)
            }
        else:
            return {"needs_clarification": False, "variations": {}, "message": ""}

    except Exception as exc:
        logger.error(f"Erro na análise de variações com IA: {exc}")
        return {"needs_clarification": False, "variations": {}, "message": ""}


__all__ = [
    "should_search_products",
    "extract_product_names",
    "format_product_catalog",
    "analyze_product_variations",
]
