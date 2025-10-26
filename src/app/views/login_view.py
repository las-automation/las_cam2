"""
Tela de login refatorada
"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Callable

from .components import ModernButton, ModernEntry, ModernLabel, show_error_dialog


class LoginView(ctk.CTkFrame):
    """Tela de login moderna"""
    
    def __init__(self, master, on_login: Callable, on_register: Callable):
        super().__init__(master, fg_color="#1C1C1C")
        
        self.on_login = on_login
        self.on_register = on_register
        
        self._create_ui()
    
    def _create_ui(self):
        """Cria interface do usuário"""
        # Frame central
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Logo/Título
        self.title_label = ModernLabel(
            self.center_frame, 
            text="LAS Cams System", 
            style="title"
        )
        self.title_label.pack(pady=(0, 10))
        
        self.subtitle_label = ModernLabel(
            self.center_frame,
            text="Sistema de Monitoramento Inteligente",
            style="caption"
        )
        self.subtitle_label.pack(pady=(0, 40))
        
        # Formulário de login
        self.form_frame = ctk.CTkFrame(
            self.center_frame, 
            fg_color="#2B2B2B", 
            corner_radius=15
        )
        self.form_frame.pack(pady=20, padx=20, fill="x")
        
        # Campos de entrada
        self.username_entry = ModernEntry(
            self.form_frame,
            placeholder_text="Nome de usuário",
            width=350
        )
        self.username_entry.pack(pady=20, padx=30)
        
        self.password_entry = ModernEntry(
            self.form_frame,
            placeholder_text="Senha",
            show="*",
            width=350
        )
        self.password_entry.pack(pady=(0, 20), padx=30)
        
        # Botões
        self.login_button = ModernButton(
            self.form_frame,
            text="Entrar",
            style="primary",
            command=self._handle_login,
            width=350
        )
        self.login_button.pack(pady=(0, 15), padx=30)
        
        self.register_button = ModernButton(
            self.form_frame,
            text="Criar Conta",
            style="outline",
            command=self._handle_register,
            width=350
        )
        self.register_button.pack(pady=(0, 20), padx=30)
        
        # Bind Enter key
        self.password_entry.bind("<Return>", lambda e: self._handle_login())
        self.username_entry.bind("<Return>", lambda e: self._handle_login())
    
    def _handle_login(self):
        """Processa tentativa de login"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            show_error_dialog("Erro", "Por favor, preencha todos os campos.")
            return
        
        self.on_login(username, password)
    
    def _handle_register(self):
        """Navega para tela de registro"""
        self.on_register()
    
    def clear_fields(self):
        """Limpa campos do formulário"""
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
    
    def focus_username(self):
        """Foca no campo de usuário"""
        self.username_entry.focus()

    def show_error(self, message: str):
        """Exibe uma mensagem de erro (chamado pelo ScreenManager)"""
        show_error_dialog("Erro de Login", message)
