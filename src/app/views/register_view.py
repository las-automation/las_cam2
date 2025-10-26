"""
Tela de registro refatorada
"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Callable

from .components import ModernButton, ModernEntry, ModernLabel, show_error_dialog


class RegisterView(ctk.CTkFrame):
    """Tela de registro moderna"""

    def __init__(self, master, on_register: Callable, on_back: Callable):
        super().__init__(master, fg_color="#1C1C1C")

        self.on_register = on_register
        self.on_back = on_back

        self._create_ui()

    def _create_ui(self):
        """Cria interface do usuário"""
        # Frame central
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Título
        self.title_label = ModernLabel(
            self.center_frame,
            text="Criar Nova Conta",
            style="title"
        )
        self.title_label.pack(pady=(0, 10))

        self.subtitle_label = ModernLabel(
            self.center_frame,
            text="Preencha os dados abaixo para criar sua conta",
            style="caption"
        )
        self.subtitle_label.pack(pady=(0, 40))

        # Formulário de registro
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
        self.password_entry.pack(pady=(0, 10), padx=30)

        self.confirm_password_entry = ModernEntry(
            self.form_frame,
            placeholder_text="Confirmar senha",
            show="*",
            width=350
        )
        self.confirm_password_entry.pack(pady=(0, 20), padx=30)

        # Botões
        self.register_button = ModernButton(
            self.form_frame,
            text="Criar Conta",
            style="success",
            command=self._handle_register,
            width=350
        )
        self.register_button.pack(pady=(0, 15), padx=30)

        self.back_button = ModernButton(
            self.form_frame,
            text="Voltar ao Login",
            style="outline",
            command=self._handle_back,
            width=350
        )
        self.back_button.pack(pady=(0, 20), padx=30)

        # Bind Enter key
        self.confirm_password_entry.bind("<Return>", lambda e: self._handle_register())
        self.password_entry.bind("<Return>", lambda e: self._handle_register())
        self.username_entry.bind("<Return>", lambda e: self._handle_register())

    def _handle_register(self):
        """Processa tentativa de registro"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        # Validações
        if not username or not password or not confirm_password:
            show_error_dialog("Erro", "Por favor, preencha todos os campos.")
            return

        if len(username) < 3:
            show_error_dialog("Erro", "Nome de usuário deve ter pelo menos 3 caracteres.")
            return

        if len(password) < 6:
            show_error_dialog("Erro", "Senha deve ter pelo menos 6 caracteres.")
            return

        if password != confirm_password:
            show_error_dialog("Erro", "As senhas não coincidem.")
            return

        self.on_register(username, password)

    def _handle_back(self):
        """Volta para tela de login"""
        self.on_back()

    def clear_fields(self):
        """Limpa campos do formulário"""
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.confirm_password_entry.delete(0, "end")

    def focus_username(self):
        """Foca no campo de usuário"""
        self.username_entry.focus()

        # --- INÍCIO DAS ADIÇÕES ---
    def show_error(self, message: str):
        """Exibe uma mensagem de erro (chamado pelo ScreenManager)"""
        # Reutiliza a função de diálogo que você já tem
        show_error_dialog("Erro de Registro", message)

    def show_notification(self, message: str, type: str = "info"):
        """Exibe uma notificação (chamado pelo ScreenManager)"""
        # Você pode melhorar isso depois (ex: usar um label),
        # mas por enquanto, um messagebox serve.
        if type == "success":
            messagebox.showinfo("Sucesso", message)
        else:
            messagebox.showinfo("Informação", message)
            # --- FIM DAS ADIÇÕES ---
