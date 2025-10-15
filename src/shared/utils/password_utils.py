# src/shared/utils/password_utils.py
"""
Utilities para hash de senhas com fallback robusto.
Contorna problemas de incompatibilidade entre passlib e bcrypt.
"""
import bcrypt
from typing import Union


class PasswordHasher:
    """Gerenciador de hash de senhas com fallback robusto."""
    
    def __init__(self, rounds: int = 12):
        self.rounds = rounds
    
    def hash_password(self, password: str) -> str:
        """
        Gera hash da senha usando bcrypt diretamente.
        
        Args:
            password: Senha em texto plano
            
        Returns:
            Hash da senha como string
        """
        # Garantir que a senha seja bytes
        if isinstance(password, str):
            password_bytes = password.encode('utf-8')
        else:
            password_bytes = password
            
        # Truncar senha se necessário (bcrypt tem limite de 72 bytes)
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
            
        # Gerar salt e hash
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        # Retornar como string
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verifica se a senha corresponde ao hash.
        
        Args:
            password: Senha em texto plano
            hashed_password: Hash da senha armazenado
            
        Returns:
            True se a senha estiver correta, False caso contrário
        """
        try:
            # Garantir que inputs sejam bytes
            if isinstance(password, str):
                password_bytes = password.encode('utf-8')
            else:
                password_bytes = password
                
            if isinstance(hashed_password, str):
                hashed_bytes = hashed_password.encode('utf-8')
            else:
                hashed_bytes = hashed_password
                
            # Truncar senha se necessário
            if len(password_bytes) > 72:
                password_bytes = password_bytes[:72]
                
            # Verificar hash
            return bcrypt.checkpw(password_bytes, hashed_bytes)
            
        except Exception:
            return False


# Instância global
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Função de conveniência para hash de senha."""
    return password_hasher.hash_password(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Função de conveniência para verificação de senha."""
    return password_hasher.verify_password(password, hashed_password)