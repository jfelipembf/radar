"""
EXEMPLO: Como a IA do RADAR consulta e compara produtos
Este arquivo mostra como implementar as buscas inteligentes com controle de acesso
"""

import os
from supabase import create_client, Client

# Conexão com Supabase - PROJETO CONSULT (lpjudjwivlfbztfquyty)
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

class RadarProductSearch:
    """Classe para buscas inteligentes de produtos no RADAR com controle de acesso"""

    def __init__(self, current_user_email: str = None):
        """Inicializa com controle de acesso"""
        self.current_user_email = current_user_email

    def set_current_user(self, email: str):
        """Define o usuário atual para controle de acesso"""
        self.current_user_email = email

    def buscar_produto_por_nome(self, nome_produto: str, setor: str = None):
        """Busca produtos por nome aproximado"""
        query = supabase.table('products').select('*').ilike('produto', f'%{nome_produto}%')

        if setor:
            query = query.eq('setor', setor)

        return query.execute()

    def buscar_produtos_loja(self, loja_id: str = None):
        """Busca apenas produtos da loja atual (para edições)"""
        if not loja_id and self.current_user_email:
            # Buscar loja_id do usuário
            loja_result = supabase.table('loja_usuarios').select('loja_id').eq('email', self.current_user_email).execute()
            if loja_result.data:
                loja_id = loja_result.data[0]['loja_id']

        if loja_id:
            return supabase.table('products').select('*').eq('loja_id', loja_id).execute()

        return {"data": [], "error": "Usuário não autorizado ou loja não encontrada"}

    def criar_produto_loja(self, dados_produto: dict):
        """Cria produto apenas para a loja do usuário atual"""
        if not self.current_user_email:
            return {"error": "Usuário não autenticado"}

        # Buscar loja_id do usuário
        loja_result = supabase.table('loja_usuarios').select('loja_id').eq('email', self.current_user_email).execute()

        if not loja_result.data:
            return {"error": "Usuário não pertence a nenhuma loja"}

        loja_id = loja_result.data[0]['loja_id']

        # Buscar nome da loja
        loja_info = supabase.table('lojas').select('nome').eq('id', loja_id).execute()

        # Adicionar campos obrigatórios
        dados_produto.update({
            'loja_id': loja_id,
            'comercio': loja_info.data[0]['nome'] if loja_info.data else 'Loja',
            'criado_por': self.current_user_email,
            'atualizado_por': self.current_user_email
        })

        return supabase.table('products').insert(dados_produto).execute()

    def atualizar_produto_loja(self, produto_id: str, dados_atualizacao: dict):
        """Atualiza produto apenas se pertencer à loja do usuário"""
        if not self.current_user_email:
            return {"error": "Usuário não autenticado"}

        # Verificar se produto pertence à loja do usuário
        produto = supabase.table('products').select('loja_id, version').eq('id', produto_id).execute()

        if not produto.data:
            return {"error": "Produto não encontrado"}

        # Verificar se usuário tem acesso à loja
        loja_result = supabase.table('loja_usuarios').select('loja_id').eq('email', self.current_user_email).execute()

        if not loja_result.data or produto.data[0]['loja_id'] != loja_result.data[0]['loja_id']:
            return {"error": "Acesso negado - produto não pertence à sua loja"}

        # Adicionar campos de auditoria
        dados_atualizacao.update({
            'atualizado_por': self.current_user_email,
            'version': produto.data[0]['version'] + 1
        })

        return supabase.table('products').update(dados_atualizacao).eq('id', produto_id).execute()

    def deletar_produto_loja(self, produto_id: str):
        """Deleta produto apenas se pertencer à loja do usuário"""
        if not self.current_user_email:
            return {"error": "Usuário não autenticado"}

        # Verificar propriedade
        produto = supabase.table('products').select('loja_id').eq('id', produto_id).execute()

        if not produto.data:
            return {"error": "Produto não encontrado"}

        loja_result = supabase.table('loja_usuarios').select('loja_id').eq('email', self.current_user_email).execute()

        if not loja_result.data or produto.data[0]['loja_id'] != loja_result.data[0]['loja_id']:
            return {"error": "Acesso negado - produto não pertence à sua loja"}

        return supabase.table('products').delete().eq('id', produto_id).execute()

    def comparar_precos(self, produto: str, setor: str = 'autopecas'):
        """Compara preços de um produto em diferentes lojas (ACESSO PÚBLICO)"""
        # Busca todos os produtos similares (dados públicos para comparação)
        produtos = self.buscar_produto_por_nome(produto, setor)

        if not produtos.data:
            return {"erro": f"Nenhum produto encontrado para: {produto}"}

        # Ordena por preço (menor para maior)
        produtos_ordenados = sorted(produtos.data, key=lambda x: x['preco'])

        # Melhor opção
        melhor = produtos_ordenados[0]

        # Calcula economia em relação ao mais caro
        mais_caro = produtos_ordenados[-1]
        economia = mais_caro['preco'] - melhor['preco']
        economia_percentual = (economia / mais_caro['preco']) * 100 if mais_caro['preco'] > 0 else 0

        return {
            "melhor_opcao": {
                "loja": melhor['comercio'],
                "produto": melhor['produto'],
                "preco": melhor['preco'],
                "marca": melhor['marca'],
                "unidade": melhor['unidade']
            },
            "comparacao": [
                {
                    "loja": p['comercio'],
                    "preco": p['preco'],
                    "diferenca": p['preco'] - melhor['preco']
                }
                for p in produtos_ordenados
            ],
            "economia_total": {
                "valor": economia,
                "percentual": round(economia_percentual, 1)
            }
        }

    def buscar_por_categoria(self, categoria: str, limite_preco: float = None):
        """Busca produtos por categoria com filtro de preço"""
        query = supabase.table('products').select('*').eq('categoria', categoria).eq('disponivel', True)

        if limite_preco:
            query = query.lte('preco', limite_preco)

        return query.limit(20).execute()

    def produtos_recentes(self, dias: int = 7):
        """Busca produtos atualizados recentemente"""
        from datetime import datetime, timedelta

        data_limite = datetime.now() - timedelta(days=dias)

        return supabase.table('products').select('*').gte('atualizado_em', data_limite.isoformat()).execute()


# EXEMPLOS DE USO:

def exemplo_busca_oleo():
    """Como a IA busca óleo de motor"""
    radar = RadarProductSearch()

    # Usuário pergunta: "Quanto custa óleo 5W30?"
    resultado = radar.comparar_precos("óleo 5W30")

    print("🎯 RESULTADO DA BUSCA:")
    if "erro" not in resultado:
        print(f"🏪 Melhor preço: {resultado['melhor_opcao']['loja']}")
        print(f"💵 Valor: R$ {resultado['melhor_opcao']['preco']}")
        print(f"📊 Economia: R$ {resultado['economia_total']['valor']} ({resultado['economia_total']['percentual']}%)")
    else:
        print(f"❌ {resultado['erro']}")


def exemplo_crud_loja():
    """Exemplo de como uma loja gerencia seus produtos"""
    radar = RadarProductSearch()

    # Definir usuário da loja
    radar.set_current_user('joao@autopecasmacedo.com.br')

    # Criar novo produto
    novo_produto = {
        'setor': 'autopecas',
        'produto': 'Velas de Ignição',
        'descricao': 'Velas de ignição para motor 1.0',
        'marca': 'Marca X',
        'unidade': 'jogo',
        'preco': 89.90,
        'categoria': 'ignicao',
        'disponivel': True
    }

    resultado = radar.criar_produto_loja(novo_produto)
    print(f"✅ Produto criado: {resultado}")


if __name__ == "__main__":
    # Testes das funções
    exemplo_busca_oleo()
    print("\n" + "="*50 + "\n")
    exemplo_crud_loja()
