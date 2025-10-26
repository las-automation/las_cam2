"""
Serviços de autenticação e gerenciamento de usuários
"""
import hashlib
import os
import json
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

from ..models.entities import User, UserRole
from ..utils.logger import log_user_action, log_error, log_system_event


class AuthService:
    """Serviço de autenticação"""
    
    def __init__(self, users_file: str = "usuarios.json"):
        self.users_file = Path(users_file)
        self._users: Dict[str, User] = {}
        self._load_users()
    
    def _load_users(self) -> None:
        """Carrega usuários do arquivo"""
        if not self.users_file.exists():
            self._create_default_admin()
            return
        
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for username, user_data in data.items():
                self._users[username] = User.from_dict(user_data)
                
        except Exception as e:
            log_error("AuthService", e, f"Erro ao carregar usuários de {self.users_file}")
            self._create_default_admin()
    
    def _create_default_admin(self) -> None:
        """Cria usuário administrador padrão"""
        admin_password = self._hash_password("admin123")
        admin_user = User(
            username="admin",
            password_hash=admin_password,
            role=UserRole.ADMIN
        )
        self._users["admin"] = admin_user
        self._save_users()
        log_system_event("Criado usuário administrador padrão")
    
    def _hash_password(self, password: str) -> str:
        """Gera hash da senha usando PBKDF2"""
        salt = os.urandom(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt.hex() + ':' + password_hash.hex()
    
    def _verify_password(self, stored_hash: str, password: str) -> bool:
        """Verifica senha contra hash armazenado"""
        try:
            salt_hex, hash_hex = stored_hash.split(':', 1)
            salt = bytes.fromhex(salt_hex)
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return password_hash == bytes.fromhex(hash_hex)
        except Exception:
            return False
    
    def _save_users(self) -> bool:
        """Salva usuários no arquivo"""
        try:
            temp_file = self.users_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {username: user.to_dict() for username, user in self._users.items()},
                    f, indent=4, ensure_ascii=False
                )
                f.flush()
                os.fsync(f.fileno())
            
            temp_file.replace(self.users_file)
            return True
            
        except Exception as e:
            log_error("AuthService", e, f"Erro ao salvar usuários em {self.users_file}")
            return False
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Autentica usuário"""
        user = self._users.get(username)
        if not user or not user.is_active:
            log_user_action(username, "LOGIN_FAILED", "Usuário não encontrado ou inativo")
            return None
        
        if not self._verify_password(user.password_hash, password):
            log_user_action(username, "LOGIN_FAILED", "Senha incorreta")
            return None
        
        # Atualiza último login
        user.last_login = datetime.now()
        self._save_users()
        
        log_user_action(username, "LOGIN_SUCCESS")
        return user
    
    def register_user(self, username: str, password: str, role: UserRole = UserRole.VIEWER) -> bool:
        """Registra novo usuário"""
        if username in self._users:
            return False
        
        password_hash = self._hash_password(password)
        user = User(
            username=username,
            password_hash=password_hash,
            role=role
        )
        
        self._users[username] = user
        
        if self._save_users():
            log_user_action(username, "USER_REGISTERED", f"Role: {role.value}")
            return True
        
        return False
    
    def get_user(self, username: str) -> Optional[User]:
        """Retorna usuário por nome"""
        return self._users.get(username)
    
    def get_all_users(self) -> List[User]:
        """Retorna todos os usuários"""
        return list(self._users.values())
    
    def update_user_role(self, username: str, new_role: UserRole) -> bool:
        """Atualiza papel do usuário"""
        user = self._users.get(username)
        if not user:
            return False
        
        old_role = user.role
        user.role = new_role
        
        if self._save_users():
            log_user_action(username, "ROLE_UPDATED", f"{old_role.value} -> {new_role.value}")
            return True
        
        return False
    
    def deactivate_user(self, username: str) -> bool:
        """Desativa usuário"""
        user = self._users.get(username)
        if not user:
            return False
        
        user.is_active = False
        
        if self._save_users():
            log_user_action(username, "USER_DEACTIVATED")
            return True
        
        return False
    
    def activate_user(self, username: str) -> bool:
        """Ativa usuário"""
        user = self._users.get(username)
        if not user:
            return False
        
        user.is_active = True
        
        if self._save_users():
            log_user_action(username, "USER_ACTIVATED")
            return True
        
        return False
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Altera senha do usuário"""
        user = self._users.get(username)
        if not user:
            return False
        
        if not self._verify_password(user.password_hash, old_password):
            return False
        
        user.password_hash = self._hash_password(new_password)
        
        if self._save_users():
            log_user_action(username, "PASSWORD_CHANGED")
            return True
        
        return False
