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


async def extract_product_specifications(message: str, product_names: List[str], openai_service: "OpenAIService") -> Dict[str, Optional[str]]:
    """Extrai especificações de produtos mencionados na mensagem usando IA.
    
    Args:
        message: Mensagem do usuário
        product_names: Lista de produtos identificados
        openai_service: Serviço OpenAI
        
    Returns:
        Dict com produto como chave e especificação como valor
        Exemplo: {"caixa d'água": "1000L", "cimento": "CP-II", "areia": "lavada"}
    """
    if not openai_service or not product_names:
        return {}

    products_list = ", ".join(product_names)
    
    prompt = f"""
Você é um assistente especializado em identificar especificações de produtos de construção.

Analise a mensagem do usuário e identifique se há ESPECIFICAÇÕES TÉCNICAS mencionadas para cada produto.

PRODUTOS IDENTIFICADOS: {products_list}

MENSAGEM: "{message}"

TAREFA:
Para cada produto, identifique se o usuário especificou:
- Capacidade/Volume (ex: 1000L, 500L, 2000L, mil litros, dois mil litros)
- Tipo/Modelo (ex: CP-II, CP-III, CP-V, cp2, cp 2)
- Característica (ex: lavada, grossa, fina)
- Tamanho/Dimensão (ex: 50kg, 20kg, 6mm, 8mm)
- Quantidade/Medida (ex: 5m3, 2 sacos, 10 unidades)
- Qualquer outra especificação técnica relevante

REGRAS IMPORTANTES:
1. Se o usuário NÃO especificou algo para um produto, retorne "null" para ele
2. Normalize as especificações:
   - "mil litros" → "1000L"
   - "dois mil litros" → "2000L"
   - "cp 2" ou "cp-ii" → "CP-II"
   - "5m3" ou "5 metros cúbicos" → "5m3"
3. Procure por números e unidades próximos ao nome do produto
4. Seja preciso e extraia exatamente o que foi mencionado
5. NÃO invente especificações que não estão na mensagem

RESPONDA APENAS com JSON válido no formato:
{{
  "produto1": "especificação" ou null,
  "produto2": "especificação" ou null
}}

EXEMPLOS:

Mensagem: "preciso de caixa dagua de mil litros e cimento"
Produtos: ["caixa d'água", "cimento"]
Resposta: {{"caixa d'água": "1000L", "cimento": null}}

Mensagem: "preciso de ua caida dagua, de mil litros, 2 sacos de cimento e 5m3 de areia"
Produtos: ["caixa d'água", "cimento", "areia"]
Resposta: {{"caixa d'água": "1000L", "cimento": null, "areia": null}}

Mensagem: "quero cimento cp-ii 50kg e areia lavada"
Produtos: ["cimento", "areia"]
Resposta: {{"cimento": "CP-II 50kg", "areia": "lavada"}}

Mensagem: "preciso de tijolo e argamassa"
Produtos: ["tijolo", "argamassa"]
Resposta: {{"tijolo": null, "argamassa": null}}
""".strip()

    try:
        response = await openai_service.generate_response(message=prompt)
        result = response.strip()
        
        logger.info(f"IA - Resposta bruta de especificações: {result}")
        
        # Parse JSON
        import json
        
        # Tentar limpar a resposta se vier com markdown
        if result.startswith("```"):
            # Remover blocos de código markdown
            result = result.replace("```json", "").replace("```", "").strip()
            logger.info(f"IA - Resposta limpa: {result}")
        
        specifications = json.loads(result)
        logger.info(f"IA - Especificações parseadas: {specifications}")
        
        # Filtrar apenas especificações não-null
        filtered = {k: v for k, v in specifications.items() if v is not None}
        logger.info(f"IA - Especificações filtradas (não-null): {filtered}")
        
        return filtered
    except Exception as exc:
        logger.error(f"Erro ao extrair especificações: {exc}")
        logger.error(f"Resposta da IA que causou erro: {result if 'result' in locals() else 'N/A'}")
        return {}


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


async def extract_product_variations(products: List[Dict[str, Any]], category: str, openai_service: "OpenAIService") -> List[str]:
    """Extrai variações únicas de produtos usando IA.
    
    Args:
        products: Lista de produtos da mesma categoria
        category: Nome da categoria (ex: "cimento", "areia")
        openai_service: Serviço OpenAI
        
    Returns:
        Lista de variações únicas encontradas
        Exemplo: ["CP-II", "CP-III", "CP-V"] ou ["Lavada", "Grossa", "Fina"]
    """
    if not openai_service or not products:
        return []

    # Preparar lista de nomes de produtos
    product_names = [p.get("name", "") for p in products[:20]]  # Limitar a 20 para não sobrecarregar
    products_text = "\n".join([f"- {name}" for name in product_names if name])
    
    prompt = f"""
Você é um assistente especializado em identificar variações de produtos.

Analise a lista de produtos abaixo da categoria "{category}" e identifique as VARIAÇÕES PRINCIPAIS que diferenciam esses produtos.

PRODUTOS:
{products_text}

TAREFA:
Identifique as variações principais que o cliente precisa escolher. Por exemplo:
- Para cimento: tipos (CP-II, CP-III, CP-V)
- Para areia: características (lavada, grossa, fina)
- Para caixa d'água: capacidades (500L, 1000L, 2000L)
- Para tinta: tipos (acrílica, latex, esmalte)
- Para tijolo: tamanhos (6 furos, 8 furos, maciço)

IMPORTANTE:
- Extraia APENAS as variações relevantes que aparecem nos nomes dos produtos
- Normalize os nomes (ex: "cp ii" → "CP-II", "lavada" → "Lavada")
- Ignore variações de preço, loja ou marca
- Retorne apenas as opções que o cliente precisa escolher
- Se não houver variações significativas, retorne lista vazia

RESPONDA APENAS com uma lista JSON de strings:
["variação1", "variação2", "variação3"]

EXEMPLOS:

Produtos de cimento:
- Cimento CP-II 50kg
- Cimento CP-III 50kg
- Cimento CP-V ARI 50kg
Resposta: ["CP-II", "CP-III", "CP-V"]

Produtos de areia:
- Areia Lavada m³
- Areia Grossa m³
- Areia Fina m³
Resposta: ["Lavada", "Grossa", "Fina"]

Produtos iguais:
- Argamassa AC-II 20kg - Loja A
- Argamassa AC-II 20kg - Loja B
Resposta: []
""".strip()

    try:
        response = await openai_service.generate_response(message=prompt)
        result = response.strip()
        
        logger.info(f"IA - Variações extraídas para '{category}': {result}")
        
        # Parse JSON
        import json
        
        # Limpar markdown se necessário
        if result.startswith("```"):
            result = result.replace("```json", "").replace("```", "").strip()
        
        variations = json.loads(result)
        
        if isinstance(variations, list):
            return [str(v) for v in variations if v]
        
        return []
    except Exception as exc:
        logger.error(f"Erro ao extrair variações: {exc}")
        return []


__all__ = [
    "should_search_products",
    "extract_product_names",
    "extract_product_specifications",
    "extract_product_variations",
    "format_product_catalog",
    "analyze_product_variations",
]
