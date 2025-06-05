"""
Sistema de criptografia para proteção de dados sensíveis
Implementa AES-256 para dados bancários e informações pessoais
"""
import base64
import os
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Union
import json
from pathlib import Path

from security.audit.security_logger import get_security_logger


class DataEncryption:
    """Sistema de criptografia AES-256 para dados sensíveis"""
    
    def __init__(self):
        self.logger = get_security_logger()
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """Obtém ou cria chave mestra de criptografia"""
        key_file = Path('.encryption_key')
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                self.logger.log_system_error(
                    error_type='key_loading_error',
                    error_message=str(e)
                )
        
        # Gerar nova chave mestra
        master_key = Fernet.generate_key()
        
        try:
            with open(key_file, 'wb') as f:
                f.write(master_key)
            # Tornar arquivo legível apenas pelo proprietário
            os.chmod(key_file, 0o600)
        except Exception as e:
            self.logger.log_system_error(
                error_type='key_storage_error',
                error_message=str(e)
            )
        
        return master_key
    
    def encrypt_string(self, plaintext: str) -> str:
        """
        Criptografa string usando AES-256
        Retorna: string criptografada em base64
        """
        try:
            if not isinstance(plaintext, str):
                raise ValueError("Input deve ser string")
            
            if not plaintext:
                return ""
            
            # Converter para bytes
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Criptografar
            encrypted_bytes = self.fernet.encrypt(plaintext_bytes)
            
            # Converter para base64 para armazenamento
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            return encrypted_b64
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='encryption_error',
                error_message=str(e)
            )
            raise
    
    def decrypt_string(self, encrypted_data: str) -> str:
        """
        Descriptografa string
        Retorna: string original
        """
        try:
            if not isinstance(encrypted_data, str):
                raise ValueError("Input deve ser string")
            
            if not encrypted_data:
                return ""
            
            # Converter de base64 para bytes
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Descriptografar
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            
            # Converter para string
            plaintext = decrypted_bytes.decode('utf-8')
            
            return plaintext
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='decryption_error',
                error_message=str(e)
            )
            raise
    
    def encrypt_financial_data(self, data: dict) -> str:
        """
        Criptografa dados financeiros sensíveis
        Retorna: JSON criptografado
        """
        try:
            # Serializar para JSON
            json_data = json.dumps(data, ensure_ascii=False)
            
            # Criptografar
            encrypted_json = self.encrypt_string(json_data)
            
            return encrypted_json
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='financial_data_encryption_error',
                error_message=str(e)
            )
            raise
    
    def decrypt_financial_data(self, encrypted_data: str) -> dict:
        """
        Descriptografa dados financeiros
        Retorna: dict com dados originais
        """
        try:
            # Descriptografar
            json_data = self.decrypt_string(encrypted_data)
            
            # Deserializar JSON
            data = json.loads(json_data)
            
            return data
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='financial_data_decryption_error',
                error_message=str(e)
            )
            raise
    
    def encrypt_pii_data(self, data: dict) -> dict:
        """
        Criptografa dados pessoais identificáveis (PII)
        Retorna: dict com campos sensíveis criptografados
        """
        try:
            sensitive_fields = {
                'cpf', 'rg', 'email', 'telefone', 'endereco',
                'conta_numero', 'agencia', 'banco_codigo'
            }
            
            encrypted_data = data.copy()
            
            for field, value in data.items():
                if field.lower() in sensitive_fields and value:
                    encrypted_data[field] = self.encrypt_string(str(value))
            
            return encrypted_data
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='pii_encryption_error',
                error_message=str(e)
            )
            raise
    
    def decrypt_pii_data(self, encrypted_data: dict, fields_to_decrypt: list = None) -> dict:
        """
        Descriptografa dados PII específicos
        Retorna: dict com campos descriptografados
        """
        try:
            if fields_to_decrypt is None:
                sensitive_fields = {
                    'cpf', 'rg', 'email', 'telefone', 'endereco',
                    'conta_numero', 'agencia', 'banco_codigo'
                }
            else:
                sensitive_fields = set(fields_to_decrypt)
            
            decrypted_data = encrypted_data.copy()
            
            for field, value in encrypted_data.items():
                if field.lower() in sensitive_fields and value:
                    try:
                        decrypted_data[field] = self.decrypt_string(str(value))
                    except Exception:
                        # Se não conseguir descriptografar, mantém valor original
                        # (pode ser dado não criptografado de versão anterior)
                        decrypted_data[field] = value
            
            return decrypted_data
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='pii_decryption_error',
                error_message=str(e)
            )
            raise


class HashingUtility:
    """Utilitários para hashing de dados não-reversível"""
    
    @staticmethod
    def hash_data(data: str, salt: str = None) -> str:
        """
        Gera hash SHA-256 dos dados com salt
        Usado para dados que não precisam ser descriptografados
        """
        try:
            if salt is None:
                salt = secrets.token_hex(16)
            
            # Combinar dados com salt
            data_with_salt = f"{data}{salt}"
            
            # Gerar hash SHA-256
            hash_obj = hashes.Hash(hashes.SHA256())
            hash_obj.update(data_with_salt.encode('utf-8'))
            hash_bytes = hash_obj.finalize()
            
            # Converter para hex
            hash_hex = hash_bytes.hex()
            
            # Retornar hash com salt para verificação futura
            return f"{salt}:{hash_hex}"
            
        except Exception as e:
            logger = get_security_logger()
            logger.log_system_error(
                error_type='hashing_error',
                error_message=str(e)
            )
            raise
    
    @staticmethod
    def verify_hash(data: str, stored_hash: str) -> bool:
        """Verifica se dados correspondem ao hash armazenado"""
        try:
            if ':' not in stored_hash:
                return False
            
            salt, expected_hash = stored_hash.split(':', 1)
            
            # Regenerar hash com mesmo salt
            data_with_salt = f"{data}{salt}"
            hash_obj = hashes.Hash(hashes.SHA256())
            hash_obj.update(data_with_salt.encode('utf-8'))
            computed_hash = hash_obj.finalize().hex()
            
            # Comparação constant-time
            return secrets.compare_digest(computed_hash, expected_hash)
            
        except Exception:
            return False


class SecureKeyManager:
    """Gerenciador de chaves específicas para diferentes tipos de dados"""
    
    def __init__(self):
        self.logger = get_security_logger()
        self.keys_dir = Path('.keys')
        self.keys_dir.mkdir(exist_ok=True, mode=0o700)
    
    def get_user_key(self, user_id: str) -> bytes:
        """Obtém chave específica do usuário"""
        key_file = self.keys_dir / f"user_{user_id}.key"
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception:
                pass
        
        # Gerar nova chave para o usuário
        user_key = Fernet.generate_key()
        
        try:
            with open(key_file, 'wb') as f:
                f.write(user_key)
            os.chmod(key_file, 0o600)
        except Exception as e:
            self.logger.log_system_error(
                error_type='user_key_creation_error',
                error_message=str(e)
            )
        
        return user_key
    
    def rotate_user_key(self, user_id: str) -> bytes:
        """Rotaciona chave do usuário (para casos de comprometimento)"""
        try:
            # Gerar nova chave
            new_key = Fernet.generate_key()
            
            # Salvar nova chave
            key_file = self.keys_dir / f"user_{user_id}.key"
            with open(key_file, 'wb') as f:
                f.write(new_key)
            
            self.logger.log_configuration_change(
                username=f"user_{user_id}",
                setting="encryption_key",
                old_value="[REDACTED]",
                new_value="[ROTATED]"
            )
            
            return new_key
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='key_rotation_error',
                error_message=str(e)
            )
            raise


# Singleton para uso global
_encryption_instance = None
_key_manager_instance = None

def get_encryption_manager() -> DataEncryption:
    """Retorna instância singleton do encryption manager"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = DataEncryption()
    return _encryption_instance

def get_key_manager() -> SecureKeyManager:
    """Retorna instância singleton do key manager"""
    global _key_manager_instance
    if _key_manager_instance is None:
        _key_manager_instance = SecureKeyManager()
    return _key_manager_instance
