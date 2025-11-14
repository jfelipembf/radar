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
        else:
            return {
                "success": False,
                "error": f"Ferramenta desconhecida: {tool_name}"
            }


__all__ = ["ProductMCPServer"]
