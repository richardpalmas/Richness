#!/usr/bin/env python3
"""
Script de migração para atualizar o constraint da tabela cache_insights_llm
Adiciona suporte aos novos tipos de insight do cartão
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database_manager_v2 import DatabaseManager

def migrar_constraint_cache_insights():
    """Migra o constraint da tabela cache_insights_llm"""
    print("🔄 Migrando constraint da tabela cache_insights_llm...")
    
    try:
        db = DatabaseManager()
        
        # Verificar se a tabela existe
        result = db.executar_query("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='cache_insights_llm'
        """)
        
        if not result:
            print("⚠️  Tabela cache_insights_llm não existe ainda. Criando nova...")
            db.init_database()
            print("✅ Tabela criada com constraint atualizado!")
            return True
        
        print("📋 Tabela cache_insights_llm encontrada. Verificando constraint...")
        
        # Verificar constraint atual
        table_info = db.executar_query("PRAGMA table_info(cache_insights_llm)")
        print(f"🔍 Colunas encontradas: {len(table_info)}")
        
        # Verificar se há dados na tabela
        count_result = db.executar_query("SELECT COUNT(*) as count FROM cache_insights_llm")
        total_registros = count_result[0]['count'] if count_result else 0
        
        print(f"📊 Total de registros existentes: {total_registros}")
        
        if total_registros > 0:
            print("⚠️  Há dados na tabela. Fazendo backup antes da migração...")
            
            # Criar backup dos dados
            backup_data = db.executar_query("SELECT * FROM cache_insights_llm")
            print(f"💾 Backup criado: {len(backup_data)} registros")
        
        print("🔧 Recriando tabela com constraint atualizado...")
        
        # 1. Renomear tabela antiga
        db.executar_update("ALTER TABLE cache_insights_llm RENAME TO cache_insights_llm_old")
        print("✅ Tabela antiga renomeada")
        
        # 2. Criar nova tabela com constraint atualizado
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
                        'total_gastos_cartao', 'maior_gasto_cartao', 'padrao_gastos_cartao', 'controle_cartao'
                    ))
                )
            """)
        
        print("✅ Nova tabela criada com constraint atualizado")
        
        # 3. Migrar dados válidos (apenas os tipos que são válidos no novo constraint)
        if total_registros > 0:
            print("📋 Migrando dados válidos...")
            
            tipos_validos = [
                'saldo_mensal', 'maior_gasto', 'economia_potencial', 'alerta_gastos',
                'total_gastos_cartao', 'maior_gasto_cartao', 'padrao_gastos_cartao', 'controle_cartao'
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
        
        # Teste de inserção com novo tipo
        print("🧪 Testando inserção com tipo do cartão...")
        try:
            test_id = db.executar_insert("""
                INSERT INTO cache_insights_llm 
                (user_id, insight_type, personalidade, data_hash, prompt_hash,
                 insight_titulo, insight_valor, insight_comentario, expires_at)
                VALUES (1, 'total_gastos_cartao', 'clara', 'test_hash', 'test_prompt',
                        'Teste', 'R$ 100,00', 'Teste de inserção', 
                        datetime('now', '+24 hours'))
            """)
            
            if test_id > 0:
                print("✅ Teste de inserção bem-sucedido!")
                # Remover registro de teste
                db.executar_update("DELETE FROM cache_insights_llm WHERE id = ?", [test_id])
            else:
                print("❌ Teste de inserção falhou")
                return False
                
        except Exception as e:
            print(f"❌ Erro no teste de inserção: {e}")
            return False
        
        print("\n🎉 Migração concluída com sucesso!")
        print("✅ Agora a tabela suporta todos os tipos de insight, incluindo os do cartão")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = migrar_constraint_cache_insights()
    sys.exit(0 if sucesso else 1) 