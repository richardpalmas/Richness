"""
Data Migration Script - Security Update
Migra senhas existentes de SHA-256 para bcrypt e implementa criptografia para dados sensíveis
"""
import sqlite3
import hashlib
from security.auth.authentication import SecureAuthentication
from security.crypto.encryption import DataEncryption
from security.audit.security_logger import get_security_logger
from database import get_connection
from datetime import datetime


class SecurityMigration:
    """Gerenciador de migração de segurança"""
    
    def __init__(self):
        self.auth = SecureAuthentication()
        self.encryption = DataEncryption()
        self.logger = get_security_logger()
        self.migration_log = []
    
    def backup_database(self) -> str:
        """Cria backup do banco antes da migração"""
        import shutil
        from pathlib import Path
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"richness_backup_{timestamp}.db"
        
        try:
            shutil.copy2("richness.db", backup_name)
            self.migration_log.append(f"✅ Backup criado: {backup_name}")
            return backup_name
        except Exception as e:
            self.migration_log.append(f"❌ Erro ao criar backup: {e}")
            raise
    
    def check_migration_needed(self) -> dict:
        """Verifica se a migração é necessária"""
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar se existem senhas SHA-256 (64 caracteres)
        cur.execute("SELECT COUNT(*) as count FROM usuarios WHERE LENGTH(senha) = 64")
        sha256_users = cur.fetchone()['count']
        
        # Verificar se existem emails não criptografados (verificação simples)
        cur.execute("SELECT COUNT(*) as count FROM usuarios WHERE email LIKE '%@%.%' AND LENGTH(email) < 100")
        unencrypted_emails = cur.fetchone()['count']
        
        # Verificar se campos de auditoria existem
        cur.execute("PRAGMA table_info(usuarios)")
        columns = [row['name'] for row in cur.fetchall()]
        
        audit_fields = ['account_locked', 'login_attempts', 'last_login', 'created_at']
        missing_audit_fields = [field for field in audit_fields if field not in columns]
        
        return {
            'sha256_passwords': sha256_users,
            'unencrypted_emails': unencrypted_emails,
            'missing_audit_fields': missing_audit_fields,
            'migration_needed': sha256_users > 0 or unencrypted_emails > 0 or len(missing_audit_fields) > 0
        }
    
    def add_missing_audit_fields(self):
        """Adiciona campos de auditoria que podem estar faltando"""
        conn = get_connection()
        cur = conn.cursor()
        
        try:
            # Verificar e adicionar campos se necessário
            audit_fields = {
                'account_locked': 'INTEGER DEFAULT 0',
                'login_attempts': 'INTEGER DEFAULT 0', 
                'last_login': 'DATETIME',
                'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
            }
            
            cur.execute("PRAGMA table_info(usuarios)")
            existing_columns = [row['name'] for row in cur.fetchall()]
            
            for field, definition in audit_fields.items():
                if field not in existing_columns:
                    cur.execute(f"ALTER TABLE usuarios ADD COLUMN {field} {definition}")
                    self.migration_log.append(f"✅ Campo adicionado: {field}")
            
            conn.commit()
            
        except Exception as e:
            self.migration_log.append(f"❌ Erro ao adicionar campos de auditoria: {e}")
            raise
    
    def migrate_passwords_to_bcrypt(self):
        """Migra senhas SHA-256 para bcrypt"""
        conn = get_connection()
        cur = conn.cursor()
        
        # Buscar usuários com senhas SHA-256 (64 caracteres)
        cur.execute("SELECT id, usuario, senha FROM usuarios WHERE LENGTH(senha) = 64")
        users_to_migrate = cur.fetchall()
        
        migrated_count = 0
        
        for user in users_to_migrate:
            user_id, username, old_hash = user['id'], user['usuario'], user['senha']
            
            try:
                # IMPORTANTE: Esta migração requer que o usuário faça login novamente
                # Não podemos recuperar a senha original do hash SHA-256
                # Então vamos marcar para reset obrigatório
                
                # Criar um hash temporário que força reset de senha
                temp_password = f"TEMP_RESET_{user_id}"
                new_hash = self.auth.hash_password(temp_password)
                
                # Atualizar com nova senha e marcar para reset
                cur.execute("""
                    UPDATE usuarios 
                    SET senha = ?, 
                        account_locked = 1,
                        login_attempts = 0
                    WHERE id = ?
                """, (new_hash, user_id))
                
                migrated_count += 1
                self.migration_log.append(f"✅ Usuário {username}: senha migrada para bcrypt (reset necessário)")
                
                # Log de auditoria
                self.logger.log_system_event(
                    event_type='password_migration',
                    details={'user_id': user_id, 'username': username, 'method': 'sha256_to_bcrypt'},
                    username=username
                )
                
            except Exception as e:
                self.migration_log.append(f"❌ Erro ao migrar usuário {username}: {e}")
        
        conn.commit()
        return migrated_count
    
    def encrypt_sensitive_data(self):
        """Criptografa dados sensíveis existentes"""
        conn = get_connection()
        cur = conn.cursor()
        
        # Buscar emails não criptografados (formato email@domain.com com menos de 100 chars)
        cur.execute("""
            SELECT id, usuario, email 
            FROM usuarios 
            WHERE email LIKE '%@%.%' 
            AND LENGTH(email) < 100
            AND email NOT LIKE '%@email.com'
        """)
        users_to_encrypt = cur.fetchall()
        
        encrypted_count = 0
        
        for user in users_to_encrypt:
            user_id, username, email = user['id'], user['usuario'], user['email']
            
            try:
                # Criptografar email
                encrypted_email = self.encryption.encrypt_data(email)
                
                # Atualizar no banco
                cur.execute("UPDATE usuarios SET email = ? WHERE id = ?", (encrypted_email, user_id))
                
                encrypted_count += 1
                self.migration_log.append(f"✅ Email do usuário {username}: criptografado")
                
                # Log de auditoria
                self.logger.log_system_event(
                    event_type='data_encryption',
                    details={'user_id': user_id, 'username': username, 'field': 'email'},
                    username=username
                )
                
            except Exception as e:
                self.migration_log.append(f"❌ Erro ao criptografar dados do usuário {username}: {e}")
        
        conn.commit()
        return encrypted_count
    
    def run_full_migration(self) -> dict:
        """Executa migração completa de segurança"""
        start_time = datetime.now()
        
        self.migration_log.append(f"🚀 Iniciando migração de segurança - {start_time}")
        
        try:
            # Verificar necessidade
            check_result = self.check_migration_needed()
            if not check_result['migration_needed']:
                self.migration_log.append("✅ Nenhuma migração necessária")
                return {'status': 'success', 'message': 'Nenhuma migração necessária', 'log': self.migration_log}
            
            # Criar backup
            backup_file = self.backup_database()
            
            # Adicionar campos de auditoria
            if check_result['missing_audit_fields']:
                self.add_missing_audit_fields()
            
            # Migrar senhas
            passwords_migrated = 0
            if check_result['sha256_passwords'] > 0:
                passwords_migrated = self.migrate_passwords_to_bcrypt()
            
            # Criptografar dados sensíveis
            data_encrypted = 0
            if check_result['unencrypted_emails'] > 0:
                data_encrypted = self.encrypt_sensitive_data()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Log final
            self.logger.log_system_event(
                event_type='security_migration_completed',
                details={
                    'duration_seconds': duration,
                    'passwords_migrated': passwords_migrated,
                    'emails_encrypted': data_encrypted,
                    'backup_file': backup_file
                }
            )
            
            self.migration_log.append(f"✅ Migração concluída em {duration:.2f}s")
            self.migration_log.append(f"📊 Senhas migradas: {passwords_migrated}")
            self.migration_log.append(f"📊 Emails criptografados: {data_encrypted}")
            
            return {
                'status': 'success',
                'message': 'Migração concluída com sucesso',
                'backup_file': backup_file,
                'passwords_migrated': passwords_migrated,
                'data_encrypted': data_encrypted,
                'log': self.migration_log
            }
            
        except Exception as e:
            self.migration_log.append(f"💥 Erro durante migração: {e}")
            self.logger.log_system_event(
                event_type='security_migration_failed',
                details={'error': str(e)},
                severity='error'
            )
            
            return {
                'status': 'error',
                'message': f'Erro durante migração: {e}',
                'log': self.migration_log
            }
    
    def create_migration_report(self, result: dict):
        """Cria relatório detalhado da migração"""
        report_name = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_name, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO DE MIGRAÇÃO DE SEGURANÇA\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Status: {result['status']}\n")
            f.write(f"Mensagem: {result['message']}\n\n")
            
            if 'backup_file' in result:
                f.write(f"Arquivo de backup: {result['backup_file']}\n")
            if 'passwords_migrated' in result:
                f.write(f"Senhas migradas: {result['passwords_migrated']}\n")
            if 'data_encrypted' in result:
                f.write(f"Dados criptografados: {result['data_encrypted']}\n")
            
            f.write("\nLOG DETALHADO:\n")
            f.write("-" * 30 + "\n")
            for log_entry in result['log']:
                f.write(f"{log_entry}\n")
        
        return report_name


def run_migration():
    """Função principal para executar migração"""
    print("🔐 MIGRAÇÃO DE SEGURANÇA - RICHNESS")
    print("=" * 50)
    
    migration = SecurityMigration()
    
    # Verificar necessidade
    check = migration.check_migration_needed()
    print(f"📊 Senhas SHA-256 encontradas: {check['sha256_passwords']}")
    print(f"📊 Emails não criptografados: {check['unencrypted_emails']}")
    print(f"📊 Campos de auditoria faltando: {len(check['missing_audit_fields'])}")
    
    if not check['migration_needed']:
        print("✅ Sistema já está atualizado!")
        return
    
    # Confirmar migração
    confirm = input("\n⚠️  ATENÇÃO: Esta migração irá:\n"
                   "- Converter senhas SHA-256 para bcrypt (usuários precisarão redefinir senhas)\n"
                   "- Criptografar emails existentes\n"
                   "- Criar backup automático\n"
                   "\nDeseja continuar? (sim/não): ")
    
    if confirm.lower() not in ['sim', 's', 'yes', 'y']:
        print("❌ Migração cancelada pelo usuário")
        return
    
    # Executar migração
    print("\n🚀 Iniciando migração...")
    result = migration.run_full_migration()
    
    # Mostrar resultado
    print(f"\n{'✅' if result['status'] == 'success' else '❌'} {result['message']}")
    
    # Criar relatório
    report_file = migration.create_migration_report(result)
    print(f"📄 Relatório salvo em: {report_file}")
    
    if result['status'] == 'success' and result.get('passwords_migrated', 0) > 0:
        print("\n⚠️  IMPORTANTE:")
        print("- Usuários com senhas migradas precisarão redefinir suas senhas")
        print("- Suas contas estão temporariamente bloqueadas")
        print("- Use a função de reset de senha ou desbloqueie manualmente")


if __name__ == "__main__":
    run_migration()
