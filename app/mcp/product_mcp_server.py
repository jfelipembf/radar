"""
MCP Server para Produtos - Model Context Protocol
Permite que a IA acesse diretamente os dados de produtos via function calling
"""

import logging
from typing import Any, Dict, List, Optional
from app.services.supabase_service import SupabaseService
from app.utils.product_matcher import match_all_keywords
from app.utils.purchase_finalizer import PurchaseFinalizer

logger = logging.getLogger(__name__)


class ProductMCPServer:
    """
    MCP Server que expõe ferramentas para a IA acessar produtos diretamente.
    A IA pode chamar estas funções via function calling do OpenAI.
    """
    
    def __init__(self, supabase_service: SupabaseService):
        self.supabase_service = supabase_service
        self.purchase_finalizer = PurchaseFinalizer(supabase_service)
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Retorna o schema das ferramentas disponíveis para a IA.
        Formato compatível com OpenAI function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "calculate_best_budget",
                    "description": "Calcula o melhor orçamento buscando produtos em TODAS as lojas e comparando totais. Use após identificar os produtos que o usuário quer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "products": {
                                "type": "array",
                                "description": "Lista de produtos solicitados com keywords e quantity",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "keywords": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Keywords do produto (ex: ['caixa', 'heineken'])"
                                        },
                                        "quantity": {
                                            "type": "integer",
                                            "default": 1,
                                            "description": "Quantidade solicitada"
                                        }
                                    },
                                    "required": ["keywords"]
                                }
                            }
                        },
                        "required": ["products"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "finalize_purchase",
                    "description": "Finaliza a compra preparando mensagens para cliente e loja. Use quando o usuário escolher finalizar (opção 1).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "store_name": {
                                "type": "string",
                                "description": "Nome da loja escolhida"
                            },
                            "products": {
                                "type": "array",
                                "description": "Lista de produtos da loja",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "price": {"type": "number"},
                                        "unit": {"type": "string"},
                                        "quantity": {"type": "integer", "default": 1}
                                    }
                                }
                            },
                            "total": {
                                "type": "number",
                                "description": "Valor total do orçamento"
                            },
                            "customer_id": {
                                "type": "string",
                                "description": "ID do cliente (telefone)"
                            }
                        },
                        "required": ["store_name", "products", "total", "customer_id"]
                    }
                }
            }
        ]
    
    def calculate_best_budget(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula o melhor orçamento buscando produtos em TODAS as lojas.
        
        Args:
            products: Lista de produtos com keywords e quantity
            
        Returns:
            Dict com orçamento por loja e loja mais barata
        """
        try:
            logger.info(f"MCP - calculate_best_budget: {len(products)} produtos solicitados")
            
            from collections import defaultdict
            
            # OTIMIZAÇÃO: Coletar TODAS as keywords de uma vez
            all_keywords = []
            for product_request in products:
                all_keywords.extend(product_request.get("keywords", []))
            
            if not all_keywords:
                logger.warning("Nenhuma keyword fornecida")
                return {
                    "success": True,
                    "stores": [],
                    "cheapest_store": None,
                    "total_stores": 0
                }
            
            # 1 QUERY para buscar TODOS os produtos de uma vez
            # Limite dinâmico: 50 produtos por item solicitado (escalável)
            dynamic_limit = max(200, len(products) * 50)
            logger.info(f"MCP - Buscando todos os produtos com keywords: {all_keywords} (limit: {dynamic_limit})")
            all_products = self.supabase_service.search_products_by_keywords(
                keywords=all_keywords,
                limit=dynamic_limit
            )
            
            if not all_products:
                logger.warning("Nenhum produto encontrado")
                return {
                    "success": True,
                    "stores": [],
                    "cheapest_store": None,
                    "total_stores": 0
                }
            
            logger.info(f"MCP - Encontrados {len(all_products)} produtos no total")
            
            # OTIMIZAÇÃO: Agrupar produtos por loja PRIMEIRO (reduz iterações)
            products_by_store = defaultdict(list)
            for product in all_products:
                store_name = product.get("store", {}).get("name", "Loja")
                products_by_store[store_name].append(product)
            
            logger.info(f"MCP - Produtos distribuídos em {len(products_by_store)} lojas")
            
            # Calcular orçamento por loja
            all_products_by_store = defaultdict(lambda: {"products": [], "total": 0.0, "has_all": True})
            
            for product_request in products:
                keywords = product_request.get("keywords", [])
                quantity = product_request.get("quantity", 1)
                
                # Para cada loja, buscar o produto mais barato
                for store_name, store_products in products_by_store.items():
                    # Filtrar produtos desta loja que correspondem às keywords
                    matching = [p for p in store_products if match_all_keywords(p, keywords)]
                    
                    if not matching:
                        continue
                    
                    # Pegar o mais barato
                    cheapest = min(matching, key=lambda p: float(p.get("price", 999999)))
                    
                    # Adicionar ao orçamento desta loja
                    all_products_by_store[store_name]["products"].append({
                        "name": cheapest.get("name"),
                        "price": float(cheapest.get("price", 0)),
                        "quantity": quantity
                    })
                    all_products_by_store[store_name]["total"] += float(cheapest.get("price", 0)) * quantity
            
            # Filtrar apenas lojas que têm TODOS os produtos
            num_products_requested = len(products)
            stores_list = []
            
            for store_name, data in all_products_by_store.items():
                if len(data["products"]) == num_products_requested:
                    store_data = {
                        "store": store_name,
                        "products": [
                            {
                                "name": p["name"],
                                "price": p["price"],
                                "quantity": p["quantity"],
                                "subtotal": p["price"] * p["quantity"]
                            }
                            for p in data["products"]
                        ],
                        "total": data["total"]
                    }
                    logger.info(f"MCP - Loja {store_name}: Total R$ {data['total']:.2f}")
                    for p in data["products"]:
                        logger.info(f"  - {p['quantity']}x {p['name']}: R$ {p['price']:.2f} = R$ {p['price'] * p['quantity']:.2f}")
                    stores_list.append(store_data)
            
            # Ordenar por total
            stores_list.sort(key=lambda x: x["total"])
            
            # Limitar para top 5 lojas (evitar mensagens muito longas)
            MAX_STORES_TO_SHOW = 5
            total_stores = len(stores_list)
            stores_to_show = stores_list[:MAX_STORES_TO_SHOW]
            
            result = {
                "success": True,
                "stores": stores_to_show,
                "cheapest_store": stores_list[0] if stores_list else None,
                "total_stores": total_stores,
                "showing_top": min(MAX_STORES_TO_SHOW, total_stores),
                "has_more": total_stores > MAX_STORES_TO_SHOW
            }
            
            logger.info(f"MCP - Encontradas {len(stores_list)} lojas com todos os produtos")
            if stores_list:
                logger.info(f"MCP - Loja mais barata: {stores_list[0]['store']}")
                logger.info(f"MCP - Resultado completo: {result}")
            return result
            
        except Exception as exc:
            logger.error(f"MCP - Erro em calculate_best_budget: {exc}")
            return {
                "success": False,
                "error": str(exc)
            }
    
    def finalize_purchase(
        self,
        store_name: str,
        products: List[Dict[str, Any]],
        total: float,
        customer_id: str
    ) -> Dict[str, Any]:
        """
        Finaliza compra preparando mensagens para cliente e loja.
        
        Args:
            store_name: Nome da loja
            products: Lista de produtos
            total: Valor total
            customer_id: ID do cliente
            
        Returns:
            Dict com mensagens e link WhatsApp
        """
        logger.info(f"MCP - finalize_purchase: {store_name}, total: R$ {total}")
        
        # Delegar para PurchaseFinalizer
        return self.purchase_finalizer.finalize_purchase(
            store_name=store_name,
            customer_id=customer_id,
            products=products,
            total=total
        )
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa uma ferramenta do MCP.
        
        Args:
            tool_name: Nome da ferramenta
            arguments: Argumentos da ferramenta
            
        Returns:
            Resultado da execução
        """
        logger.info(f"MCP - Executando ferramenta: {tool_name} com args: {arguments}")
        
        if tool_name == "calculate_best_budget":
            return self.calculate_best_budget(**arguments)
        elif tool_name == "finalize_purchase":
            return self.finalize_purchase(**arguments)
        else:
            return {
                "success": False,
                "error": f"Ferramenta desconhecida: {tool_name}"
            }


__all__ = ["ProductMCPServer"]
