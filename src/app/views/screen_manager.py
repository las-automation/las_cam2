"""
Gerenciador de telas da aplicação
"""

import customtkinter as ctk
import tkinter  # Importa a biblioteca base do tkinter para o TclError
from typing import Optional, Dict, Any

from .login_view import LoginView
from .register_view import RegisterView
from .dashboard_view import DashboardView
from .camera_view import CameraView
from .settings_view import SettingsView
from ..controllers.app_controller import AppController
# --- ADICIONADO: Importa CargoType e User ---
from ..models.entities import CargoType, User
# --- FIM ADIÇÃO ---
from .components import show_error_dialog


class ScreenManager:
    """Gerenciador de telas da aplicação"""

    def __init__(self, root: ctk.CTk, controller: AppController):
        self.root = root
        self.controller = controller
        self.current_view: Optional[ctk.CTkFrame] = None
        # Mapeia camera_id para a instância da janela CameraView
        self.camera_windows: Dict[int, CameraView] = {}

        # Configura callbacks do controller
        self._setup_controller_callbacks()

        # Cria telas
        self._create_views()

        # Inicia com tela de login
        self.show_login()

    def _setup_controller_callbacks(self):
        """Configura callbacks do controller"""
        callbacks = {
            "login_success": self._on_login_success,
            "login_failed": self._on_login_failed,
            "register_success": self._on_register_success,
            "self_register_success": self._on_self_register_success,
            "register_failed": self._on_register_failed,
            "logout_success": self._on_logout_success,
            "detection_starting": self._on_detection_starting,
            "detection_started": self._on_detection_started,
            "detection_stopped": self._on_detection_stopped,
            "detection_failed": self._on_detection_failed,
            "detection_update": self._on_detection_update,
            "count_reset": self._on_count_reset,
            "report_generated": self._on_report_generated,
            "report_failed": self._on_report_failed,
            "config_updated": self._on_config_updated,
            "camera_added": self._on_camera_added,
            "camera_removed": self._on_camera_removed,
            "error": self._on_error,
            # Callbacks específicos da API (opcional, mas bom para feedback)
            "api_report_sent": self._on_api_report_sent,
            "api_report_failed": self._on_api_report_failed,
        }
        for event, callback in callbacks.items():
            self.controller.set_ui_callback(event, callback)

    def _create_views(self):
        """Cria todas as telas"""
        self.login_view = LoginView(
            self.root,
            on_login=self._handle_login,
            on_register=self.show_register
        )
        self.register_view = RegisterView(
            self.root,
            on_register=self._handle_register,
            on_back=self.show_login
        )
        self.dashboard_view = DashboardView(
            self.root,
            on_camera_click=self._handle_camera_click,
            on_logout=self._handle_logout,
            on_settings_click=self.show_settings
        )
        self.settings_view = SettingsView(
            self.root,
            controller=self.controller,
            on_back=self.show_dashboard
        )

    def _switch_view(self, new_view: ctk.CTkFrame):
        """Alterna para nova tela"""
        if self.current_view:
            self.current_view.pack_forget()
        self.current_view = new_view
        self.current_view.pack(expand=True, fill="both")

    def show_login(self):
        """Mostra tela de login"""
        self._switch_view(self.login_view)
        if hasattr(self.login_view, 'focus_username'):
            self.login_view.focus_username()

    def show_register(self):
        """Mosta tela de registro"""
        self._switch_view(self.register_view)
        if hasattr(self.register_view, 'focus_username'):
            self.register_view.focus_username()

    def show_dashboard(self):
        """Mostra tela principal (Dashboard)"""
        self._switch_view(self.dashboard_view)
        user = self.controller.get_current_user()
        if user and hasattr(self.dashboard_view, 'update_user_info'):
            role = user.role.value if hasattr(user.role, 'value') else str(user.role)
            self.dashboard_view.update_user_info(user.username, role)
        if hasattr(self.dashboard_view, 'update_cameras'):
            cameras = self.controller.get_cameras()
            self.dashboard_view.update_cameras(cameras)

    def show_settings(self):
        """Mostra tela de configurações"""
        if hasattr(self.settings_view, 'load_settings_to_ui'):
            self.settings_view.load_settings_to_ui()
        self._switch_view(self.settings_view)

    def show_camera_window(self, camera_id: int):
        """Mostra (ou traz para frente) a janela de uma câmera específica."""
        if camera_id in self.camera_windows:
            try:
                window = self.camera_windows[camera_id]
                window.state('normal');
                window.lift();
                window.focus_force()
                print(f"[ScreenManager] Janela da Câmera {camera_id} trazida para frente.")
                return
            except (tkinter.TclError, AttributeError):
                print(f"[ScreenManager] Removendo referência inválida da Câmera {camera_id}.")
                del self.camera_windows[camera_id]

        cameras = self.controller.get_cameras()
        camera_config_dict = next((c for c in cameras if c.get('id') == camera_id), None)

        if not camera_config_dict:
            if hasattr(self.dashboard_view, 'show_error'):
                self.dashboard_view.show_error(f"Configuração da Câmera {camera_id} não encontrada.")
            else:
                show_error_dialog("Erro", f"Configuração da Câmera {camera_id} não encontrada.")
            return

        if not camera_config_dict.get('enabled', True):
            if hasattr(self.dashboard_view, 'show_notification'):
                self.dashboard_view.show_notification(f"Câmera {camera_id} está desabilitada.", "warning")
            return

        try:
            print(f"[ScreenManager] Criando nova janela para Câmera {camera_id}...")
            # --- MODIFICADO: Passa on_finalize_session ---
            camera_window = CameraView(
                master=self.root,
                camera_id=camera_id,
                camera_name=camera_config_dict.get('name', f'Câmera {camera_id}'),
                on_start_detection=self._handle_start_detection,
                on_stop_detection=self._handle_stop_detection,
                on_finalize_session=self._handle_finalize_session  # Substitui on_generate_report
            )
            # --- FIM MODIFICAÇÃO ---
            self.camera_windows[camera_id] = camera_window
            camera_window.protocol("WM_DELETE_WINDOW", lambda cid=camera_id: self._on_camera_window_close(cid))
            print(f"[ScreenManager] Janela da Câmera {camera_id} criada.")
        except Exception as e:
            error_msg = f"Erro ao criar janela para Câmera {camera_id}: {e}"
            print(f"[ScreenManager] {error_msg}")
            show_error_dialog("Erro Crítico", error_msg)

    def _on_camera_window_close(self, camera_id: int):
        """Callback chamado quando a janela da câmera é fechada (pelo 'X' ou pelo botão 'Fechar' que chama destroy)."""
        print(f"[ScreenManager] Tentativa de fechar janela da Câmera {camera_id}.")
        window = self.camera_windows.get(camera_id)

        if window is None:
            print(f"[ScreenManager] Janela da Câmera {camera_id} já não existe.")
            # Garante que a referência seja removida se ainda existir por algum motivo
            if camera_id in self.camera_windows:
                del self.camera_windows[camera_id]
            return

        # A CameraView._on_closing_attempt() já impede o destroy() se a detecção estiver ativa.
        # Se chegamos aqui, ou a detecção está inativa, ou algo forçou o destroy.
        # Em qualquer caso, garantimos a parada e a limpeza.
        try:
            print(f"[ScreenManager] Garantindo parada da detecção para Câmera {camera_id} antes de fechar.")
            # Chama o stop do controller (que agora NÃO gera relatório)
            self.controller.stop_camera_detection(camera_id)

            # Destrói o widget se ele ainda existir
            if window.winfo_exists():
                print(f"[ScreenManager] Destruindo widget da Câmera {camera_id}.")
                window.destroy()
        except Exception as e:
            print(f"[ScreenManager] Erro durante o fechamento da Câmera {camera_id}: {e}")
        finally:
            # Remove a referência do dicionário
            if camera_id in self.camera_windows:
                del self.camera_windows[camera_id]
                print(f"[ScreenManager] Referência da Câmera {camera_id} removida.")

    # --- Handlers de Eventos da UI ---

    def _handle_login(self, username: str, password: str):
        self.controller.login(username, password)

    def _handle_register(self, username: str, password: str):
        self.controller.register(username, password)

    def _handle_logout(self):
        self.controller.logout()

    def _handle_camera_click(self, camera_id: int):
        self.show_camera_window(camera_id)

    # --- MÉTODO ATUALIZADO ---
    def _handle_start_detection(self, camera_id: int, cargo_type: CargoType):
        """Chamado pela CameraView para iniciar a detecção."""
        print(f"[ScreenManager] Recebida solicitação para iniciar Câmera {camera_id} com tipo {cargo_type.value}")
        self.controller.start_camera_detection(camera_id, cargo_type)

    # --- FIM ATUALIZAÇÃO ---

    def _handle_stop_detection(self, camera_id: int):
        """Chamado pela CameraView para parar a detecção."""
        print(f"[ScreenManager] Recebida solicitação para parar Câmera {camera_id}")
        self.controller.stop_camera_detection(camera_id)  # Agora só para

    # --- MÉTODO RENOMEADO/ATUALIZADO ---
    def _handle_finalize_session(self, camera_id: int):
        """Chamado pela CameraView para gerar relatório e enviar API."""
        print(f"[ScreenManager] Recebida solicitação para finalizar sessão da Câmera {camera_id}")
        # Chama o novo método no controller
        self.controller.finalize_and_report_session(camera_id)

    # --- FIM ATUALIZAÇÃO ---

    # --- Callbacks do Controller ---

    def _on_login_success(self, user: User):
        print(f"[ScreenManager] Login bem-sucedido: {user.username}")
        self.show_dashboard()
        if hasattr(self.login_view, 'clear_fields'):
            self.login_view.clear_fields()

    def _on_login_failed(self, message: str):
        print(f"[ScreenManager] Login falhou: {message}")
        if hasattr(self.login_view, 'show_error'):
            self.login_view.show_error(message)
        else:
            show_error_dialog("Erro de Login", message)

    def _on_register_success(self, message: str):
        print(f"[ScreenManager] Registro (admin) bem-sucedido: {message}")
        if hasattr(self.register_view, 'show_notification'): self.register_view.show_notification(message, "success")
        if hasattr(self.register_view, 'clear_fields'): self.register_view.clear_fields()
        self.root.after(2000, self.show_login)

    def _on_self_register_success(self, message: str):
        print(f"[ScreenManager] Auto-registro bem-sucedido: {message}")
        if hasattr(self.register_view, 'show_notification'): self.register_view.show_notification(message, "success")
        if hasattr(self.register_view, 'clear_fields'): self.register_view.clear_fields()
        self.root.after(2000, self.show_login)

    def _on_register_failed(self, message: str):
        print(f"[ScreenManager] Registro falhou: {message}")
        if hasattr(self.register_view, 'show_error'):
            self.register_view.show_error(message)
        else:
            show_error_dialog("Erro de Registro", message)

    def _on_logout_success(self):
        print("[ScreenManager] Logout realizado. Fechando janelas de câmera...")
        for camera_id in list(self.camera_windows.keys()):
            self._on_camera_window_close(camera_id)
        self.show_login()

    def _on_detection_starting(self, camera_id: int):
        print(f"[ScreenManager] Detecção iniciando para Câmera {camera_id}.")
        if camera_id in self.camera_windows and hasattr(self.camera_windows[camera_id], 'status_label'):
            self.camera_windows[camera_id].status_label.configure(text="Status: Conectando...", text_color="orange")

    def _on_detection_started(self, camera_id: int):
        print(f"[ScreenManager] Detecção iniciada para Câmera {camera_id}.")
        if camera_id in self.camera_windows and hasattr(self.camera_windows[camera_id], 'update_detection_status'):
            self.camera_windows[camera_id].update_detection_status(True)
        if hasattr(self.dashboard_view, 'update_camera_status'):
            self.dashboard_view.update_camera_status(camera_id, "Detecção Ativa", "success")

    def _on_detection_stopped(self, camera_id: int):
        print(f"[ScreenManager] Detecção parada para Câmera {camera_id}.")
        if camera_id in self.camera_windows and hasattr(self.camera_windows[camera_id], 'update_detection_status'):
            self.camera_windows[camera_id].update_detection_status(False)
        if hasattr(self.dashboard_view, 'update_camera_status'):
            self.dashboard_view.update_camera_status(camera_id, "Inativa", "warning")

    def _on_detection_failed(self, camera_id: int, message: str):
        print(f"[ScreenManager] Falha na detecção da Câmera {camera_id}: {message}")
        if hasattr(self.dashboard_view, 'show_error'):
            self.dashboard_view.show_error(f"Câmera {camera_id}: {message}")
        else:
            show_error_dialog(f"Erro Câmera {camera_id}", message)
        if camera_id in self.camera_windows:
            print(f"[ScreenManager] Fechando janela da Câmera {camera_id} devido à falha.")
            self._on_camera_window_close(camera_id)

    def _on_detection_update(self, camera_id: int, count: int, frame: Optional[Any]):
        if camera_id in self.camera_windows:
            window = self.camera_windows[camera_id]
            if hasattr(window, 'update_count'): window.update_count(count)
            if frame is not None and hasattr(window, 'update_video_frame'):
                window.update_video_frame(frame)

    def _on_count_reset(self, camera_id: int):
        print(f"[ScreenManager] Contagem resetada para Câmera {camera_id}.")
        if camera_id in self.camera_windows and hasattr(self.camera_windows[camera_id], 'update_count'):
            self.camera_windows[camera_id].update_count(0)

    def _on_report_generated(self, camera_id: int, filepath: str):
        print(f"[ScreenManager] Relatório gerado para Câmera {camera_id}: {filepath}")
        msg = f"Relatório salvo em:\n{filepath}"
        if camera_id in self.camera_windows and hasattr(self.camera_windows[camera_id], 'show_notification'):
            self.camera_windows[camera_id].show_notification(msg, "success")
        elif hasattr(self.dashboard_view, 'show_notification'):
            self.dashboard_view.show_notification(msg, "success")

    def _on_report_failed(self, camera_id: int, message: str):
        print(f"[ScreenManager] Falha ao gerar relatório para Câmera {camera_id}: {message}")
        msg = f"Erro ao gerar relatório: {message}"
        if camera_id in self.camera_windows and hasattr(self.camera_windows[camera_id], 'show_error'):
            self.camera_windows[camera_id].show_error(msg)
        elif hasattr(self.dashboard_view, 'show_error'):
            self.dashboard_view.show_error(f"Câmera {camera_id}: {msg}")
        else:
            show_error_dialog(f"Erro Relatório Câmera {camera_id}", message)

    # --- NOVOS CALLBACKS PARA API ---
    def _on_api_report_sent(self, camera_id: int, message: str):
        """Callback de sucesso ao enviar para API."""
        print(f"[ScreenManager] Relatório da Câmera {camera_id} enviado para API: {message}")
        if camera_id in self.camera_windows and hasattr(self.camera_windows[camera_id], 'show_notification'):
            self.camera_windows[camera_id].show_notification(message, "success")
        elif hasattr(self.dashboard_view, 'show_notification'):
            self.dashboard_view.show_notification(f"Câmera {camera_id}: {message}", "success")

    def _on_api_report_failed(self, camera_id: int, message: str):
        """Callback de falha ao enviar para API."""
        print(f"[ScreenManager] Falha ao enviar relatório da Câmera {camera_id} para API: {message}")
        msg = f"Falha ao enviar para API: {message}"
        if camera_id in self.camera_windows and hasattr(self.camera_windows[camera_id], 'show_error'):
            self.camera_windows[camera_id].show_error(msg)
        elif hasattr(self.dashboard_view, 'show_error'):
            self.dashboard_view.show_error(f"Câmera {camera_id}: {msg}")
        else:
            show_error_dialog(f"Erro API Câmera {camera_id}", message)

    # --- FIM NOVOS CALLBACKS ---

    # (Callbacks de Configuração - sem mudanças)
    def _on_config_updated(self, camera_id: Optional[int] = None):
        print(
            f"[ScreenManager] Configuração atualizada (Câmera: {camera_id if camera_id else 'Geral'}). Atualizando Dashboard.")
        if self.current_view == self.dashboard_view and hasattr(self.dashboard_view, 'update_cameras'):
            cameras = self.controller.get_cameras();
            self.dashboard_view.update_cameras(cameras)

    def _on_camera_added(self, camera_id: int):
        print(f"[ScreenManager] Câmera {camera_id} adicionada. Atualizando Dashboard.")
        if self.current_view == self.dashboard_view and hasattr(self.dashboard_view, 'update_cameras'):
            cameras = self.controller.get_cameras();
            self.dashboard_view.update_cameras(cameras)

    def _on_camera_removed(self, camera_id: int):
        print(f"[ScreenManager] Câmera {camera_id} removida. Fechando janela e atualizando Dashboard.")
        if camera_id in self.camera_windows: self._on_camera_window_close(camera_id)
        if self.current_view == self.dashboard_view and hasattr(self.dashboard_view, 'update_cameras'):
            cameras = self.controller.get_cameras();
            self.dashboard_view.update_cameras(cameras)

    def _on_error(self, message: str):
        print(f"[ScreenManager] Recebido erro do Controller: {message}")
        if self.current_view and hasattr(self.current_view, 'show_error'):
            self.current_view.show_error(message)
        else:
            show_error_dialog("Erro de Sistema", message)

    def shutdown(self):
        """Encerra o gerenciador de telas e chama shutdown do controller."""
        print("[ScreenManager] Iniciando processo de desligamento...")
        for camera_id in list(self.camera_windows.keys()):
            self._on_camera_window_close(camera_id)
        self.controller.shutdown()
        print("[ScreenManager] Desligamento concluído.")