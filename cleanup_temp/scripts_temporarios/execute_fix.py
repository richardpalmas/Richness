#!/usr/bin/env python3

print("🚀 EXECUTANDO CORREÇÃO DE CATEGORIZAÇÃO")
print("=" * 50)

try:
    import sqlite3
    import os
      # Conectar ao banco
    db_path = 'richness.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        exit(1)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Regras de categorização
    def categorize_basic(descricao, valor):
        if not descricao:
            return 'Outros'
        
        desc = descricao.lower()
        
        if any(word in desc for word in ['mercado', 'supermercado', 'padaria', 'restaurante', 'lanchonete', 'ifood']):
            return 'Alimentação'
        elif any(word in desc for word in ['uber', 'taxi', '99', 'combustivel', 'gasolina', 'posto']):
            return 'Transporte'
        elif any(word in desc for word in ['farmacia', 'hospital', 'medico', 'clinica']):
            return 'Saúde'
        elif any(word in desc for word in ['pix', 'ted', 'doc', 'transferencia']):
            return 'Transferência'
        elif any(word in desc for word in ['agua', 'luz', 'gas', 'telefone', 'internet', 'aluguel']):
            return 'Moradia'
        elif any(word in desc for word in ['loja', 'shopping', 'roupa', 'eletronico']):
            return 'Compras'
        elif any(word in desc for word in ['cinema', 'teatro', 'netflix', 'spotify']):
            return 'Lazer'
        elif any(word in desc for word in ['salario', 'vencimento']) and valor > 0:
            return 'Salário'
        elif valor > 0 and any(word in desc for word in ['rendimento', 'dividendo']):
            return 'Receita'
        else:
            return 'Outros'
    
    # Buscar usuário
    cur.execute('SELECT id, nome FROM usuarios LIMIT 1')
    user = cur.fetchone()
    
    if not user:
        print("❌ Nenhum usuário encontrado")
        conn.close()
        exit(1)
    
    user_id = user['id']
    nome = user['nome']
    print(f"👤 Processando usuário: {nome} (ID: {user_id})")
      # Buscar extratos para categorizar
    cur.execute('''
        SELECT id, descricao, valor, categoria 
        FROM extratos 
        WHERE usuario_id = ? AND (categoria IS NULL OR categoria = 'Outros' OR categoria = 'Transferência')
        ORDER BY data DESC 
        LIMIT 100
    ''', (user_id,))
    
    extratos = cur.fetchall()
    print(f"📝 Encontrados {len(extratos)} extratos para processar")
    
    processed = 0
    for extrato in extratos:
        id_transacao = extrato['id']
        descricao = extrato['descricao']
        valor = extrato['valor'] or 0
        categoria_atual = extrato['categoria']
        
        # Aplicar categorização
        nova_categoria = categorize_basic(descricao, valor)
        
        if nova_categoria != categoria_atual:
            try:
                # Atualizar categoria
                cur.execute('UPDATE extratos SET categoria = ? WHERE id = ?', (nova_categoria, id_transacao))
                  # Salvar na tabela de IA (se existir)
                try:
                    cur.execute('''
                        INSERT INTO ai_categorizations 
                        (usuario_id, transaction_type, transaction_id, original_description, 
                         original_category, ai_category, ai_confidence, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ''', (user_id, 'extrato', id_transacao, descricao or '', 
                         categoria_atual, nova_categoria, 0.7))
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e):
                        print(f"  ⚠️  Tabela ai_categorizations não existe, pulando...")
                    else:
                        print(f"  ⚠️  Erro ao salvar em ai_categorizations: {e}")
                except Exception as e:
                    print(f"  ⚠️  Erro ao salvar em ai_categorizations: {e}")
                
                processed += 1
                desc_show = (descricao or 'Sem descrição')[:30]
                print(f"  ✅ {id_transacao}: {desc_show}... -> {nova_categoria}")
                
            except Exception as e:
                print(f"  ❌ Erro ao processar {id_transacao}: {e}")
    
    # Commit changes
    conn.commit()
    print(f"\n✅ Processados {processed} extratos!")
    
    # Mostrar resumo
    print("\n📊 RESUMO DAS CATEGORIAS:")
    cur.execute('SELECT categoria, COUNT(*) as count FROM extratos WHERE usuario_id = ? GROUP BY categoria ORDER BY count DESC', (user_id,))
    results = cur.fetchall()
    
    for row in results:
        categoria = row['categoria'] or 'NULL'
        count = row['count']
        print(f"  {categoria}: {count}")
    
    conn.close()
    print("\n🎉 CORREÇÃO CONCLUÍDA!")
    
except Exception as e:
    print(f"❌ Erro durante execução: {e}")
    import traceback
    traceback.print_exc()
