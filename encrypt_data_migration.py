#!/usr/bin/env python3
"""
Data Encryption Migration - Criptografia de dados sensíveis existentes
"""
import sqlite3
import sys
import os
import json
from datetime import datetime

# Adicionar projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def encrypt_sensitive_data():
    """Criptografa dados sensíveis existentes no banco"""
    try:
        from security.crypto.encryption import DataEncryption
        from security.audit.security_logger import get_security_logger
        
        print("🔐 CRIPTOGRAFIA DE DADOS SENSÍVEIS")
        print("=" * 40)
        
        # Inicializar componentes
        encryption = DataEncryption()
        logger = get_security_logger()
        
        # Conectar ao banco
        conn = sqlite3.connect('richness.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Verificar emails não criptografados
        cur.execute("""
            SELECT id, usuario, email 
            FROM usuarios 
            WHERE email LIKE '%@%.%' 
            AND LENGTH(email) < 200
            AND email NOT LIKE 'encrypted:%'
        """)
        
        users_to_encrypt = cur.fetchall()
        print(f"📊 Encontrados {len(users_to_encrypt)} usuários com emails para criptografar")
        
        encrypted_count = 0
        
        for user in users_to_encrypt:
            user_id, username, email = user['id'], user['usuario'], user['email']
            
            print(f"🔄 Criptografando email do usuário: {username}")
            print(f"   Email original: {email}")
            
            try:                # Criptografar email
                encrypted_email = encryption.encrypt_string(email)
                
                # Adicionar prefixo para identificar dados criptografados
                encrypted_email_marked = f"encrypted:{encrypted_email}"
                
                # Atualizar no banco
                cur.execute("""
                    UPDATE usuarios 
                    SET email = ? 
                    WHERE id = ?
                """, (encrypted_email_marked, user_id))
                
                encrypted_count += 1
                print(f"✅ Email criptografado ({len(encrypted_email_marked)} chars)")
                
                # Log da criptografia
                logger.log_data_access(
                    username=username,
                    operation='encrypt',
                    resource='user_email',
                    success=True
                )
                
                logger.log_system_event(
                    event_type='data_encryption',
                    details={
                        'user_id': user_id,
                        'username': username,
                        'field': 'email',
                        'encryption_method': 'AES-256'
                    },
                    username=username
                )
                
            except Exception as e:
                print(f"❌ Erro ao criptografar email do usuário {username}: {e}")
                logger.log_system_event(
                    event_type='encryption_error',
                    details={
                        'user_id': user_id,
                        'username': username,
                        'error': str(e)
                    },
                    severity='error'
                )
        
        # Verificar dados financeiros para criptografia
        print(f"\n📊 Verificando dados financeiros...")
        
        # Verificar tabela economias
        cur.execute("SELECT COUNT(*) as count FROM economias")
        economia_count = cur.fetchone()['count']
        print(f"   Registros de economia: {economia_count}")
        
        # Verificar tabela cartões
        cur.execute("SELECT COUNT(*) as count FROM cartoes")
        cartao_count = cur.fetchone()['count']
        print(f"   Registros de cartão: {cartao_count}")
        
        # Verificar tabela extratos
        cur.execute("SELECT COUNT(*) as count FROM extratos")
        extrato_count = cur.fetchone()['count']
        print(f"   Registros de extrato: {extrato_count}")
        
        # Criptografar dados financeiros
        print(f"\n🔄 Iniciando criptografia de dados financeiros...")
        
        # Criptografar descrições de extratos
        print(f"   Criptografando extratos...")
        cur.execute("""
            SELECT id, usuario_id, descricao 
            FROM extratos 
            WHERE descricao IS NOT NULL
            AND descricao NOT LIKE 'encrypted:%'
            LIMIT 500
        """)
        
        extratos_to_encrypt = cur.fetchall()
        extratos_encrypted = 0
        
        for extrato in extratos_to_encrypt:
            extrato_id, usuario_id, descricao = extrato
            
            try:
                # Obter usuário associado para logging
                cur.execute("SELECT usuario FROM usuarios WHERE id = ?", (usuario_id,))
                user_result = cur.fetchone()
                username = user_result['usuario'] if user_result else 'unknown'
                
                # Criptografar descrição
                encrypted_desc = encryption.encrypt_string(descricao)
                encrypted_desc_marked = f"encrypted:{encrypted_desc}"
                
                # Atualizar no banco
                cur.execute("""
                    UPDATE extratos 
                    SET descricao = ? 
                    WHERE id = ?
                """, (encrypted_desc_marked, extrato_id))
                
                extratos_encrypted += 1
                
                # Log para cada 50 registros para não sobrecarregar
                if extratos_encrypted % 50 == 0:
                    print(f"     ✅ {extratos_encrypted} extratos criptografados")
                    
                    # Log para o sistema
                    logger.log_system_event(
                        event_type='data_encryption_batch',
                        details={
                            'records_encrypted': 50,
                            'table': 'extratos',
                            'encryption_method': 'AES-256'
                        },
                        username='system'
                    )
                
            except Exception as e:
                print(f"     ❌ Erro ao criptografar extrato ID {extrato_id}: {str(e)[:100]}...")
        
        print(f"     ✅ Total de {extratos_encrypted} extratos criptografados")
        
        # Criptografar dados de cartões
        print(f"   Criptografando cartões...")
        cur.execute("""
            SELECT id, usuario_id, descricao, cartao_nome
            FROM cartoes 
            WHERE (descricao IS NOT NULL AND descricao NOT LIKE 'encrypted:%')
            OR (cartao_nome IS NOT NULL AND cartao_nome NOT LIKE 'encrypted:%')
        """)
        
        cartoes_to_encrypt = cur.fetchall()
        cartoes_encrypted = 0
        
        for cartao in cartoes_to_encrypt:
            cartao_id, usuario_id, descricao, cartao_nome = cartao
            
            try:
                # Obter usuário associado para logging
                cur.execute("SELECT usuario FROM usuarios WHERE id = ?", (usuario_id,))
                user_result = cur.fetchone()
                username = user_result['usuario'] if user_result else 'unknown'
                
                # Criptografar campos sensíveis
                updates = []
                params = []
                
                if descricao and not descricao.startswith('encrypted:'):
                    encrypted_desc = encryption.encrypt_string(descricao)
                    encrypted_desc_marked = f"encrypted:{encrypted_desc}"
                    updates.append("descricao = ?")
                    params.append(encrypted_desc_marked)
                
                if cartao_nome and not cartao_nome.startswith('encrypted:'):
                    encrypted_card = encryption.encrypt_string(cartao_nome)
                    encrypted_card_marked = f"encrypted:{encrypted_card}"
                    updates.append("cartao_nome = ?")
                    params.append(encrypted_card_marked)
                
                if updates:
                    # Atualizar no banco
                    query = f"UPDATE cartoes SET {', '.join(updates)} WHERE id = ?"
                    params.append(cartao_id)
                    cur.execute(query, params)
                    
                    cartoes_encrypted += 1
            
            except Exception as e:
                print(f"     ❌ Erro ao criptografar cartão ID {cartao_id}: {str(e)[:100]}...")
        
        print(f"     ✅ Total de {cartoes_encrypted} cartões criptografados")
        
        # Criptografar dados de economias
        print(f"   Criptografando economias...")
        cur.execute("""
            SELECT id, usuario_id, descricao
            FROM economias 
            WHERE descricao IS NOT NULL
            AND descricao NOT LIKE 'encrypted:%'
        """)
        
        economias_to_encrypt = cur.fetchall()
        economias_encrypted = 0
        
        for economia in economias_to_encrypt:
            economia_id, usuario_id, descricao = economia
            
            try:
                # Criptografar descrição
                if descricao:
                    encrypted_desc = encryption.encrypt_string(descricao)
                    encrypted_desc_marked = f"encrypted:{encrypted_desc}"
                    
                    # Atualizar no banco
                    cur.execute("""
                        UPDATE economias 
                        SET descricao = ? 
                        WHERE id = ?
                    """, (encrypted_desc_marked, economia_id))
                    
                    economias_encrypted += 1
            
            except Exception as e:
                print(f"     ❌ Erro ao criptografar economia ID {economia_id}: {str(e)[:100]}...")
        
        print(f"     ✅ Total de {economias_encrypted} economias criptografadas")
        
        # Commit das mudanças
        conn.commit()
        conn.close()
        
        # Total de registros financeiros criptografados
        total_financial_encrypted = extratos_encrypted + cartoes_encrypted + economias_encrypted
        
        print(f"\n✅ CRIPTOGRAFIA CONCLUÍDA!")
        print(f"📊 Emails criptografados: {encrypted_count}")
        print(f"📊 Dados financeiros criptografados: {total_financial_encrypted}")
        print(f"📊 Total de registros protegidos: {encrypted_count + total_financial_encrypted}")
        
        if encrypted_count > 0 or total_financial_encrypted > 0:
            print("\n✅ RESULTADOS:")
            print("- Emails dos usuários foram criptografados com AES-256")
            if total_financial_encrypted > 0:
                print("- Dados financeiros (extratos, cartões e economias) criptografados")
            print("- Dados são descriptografados automaticamente durante o uso")
            print("- Logs de auditoria foram gerados para compliance")
        
        return {
            'emails_encrypted': encrypted_count,
            'financial_records_encrypted': total_financial_encrypted,
            'extratos_encrypted': extratos_encrypted,
            'cartoes_encrypted': cartoes_encrypted,
            'economias_encrypted': economias_encrypted
        }
        
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        return {'error': 'import_failed'}
    except Exception as e:
        print(f"❌ Erro durante criptografia: {e}")
        return {'error': str(e)}

def test_encryption_decryption():
    """Testa se a criptografia/descriptografia está funcionando"""
    try:
        from security.crypto.encryption import DataEncryption
        
        print(f"\n🧪 TESTE DE CRIPTOGRAFIA")
        print("=" * 30)
        
        encryption = DataEncryption()
          # Teste básico
        test_data = "test@email.com"
        encrypted = encryption.encrypt_string(test_data)
        decrypted = encryption.decrypt_string(encrypted)
        
        print(f"Dados originais: {test_data}")
        print(f"Dados criptografados: {encrypted[:20]}...")
        print(f"Dados descriptografados: {decrypted}")
        print(f"Teste bem-sucedido: {test_data == decrypted}")
        
        return test_data == decrypted
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

if __name__ == "__main__":
    # Testar criptografia primeiro
    if test_encryption_decryption():
        print(f"\n🚀 Executando migração de criptografia...")
        result = encrypt_sensitive_data()
        
        if 'error' not in result:
            print(f"\n🎉 Migração de criptografia realizada com sucesso!")
            print(f"📊 Resumo: {result}")
        else:
            print(f"\n❌ Migração falhou: {result['error']}")
    else:
        print(f"\n❌ Teste de criptografia falhou - abortando migração")
