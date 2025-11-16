#!/usr/bin/env python3
"""Script para analisar uso de tokens dos logs."""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any

# Adicionar app ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.token_analytics import calculate_cost, is_usage_high


def parse_log_file(log_file: str) -> List[Dict[str, Any]]:
    """
    Parse log file e extrai informações de uso de tokens.
    
    Args:
        log_file: Caminho para o arquivo de log
        
    Returns:
        Lista de dicts com informações de uso
    """
    pattern = r"📊 Token Usage: prompt=(\d+), completion=(\d+), total=(\d+), model=([^\s]+)"
    
    usages = []
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                match = re.search(pattern, line)
                if match:
                    usages.append({
                        "prompt_tokens": int(match.group(1)),
                        "completion_tokens": int(match.group(2)),
                        "total_tokens": int(match.group(3)),
                        "model": match.group(4)
                    })
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {log_file}")
        return []
    
    return usages


def generate_report(usages: List[Dict[str, Any]]) -> None:
    """
    Gera relatório de uso de tokens.
    
    Args:
        usages: Lista de informações de uso
    """
    if not usages:
        print("❌ Nenhum dado de uso encontrado nos logs")
        print("\n💡 Dica: Execute o sistema e faça algumas interações primeiro")
        return
    
    print("=" * 80)
    print("📊 RELATÓRIO DE USO DE TOKENS")
    print("=" * 80)
    
    # Estatísticas gerais
    total_calls = len(usages)
    total_prompt = sum(u["prompt_tokens"] for u in usages)
    total_completion = sum(u["completion_tokens"] for u in usages)
    total_tokens = sum(u["total_tokens"] for u in usages)
    
    avg_prompt = total_prompt / total_calls
    avg_completion = total_completion / total_calls
    avg_total = total_tokens / total_calls
    
    print(f"\n📈 ESTATÍSTICAS GERAIS:")
    print(f"  • Total de chamadas: {total_calls}")
    print(f"  • Total de tokens: {total_tokens:,}")
    print(f"  • Média por chamada: {avg_total:.0f} tokens")
    print(f"    - Prompt: {avg_prompt:.0f} tokens")
    print(f"    - Completion: {avg_completion:.0f} tokens")
    
    # Análise de custo
    model = usages[0]["model"]
    cost_analysis = calculate_cost(total_prompt, total_completion, model)
    
    print(f"\n💰 ANÁLISE DE CUSTOS ({model}):")
    print(f"  • Custo total: ${cost_analysis['total_cost_usd']:.6f} USD")
    print(f"    - Input: ${cost_analysis['input_cost_usd']:.6f} USD")
    print(f"    - Output: ${cost_analysis['output_cost_usd']:.6f} USD")
    print(f"  • Custo por 1000 interações: ${cost_analysis['cost_per_1k_interactions']:.2f} USD")
    print(f"  • Estimativa mensal (30 int/dia): ${cost_analysis['estimated_monthly_cost']:.2f} USD")
    
    # Verificar se está alto
    usage_check = is_usage_high(int(avg_prompt), int(avg_completion))
    
    print(f"\n🎯 ANÁLISE DE USO:")
    print(f"  • Prompt: {usage_check['prompt_status']} ({avg_prompt:.0f} tokens)")
    print(f"  • Completion: {usage_check['completion_status']} ({avg_completion:.0f} tokens)")
    
    if usage_check['is_high']:
        print(f"\n⚠️  USO ALTO DETECTADO!")
        print(f"\n📝 RECOMENDAÇÕES:")
        for rec in usage_check['recommendations']:
            print(f"  {rec}")
    else:
        print(f"\n✅ Uso de tokens está dentro do esperado")
    
    # Breakdown por iteração
    print(f"\n📋 DETALHAMENTO POR CHAMADA:")
    print(f"  {'#':<4} {'Prompt':<10} {'Completion':<12} {'Total':<10} {'Custo (USD)':<15}")
    print(f"  {'-'*4} {'-'*10} {'-'*12} {'-'*10} {'-'*15}")
    
    for i, usage in enumerate(usages[:10], 1):  # Mostrar apenas primeiras 10
        cost = calculate_cost(
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["model"]
        )
        print(
            f"  {i:<4} "
            f"{usage['prompt_tokens']:<10} "
            f"{usage['completion_tokens']:<12} "
            f"{usage['total_tokens']:<10} "
            f"${cost['total_cost_usd']:<14.6f}"
        )
    
    if len(usages) > 10:
        print(f"  ... e mais {len(usages) - 10} chamadas")
    
    print("\n" + "=" * 80)


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analisa uso de tokens dos logs")
    parser.add_argument(
        "--log-file",
        default="app.log",
        help="Caminho para o arquivo de log (padrão: app.log)"
    )
    
    args = parser.parse_args()
    
    usages = parse_log_file(args.log_file)
    generate_report(usages)


if __name__ == "__main__":
    main()
