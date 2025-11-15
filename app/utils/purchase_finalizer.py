"""Gerenciador de finalização de compras."""

import logging
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PurchaseFinalizer:
    """Gerencia finalização de compras e comunicação com lojas."""
    
    def __init__(self, supabase_service):
        """
        Inicializa o finalizador.
        
        Args:
            supabase_service: Instância do SupabaseService
        """
        self.supabase_service = supabase_service
    
    def get_store_phone(self, store_name: str) -> Optional[str]:
        """
        Busca telefone da loja no Supabase.
        
        Args:
            store_name: Nome da loja
            
        Returns:
            Telefone formatado ou None
        """
        try:
            import requests
            
            url = f"{self.supabase_service._rest_base}/stores"
            params = {
                "select": "phone",
                "name": f"eq.{store_name}",
                "limit": "1"
            }
            
            response = requests.get(url, headers=self.supabase_service._headers, params=params, timeout=10)
            
            if response.ok and response.json():
                stores = response.json()
                if stores and len(stores) > 0:
                    phone = stores[0].get("phone", "")
                    # Limpar formatação
                    return phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            
            return None
        except Exception as exc:
            logger.warning(f"Erro ao buscar telefone da loja {store_name}: {exc}")
            return None
    
    def format_products_for_customer(self, products: List[Dict[str, Any]]) -> str:
        """
        Formata lista de produtos para o cliente.
        
        Args:
            products: Lista de produtos com name, price, quantity
            
        Returns:
            Texto formatado
        """
        lines = []
        for p in products:
            name = p.get("name", "Produto")
            price = float(p.get("price", 0))
            quantity = int(p.get("quantity", 1))
            subtotal = price * quantity
            
            if quantity > 1:
                lines.append(f"• {quantity}x {name}: R$ {subtotal:.2f} (R$ {price:.2f} cada)")
            else:
                lines.append(f"• {name}: R$ {price:.2f}")
        
        return "\n".join(lines)
    
    def format_products_for_store(self, products: List[Dict[str, Any]]) -> str:
        """
        Formata lista de produtos para a loja (mais detalhada).
        
        Args:
            products: Lista de produtos com name, price, quantity
            
        Returns:
            Texto formatado
        """
        lines = []
        for p in products:
            name = p.get("name", "Produto")
            price = float(p.get("price", 0))
            quantity = int(p.get("quantity", 1))
            subtotal = price * quantity
            
            lines.append(f"• {quantity}x {name}")
            lines.append(f"  Valor unitário: R$ {price:.2f}")
            lines.append(f"  Subtotal: R$ {subtotal:.2f}")
        
        return "\n".join(lines)
    
    def create_store_message(
        self,
        store_name: str,
        customer_id: str,
        products: List[Dict[str, Any]],
        total: float
    ) -> str:
        """
        Cria mensagem para enviar à loja.
        
        Args:
            store_name: Nome da loja
            customer_id: ID/telefone do cliente
            products: Lista de produtos
            total: Valor total
            
        Returns:
            Mensagem formatada para a loja
        """
        today = datetime.now().strftime("%d/%m/%Y às %H:%M")
        products_text = self.format_products_for_store(products)
        
        message = f"""🛒 *NOVO ORÇAMENTO - RADAR*

📅 *Data:* {today}
📞 *Cliente:* {customer_id}

📦 *PRODUTOS SOLICITADOS:*
{products_text}

💰 *VALOR TOTAL: R$ {total:.2f}*

⚠️ *IMPORTANTE:*
Por favor, entre em contato com o cliente para:
• Confirmar se os valores estão atualizados
• Informar sobre taxas de entrega (se houver)
• Confirmar disponibilidade dos produtos

O cliente aguarda seu contato! 📱"""
        
        return message
    
    def create_customer_message(
        self,
        store_name: str,
        products: List[Dict[str, Any]],
        total: float,
        store_phone: Optional[str] = None
    ) -> str:
        """
        Cria mensagem para enviar ao cliente.
        
        Args:
            store_name: Nome da loja
            products: Lista de produtos
            total: Valor total
            store_phone: Telefone da loja (opcional)
            
        Returns:
            Mensagem formatada para o cliente
        """
        products_text = self.format_products_for_customer(products)
        
        message = f"""✅ *Pedido Confirmado!*

📦 *Resumo do Pedido:*
🏪 Loja: {store_name}
💰 Total: R$ {total:.2f}

📋 *Produtos:*
{products_text}

💰 *Valor Total: R$ {total:.2f}*

📞 *Próximos Passos:*
A loja {store_name} receberá seu pedido e entrará em contato para:
• Confirmar valores atualizados
• Informar sobre taxas de entrega
• Combinar forma de pagamento e entrega"""
        
        # Adicionar link do WhatsApp se disponível
        if store_phone:
            whatsapp_link = f"https://wa.me/{store_phone}"
            message += f"\n\n🔗 *Contato da Loja:*\n{whatsapp_link}"
        
        message += "\n\nObrigado pela preferência! 🎉"
        
        return message
    
    def create_whatsapp_link(self, phone: str, message: str) -> str:
        """
        Cria link do WhatsApp com mensagem pré-preenchida.
        
        Args:
            phone: Telefone (apenas números)
            message: Mensagem a ser enviada
            
        Returns:
            URL do WhatsApp
        """
        encoded_message = urllib.parse.quote(message)
        return f"https://wa.me/{phone}?text={encoded_message}"
    
    def finalize_purchase(
        self,
        store_name: str,
        customer_id: str,
        products: List[Dict[str, Any]],
        total: float
    ) -> Dict[str, Any]:
        """
        Finaliza compra criando mensagens e links.
        
        Args:
            store_name: Nome da loja vencedora
            customer_id: ID/telefone do cliente
            products: Lista de produtos com name, price, quantity
            total: Valor total da compra
            
        Returns:
            Dict com:
                - success: bool
                - customer_message: mensagem para o cliente
                - store_message: mensagem para a loja
                - store_phone: telefone da loja
                - whatsapp_link: link direto para WhatsApp da loja
        """
        try:
            logger.info(f"Finalizando compra: {store_name}, total: R$ {total:.2f}")
            
            # Buscar telefone da loja
            store_phone = self.get_store_phone(store_name)
            
            if not store_phone:
                logger.warning(f"Telefone da loja {store_name} não encontrado")
            
            # Criar mensagens
            store_message = self.create_store_message(
                store_name=store_name,
                customer_id=customer_id,
                products=products,
                total=total
            )
            
            customer_message = self.create_customer_message(
                store_name=store_name,
                products=products,
                total=total,
                store_phone=store_phone
            )
            
            # Criar link WhatsApp (direto, sem mensagem pré-preenchida)
            whatsapp_link = None
            if store_phone:
                whatsapp_link = f"https://wa.me/{store_phone}"
            
            result = {
                "success": True,
                "customer_message": customer_message,
                "store_message": store_message,
                "store_phone": store_phone,
                "whatsapp_link": whatsapp_link
            }
            
            logger.info("Compra finalizada com sucesso")
            return result
            
        except Exception as exc:
            logger.error(f"Erro ao finalizar compra: {exc}")
            return {
                "success": False,
                "error": str(exc)
            }


__all__ = ["PurchaseFinalizer"]
