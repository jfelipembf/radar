"""
MCP Server para Produtos - Model Context Protocol
Permite que a IA acesse diretamente os dados de produtos via function calling
"""

import logging
from typing import Any, Dict, List, Optional
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class ProductMCPServer:
    """
    MCP Server que expõe ferramentas para a IA acessar produtos diretamente.
    A IA pode chamar estas funções via function calling do OpenAI.
    """
    
    def __init__(self, supabase_service: SupabaseService):
        self.supabase_service = supabase_service
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Retorna o schema das ferramentas disponíveis para a IA.
        Formato compatível com OpenAI function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_multiple_products",
                    "description": "🚀 BUSCA OTIMIZADA: Busca múltiplos produtos de uma vez (MUITO MAIS RÁPIDO). Use esta função quando o usuário pedir vários produtos. Exemplo: 'cerveja skol, brahma e coca-cola' → busca os 3 de uma vez.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "products": {
                                "type": "array",
                                "description": "Lista de produtos para buscar",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "keywords": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Palavras-chave do produto (ex: ['cerveja', 'skol'])"
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
            
            # Buscar cada produto em TODAS as lojas
            all_products_by_store = defaultdict(lambda: {"products": [], "total": 0.0, "has_all": True})
            
            for product_request in products:
                keywords = product_request.get("keywords", [])
                quantity = product_request.get("quantity", 1)
                
                # Buscar este produto em todas as lojas
                search_result = self.supabase_service.search_products_by_keywords(
                    keywords=keywords,
                    limit=50  # Buscar em várias lojas
                )
                
                if not search_result:
                    logger.warning(f"Produto não encontrado: {keywords}")
                    continue
                
                # Agrupar por loja
                stores_with_product = {}
                for product in search_result:
                    store_name = product.get("store", {}).get("name", "Loja")
                    price = float(product.get("price", 0))
                    
                    # Guardar apenas o mais barato de cada loja
                    if store_name not in stores_with_product or price < stores_with_product[store_name]["price"]:
                        stores_with_product[store_name] = {
                            "name": product.get("name"),
                            "price": price,
                            "quantity": quantity
                        }
                
                # Adicionar aos orçamentos por loja
                for store_name, product_data in stores_with_product.items():
                    all_products_by_store[store_name]["products"].append(product_data)
                    all_products_by_store[store_name]["total"] += product_data["price"] * quantity
            
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
            
            result = {
                "success": True,
                "stores": stores_list,
                "cheapest_store": stores_list[0] if stores_list else None,
                "total_stores": len(stores_list)
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
        try:
            logger.info(f"MCP - finalize_purchase: {store_name}, total: R$ {total}")
            
            # Buscar telefone da loja
            store_phone = None
            try:
                # Buscar loja no Supabase
                stores = self.supabase_service.supabase.table("stores").select("phone").eq("name", store_name).execute()
                if stores.data and len(stores.data) > 0:
                    store_phone = stores.data[0].get("phone", "").replace("+", "").replace(" ", "").replace("-", "")
            except Exception as exc:
                logger.warning(f"Erro ao buscar telefone da loja: {exc}")
            
            # Formatar lista de produtos
            products_list = []
            for p in products:
                name = p.get("name", "Produto")
                price = p.get("price", 0)
                unit = p.get("unit", "unidade")
                quantity = p.get("quantity", 1)
                
                if quantity > 1:
                    products_list.append(f"• {name}: R$ {price:.2f} por {unit} (x{quantity})")
                else:
                    products_list.append(f"• {name}: R$ {price:.2f} por {unit}")
            
            products_text = "\n".join(products_list)
            
            # Mensagem para a LOJA
            store_message = f"""🛒 *NOVA SOLICITAÇÃO DE ORÇAMENTO*

📞 *Cliente:* {customer_id}

📦 *Produtos solicitados:*
{products_text}

💰 *Valor total estimado: R$ {total:.2f}*

📱 Cliente será direcionado via WhatsApp."""
            
            # Mensagem para o CLIENTE
            customer_message = f"""✅ Compra finalizada - {store_name}

📦 Produtos selecionados:
{products_text}

💰 *Valor total: R$ {total:.2f}*

📱 Você será direcionado para o WhatsApp da loja para finalizar a compra.
Envie esta lista diretamente para a loja!"""
            
            # Link WhatsApp
            whatsapp_link = None
            if store_phone:
                import urllib.parse
                encoded_message = urllib.parse.quote(store_message)
                whatsapp_link = f"https://wa.me/{store_phone}?text={encoded_message}"
                customer_message += f"\n\n🔗 {whatsapp_link}"
            
            result = {
                "success": True,
                "store_message": store_message,
                "customer_message": customer_message,
                "whatsapp_link": whatsapp_link,
                "store_phone": store_phone
            }
            
            logger.info(f"MCP - Compra finalizada com sucesso")
            return result
            
        except Exception as exc:
            logger.error(f"MCP - Erro em finalize_purchase: {exc}")
            return {
                "success": False,
                "error": str(exc)
            }
    
    def search_multiple_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Busca múltiplos produtos de uma vez (OTIMIZADO).
        
        Args:
            products: Lista de produtos com keywords e quantity
            
        Returns:
            Dict com produtos mais baratos encontrados para cada query
        """
        try:
            logger.info(f"MCP - search_multiple_products: {len(products)} produtos")
            
            # Preparar queries para busca em lote
            product_queries = []
            for product in products:
                keywords = product.get('keywords', [])
                if keywords:
                    product_queries.append({'keywords': keywords})
            
            if not product_queries:
                return {
                    "success": False,
                    "error": "Nenhuma keyword fornecida",
                    "products": []
                }
            
            # Buscar TODOS os produtos de uma vez
            batch_results = self.supabase_service.search_multiple_products_batch(
                product_queries=product_queries,
                segment=None
            )
            
            # Processar resultados e encontrar o mais barato de cada
            found_products = []
            for i, product_request in enumerate(products):
                query_key = f"query_{i}"
                matching_products = batch_results.get(query_key, [])
                
                if matching_products:
                    # Encontrar o mais barato
                    cheapest = min(matching_products, key=lambda p: float(p.get("price", 999999)))
                    
                    # Adicionar unit_label se não existir
                    if "unit" not in cheapest:
                        description = cheapest.get("description", "").lower()
                        if "m³" in description or "m3" in description:
                            cheapest["unit"] = "m³"
                        elif "kg" in description:
                            cheapest["unit"] = "kg"
                        elif "litro" in description or "l" in description:
                            cheapest["unit"] = "L"
                        else:
                            cheapest["unit"] = "unidade"
                    
                    found_products.append({
                        "name": cheapest.get("name"),
                        "price": cheapest.get("price"),
                        "store": cheapest.get("store", {}).get("name", "Loja"),
                        "unit": cheapest.get("unit", "unidade"),
                        "quantity": product_request.get("quantity", 1),
                        "keywords": product_request.get("keywords")
                    })
                else:
                    # Produto não encontrado
                    keywords_str = " ".join(product_request.get("keywords", []))
                    logger.warning(f"MCP - Produto não encontrado: {keywords_str}")
            
            result = {
                "success": True,
                "products": found_products,
                "total_found": len(found_products),
                "total_requested": len(products)
            }
            
            logger.info(f"MCP - search_multiple_products: {len(found_products)}/{len(products)} produtos encontrados")
            return result
            
        except Exception as exc:
            logger.error(f"MCP - Erro em search_multiple_products: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "products": []
            }
    
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
        
        if tool_name == "search_multiple_products":
            return self.search_multiple_products(**arguments)
        elif tool_name == "calculate_best_budget":
            return self.calculate_best_budget(**arguments)
        elif tool_name == "finalize_purchase":
            return self.finalize_purchase(**arguments)
        else:
            return {
                "success": False,
                "error": f"Ferramenta desconhecida: {tool_name}"
            }


__all__ = ["ProductMCPServer"]
