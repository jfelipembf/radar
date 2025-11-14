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
                    "name": "search_products",
                    "description": "Busca produtos no catálogo por categoria e filtros opcionais. Use esta função para encontrar produtos disponíveis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Categoria do produto (ex: 'cimento', 'areia', 'caixa d'água')"
                            },
                            "specification": {
                                "type": "string",
                                "description": "Especificação opcional (ex: 'CP-II', '1000L', 'lavada')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Número máximo de produtos a retornar",
                                "default": 20
                            }
                        },
                        "required": ["category"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_product_variations",
                    "description": "Obtém as variações disponíveis de uma categoria de produto. Use quando o usuário perguntar 'quais tipos?' ou 'que opções?'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Categoria do produto (ex: 'cimento', 'areia')"
                            }
                        },
                        "required": ["category"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_cheapest_product",
                    "description": "Retorna o produto mais barato de uma categoria com especificação opcional",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Categoria do produto"
                            },
                            "specification": {
                                "type": "string",
                                "description": "Especificação opcional"
                            }
                        },
                        "required": ["category"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_best_budget",
                    "description": "Calcula o melhor orçamento agrupando produtos por loja e retorna a loja mais barata. Use após adicionar todos os produtos ao orçamento.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "products": {
                                "type": "array",
                                "description": "Lista de produtos adicionados ao orçamento",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "price": {"type": "number"},
                                        "store": {"type": "string"},
                                        "quantity": {"type": "integer", "default": 1}
                                    }
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
    
    def search_products(
        self, 
        category: str, 
        specification: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Busca produtos no catálogo.
        
        Args:
            category: Categoria do produto
            specification: Especificação opcional (tipo, capacidade, etc)
            limit: Limite de resultados
            
        Returns:
            Dict com produtos encontrados e metadados
        """
        try:
            logger.info(f"MCP - search_products: category={category}, spec={specification}")
            
            # Preparar filtros
            search_terms = [category]
            exact_filters = None
            
            if specification:
                exact_filters = {"specification": specification}
            
            # Buscar produtos
            products = self.supabase_service.get_products(
                segment="material_construcao",
                search_terms=search_terms,
                limit=limit,
                exact_filters=exact_filters
            )
            
            # Formatar resposta
            result = {
                "success": True,
                "category": category,
                "specification": specification,
                "count": len(products),
                "products": [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "price": p.get("price"),
                        "store": p.get("store", {}).get("name"),
                        "description": p.get("description", "")
                    }
                    for p in products
                ]
            }
            
            logger.info(f"MCP - search_products: encontrados {len(products)} produtos")
            return result
            
        except Exception as exc:
            logger.error(f"MCP - Erro em search_products: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "category": category,
                "products": []
            }
    
    def get_product_variations(self, category: str) -> Dict[str, Any]:
        """
        Obtém variações disponíveis de uma categoria.
        
        Args:
            category: Categoria do produto
            
        Returns:
            Dict com variações encontradas
        """
        try:
            logger.info(f"MCP - get_product_variations: category={category}")
            
            # Buscar todos os produtos da categoria
            products = self.supabase_service.get_products(
                segment="material_construcao",
                search_terms=[category],
                limit=50
            )
            
            # Extrair variações únicas dos nomes
            variations = set()
            for product in products:
                name = product.get("name", "").lower()
                
                # Padrões comuns de variação
                patterns = {
                    "cp-ii": "CP-II",
                    "cp ii": "CP-II",
                    "cp-iii": "CP-III",
                    "cp iii": "CP-III",
                    "cp-v": "CP-V",
                    "cp v": "CP-V",
                    "lavada": "Lavada",
                    "grossa": "Grossa",
                    "fina": "Fina",
                    "1000l": "1000L",
                    "500l": "500L",
                    "2000l": "2000L"
                }
                
                for pattern, variation in patterns.items():
                    if pattern in name:
                        variations.add(variation)
            
            result = {
                "success": True,
                "category": category,
                "variations": sorted(list(variations)),
                "count": len(variations)
            }
            
            logger.info(f"MCP - get_product_variations: {len(variations)} variações encontradas")
            return result
            
        except Exception as exc:
            logger.error(f"MCP - Erro em get_product_variations: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "category": category,
                "variations": []
            }
    
    def get_cheapest_product(
        self, 
        category: str,
        specification: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retorna o produto mais barato de uma categoria.
        
        Args:
            category: Categoria do produto
            specification: Especificação opcional
            
        Returns:
            Dict com o produto mais barato
        """
        try:
            logger.info(f"MCP - get_cheapest_product: category={category}, spec={specification}")
            
            # Buscar produtos
            search_result = self.search_products(category, specification, limit=50)
            
            if not search_result["success"] or not search_result["products"]:
                return {
                    "success": False,
                    "error": "Nenhum produto encontrado",
                    "category": category
                }
            
            # Encontrar o mais barato
            products = search_result["products"]
            cheapest = min(products, key=lambda p: float(p.get("price", 999999)))
            
            result = {
                "success": True,
                "category": category,
                "specification": specification,
                "product": cheapest
            }
            
            logger.info(f"MCP - get_cheapest_product: {cheapest['name']} - R$ {cheapest['price']}")
            return result
            
        except Exception as exc:
            logger.error(f"MCP - Erro em get_cheapest_product: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "category": category
            }
    
    def calculate_best_budget(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula o melhor orçamento agrupando produtos por loja.
        
        Args:
            products: Lista de produtos com name, price, store, quantity
            
        Returns:
            Dict com orçamento por loja e loja mais barata
        """
        try:
            logger.info(f"MCP - calculate_best_budget: {len(products)} produtos")
            
            from collections import defaultdict
            
            # Agrupar por loja
            stores = defaultdict(lambda: {"products": [], "total": 0.0})
            
            for product in products:
                store_name = product.get("store", "Loja Desconhecida")
                quantity = product.get("quantity", 1)
                price = float(product.get("price", 0))
                
                stores[store_name]["products"].append({
                    "name": product.get("name"),
                    "price": price,
                    "quantity": quantity,
                    "subtotal": price * quantity
                })
                stores[store_name]["total"] += price * quantity
            
            # Converter para lista e ordenar por total
            stores_list = [
                {
                    "store": store_name,
                    "products": data["products"],
                    "total": data["total"]
                }
                for store_name, data in stores.items()
            ]
            stores_list.sort(key=lambda x: x["total"])
            
            result = {
                "success": True,
                "stores": stores_list,
                "cheapest_store": stores_list[0] if stores_list else None,
                "total_stores": len(stores_list)
            }
            
            logger.info(f"MCP - Loja mais barata: {stores_list[0]['store'] if stores_list else 'N/A'}")
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
        
        if tool_name == "search_products":
            return self.search_products(**arguments)
        elif tool_name == "get_product_variations":
            return self.get_product_variations(**arguments)
        elif tool_name == "get_cheapest_product":
            return self.get_cheapest_product(**arguments)
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
