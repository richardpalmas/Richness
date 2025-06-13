"""
Utilitários para descriptografia transparente de dados financeiros
"""
import functools
from typing import Optional, Dict, List, Any, Union

def decrypt_financial_data(func):
    """
    Decorator para descriptografar automaticamente dados financeiros
    
    Uso:
        @decrypt_financial_data
        def get_extratos(usuario_id):
            # função original
            
    Funciona tanto para listas de dicionários quanto para dicionários únicos
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from security.crypto.encryption import DataEncryption
        
        # Executar função original
        result = func(*args, **kwargs)
        
        if not result:
            return result
            
        # Inicializar criptografia
        encryption = DataEncryption()
        
        # Determinar se o resultado é uma lista ou um único item
        if isinstance(result, list):
            # Lista de itens
            for item in result:
                decrypt_item(item, encryption)
        else:
            # Item único
            decrypt_item(result, encryption)
            
        return result
    
    return wrapper

def decrypt_item(item: Dict[str, Any], encryption) -> None:
    """Descriptografa todos os campos marcados com 'encrypted:' em um item"""
    fields_to_decrypt = ['descricao', 'cartao_nome', 'email']
    
    for field in fields_to_decrypt:
        if field in item and item[field] and isinstance(item[field], str):
            if item[field].startswith('encrypted:'):
                try:
                    # Remover prefixo e descriptografar
                    encrypted_data = item[field].replace('encrypted:', '')
                    item[field] = encryption.decrypt_string(encrypted_data)
                except Exception as e:
                    # Manter valor original em caso de erro
                    pass

def safe_decrypt(value: Optional[str]) -> Optional[str]:
    """
    Função auxiliar para descriptografar um único valor
    
    Uso:
        email = safe_decrypt(usuario['email'])
    """
    if not value or not isinstance(value, str) or not value.startswith('encrypted:'):
        return value
        
    try:
        from security.crypto.encryption import DataEncryption
        encryption = DataEncryption()
        
        encrypted_data = value.replace('encrypted:', '')
        return encryption.decrypt_string(encrypted_data)
    except Exception as e:
        return value
