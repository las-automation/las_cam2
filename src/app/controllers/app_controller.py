"""
Controlador principal da aplicação
"""
from typing import Optional, Callable, Any
from datetime import datetime

# Importa todos os modelos necessários
from ..models.entities import User, DetectionSession, CameraStatus, CargoType, DailyReport
from ..services.auth_service import AuthService
from ..services.detection_service import DetectionService
from ..services.report_service import ReportService
# --- ADICIONADO: Importa ApiService ---
from ..services.api_service import ApiService
# --- FIM ADIÇÃO ---
from ..config.settings import config_manager, CameraConfig, AppConfig
from ..utils.logger import log_user_action, log_system_event, log_error


class AppController:
    """Controlador principal da aplicação"""

    def __init__(self):
        self.auth_service = AuthService()
        # --- MODIFICADO: Injeta a função trigger_ui_event ---
        self.detection_service = DetectionService(trigger_ui_event_func=self.trigger_ui_event)
        # --- FIM MODIFICAÇÃO ---
        self.report_service = ReportService()
        # --- ADICIONADO: Instancia ApiService ---
        self.api_service = ApiService()
        # --- FIM ADIÇÃO ---
        self.config = config_manager

        self.current_user: Optional[User] = None
        self.ui_callbacks: dict[str, Callable] = {}

        log_system_event("APP_CONTROLLER_INITIALIZED")

    def set_ui_callback(self, event: str, callback: Callable) -> None:
        """Define callback para eventos da UI"""
        self.ui_callbacks[event] = callback
        log_system_event(f"UI_CALLBACK_SET: {event}")

    def restore_all_factory_defaults(self) -> bool:
        """
        PARA TUDO, restaura config.json E usuarios.json
        para os padrões de fábrica e, em seguida, faz LOGOUT.
        """
        user = self.current_user.username if self.current_user else "system"
        log_user_action(user, "FACTORY_RESET_REQUESTED")

        try:
            # 1. Parar todas as detecções ativas
            print("INFO: Parando todas as detecções antes do reset...")
            self.detection_service.stop_all_detections()
            print("INFO: Detecções paradas.")

            # 2. Restaurar config.json
            print("INFO: Restaurando config.json...")
            if not self.config.restore_defaults():
                # Erro já logado pelo ConfigManager
                raise Exception("Falha ao restaurar config.json")

            # 3. Restaurar usuarios.json
            print("INFO: Restaurando usuarios.json...")
            if not self.auth_service.restore_default_users():
                # Erro já logado pelo AuthService
                raise Exception("Falha ao restaurar usuarios.json")

            log_system_event("FACTORY_RESET_SUCCESS")

            # 4. Fazer Logout (isso mudará a tela para Login)
            print("INFO: Reset de fábrica concluído. Fazendo logout...")
            # O logout dispara 'logout_success', que o ScreenManager ouve
            self.logout()

            return True

        except Exception as e:
            # Loga o erro específico que falhou (config ou auth)
            log_error("AppController", e, "Erro crítico durante a restauração de fábrica")
            self.trigger_ui_event("error", f"Erro inesperado ao restaurar: {e}")
            return False

    # --- FIM NOVO MÉTODO ---

    def trigger_ui_event(self, event: str, *args, **kwargs) -> None:
        """Dispara evento para a UI"""
        callback = self.ui_callbacks.get(event)
        if callback:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                log_error("AppController", e, f"Erro fatal no callback da UI '{event}'")
        else:
            # Não loga erro para eventos comuns que podem não ter callbacks
            if event not in ["detection_starting", "detection_stopped_no_report",
                             "camera_status_update", "api_report_sent", "api_report_failed"]:
                log_error("AppController", None, f"Tentativa de disparar evento UI não registrado: '{event}'")

    # --- Métodos de Autenticação (Sem mudanças) ---
    def login(self, username: str, password: str) -> bool:
        user = self.auth_service.authenticate(username, password)
        if user:
            self.current_user = user
            log_user_action(username, "LOGIN_SUCCESS")
            self.trigger_ui_event("login_success", user)
            return True
        else:
            self.trigger_ui_event("login_failed", "Credenciais inválidas")
            return False

    def register(self, username: str, password: str) -> bool:
        success = self.auth_service.register_user(username, password)
        if success:
            log_user_action(username, "SELF_REGISTER_SUCCESS")
            self.trigger_ui_event("self_register_success", "Usuário registrado com sucesso! Faça o login.")
        else:
            self.trigger_ui_event("register_failed", "Nome de usuário já existe ou erro interno.")
        return success

    def logout(self) -> None:
        if self.current_user:
            username = self.current_user.username
            log_user_action(username, "LOGOUT_REQUESTED")
            print("Parando detecções antes do logout...")
            self.detection_service.stop_all_detections()
            self.current_user = None
            log_user_action(username, "LOGOUT_COMPLETED")
            self.trigger_ui_event("logout_success")
        else:
            log_system_event("LOGOUT_ATTEMPT_WITHOUT_USER")

    def get_current_user(self) -> Optional[User]:
        return self.current_user

    # --- Métodos de Câmera e Detecção ---
    def get_cameras(self) -> list[dict]:
        """Retorna lista de dicionários com dados das câmeras configuradas e status."""
        cameras_data = []
        try:
            current_cameras = dict(self.config.config.cameras)
            for camera_id, camera_config in current_cameras.items():
                status = self.detection_service.get_camera_status(camera_id)
                cameras_data.append({
                    'id': camera_id,
                    'name': camera_config.name,
                    'source': camera_config.source,  # Corrigido para 'source'
                    'description': camera_config.description,
                    'enabled': camera_config.enabled,
                    'is_active': status.is_active if status else False,
                    'status_message': status.backend if status and status.is_active else (
                        "Desabilitada" if not camera_config.enabled else "Inativa"),
                    'status_obj': status.to_dict() if status else None
                })
        except Exception as e:
            log_error("AppController", e, "Erro ao obter lista de câmeras")
            self.trigger_ui_event("error", "Erro ao carregar câmeras.")
        return cameras_data

    def start_camera_detection(self, camera_id: int, cargo_type: CargoType) -> bool:
        """Inicia detecção em uma câmera, especificando o tipo de carga"""
        if not self.current_user:
            self.trigger_ui_event("error", "Usuário não autenticado")
            return False
        log_user_action(self.current_user.username,
                        f"START_DETECTION_REQUESTED: Cam={camera_id}, Type={cargo_type.value}")
        # A assinatura do DetectionService foi corrigida para aceitar cargo_type
        success = self.detection_service.start_detection(
            camera_id=camera_id,
            username=self.current_user.username,
            cargo_type=cargo_type,
            callback=self._on_detection_update
        )
        if not success:
            log_error("AppController", None, f"Falha ao solicitar início da detecção para Cam={camera_id}")
            # A UI já foi notificada da falha pelo DetectionService
        return success

    # --- MÉTODO stop_camera_detection SIMPLIFICADO ---
    def stop_camera_detection(self, camera_id: int) -> bool:
        """Apenas para a detecção em uma câmera, SEM gerar relatório."""
        log_system_event(f"STOP_DETECTION_REQUESTED: Cam={camera_id}", camera_id)

        session = self.detection_service.get_session(camera_id)
        stopped = self.detection_service.stop_detection(camera_id)

        if stopped:
            if session and session.end_time is None:
                session.end_session()  # Garante que a sessão seja marcada como finalizada
                log_system_event(f"SESSION_STOPPED_NO_REPORT: Cam={camera_id}, Count={session.detection_count}",
                                 camera_id)
            elif not session:
                log_system_event(f"STOP_DETECTION_OK_NO_SESSION: Cam={camera_id}", camera_id)
            # A UI é notificada pelo DetectionService ("detection_stopped")
        else:
            if session:  # Só notifica falha se havia sessão
                log_error("AppController", None, f"Falha ao parar detecção (ver logs) para Cam={camera_id}")
                # DetectionService deve ter disparado "detection_failed"
        return stopped

    # --- FIM MODIFICAÇÃO ---

    # --- NOVO MÉTODO: finalize_and_report_session ---
    def finalize_and_report_session(self, camera_id: int):
        """
        Pega a última sessão (parada), gera o PDF e envia para a API.
        Chamado pelo botão "Finalizar e Enviar".
        """
        log_system_event(f"FINALIZE_SESSION_REQUESTED: Cam={camera_id}", camera_id)

        # 1. Verifica se a detecção ainda está ativa
        if self.detection_service.is_detection_active(camera_id):
            log_error("AppController", None, f"Tentativa de finalizar sessão ATIVA para Cam={camera_id}")
            self.trigger_ui_event("report_failed", camera_id, "Erro: A detecção ainda está ativa. Pare-a primeiro.")
            return

        # 2. Pega a sessão (que deve estar parada e ter dados)
        session = self.detection_service.get_session(camera_id)
        if not session:
            log_error("AppController", None, f"Tentativa de finalizar sessão inexistente para Cam={camera_id}")
            self.trigger_ui_event("report_failed", camera_id, "Nenhuma sessão encontrada para finalizar.")
            return

        # Garante que end_time esteja definido
        if session.end_time is None:
            session.end_session()
            log_system_event(f"SESSION_FORCE_ENDED_ON_FINALIZE: Cam={camera_id}", camera_id)

        log_system_event(f"PROCESSING_REPORT_AND_API: Cam={camera_id}, Count={session.detection_count}", camera_id)

        try:
            # 3. Cria o objeto DailyReport
            cam_config = self.config.get_camera(camera_id)
            cam_name = cam_config.name if cam_config else f"Câmera {camera_id}"

            report_data = DailyReport(
                camera_name=cam_name,
                tipo=session.cargo_type,
                total=session.detection_count,
                horaInicio=session.start_time,
                horaTermino=session.end_time
            )

            # 4. Gera Relatório PDF
            log_system_event(f"GENERATING_FINAL_REPORT_PDF: Cam={camera_id}")
            filepath = self.report_service.generate_daily_report(report_data)
            if filepath:
                log_system_event(f"REPORT_GENERATED: {filepath}", camera_id)
                self.trigger_ui_event("report_generated", camera_id, filepath)
            else:
                log_error("AppController", None, f"ReportService falhou ao gerar PDF para Cam={camera_id}")
                self.trigger_ui_event("report_failed", camera_id, "Falha ao gerar PDF (ver logs)")

            # 5. Envia para API
            log_system_event(f"SENDING_REPORT_TO_API: Cam={camera_id}")
            if self.api_service.send_daily_report(report_data):
                log_system_event(f"API_REPORT_SENT_SUCCESS: Cam={camera_id}")
                self.trigger_ui_event("api_report_sent", camera_id, "Relatório enviado para API com sucesso.")
            else:
                log_error("AppController", None, f"Falha ao enviar relatório para API (Cam={camera_id})")
                self.trigger_ui_event("api_report_failed", camera_id, "Falha ao enviar dados para API (ver logs).")

        except Exception as e:
            log_error("AppController", e, f"Erro crítico ao processar relatório/API para Cam={camera_id}")
            self.trigger_ui_event("report_failed", camera_id, f"Erro interno ao gerar/enviar relatório: {e}")

    # --- FIM NOVO MÉTODO ---

    def get_detection_count(self, camera_id: int) -> int:
        return self.detection_service.get_detection_count(camera_id)

    def reset_detection_count(self, camera_id: int) -> bool:
        """Solicita ao DetectionService para resetar contagem de uma câmera."""
        log_system_event(f"RESET_COUNT_REQUESTED: Cam={camera_id}", camera_id)
        success = self.detection_service.reset_count(camera_id)
        if success:
            log_system_event(f"COUNT_RESET_CONFIRMED_BY_SERVICE: Cam={camera_id}", camera_id)
            # O DetectionService já dispara o "count_reset"
        else:
            log_error("AppController", None, f"Falha ao solicitar reset da contagem para Cam={camera_id}")
            self.trigger_ui_event("error", f"Não foi possível resetar a contagem da Câmera {camera_id}.")
        return success

    def _on_detection_update(self, camera_id: int, count: int, frame: Optional[Any]) -> None:
        """Callback do DetectionService para atualizações de frame e contagem."""
        self.trigger_ui_event("detection_update", camera_id, count, frame)

    # --- Métodos de Relatório (Manter para botão 'Relatório Manual*') ---
    def generate_simple_report(self, camera_id: int) -> Optional[str]:
        """Gera relatório simples (usado pelo botão 'Relatório Manual*')."""
        if not self.current_user: self.trigger_ui_event("error", "Usuário não autenticado"); return None
        # Pega a sessão atual/última
        session = self.detection_service.get_session(camera_id)
        if not session: self.trigger_ui_event("report_failed", camera_id,
                                              "Nenhuma sessão encontrada para relatório manual"); return None

        log_system_event(f"MANUAL_SIMPLE_REPORT_REQUESTED: Cam={camera_id}", camera_id)
        filepath = self.report_service.generate_simple_pdf(self.current_user.username, camera_id, session)
        if filepath:
            log_system_event(f"MANUAL_SIMPLE_REPORT_GENERATED: {filepath}", camera_id)
            self.trigger_ui_event("report_generated", camera_id, filepath)
        else:
            log_error("AppController", None, f"Falha ao gerar relatório simples manual para Cam={camera_id}")
            self.trigger_ui_event("report_failed", camera_id, "Erro ao gerar relatório simples (ver logs)")
        return filepath

    def get_reports_list(self) -> list:
        """Retorna lista de arquivos de relatório existentes."""
        try:
            return self.report_service.get_reports_list()
        except Exception as e:
            log_error("AppController", e, "Erro ao listar relatórios"); self.trigger_ui_event("error",
                                                                                              "Não foi possível listar os relatórios."); return []

    # --- Métodos de Configuração ---
    def get_config(self) -> AppConfig:
        return self.config.config

    def update_camera_config(self, camera_id: int, **kwargs) -> bool:
        log_system_event(f"UPDATE_CAMERA_CONFIG_REQUESTED: ID={camera_id}, Data={kwargs}", camera_id);
        success = self.config.update_camera_config(camera_id, **kwargs)
        if success:
            self.trigger_ui_event("config_updated", camera_id); log_system_event(
                f"UPDATE_CAMERA_CONFIG_SUCCESS: ID={camera_id}", camera_id)
        else:
            self.trigger_ui_event("error", f"Falha ao salvar configuração da Câmera {camera_id}")
        return success

    def add_camera(self, camera_config: CameraConfig) -> bool:
        log_system_event(f"ADD_CAMERA_REQUESTED: ID={camera_config.id}, Name={camera_config.name}");
        success = self.config.add_camera(camera_config)
        if success:
            self.trigger_ui_event("camera_added", camera_config.id); log_system_event(
                f"ADD_CAMERA_SUCCESS: ID={camera_config.id}")
        else:
            self.trigger_ui_event("error", f"Falha ao adicionar Câmera {camera_config.id}")
        return success

    def remove_camera(self, camera_id: int) -> bool:
        log_system_event(f"REMOVE_CAMERA_REQUESTED: ID={camera_id}", camera_id)
        if self.detection_service.is_detection_active(camera_id): log_system_event(
            f"Stopping active detection before removing Cam={camera_id}",
            camera_id); self.detection_service.stop_detection(camera_id)
        success = self.config.remove_camera(camera_id)
        if success:
            self.trigger_ui_event("camera_removed", camera_id); log_system_event(
                f"REMOVE_CAMERA_SUCCESS: ID={camera_id}")
        else:
            self.trigger_ui_event("error", f"Falha ao remover Câmera {camera_id} da configuração")
        return success

    # --- Métodos de Sistema ---
    def shutdown(self) -> None:
        """Encerra a aplicação de forma organizada."""
        log_system_event("APP_SHUTDOWN_REQUESTED");
        print("\n⏳ Encerrando serviços...");
        self.detection_service.stop_all_detections();
        self.logout();
        print("✅ Serviços encerrados.");
        log_system_event("APP_SHUTDOWN_COMPLETED")

    def get_system_status(self) -> dict:
        """Retorna um dicionário com o status atual do sistema."""
        backend_info = self.detection_service.get_backend_info();
        total_cameras = 0
        try:
            total_cameras = len(self.config.config.cameras)
        except:
            pass
        return {'active_sessions': backend_info.get('active_sessions', 0), 'total_cameras': total_cameras,
                'current_user': self.current_user.username if self.current_user else None,
                'backend_in_use': backend_info.get('backend_name', 'N/A'), 'system_time': datetime.now().isoformat()}