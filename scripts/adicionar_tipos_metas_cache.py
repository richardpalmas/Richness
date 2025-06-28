#!/usr/bin/env python3
"""
Script para adicionar tipos de insight de metas ao constraint da tabela cache_insights_llm
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.database_manager_v2 import DatabaseManager
from datetime import datetime

def adicionar_tipos_metas_cache():
    """Adiciona tipos de insights de metas ao constraint da tabela cache"""
    print("🔄 Adicionando tipos de insight de metas ao constraint...")
    
    try:
        db = DatabaseManager()
        
        # Verificar se a tabela existe
        tabelas = db.executar_query("SELECT name FROM sqlite_master WHERE type='table' AND name='cache_insights_llm'")
        if not tabelas:
            print("❌ Tabela cache_insights_llm não encontrada!")
            return False
        
        print("✅ Tabela cache_insights_llm encontrada")
        
        # Verificar estrutura atual
        colunas = db.executar_query("PRAGMA table_info(cache_insights_llm)")
        print(f"🔍 Colunas encontradas: {len(colunas)}")
        
        # Verificar registros existentes
        total_registros = db.executar_query("SELECT COUNT(*) as count FROM cache_insights_llm")[0]['count']
        print(f"📊 Total de registros existentes: {total_registros}")
        
        # Fazer backup dos dados existentes
        backup_data = []
        if total_registros > 0:
            print("⚠️  Há dados na tabela. Fazendo backup antes da migração...")
            backup_data = db.executar_query("SELECT * FROM cache_insights_llm ORDER BY id")
            print(f"💾 Backup criado: {len(backup_data)} registros")
        
        print("🔧 Recriando tabela com constraint atualizado incluindo tipos de metas...")
        
        # 1. Renomear tabela antiga
        db.executar_update("ALTER TABLE cache_insights_llm RENAME TO cache_insights_llm_old")
        print("✅ Tabela antiga renomeada")
        
        # 2. Criar nova tabela com constraint atualizado INCLUINDO tipos de metas
        with db.get_connection() as conn:
            conn.execute("""
                CREATE TABLE cache_insights_llm (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    insight_type TEXT NOT NULL,
                    personalidade TEXT NOT NULL,
                    data_hash TEXT NOT NULL,
                    prompt_hash TEXT NOT NULL,
                    insight_titulo TEXT NOT NULL,
                    insight_valor TEXT,
                    insight_comentario TEXT NOT NULL,
                    modelo_usado TEXT DEFAULT 'gpt-4o-mini',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    used_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    UNIQUE(user_id, insight_type, personalidade, data_hash, prompt_hash),
                    CONSTRAINT insight_type_valid CHECK (insight_type IN (
                        'saldo_mensal', 'maior_gasto', 'economia_potencial', 'alerta_gastos',
                        'total_gastos_cartao', 'maior_gasto_cartao', 'padrao_gastos_cartao', 'controle_cartao',
                        'analise_compromissos_metas', 'progresso_metas_economia', 
                        'capacidade_pagamento_metas', 'estrategia_financeira_metas'
                    ))
                )
            """)
        
        print("✅ Nova tabela criada com constraint atualizado incluindo tipos de metas")
        
        # 3. Migrar dados válidos (agora incluindo os tipos de metas)
        if total_registros > 0:
            print("📋 Migrando dados válidos...")
            
            tipos_validos = [
                'saldo_mensal', 'maior_gasto', 'economia_potencial', 'alerta_gastos',
                'total_gastos_cartao', 'maior_gasto_cartao', 'padrao_gastos_cartao', 'controle_cartao',
                'analise_compromissos_metas', 'progresso_metas_economia', 
                'capacidade_pagamento_metas', 'estrategia_financeira_metas'
            ]
            
            migrated_count = 0
            for row in backup_data:
                if row['insight_type'] in tipos_validos:
                    try:
                        db.executar_insert("""
                            INSERT INTO cache_insights_llm 
                            (user_id, insight_type, personalidade, data_hash, prompt_hash,
                             insight_titulo, insight_valor, insight_comentario, modelo_usado,
                             created_at, expires_at, used_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, [
                            row['user_id'], row['insight_type'], row['personalidade'],
                            row['data_hash'], row['prompt_hash'], row['insight_titulo'],
                            row['insight_valor'], row['insight_comentario'], row['modelo_usado'],
                            row['created_at'], row['expires_at'], row['used_count']
                        ])
                        migrated_count += 1
                    except Exception as e:
                        print(f"⚠️  Erro ao migrar registro {row['id']}: {e}")
                else:
                    print(f"⚠️  Registro com tipo inválido ignorado: {row['insight_type']}")
            
            print(f"✅ {migrated_count} registros migrados com sucesso")
        
        # 4. Remover tabela antiga
        db.executar_update("DROP TABLE cache_insights_llm_old")
        print("✅ Tabela antiga removida")
        
        # 5. Verificar se migração foi bem-sucedida
        new_count = db.executar_query("SELECT COUNT(*) as count FROM cache_insights_llm")[0]['count']
        print(f"📊 Registros na nova tabela: {new_count}")
        
        # 6. Teste de inserção com novos tipos de metas
        print("🧪 Testando inserção com tipos de metas...")
        try:
            # Testar cada tipo de meta
            tipos_teste = [
                'analise_compromissos_metas',
                'progresso_metas_economia', 
                'capacidade_pagamento_metas',
                'estrategia_financeira_metas'
            ]
            
            for tipo in tipos_teste:
                test_id = db.executar_insert("""
                    INSERT INTO cache_insights_llm 
                    (user_id, insight_type, personalidade, data_hash, prompt_hash,
                     insight_titulo, insight_valor, insight_comentario, expires_at)
                    VALUES (1, ?, 'clara', 'test_hash', 'test_prompt',
                            'Teste Metas', 'R$ 100,00', 'Teste de inserção metas', 
                            datetime('now', '+24 hours'))
                """, [tipo])
                
                if test_id > 0:
                    print(f"✅ Teste {tipo} bem-sucedido!")
                    # Remover registro de teste
                    db.executar_update("DELETE FROM cache_insights_llm WHERE id = ?", [test_id])
                else:
                    print(f"❌ Teste {tipo} falhou")
                    return False
                    
        except Exception as e:
            print(f"❌ Erro nos testes de inserção: {e}")
            return False
        
        print("\n🎉 Migração concluída com sucesso!")
        print("✅ Agora a tabela suporta TODOS os tipos de insight, incluindo:")
        print("   - Insights gerais (saldo_mensal, maior_gasto, etc.)")
        print("   - Insights do cartão (total_gastos_cartao, maior_gasto_cartao, etc.)")
        print("   - Insights de metas (analise_compromissos_metas, progresso_metas_economia, etc.)")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = adicionar_tipos_metas_cache()
    if sucesso:
        print("\n🚀 Sistema pronto para usar cache de insights de metas!")
    else:
        print("\n❌ Falha na migração. Verifique os logs acima.")
    exit(0 if sucesso else 1) 