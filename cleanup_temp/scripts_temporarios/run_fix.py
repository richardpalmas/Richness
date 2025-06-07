#!/usr/bin/env python3

import os
import sys
from database import get_connection, save_ai_categorization, update_transaction_category

def categorize_basic(descricao, valor):
    """Categorização básica por regras"""
    if not descricao:
        return 'Outros'
    
    desc = descricao.lower()
    
    # Regras de categorização
    if any(word in desc for word in ['mercado', 'supermercado', 'padaria', 'restaurante', 'lanchonete', 'ifood', 'alimentacao']):
        return 'Alimentação'
    elif any(word in desc for word in ['uber', 'taxi', '99', 'combustivel', 'gasolina', 'transporte', 'posto']):
        return 'Transporte'
    elif any(word in desc for word in ['farmacia', 'hospital', 'medico', 'clinica', 'medicamento']):
        return 'Saúde'
    elif any(word in desc for word in ['pix', 'ted', 'doc', 'transferencia', 'deposito', 'saque']):
        return 'Transferência'
    elif any(word in desc for word in ['agua', 'luz', 'gas', 'telefone', 'internet', 'aluguel', 'condominio']):
        return 'Moradia'
    elif any(word in desc for word in ['loja', 'shopping', 'roupa', 'eletronico', 'mercadolivre']):
        return 'Compras'
    elif any(word in desc for word in ['cinema', 'teatro', 'netflix', 'spotify', 'jogo', 'festa']):
        return 'Lazer'
    elif any(word in desc for word in ['salario', 'vencimento', 'bonus']) and valor > 0:
        return 'Salário'
    elif valor > 0 and any(word in desc for word in ['rendimento', 'dividendo', 'investimento']):
        return 'Receita'
    else:
        return 'Outros'

def main():
    print("🚀 CORREÇÃO DE CATEGORIZAÇÃO - VERSÃO DIRETA")
    print("=" * 50)
    
    # Limpar caches
    print("🧹 Limpando caches...")
    cache_files = ['cache/cache.pkl', 'cache/categorias_cache.pkl', 'cache/descricoes_cache.pkl']
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"  ✅ Removido: {cache_file}")
    
    # Conectar ao banco
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Buscar primeiro usuário para teste
        cur.execute('SELECT id, nome FROM usuarios LIMIT 1')
        user = cur.fetchone()
        
        if not user:
            print("❌ Nenhum usuário encontrado")
            return
        
        user_dict = dict(user)
        user_id = user_dict['id']
        nome = user_dict['nome']
        
        print(f"👤 Processando usuário: {nome} (ID: {user_id})")
          # Buscar extratos que precisam ser categorizados
        cur.execute('''
            SELECT id, descricao, valor, categoria 
            FROM extratos 
            WHERE usuario_id = ? 
            ORDER BY data DESC 
            LIMIT 50
        ''', (user_id,))
        
        extratos = cur.fetchall()
        print(f"📝 Encontrados {len(extratos)} extratos para processar")
        
        processed = 0
        for extrato in extratos:
            extrato_dict = dict(extrato)
            id_transacao = extrato_dict['id']
            descricao = extrato_dict['descricao']
            valor = extrato_dict['valor'] or 0
            categoria_atual = extrato_dict['categoria']
            
            # Aplicar categorização
            nova_categoria = categorize_basic(descricao, valor)
            
            try:
                # Salvar na tabela de IA
                save_ai_categorization(
                    usuario_id=user_id,
                    transaction_type='extrato',
                    transaction_id=id_transacao,
                    original_description=descricao or '',
                    original_category=categoria_atual,
                    ai_category=nova_categoria,
                    ai_confidence=0.7
                )
                
                # Atualizar na tabela original
                update_transaction_category('extrato', id_transacao, nova_categoria)
                
                processed += 1
                desc_show = (descricao or 'Sem descrição')[:30]
                print(f"  ✅ {id_transacao}: {desc_show}... -> {nova_categoria}")
                
            except Exception as e:
                print(f"  ❌ Erro ao processar {id_transacao}: {e}")
        
        print(f"\n✅ Processados {processed} extratos!")
        
        # Mostrar resumo
        print("\n📊 RESUMO DAS CATEGORIAS:")
        cur.execute('SELECT categoria, COUNT(*) FROM extratos WHERE usuario_id = ? GROUP BY categoria ORDER BY COUNT(*) DESC', (user_id,))
        results = cur.fetchall()
        
        for row in results:
            row_dict = dict(row)
            categoria = row_dict['categoria'] or 'NULL'
            count = row_dict['COUNT(*)']
            print(f"  {categoria}: {count}")
        
        # Verificar registros de IA
        cur.execute('SELECT COUNT(*) FROM ai_categorizations WHERE usuario_id = ?', (user_id,))
        ai_count = cur.fetchone()[0]
        print(f"\n🤖 Registros na ai_categorizations: {ai_count}")
        
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
    
    print("\n🎉 CORREÇÃO CONCLUÍDA!")

if __name__ == "__main__":
    main()
