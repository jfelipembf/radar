"""Serviço principal do chatbot para processamento de mensagens."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.business.construction_rules import (
    should_search_products,
    extract_product_names,
    extract_product_specifications,
    format_product_catalog,
    analyze_product_variations,
)
from app.business.message_templates import (
    format_purchase_summary,
    create_whatsapp_link,
    format_best_price_details,
    format_all_stores_details,
    format_product_catalog_with_budget,
    format_selected_products,
    get_menu_options,
)
from app.utils.formatters import _coerce_price, _format_currency, _format_date, _format_phone, _parse_created_at
from app.services.openai_service import OpenAIService
from app.services.supabase_service import SupabaseService
from app.services.evolution_service import EvolutionService
from app.utils.parsers import _consolidate_temp_messages, _latest_user_content
from app.utils.formatters import _sort_key

logger = logging.getLogger(__name__)


class ConversationManager:
    """Gerencia estado conversacional dos usuários."""

    def __init__(self):
        self.conversation_state: Dict[str, Dict[str, Any]] = {}

    def get_user_state(self, user_id: str) -> Dict[str, Any]:
        """Retorna estado do usuário, criando se não existir."""
        if user_id not in self.conversation_state:
            self.conversation_state[user_id] = {
                "store_totals": {},
                "awaiting_store_selection": False,
                "awaiting_purchase_confirmation": None,
                "selected_store_data": None,
                "timestamp": asyncio.get_event_loop().time()
            }
        return self.conversation_state[user_id]

    def update_user_state(self, user_id: str, updates: Dict[str, Any]):
        """Atualiza estado do usuário."""
        state = self.get_user_state(user_id)
        state.update(updates)
        state["timestamp"] = asyncio.get_event_loop().time()

    def clear_user_state(self, user_id: str):
        """Limpa estado do usuário."""
        if user_id in self.conversation_state:
            del self.conversation_state[user_id]

    def has_active_state(self, user_id: str) -> bool:
        """Verifica se usuário tem estado conversacional ativo."""
        return user_id in self.conversation_state


class MessageHandler:
    """Gerencia processamento de mensagens e opções interativas."""

    def __init__(self, conversation_manager: ConversationManager, chatbot_service):
        self.conversation_manager = conversation_manager
        self.chatbot_service = chatbot_service

    async def handle_interactive_option(self, user_id: str, text: str) -> Optional[str]:
        """Processa opções interativas do usuário (1, 2, 3, etc.)."""
        if not self.conversation_manager.has_active_state(user_id):
            return None

        state = self.conversation_manager.get_user_state(user_id)

        # PRIORIDADE 1: Verificar se está aguardando esclarecimento sobre produtos
        if state.get("awaiting_clarification"):
            return await self._handle_product_clarification(user_id, text.strip())

        # PRIORIDADE 2: Verificar se está aguardando seleção de loja
        if state.get("awaiting_store_selection"):
            return await self._handle_store_selection(user_id, text)

        # PRIORIDADE 3: Verificar se está aguardando confirmação de compra
        if state.get("awaiting_purchase_confirmation"):
            if text.strip() == "1":
                return await self._handle_finalize_purchase(user_id)
            elif text.strip() == "0":
                # Limpar estado e voltar ao menu
                self.conversation_manager.clear_user_state(user_id)
                return "Voltando ao menu principal. Como posso ajudar?"
            else:
                return "Por favor, digite 1 para finalizar a compra ou 0 para voltar ao menu."

        # PRIORIDADE 5: Processar opções principais do menu
        if text == "1":
            return await self._handle_finalize_purchase(user_id)
        elif text == "2":
            return await self._handle_best_price_details(user_id)
        elif text == "3":
            return await self._handle_all_stores_details(user_id)
        elif text == "0":
            # Limpar estado e voltar ao menu
            self.conversation_manager.clear_user_state(user_id)
            return "Voltando ao menu principal. Como posso ajudar?"

        return None

    async def _handle_finalize_purchase(self, user_id: str) -> str:
        """Processa finalização de compra da loja mais barata ou selecionada."""
        state = self.conversation_manager.get_user_state(user_id)
        if not state or "store_totals" not in state:
            return "Estado da conversa expirou. Por favor, faça uma nova busca de produtos."

        # Verificar se há uma loja específica selecionada (depois de ver detalhes)
        if state.get("selected_store_data"):
            store_name = state["awaiting_purchase_confirmation"]
            store_data = state["selected_store_data"]
        else:
            # Pegar a loja mais barata
            sorted_stores = sorted(state["store_totals"].items(), key=lambda x: x[1]["total"])
            if not sorted_stores:
                return "Erro: Nenhuma loja disponível."

            store_name, store_data = sorted_stores[0]

        products = store_data["products"]
        store_phone = store_data["store_info"].get("phone")

        # Formatar mensagens
        customer_msg, store_msg = format_purchase_summary(store_name, products, user_id)

        # Criar link do WhatsApp se houver telefone
        whatsapp_link = ""
        if store_phone:
            whatsapp_link = create_whatsapp_link(store_phone, store_msg)
            customer_msg += f"\n\n🔗 {whatsapp_link}"

        # Enviar mensagem para a loja
        if store_phone:
            try:
                await self.chatbot_service._send_whatsapp_message(store_phone, store_msg)
                logger.info(f"Mensagem enviada para loja {store_name}: {store_phone}")
            except Exception as exc:
                logger.error(f"Erro ao enviar mensagem para loja {store_name}: {exc}")

        # Limpar estado da conversa
        self.conversation_manager.clear_user_state(user_id)

        return customer_msg

    async def _handle_best_price_details(self, user_id: str) -> str:
        """Mostra detalhes do melhor preço."""
        state = self.conversation_manager.get_user_state(user_id)
        if not state or "store_totals" not in state:
            return "Estado da conversa expirou. Por favor, faça uma nova busca de produtos."

        # Pegar a loja mais barata
        sorted_stores = sorted(state["store_totals"].items(), key=lambda x: x[1]["total"])
        if not sorted_stores:
            return "Erro: Nenhuma loja disponível."

        store_name, store_data = sorted_stores[0]

        # Manter estado para aguardar confirmação de compra
        self.conversation_manager.update_user_state(user_id, {
            "awaiting_purchase_confirmation": store_name,
            "selected_store_data": store_data
        })

        return format_best_price_details(store_data)

    async def _handle_all_stores_details(self, user_id: str) -> str:
        """Mostra detalhes de todas as lojas."""
        state = self.conversation_manager.get_user_state(user_id)
        if not state or "store_totals" not in state:
            return "Estado da conversa expirou. Por favor, faça uma nova busca de produtos."

        # Atualizar estado para aguardar seleção
        self.conversation_manager.update_user_state(user_id, {
            "awaiting_store_selection": True
        })

        return format_all_stores_details(state["store_totals"])

    async def _handle_store_selection(self, user_id: str, selection: str) -> Optional[str]:
        """Processa seleção de loja específica."""
        state = self.conversation_manager.get_user_state(user_id)
        if not state or "store_totals" not in state:
            return "Estado da conversa expirou. Por favor, faça uma nova busca de produtos."

        if selection == "0":
            # Voltar ao menu principal
            self.conversation_manager.update_user_state(user_id, {"awaiting_store_selection": False})
            return "Voltando ao menu principal. " + format_all_stores_details(state["store_totals"])

        try:
            store_index = int(selection) - 1
            sorted_stores = sorted(state["store_totals"].items(), key=lambda x: x[1]["total"])

            if 0 <= store_index < len(sorted_stores):
                store_name, store_data = sorted_stores[store_index]

                # Limpar flags de espera e preparar para finalização
                self.conversation_manager.update_user_state(user_id, {
                    "awaiting_store_selection": False,
                    "awaiting_purchase_confirmation": store_name,
                    "selected_store_data": store_data
                })

                return format_best_price_details(store_data)
            else:
                return f"Opção inválida. Digite um número de 1 a {len(sorted_stores)} ou 0 para voltar."
        except ValueError:
            return "Por favor, digite apenas o número da opção desejada."


    async def _handle_product_clarification(self, user_id: str, text: str) -> Optional[str]:
        """Processa esclarecimentos de produtos - lógica baseada na mensagem original."""
        state = self.conversation_manager.get_user_state(user_id)

        if not state.get("pending_products"):
            return "Estado da conversa expirou. Por favor, faça uma nova busca de produtos."

        pending_products = state["pending_products"]
        current_category = state.get("current_category")
        clarified_categories = state.get("clarified_categories", [])
        selected_products = state.get("selected_products", [])

        # Usar IA para filtrar produtos baseado na resposta
        conversation_history = await self.chatbot_service._build_message_history(user_id)
        logger.info(f"Processando esclarecimento - categoria atual: {current_category}")
        logger.info(f"Produtos pendentes: {len(pending_products)}")
        logger.info(f"Categorias já esclarecidas: {clarified_categories}")

        # Buscar produtos específicos baseado na resposta do usuário
        # Estratégia mais inteligente: se é uma especificação (números, tipos), buscar por ela
        # Se é uma categoria, manter como está
        if text.isdigit() or any(char in text.lower() for char in ['l', 'kg', 'cp-', 'm³', 'm3']):
            # Parece uma especificação (500L, CP-II, 50kg, etc.)
            # Buscar por essa especificação nos produtos da categoria
            search_text = text.strip()
        elif current_category and current_category != "produto":
            search_text = f"{current_category} {text}".strip()
        else:
            search_text = text.strip()

        logger.info(f"Buscando produtos com query: '{search_text}' para categoria '{current_category}'")

        try:
            # Buscar produtos no banco baseado na resposta
            found_products = await asyncio.to_thread(
                self.chatbot_service.supabase_service.get_products,
                "material_construcao",
                [search_text],  # Usar como termo de busca
                20
            )

            logger.info(f"Produtos encontrados para '{search_text}': {len(found_products)}")
            if found_products:
                logger.info(f"Primeiro produto encontrado: {found_products[0].get('name', 'N/A')}")

            if found_products:
                # Pegar o produto mais barato encontrado
                cheapest_product = min(found_products, key=lambda x: _coerce_price(x.get("price", 0)))

                # Criar nome do tipo baseado no produto encontrado e resposta do usuário
                # Usar uma abordagem genérica que funciona com qualquer produto
                product_name = cheapest_product.get("name", "").strip()

                # Se o produto já contém a especificação na resposta do usuário, usar o nome completo
                if text.lower() in product_name.lower():
                    type_name = product_name
                else:
                    # Combinar categoria com especificação do usuário
                    if current_category and current_category != "produto":
                        type_name = f"{current_category.title()} {text}"
                    else:
                        type_name = f"{product_name} - {text}"

                logger.info(f"Nome do produto identificado: '{product_name}' -> Tipo: '{type_name}'")

                # Adicionar à lista de selecionados
                selected_product = {
                    "type": type_name,
                    "product": cheapest_product,
                    "price": _coerce_price(cheapest_product.get("price", 0)),
                    "store": cheapest_product.get("store", {}).get("name", "Loja"),
                    "quantity": 1
                }
                selected_products.append(selected_product)

                logger.info(f"Produto adicionado: {selected_product['type']} - R$ {selected_product['price']}")

            # Marcar categoria como esclarecida
            updated_clarified_categories = clarified_categories + [current_category]

            # Verificar se ainda há produtos para esclarecer na mensagem original
            # DEIXAR IA DECIDIR livremente baseado nos produtos restantes
            variation_analysis = await analyze_product_variations(
                pending_products,
                self.chatbot_service.openai_service,
                clarified_categories=updated_clarified_categories
            )

            logger.info(f"Análise de variações restantes: needs_clarification={variation_analysis.get('needs_clarification')}")

            if variation_analysis["needs_clarification"]:
                # Ainda há variações para esclarecer
                next_category = variation_analysis.get("category_to_clarify", "produto")

                # Atualizar estado
                self.conversation_manager.update_user_state(user_id, {
                    "selected_products": selected_products,
                    "awaiting_clarification": True,
                    "current_category": next_category or variation_analysis.get("category_to_clarify", "produto"),
                    "clarified_categories": updated_clarified_categories
                })

                # Formatar mensagem com produtos selecionados + próxima pergunta
                selected_message = format_selected_products(selected_products)

                # Verificar se tem clarification_message ou message
                clarification_msg = variation_analysis.get("clarification_message") or variation_analysis.get("message")
                if not clarification_msg:
                    logger.error(f"IA não retornou clarification_message ou message: {variation_analysis}")
                    clarification_msg = "Poderia especificar mais detalhes?"

                return f"Produto adicionado!\n\n{selected_message}\n\n{clarification_msg}"
            else:
                # Todas as variações esclarecidas - mostrar orçamento final
                self.conversation_manager.update_user_state(user_id, {
                    "awaiting_clarification": False,
                    "selected_products": selected_products,
                    "clarified_categories": updated_clarified_categories
                })

                # Converter produtos selecionados para formato de orçamento
                final_products = [item["product"] for item in selected_products]

                # Salvar como orçamento final
                await self.chatbot_service.product_service._save_conversation_state_for_products(user_id, final_products)

                # Formatar orçamento final
                selected_message = format_selected_products(selected_products)
                model_context, user_message = format_product_catalog(final_products, self.chatbot_service.supabase_service)

                return f"Todos os produtos selecionados!\n\n{selected_message}\n\n**ORÇAMENTO FINAL:**\n\n{user_message}"

        except Exception as exc:
            logger.warning(f"Erro no processamento de esclarecimento: {exc}")
            return "Desculpe, houve um erro. Vamos tentar novamente."


class ProductService:
    """Gerencia busca e processamento de produtos."""

    def __init__(self, conversation_manager: ConversationManager, chatbot_service):
        self.conversation_manager = conversation_manager
        self.chatbot_service = chatbot_service

    async def build_product_context(self, user_id: str, search_text: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
        """Constrói contexto de produtos baseado no texto de busca."""
        if not search_text:
            return None

        # Primeiro, perguntar à IA se deve buscar produtos
        should_search = await should_search_products(search_text, self.chatbot_service.openai_service)
        if not should_search:
            logger.info("Catálogo → IA decidiu não buscar produtos para: %s", search_text)
            return None

        # Extrair produtos específicos mencionados usando IA
        product_names = await extract_product_names(search_text, self.chatbot_service.openai_service)
        if not product_names:
            logger.info("Catálogo → Nenhum produto específico identificado em: %s", search_text)
            return None

        logger.info(f"Catálogo → produtos identificados pela IA: {product_names}")

        try:
            # USAR IA PARA EXTRAIR ESPECIFICAÇÕES DE FORMA GENÉRICA
            logger.info(f"Extraindo especificações da mensagem: '{search_text}'")
            
            specified_products = await extract_product_specifications(
                search_text,
                product_names,
                self.chatbot_service.openai_service
            )
            
            logger.info(f"Especificações extraídas pela IA: {specified_products}")

            # BUSCAR PRODUTOS COM FILTROS ESPECÍFICOS
            # Para cada produto identificado, buscar com filtros se houver especificação
            all_found_products = []
            
            for product_name in product_names:
                # Verificar se há especificação para este produto
                exact_filter = None
                
                # Normalizar nome do produto para comparação
                product_key = product_name.lower().replace("'", "'").strip()
                
                # Procurar especificação correspondente
                for spec_key, spec_value in specified_products.items():
                    spec_key_normalized = spec_key.lower().replace("'", "'").strip()
                    if spec_key_normalized in product_key or product_key in spec_key_normalized:
                        exact_filter = {"specification": spec_value}
                        logger.info(f"Aplicando filtro '{spec_value}' para produto '{product_name}'")
                        break
                
                # Buscar produtos com ou sem filtro
                found_products = await asyncio.to_thread(
                    self.chatbot_service.supabase_service.get_products,
                    "material_construcao",
                    [product_name],
                    20,
                    exact_filter  # Aplicar filtro se existir
                )
                
                all_found_products.extend(found_products)
                logger.info(f"Encontrados {len(found_products)} produtos para '{product_name}' (filtro: {exact_filter})")

            logger.info(f"Total de produtos encontrados: {len(all_found_products)}")

            # Filtrar duplicatas
            unique_products = []
            seen_names = set()
            for product in all_found_products:
                name = product.get("name", "").strip()
                if name and name not in seen_names:
                    unique_products.append(product)
                    seen_names.add(name)

            logger.info(f"Produtos únicos após filtro: {len(unique_products)}")
            
            if not unique_products:
                logger.info("Nenhum produto encontrado após busca")
                return None

            # SEPARAR produtos já especificados dos que precisam esclarecimento
            # Usar os produtos já encontrados com filtros aplicados
            clarified_categories = []
            selected_products = []
            products_to_clarify = []

            # AGRUPAR PRODUTOS POR CATEGORIA DE FORMA DINÂMICA
            # Usar os nomes de produtos identificados pela IA como categorias
            products_by_category = {}
            
            for product in unique_products:
                product_name_lower = product.get("name", "").lower()
                
                # Identificar a qual categoria (produto identificado) este item pertence
                matched_category = None
                for product_name in product_names:
                    # Verificar se o nome do produto está no nome do item
                    if product_name.lower() in product_name_lower:
                        matched_category = product_name
                        break
                
                if matched_category:
                    if matched_category not in products_by_category:
                        products_by_category[matched_category] = []
                    products_by_category[matched_category].append(product)

            logger.info(f"Produtos agrupados por categoria: {list(products_by_category.keys())}")

            # Para cada categoria especificada, selecionar o produto mais barato
            for category, specification in specified_products.items():
                # Normalizar categoria para comparação
                category_normalized = category.lower().strip()
                
                # Procurar categoria correspondente nos produtos agrupados
                matched_category = None
                for cat_key in products_by_category.keys():
                    if category_normalized in cat_key.lower() or cat_key.lower() in category_normalized:
                        matched_category = cat_key
                        break
                
                if matched_category:
                    category_products = products_by_category[matched_category]
                    
                    # Filtrar produtos que contenham a especificação
                    spec_lower = specification.lower()
                    matching_products = [
                        p for p in category_products
                        if spec_lower in p.get("name", "").lower() or 
                           spec_lower in p.get("description", "").lower()
                    ]
                    
                    if matching_products:
                        # Pegar o mais barato
                        cheapest = min(matching_products, key=lambda x: _coerce_price(x.get("price", 0)))
                        selected_products.append({
                            "type": f"{category.title()} {specification}",
                            "product": cheapest,
                            "price": _coerce_price(cheapest.get("price", 0)),
                            "store": cheapest.get("store", {}).get("name", "Loja"),
                            "quantity": 1
                        })
                        clarified_categories.append(matched_category)
                        logger.info(f"Produto especificado adicionado: {category} {specification} - {cheapest.get('name')}")
                    else:
                        # Não encontrou produto com a especificação, adicionar para esclarecimento
                        products_to_clarify.extend(category_products)
                        logger.info(f"Produto '{category}' especificado mas não encontrado com '{specification}'")
                else:
                    logger.info(f"Categoria '{category}' especificada mas não encontrada nos produtos")

            # Identificar produtos que ainda precisam esclarecimento
            # Comparar de forma normalizada
            clarified_normalized = [c.lower().strip() for c in clarified_categories]
            
            for category, category_products in products_by_category.items():
                category_normalized = category.lower().strip()
                if category_normalized not in clarified_normalized:
                    products_to_clarify.extend(category_products)
                    logger.info(f"Categoria '{category}' precisa esclarecimento")

            logger.info(f"Categorias esclarecidas: {clarified_categories}")
            logger.info(f"Produtos que precisam esclarecimento: {len(products_to_clarify)}")

            if products_to_clarify:
                # Ainda há produtos para esclarecer - deixar IA decidir qual perguntar primeiro
                logger.info(f"Produtos precisam esclarecimento ({len(products_to_clarify)}) - consultando IA")

                variation_analysis = await analyze_product_variations(
                    products_to_clarify,
                    self.chatbot_service.openai_service,
                    conversation_history=await self.chatbot_service._build_message_history(user_id),
                    clarified_categories=clarified_categories
                )

                if variation_analysis["needs_clarification"]:
                    logger.info("IA identificou necessidade de esclarecimento")

                    # Verificar se tem clarification_message ou message
                    clarification_msg = variation_analysis.get("clarification_message") or variation_analysis.get("message")
                    if not clarification_msg:
                        logger.error(f"IA não retornou clarification_message ou message: {variation_analysis}")
                        clarification_msg = "Poderia especificar mais detalhes sobre os produtos?"

                    self.conversation_manager.update_user_state(user_id, {
                        "pending_products": unique_products,
                        "awaiting_clarification": True,
                        "current_category": variation_analysis.get("category_to_clarify", "produto"),
                        "clarified_categories": clarified_categories,
                        "selected_products": selected_products
                    })

                    # Mostrar produtos já selecionados + pergunta
                    if selected_products:
                        selected_message = format_selected_products(selected_products)
                        return {
                            "model": f"Produtos parcialmente especificados, alguns precisam esclarecimento",
                            "user": f"{selected_message}\n\n{clarification_msg}"
                        }
                    else:
                        return {
                            "model": f"Produtos precisam esclarecimento",
                            "user": clarification_msg
                        }

            # Todos os produtos foram especificados ou não precisam esclarecimento
            if selected_products:
                logger.info("Todos os produtos foram especificados - mostrando orçamento")
                await self._save_conversation_state_for_products(user_id, [item["product"] for item in selected_products])

                selected_message = format_selected_products(selected_products)
                model_context, user_message = format_product_catalog([item["product"] for item in selected_products], self.chatbot_service.supabase_service)

                return {"model": "Produtos especificados completamente", "user": f"{selected_message}\n\n**ORÇAMENTO COMPLETO:**\n\n{user_message}"}

            # Fallback: deixar IA analisar todos os produtos
            logger.info("Fallback: deixando IA analisar todos os produtos")
            variation_analysis = await analyze_product_variations(
                unique_products,
                self.chatbot_service.openai_service,
                conversation_history=await self.chatbot_service._build_message_history(user_id),
                clarified_categories=clarified_categories
            )

            if variation_analysis["needs_clarification"]:
                logger.info("IA detectou necessidade de esclarecimento geral")

                # Verificar se tem clarification_message ou message
                clarification_msg = variation_analysis.get("clarification_message") or variation_analysis.get("message")
                if not clarification_msg:
                    logger.error(f"IA não retornou clarification_message ou message: {variation_analysis}")
                    clarification_msg = "Poderia especificar mais detalhes sobre os produtos?"

                self.conversation_manager.update_user_state(user_id, {
                    "pending_products": unique_products,
                    "awaiting_clarification": True,
                    "current_category": variation_analysis.get("category_to_clarify", "produto"),
                    "clarified_categories": clarified_categories,
                    "selected_products": selected_products
                })

                return {
                    "model": f"Produtos encontrados, IA identificou necessidade de esclarecimento",
                    "user": clarification_msg
                }
            else:
                # IA não viu necessidade de esclarecimento - mostrar orçamento direto
                logger.info("IA não detectou variações - mostrando orçamento direto")
                await self._save_conversation_state_for_products(user_id, unique_products)

                model_context, user_message = format_product_catalog(unique_products, self.chatbot_service.supabase_service)

                return {"model": "Produtos encontrados sem variações conflitantes", "user": user_message}
        except Exception as exc:
            logger.error("Erro ao buscar catálogo de produtos: %s", exc)
            # Em vez de retornar None (que cai no fallback do OpenAI), retornar mensagem clara
            return {
                "model": "Erro na busca de produtos",
                "user": "Desculpe, ocorreu um problema técnico ao buscar os produtos. Tente novamente em alguns instantes ou reformule sua solicitação."
            }

    async def _save_conversation_state_for_products(self, user_id: str, products: List[dict]):
        """Salva estado da conversa com dados dos produtos para opções interativas."""
        from collections import defaultdict

        # Agrupar produtos por loja
        store_totals = defaultdict(lambda: {"products": defaultdict(dict), "total": 0.0, "store_info": {}})

        for product in products:
            store_info = product.get("store", {})
            store_name = store_info.get("name", "Loja")
            store_phone = _format_phone(product.get("store_phone") or store_info.get("phone"))

            product_name = product.get("name", "").strip()
            if not product_name:
                continue

            price_value = _coerce_price(product.get("price"))
            if price_value <= 0:
                continue

            unit_label = product.get("unit_label", "unidade")

            # Se já temos este produto nesta loja, manter o mais barato
            if product_name not in store_totals[store_name]["products"] or \
               price_value < store_totals[store_name]["products"][product_name]["price"]:
                store_totals[store_name]["products"][product_name] = {
                    "name": product_name,
                    "price": price_value,
                    "price_str": _format_currency(price_value),
                    "unit_label": unit_label
                }

            # Atualizar informações da loja
            store_totals[store_name]["store_info"] = {
                "name": store_name,
                "phone": store_phone
            }

        # Calcular totais e converter para lista
        for store_name, store_data in store_totals.items():
            # Converter defaultdict para lista e calcular total
            products_list = list(store_data["products"].values())
            store_data["products"] = products_list
            store_data["total"] = sum(p["price"] for p in products_list)

        # Salvar estado da conversa
        self.conversation_manager.update_user_state(user_id, {"store_totals": dict(store_totals)})


class ChatbotService:
    """Serviço principal para processamento de mensagens do chatbot - Orquestrador."""

    def __init__(
        self,
        openai_service: OpenAIService,
        supabase_service: Optional[SupabaseService],
        evolution_service: EvolutionService
    ):
        self.openai_service = openai_service
        self.supabase_service = supabase_service
        self.evolution_service = evolution_service

        # Serviços auxiliares
        self.conversation_manager = ConversationManager()
        self.message_handler = MessageHandler(self.conversation_manager, self)
        self.product_service = ProductService(self.conversation_manager, self)

    async def process_message(self, user_id: str, text: str, message_data: dict) -> str:
        """Processa uma mensagem do usuário - Método principal orquestrador."""
        logger.info(f"Processing message from {user_id}: {text}")

        # 1. Verificar se é uma opção interativa
        interactive_response = await self.message_handler.handle_interactive_option(user_id, text.strip())
        if interactive_response:
            # Enviar resposta interativa diretamente via WhatsApp
            await self._send_whatsapp_message(user_id, interactive_response)
            # Atualizar presença
            await self._update_presence(user_id, "paused")
            return "interactive_processed"

        # 2. Se Supabase não está disponível, responder imediatamente
        if not self.supabase_service:
            response_text = await self.openai_service.generate_response(message=text)
            logger.debug(f"Generated response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
            return response_text


        # 3. Verificar saudação diária
        await self._maybe_send_daily_greeting(user_id)

        # 4. Registrar mensagem temporária
        await self._record_temp_message(user_id, text, message_data)

        # 5. Agendar processamento (debounced) - APENAS se não for opção interativa
        await self._schedule_user_processing(user_id)

        return "queued"  # Resposta será enviada posteriormente via debounce

    async def process_debounced_messages(self, user_id: str) -> Optional[str]:
        if not self.supabase_service:
            return None

        # Buscar mensagens temporárias
        temp_messages = await asyncio.to_thread(self.supabase_service.get_temp_messages, user_id)
        if not temp_messages:
            return None

        # Buscar histórico de mensagens
        history = await self._build_message_history(user_id)

        # Consolidar mensagens temporárias
        consolidated = _consolidate_temp_messages(temp_messages)
        if consolidated:
            history.append(consolidated)

        # Encontrar texto para busca de produtos
        search_source = consolidated["content"] if consolidated else _latest_user_content(history)

        # VERIFICAR SE USUÁRIO ESTÁ PEDINDO ORÇAMENTO SALVO
        user_text = search_source.lower()
        budget_keywords = ["orcamento", "orçamento", "preco", "preço", "valor", "custo", "total", "completo", "tudo"]

        state = self.conversation_manager.get_user_state(user_id)
        if state.get("store_totals") and any(keyword in user_text for keyword in budget_keywords):
            logger.info("Usuário pedindo orçamento salvo - mostrando orçamento completo")
            # Mostrar orçamento completo salvo
            response_text = format_product_catalog_with_budget(state["store_totals"])
            await self._cleanup_and_save(user_id, temp_messages, consolidated, response_text)
            await self._send_whatsapp_message(user_id, response_text)
            await self._update_presence(user_id, "paused")
            return response_text

        # Buscar produtos usando ProductService
        catalog_context = await self.product_service.build_product_context(user_id, search_source)

        # Preparar resposta
        response_text = await self._prepare_response(user_id, history, catalog_context)

        # Limpar mensagens temporárias e salvar resposta
        await self._cleanup_and_save(user_id, temp_messages, consolidated, response_text)

        # ENVIAR resposta final via WhatsApp
        await self._send_whatsapp_message(user_id, response_text)

        # Atualizar presença para "paused"
        await self._update_presence(user_id, "paused")

        return response_text

    async def _build_message_history(self, user_id: str) -> List[Dict[str, str]]:
        """Constrói histórico de mensagens do usuário."""
        HISTORY_LIMIT = 40  # TODO: mover para configuração

        history: List[Dict[str, str]] = []
        recent_messages = await asyncio.to_thread(
            self.supabase_service.get_recent_messages,
            user_id,
            HISTORY_LIMIT,
        )

        for msg in sorted(recent_messages, key=_sort_key):
            if msg.get("content"):
                history.append({
                    "role": msg.get("role", "user"),
                    "content": msg["content"],
                })

        return history

    async def _prepare_response(
        self,
        user_id: str,
        history: List[Dict[str, str]],
        catalog_context: Optional[Dict[str, Optional[str]]]
    ) -> str:
        """Prepara a resposta final baseada no contexto."""
        catalog_message = None
        if catalog_context:
            model_context = catalog_context.get("model")
            catalog_message = catalog_context.get("user")
            if model_context:
                history.append({"role": "system", "content": model_context})

        if catalog_message:
            logger.info("Catálogo Supabase encontrado para %s; respondendo com dados estruturados", user_id)
            response_text = catalog_message
        else:
            logger.info("Nenhum catálogo disponível para %s; delegando resposta à OpenAI", user_id)
            response_text = await self.openai_service.generate_response(history=history)

        logger.debug(f"Generated response after debounce for {user_id}: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
        return response_text

    async def _cleanup_and_save(
        self,
        user_id: str,
        temp_messages: List[dict],
        consolidated: Optional[Dict[str, str]],
        response_text: str
    ):
        """Limpa mensagens temporárias e salva a conversa."""
        # Coletar IDs para limpeza
        temp_ids: List[str] = []
        if consolidated:
            for temp in temp_messages:
                temp_id = temp.get("id")
                if temp_id:
                    temp_ids.append(str(temp_id))

            # Salvar mensagem consolidada
            await self._log_message(
                user_id=user_id,
                content=consolidated["content"],
                role=consolidated["role"],
                created_at=consolidated.get("created_at"),
            )

        # Salvar resposta do assistente
        await self._log_message(user_id, response_text, role="assistant")

        # Limpar mensagens temporárias
        await asyncio.to_thread(self.supabase_service.delete_temp_messages, temp_ids)

    async def _maybe_send_daily_greeting(self, user_id: str):
        """Verifica e envia saudação diária se necessário."""
        if not self.supabase_service or not user_id:
            return

        try:
            latest_message = await asyncio.to_thread(self.supabase_service.get_latest_message, user_id)
        except Exception as exc:
            logger.error("Erro ao verificar primeira mensagem do dia para %s: %s", user_id, exc)
            return

        # Lógica de saudação diária (simplificada)
        now_local = asyncio.get_event_loop().time()  # TODO: implementar timezone
        should_send = not latest_message

        if should_send:
            greeting = "Radar ativado 🚨"
            await self._log_message(user_id, greeting, role="assistant")
            await self._send_whatsapp_message(user_id, greeting)

    async def _record_temp_message(self, user_id: str, text: str, message_data: dict):
        """Registra mensagem temporária."""
        from app.utils.formatters import _extract_created_at

        created_at = _extract_created_at(message_data)
        message_id = message_data.get('key', {}).get('id') or message_data.get('id') or ""

        payload = {
            "user_id": user_id,
            "role": "user",
            "content": text,
            "message_id": message_id,
            "created_at": created_at,
        }
        await asyncio.to_thread(self.supabase_service.save_temp_message, payload)

    async def _schedule_user_processing(self, user_id: str):
        """Agenda processamento debounced com typing indicator."""
        # Enviar status "composing" durante o processamento com delay longo
        await self._update_presence(user_id, "composing", 20000)  # 20 segundos como no N8N

        # Aguardar debounce de 10 segundos
        await asyncio.sleep(10)

        # Voltar ao status normal antes de processar
        await self._update_presence(user_id, "paused")

        await self.process_debounced_messages(user_id)

    async def _log_message(self, user_id: str, content: str, role: str, created_at: Optional[str] = None):
        """Persiste mensagem no Supabase."""
        if not self.supabase_service:
            return

        try:
            from datetime import datetime, timezone
            payload = {
                "user_id": user_id,
                "role": role,
                "content": content,
                "created_at": created_at or datetime.now(timezone.utc).isoformat(),
            }
            await asyncio.to_thread(self.supabase_service.save_message, payload)
        except Exception as exc:
            logger.error("Erro ao salvar mensagem no Supabase: %s", exc)

    async def _send_whatsapp_message(self, user_id: str, text: str):
        """Envia mensagem para o usuário via WhatsApp."""
        try:
            await asyncio.to_thread(self.evolution_service.send_message, user_id, text)
        except Exception as exc:
            logger.error("Erro ao enviar mensagem WhatsApp para %s: %s", user_id, exc)

    async def _update_presence(self, user_id: str, presence: str, delay_ms: Optional[int] = None):
        """Atualiza a presença do usuário no WhatsApp."""
        try:
            result = await asyncio.to_thread(self.evolution_service.send_presence, user_id, presence, delay_ms)
            if result is None:
                logger.debug("Presence update skipped (timeout) for %s", user_id)
            else:
                logger.debug("Presence updated successfully for %s", user_id)
        except Exception as exc:
            logger.error("Erro ao atualizar presença para %s: %s", user_id, exc)

__all__ = ["ChatbotService", "ConversationManager", "MessageHandler", "ProductService"]
