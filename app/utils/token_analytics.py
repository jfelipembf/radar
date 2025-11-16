"""Análise de consumo de tokens e custos."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# Preços por 1M tokens (atualizado Nov 2024)
TOKEN_PRICES = {
    "gpt-4o-mini": {
        "input": 0.150,   # $0.150 por 1M tokens de input
        "output": 0.600,  # $0.600 por 1M tokens de output
    },
    "gpt-4o": {
        "input": 2.50,    # $2.50 por 1M tokens de input
        "output": 10.00,  # $10.00 por 1M tokens de output
    },
    "gpt-4-turbo": {
        "input": 10.00,   # $10.00 por 1M tokens de input
        "output": 30.00,  # $30.00 por 1M tokens de output
    }
}


def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Calcula custo de uma chamada à API OpenAI.
    
    Args:
        prompt_tokens: Tokens de entrada (prompt)
        completion_tokens: Tokens de saída (completion)
        model: Nome do modelo usado
        
    Returns:
        Dict com análise de custos
    """
    if model not in TOKEN_PRICES:
        logger.warning(f"Modelo {model} não encontrado na tabela de preços")
        return {
            "error": f"Modelo {model} não suportado",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    
    prices = TOKEN_PRICES[model]
    
    # Calcular custos (preço é por 1M tokens)
    input_cost = (prompt_tokens / 1_000_000) * prices["input"]
    output_cost = (completion_tokens / 1_000_000) * prices["output"]
    total_cost = input_cost + output_cost
    
    # Calcular custo por 1000 interações
    cost_per_1k = total_cost * 1000
    
    # Calcular custo mensal estimado (assumindo 30 interações/dia)
    daily_interactions = 30
    monthly_cost = total_cost * daily_interactions * 30
    
    return {
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total_cost, 6),
        "cost_per_1k_interactions": round(cost_per_1k, 2),
        "estimated_monthly_cost": round(monthly_cost, 2),
        "cost_breakdown": {
            "input_price_per_1m": prices["input"],
            "output_price_per_1m": prices["output"]
        }
    }


def analyze_conversation_cost(
    iterations: int,
    avg_prompt_tokens: int,
    avg_completion_tokens: int,
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Analisa custo de uma conversa completa com múltiplas iterações.
    
    Args:
        iterations: Número de iterações (chamadas à API)
        avg_prompt_tokens: Média de tokens de prompt por iteração
        avg_completion_tokens: Média de tokens de completion por iteração
        model: Nome do modelo usado
        
    Returns:
        Dict com análise de custos da conversa
    """
    total_prompt = avg_prompt_tokens * iterations
    total_completion = avg_completion_tokens * iterations
    
    cost_analysis = calculate_cost(total_prompt, total_completion, model)
    cost_analysis["iterations"] = iterations
    cost_analysis["avg_prompt_per_iteration"] = avg_prompt_tokens
    cost_analysis["avg_completion_per_iteration"] = avg_completion_tokens
    
    return cost_analysis


def is_usage_high(
    prompt_tokens: int,
    completion_tokens: int,
    threshold_prompt: int = 4000,
    threshold_completion: int = 1000
) -> Dict[str, Any]:
    """
    Verifica se o uso de tokens está alto.
    
    Args:
        prompt_tokens: Tokens de entrada
        completion_tokens: Tokens de saída
        threshold_prompt: Limite para prompt (padrão: 4000)
        threshold_completion: Limite para completion (padrão: 1000)
        
    Returns:
        Dict com análise de uso
    """
    total = prompt_tokens + completion_tokens
    
    return {
        "is_high": prompt_tokens > threshold_prompt or completion_tokens > threshold_completion,
        "prompt_status": "🔴 ALTO" if prompt_tokens > threshold_prompt else "🟢 OK",
        "completion_status": "🔴 ALTO" if completion_tokens > threshold_completion else "🟢 OK",
        "total_tokens": total,
        "recommendations": _get_recommendations(prompt_tokens, completion_tokens, threshold_prompt, threshold_completion)
    }


def _get_recommendations(
    prompt_tokens: int,
    completion_tokens: int,
    threshold_prompt: int,
    threshold_completion: int
) -> list:
    """Gera recomendações para reduzir uso de tokens."""
    recommendations = []
    
    if prompt_tokens > threshold_prompt:
        recommendations.append("⚠️ Prompt muito grande - considere:")
        recommendations.append("  • Reduzir instruções redundantes")
        recommendations.append("  • Limitar histórico de conversa")
        recommendations.append("  • Usar exemplos mais concisos")
    
    if completion_tokens > threshold_completion:
        recommendations.append("⚠️ Resposta muito longa - considere:")
        recommendations.append("  • Instruir IA a ser mais concisa")
        recommendations.append("  • Limitar número de lojas exibidas")
        recommendations.append("  • Reduzir detalhes nas respostas")
    
    if not recommendations:
        recommendations.append("✅ Uso de tokens está dentro do esperado")
    
    return recommendations


__all__ = [
    "calculate_cost",
    "analyze_conversation_cost",
    "is_usage_high",
    "TOKEN_PRICES"
]
