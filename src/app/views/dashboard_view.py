"""
Tela principal (dashboard) refatorada
"""
import customtkinter as ctk
from typing import Callable, List, Dict, Any

from .components import (
    ModernButton, ModernLabel, CameraCard, StatusBar,
    show_notification, show_error_dialog
)


class DashboardView(ctk.CTkFrame):
    """Tela principal do sistema"""

    def __init__(self, master,
                 on_camera_click: Callable,
                 on_logout: Callable,
                 on_settings_click: Callable):  # <--- 1. ADICIONE ESTE ARGUMENTO

        super().__init__(master, fg_color="#1C1C1C")

        self.on_camera_click = on_camera_click
        self.on_logout = on_logout
        self.on_settings_click = on_settings_click  # <--- 2. SALVE O CALLBACK
        self.camera_cards: Dict[int, CameraCard] = {}

        self._create_ui()

    def _create_ui(self):
        """Cria interface do usuário"""
        # Barra superior
        self._create_top_bar()

        # Conteúdo principal
        self._create_main_content()

        # Barra de status
        self.status_bar = StatusBar(self)

    def _create_top_bar(self):
        """Cria barra superior"""
        self.top_bar = ctk.CTkFrame(self, fg_color="#4A90A4", height=70)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        # Logo/Título
        self.title_label = ModernLabel(
            self.top_bar,
            text="LAS Cams System",
            style="heading"
        )
        self.title_label.pack(side="left", padx=20, pady=20)

        # Informações do usuário
        self.user_info_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.user_info_frame.pack(side="right", padx=20, pady=15)

        self.user_label = ModernLabel(
            self.user_info_frame,
            text="",
            style="body"
        )
        self.user_label.pack(side="right", padx=(0, 15))

        # --- 3. ADICIONE O BOTÃO DE CONFIGURAÇÕES ---
        self.settings_button = ModernButton(
            self.user_info_frame,
            text="Configurações",
            style="secondary",
            command=self.on_settings_click,  # <-- Chama o callback
            width=140,
            height=35
        )
        self.settings_button.pack(side="right", padx=(0, 10))
        # ---------------------------------------------

        # Botão logout
        self.logout_button = ModernButton(
            self.user_info_frame,
            text="Sair",
            style="danger",
            command=self._handle_logout,
            width=80,
            height=35
        )
        self.logout_button.pack(side="right")

    def _create_main_content(self):
        """Cria conteúdo principal"""
        # Frame principal
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Título da seção
        self.section_title = ModernLabel(
            self.main_frame,
            text="Câmeras Disponíveis",
            style="subtitle"
        )
        self.section_title.pack(pady=(0, 20))

        # Grid de câmeras
        self.cameras_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.cameras_frame.pack(expand=True, fill="both")

        # Configuração do grid
        self.cameras_frame.grid_rowconfigure((0, 1), weight=1)
        self.cameras_frame.grid_columnconfigure((0, 1, 2), weight=1)

    def _handle_logout(self):
        """Processa logout"""
        self.on_logout()

    def update_user_info(self, username: str, role: str = ""):
        """Atualiza informações do usuário"""
        role_text = f" ({role})" if role else ""
        self.user_label.configure(text=f"Bem-vindo, {username}{role_text}")
        self.status_bar.update_user(username)

    def update_cameras(self, cameras: List[Dict[str, Any]]):
        """Atualiza lista de câmeras"""
        # Limpa cards antigos
        for card in self.camera_cards.values():
            card.destroy()
        self.camera_cards.clear()

        # Filtra apenas câmeras habilitadas
        enabled_cameras = [cam for cam in cameras if cam.get('enabled', True)]

        # Cria novos cards
        for i, camera in enumerate(enabled_cameras):
            row = i // 3
            col = i % 3

            card = CameraCard(
                self.cameras_frame,
                camera_id=camera['id'],
                camera_name=camera['name'],
                on_click=self._handle_camera_click
            )

            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.camera_cards[camera['id']] = card

            # Atualiza status (se a detecção está ativa ou não)
            if camera.get('is_active', False):
                card.update_status("Detecção Ativa", "success")
            elif camera.get('status') and camera['status']['is_connected']:
                card.update_status("Conectada", "info")
            else:
                card.update_status("Inativa/Desconectada", "warning")

    def _handle_camera_click(self, camera_id: int):
        """Processa clique em câmera"""
        self.on_camera_click(camera_id)

    def update_camera_status(self, camera_id: int, status: str, status_type: str = "warning"):
        """Atualiza status de uma câmera específica"""
        if camera_id in self.camera_cards:
            self.camera_cards[camera_id].update_status(status, status_type)

    def show_notification(self, message: str, notification_type: str = "info"):
        """Mostra notificação"""
        show_notification(self, message, notification_type)

    def show_error(self, message: str):
        """Mostra erro"""
        show_error_dialog("Erro", message)

    def update_system_status(self, status: str):
        """Atualiza status do sistema"""
        self.status_bar.update_system_status(status)