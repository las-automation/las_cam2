"""
Controlador principal da aplicação
"""
from typing import Optional, Callable, Any
from datetime import datetime

# --- MODIFICADO: Imports ---
from ..models.entities import User, DetectionSession, CameraStatus, CargoType, DailyReport
# --- FIM MODIFICAÇÃO ---
from ..services.auth_service import AuthService
from ..services.detection_service import DetectionService
from ..services.report_service import ReportService
from ..config.settings import config_manager, CameraConfig, AppConfig  # Importa CameraConfig e AppConfig
from ..utils.logger import log_user_action, log_system_event, log_error


class AppController:
    """Controlador principal da aplicação"""

    def __init__(self):
        self.auth_service = AuthService()
        # --- MODIFICADO: Criação do DetectionService ---
        # Passa o método trigger_ui_event do controller para o service
        # permitindo que o service notifique a UI diretamente.
        self.detection_service = DetectionService(trigger_ui_event_func=self.trigger_ui_event)
        # --- FIM MODIFICAÇÃO ---
        self.report_service = ReportService()
        self.config = config_manager  # Instância global do ConfigManager

        self.current_user: Optional[User] = None
        self.ui_callbacks: dict[str, Callable] = {}  # Melhor type hint

        log_system_event("APP_CONTROLLER_INITIALIZED")

    def set_ui_callback(self, event: str, callback: Callable) -> None:
        """Define callback para eventos da UI"""
        self.ui_callbacks[event] = callback
        log_system_event(f"UI_CALLBACK_SET: {event}")  # Log para debug

    def trigger_ui_event(self, event: str, *args, **kwargs) -> None:
        """Dispara evento para a UI"""
        callback = self.ui_callbacks.get(event)
        if callback:
            try:
                # print(f"DEBUG: Triggering UI event '{event}' with args: {args}, kwargs: {kwargs}") # Debug print
                callback(*args, **kwargs)
            except Exception as e:
                log_error("AppController", e, f"Erro fatal no callback da UI '{event}'")
                # Considerar mostrar um erro genérico na UI aqui, mas cuidado com loops
                # if event != "error":
                #    self.trigger_ui_event("error", f"Erro interno processando evento {event}")
        else:
            # Apenas loga se não for um evento opcional esperado
            if event not in ["detection_starting", "detection_stopped_no_report", "camera_status_update"]:
                log_error("AppController", None, f"Tentativa de disparar evento UI não registrado: '{event}'")

    # --- Métodos de Autenticação (sem mudanças funcionais) ---
    def login(self, username: str, password: str) -> bool:
        """Realiza login do usuário"""
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
        """Registra novo usuário"""
        success = self.auth_service.register_user(username, password)
        if success:
            log_user_action(username, "SELF_REGISTER_SUCCESS")
            # Usa 'register_success' ou 'self_register_success' dependendo do seu ScreenManager
            self.trigger_ui_event("self_register_success", "Usuário registrado com sucesso! Faça o login.")
        else:
            self.trigger_ui_event("register_failed", "Nome de usuário já existe ou erro interno.")
        return success

    def logout(self) -> None:
        """Realiza logout do usuário"""
        if self.current_user:
            username = self.current_user.username
            log_user_action(username, "LOGOUT_REQUESTED")
            # Parar todas as detecções antes de deslogar
            print("Parando detecções antes do logout...")
            self.detection_service.stop_all_detections()
            self.current_user = None
            log_user_action(username, "LOGOUT_COMPLETED")
            self.trigger_ui_event("logout_success")
        else:
            log_system_event("LOGOUT_ATTEMPT_WITHOUT_USER")

    def get_current_user(self) -> Optional[User]:
        """Retorna usuário atual"""
        return self.current_user

    # --- Métodos de Câmera e Detecção ---
    def get_cameras(self) -> list[dict]:
        """Retorna lista de dicionários com dados das câmeras configuradas e status."""
        cameras_data = []
        try:
            # Garante que iteramos sobre uma cópia segura
            current_cameras = dict(self.config.config.cameras)
            for camera_id, camera_config in current_cameras.items():
                status = self.detection_service.get_camera_status(camera_id)
                cameras_data.append({
                    'id': camera_id,
                    'name': camera_config.name,
                    'rtsp_url': camera_config.rtsp_url,
                    'description': camera_config.description,
                    'enabled': camera_config.enabled,
                    'is_active': status.is_active if status else False,
                    # Mensagem de status mais descritiva
                    'status_message': status.backend if status and status.is_active else (
                        "Desabilitada" if not camera_config.enabled else "Inativa"),
                    'status_obj': status.to_dict() if status else None
                })
        except Exception as e:
            log_error("AppController", e, "Erro ao obter lista de câmeras")
            self.trigger_ui_event("error", "Erro ao carregar câmeras.")
        return cameras_data

    # --- MÉTODO ATUALIZADO ---
    def start_camera_detection(self, camera_id: int, cargo_type: CargoType) -> bool:
        """Inicia detecção em uma câmera, especificando o tipo de carga"""
        if not self.current_user:
            self.trigger_ui_event("error", "Usuário não autenticado")
            return False

        log_user_action(self.current_user.username,
                        f"START_DETECTION_REQUESTED: Cam={camera_id}, Type={cargo_type.value}")

        # Delega para o DetectionService, passando o callback de atualização
        success = self.detection_service.start_detection(
            camera_id=camera_id,
            username=self.current_user.username,
            cargo_type=cargo_type,  # Passa o tipo selecionado
            callback=self._on_detection_update  # Passa o método do controller como callback
        )

        # A notificação de sucesso/falha agora é feita pelo DetectionService via trigger_ui_event
        if not success:
            # Log adicional no controller pode ser útil
            log_error("AppController", None, f"Falha ao solicitar início da detecção para Cam={camera_id}")
            # A UI já foi notificada pelo DetectionService

        return success

    # --- FIM ATUALIZAÇÃO ---

    # --- MÉTODO ATUALIZADO ---
    def stop_camera_detection(self, camera_id: int) -> bool:
        """Para detecção em uma câmera e gera o relatório diário se aplicável."""
        log_system_event(f"STOP_DETECTION_REQUESTED: Cam={camera_id}", camera_id)

        # 1. Pega a sessão ATIVA antes de solicitar a parada
        # É importante pegar antes, pois stop_detection pode limpar a referência
        session = self.detection_service.get_session(camera_id)
        if not session:
            log_system_event(f"STOP_DETECTION_IGNORED: Nenhuma sessão ativa encontrada para Cam={camera_id}", camera_id)
            # Tenta parar a thread mesmo assim, caso haja inconsistência
            stopped = self.detection_service.stop_detection(camera_id)
            # A UI será notificada pelo stop_detection se algo for parado
            return stopped

        # 2. Solicita a parada da detecção
        # O método stop_detection agora é responsável por aguardar a thread e notificar a UI
        stopped = self.detection_service.stop_detection(camera_id)

        # 3. Se parou com sucesso, processa a sessão finalizada para o relatório
        if stopped:
            # Garante que temos um end_time (caso a thread tenha terminado abruptamente)
            if session.end_time is None:
                session.end_session()  # Define agora

            log_system_event(
                f"SESSION_ENDED: Cam={camera_id}, Count={session.detection_count}, Duration={session.get_duration()}",
                camera_id)

            # Gera relatório se houve contagem válida
            if session.detection_count > 0:
                log_system_event(f"GENERATING_DAILY_REPORT: Cam={camera_id}", camera_id)
                try:
                    cam_config = self.config.get_camera(camera_id)
                    cam_name = cam_config.name if cam_config else f"Câmera {camera_id}"

                    report_data = DailyReport(
                        camera_name=cam_name, tipo=session.cargo_type, total=session.detection_count,
                        horaInicio=session.start_time, horaTermino=session.end_time
                    )

                    filepath = self.report_service.generate_daily_report(report_data)

                    if filepath:
                        log_system_event(f"REPORT_GENERATED: {filepath}", camera_id)
                        self.trigger_ui_event("report_generated", camera_id, filepath)  # Notifica UI do sucesso
                    else:
                        log_error("AppController", None, f"ReportService falhou ao gerar PDF para Cam={camera_id}")
                        self.trigger_ui_event("report_failed", camera_id,
                                              "Falha ao gerar PDF do relatório (ver logs)")  # Notifica UI da falha

                except Exception as e:
                    log_error("AppController", e, f"Erro crítico ao preparar/gerar relatório para Cam={camera_id}")
                    self.trigger_ui_event("report_failed", camera_id, f"Erro interno ao gerar relatório: {e}")
            else:
                log_system_event(f"SKIPPING_REPORT_NO_COUNT: Cam={camera_id}", camera_id)
                # Notifica UI que parou, mas sem relatório
                self.trigger_ui_event("detection_stopped_no_report", camera_id)

        # Se 'stopped' for False, o DetectionService já logou o erro e notificou a UI via 'detection_failed'
        return stopped

    # --- FIM ATUALIZAÇÃO ---

    def get_detection_count(self, camera_id: int) -> int:
        """Retorna contagem atual de uma câmera"""
        return self.detection_service.get_detection_count(camera_id)

    # --- MÉTODO ATUALIZADO ---
    def reset_detection_count(self, camera_id: int) -> bool:
        """Solicita ao DetectionService para resetar contagem de uma câmera."""
        log_system_event(f"RESET_COUNT_REQUESTED: Cam={camera_id}", camera_id)
        # Delega a lógica de reset para o DetectionService
        success = self.detection_service.reset_count(camera_id)
        if success:
            # O DetectionService notificará a UI via trigger_ui_event("count_reset", camera_id)
            log_system_event(f"COUNT_RESET_CONFIRMED_BY_SERVICE: Cam={camera_id}", camera_id)
        else:
            log_error("AppController", None,
                      f"Falha ao solicitar reset da contagem para Cam={camera_id} (provavelmente inativa)")
            self.trigger_ui_event("error", f"Não foi possível resetar a contagem da Câmera {camera_id}.")
        return success

    # --- FIM ATUALIZAÇÃO ---

    def _on_detection_update(self, camera_id: int, count: int, frame: Optional[Any]) -> None:
        """Callback do DetectionService para atualizações de frame e contagem."""
        # Repassa o evento para o ScreenManager/UI
        self.trigger_ui_event("detection_update", camera_id, count, frame)

    # --- Métodos de Relatório ---
    def generate_simple_report(self, camera_id: int) -> Optional[str]:
        """Gera relatório simples (para botão manual ou fallback)."""
        if not self.current_user: self.trigger_ui_event("error", "Usuário não autenticado"); return None
        session = self.detection_service.get_session(camera_id)
        if not session: self.trigger_ui_event("report_failed", camera_id,
                                              "Nenhuma sessão encontrada para relatório manual"); return None
        log_system_event(f"MANUAL_SIMPLE_REPORT_REQUESTED: Cam={camera_id}", camera_id);
        filepath = self.report_service.generate_simple_pdf(self.current_user.username, camera_id, session)
        if filepath:
            log_system_event(f"MANUAL_SIMPLE_REPORT_GENERATED: {filepath}", camera_id); self.trigger_ui_event(
                "report_generated", camera_id, filepath)
        else:
            log_error("AppController", None,
                      f"Falha ao gerar relatório simples manual para Cam={camera_id}"); self.trigger_ui_event(
                "report_failed", camera_id, "Erro ao gerar relatório simples (ver logs)")
        return filepath

    def get_reports_list(self) -> list:
        """Retorna lista de arquivos de relatório existentes."""
        try:
            return self.report_service.get_reports_list()
        except Exception as e:
            log_error("AppController", e, "Erro ao listar relatórios"); self.trigger_ui_event("error",
                                                                                              "Não foi possível listar os relatórios."); return []

    # --- Métodos de Configuração (sem mudanças funcionais) ---
    def get_config(self) -> AppConfig:
        """Retorna o objeto de configuração AppConfig atual"""
        return self.config.config  # Acessa o atributo 'config' da instância 'config_manager'

    def update_camera_config(self, camera_id: int, **kwargs) -> bool:
        """Atualiza configuração de uma câmera via ConfigManager."""
        log_system_event(f"UPDATE_CAMERA_CONFIG_REQUESTED: ID={camera_id}, Data={kwargs}", camera_id);
        success = self.config.update_camera_config(camera_id, **kwargs)
        if success:
            self.trigger_ui_event("config_updated", camera_id); log_system_event(
                f"UPDATE_CAMERA_CONFIG_SUCCESS: ID={camera_id}", camera_id)
        else:
            self.trigger_ui_event("error", f"Falha ao salvar configuração da Câmera {camera_id}")
        return success

    def add_camera(self, camera_config: CameraConfig) -> bool:
        """Adiciona nova câmera via ConfigManager."""
        log_system_event(f"ADD_CAMERA_REQUESTED: ID={camera_config.id}, Name={camera_config.name}");
        success = self.config.add_camera(camera_config)
        if success:
            self.trigger_ui_event("camera_added", camera_config.id); log_system_event(
                f"ADD_CAMERA_SUCCESS: ID={camera_config.id}")
        else:
            self.trigger_ui_event("error", f"Falha ao adicionar Câmera {camera_config.id}")
        return success

    def remove_camera(self, camera_id: int) -> bool:
        """Remove câmera via ConfigManager, parando a detecção antes."""
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

    # --- Métodos de Sistema (sem mudanças funcionais) ---
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
            total_cameras = len(self.config.config.cameras)  # Mais seguro
        except:
            pass
        return {'active_sessions': backend_info.get('active_sessions', 0), 'total_cameras': total_cameras,
                'current_user': self.current_user.username if self.current_user else None,
                'backend_in_use': backend_info.get('backend_name', 'N/A'), 'system_time': datetime.now().isoformat()}