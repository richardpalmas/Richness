"""
Fallback encryption system for environments with cryptography issues
Uses hashlib-based encryption as temporary fallback
"""
import hashlib
import secrets
import base64
import json
from typing import Any, Dict, Optional


class DataEncryption:
    """
    Sistema de criptografia fallback usando hashlib
    Para ambientes com problemas na biblioteca cryptography
    """
    
    def __init__(self, key: Optional[str] = None):
        """Inicializa com chave de criptografia"""
        self.key = key or self._generate_key()
    
    def _generate_key(self) -> str:
        """Gera chave segura"""
        return secrets.token_hex(32)
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Deriva chave usando PBKDF2 simples com hashlib"""
        key = password.encode()
        for _ in range(100000):  # 100,000 iterações
            key = hashlib.sha256(key + salt).digest()
        return key
    
    def encrypt_data(self, data: str, context: str = "general") -> str:
        """
        Criptografa dados usando XOR com chave derivada
        Nota: Esta é uma implementação fallback simples
        """
        try:
            if not data:
                return ""
            
            # Gerar salt único
            salt = secrets.token_bytes(16)
            
            # Derivar chave
            derived_key = self._derive_key(self.key, salt)
            
            # Converter dados para bytes
            data_bytes = data.encode('utf-8')
            
            # Criptografia XOR simples (fallback)
            encrypted_bytes = bytearray()
            for i, byte in enumerate(data_bytes):
                key_byte = derived_key[i % len(derived_key)]
                encrypted_bytes.append(byte ^ key_byte)
            
            # Combinar salt + dados criptografados
            result = salt + bytes(encrypted_bytes)
            
            # Codificar em base64
            return base64.b64encode(result).decode('utf-8')
            
        except Exception as e:
            print(f"Encryption error: {e}")
            return data  # Fallback: retornar dados originais
    
    def decrypt_data(self, encrypted_data: str, context: str = "general") -> str:
        """
        Descriptografa dados
        """
        try:
            if not encrypted_data:
                return ""
            
            # Decodificar base64
            try:
                combined_data = base64.b64decode(encrypted_data.encode('utf-8'))
            except:
                # Se falhar, assumir que dados não estão criptografados
                return encrypted_data
            
            # Separar salt dos dados
            if len(combined_data) < 16:
                return encrypted_data  # Dados muito pequenos, não criptografados
                
            salt = combined_data[:16]
            encrypted_bytes = combined_data[16:]
            
            # Derivar chave
            derived_key = self._derive_key(self.key, salt)
            
            # Descriptografar usando XOR
            decrypted_bytes = bytearray()
            for i, byte in enumerate(encrypted_bytes):
                key_byte = derived_key[i % len(derived_key)]
                decrypted_bytes.append(byte ^ key_byte)
            
            return bytes(decrypted_bytes).decode('utf-8')
            
        except Exception as e:
            print(f"Decryption error: {e}")
            return encrypted_data  # Fallback: retornar dados originais
    
    def encrypt_dict(self, data_dict: Dict[str, Any], fields_to_encrypt: Optional[list] = None) -> Dict[str, Any]:
        """
        Criptografa campos específicos de um dicionário
        """
        if not data_dict or not fields_to_encrypt:
            return data_dict
        
        encrypted_dict = data_dict.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_dict and encrypted_dict[field]:
                encrypted_dict[field] = self.encrypt_data(str(encrypted_dict[field]))
        
        return encrypted_dict
    
    def decrypt_dict(self, encrypted_dict: Dict[str, Any], fields_to_decrypt: Optional[list] = None) -> Dict[str, Any]:
        """
        Descriptografa campos específicos de um dicionário
        """
        if not encrypted_dict or not fields_to_decrypt:
            return encrypted_dict
        
        decrypted_dict = encrypted_dict.copy()
        
        for field in fields_to_decrypt:
            if field in decrypted_dict and decrypted_dict[field]:
                decrypted_dict[field] = self.decrypt_data(str(decrypted_dict[field]))
        
        return decrypted_dict
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Gera token seguro"""
        return secrets.token_urlsafe(length)
    
    def hash_data(self, data: str, salt: Optional[str] = None) -> str:
        """Gera hash seguro dos dados"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        combined = data + salt
        hashed = hashlib.sha256(combined.encode()).hexdigest()
        return f"{salt}${hashed}"
    
    def verify_hash(self, data: str, hashed_data: str) -> bool:
        """Verifica hash dos dados"""
        try:
            if '$' not in hashed_data:
                return False
            
            salt, original_hash = hashed_data.split('$', 1)
            new_hash = self.hash_data(data, salt)
            
            return secrets.compare_digest(hashed_data, new_hash)
        except:
            return False


# Instância global para reutilização
_encryption_instance = None

def get_encryption_manager() -> DataEncryption:
    """Retorna instância do gerenciador de criptografia"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = DataEncryption()
    return _encryption_instance
