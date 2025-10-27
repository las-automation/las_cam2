"""
Gerenciamento de configurações da aplicação
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, Optional, Literal
from ..utils.logger import log_system_event, log_error
# Importa o caminho padrão do AppData
from ..utils.paths import CONFIG_FILE_PATH

BackendOption = Literal["auto", "tensorrt", "directml", "openvino", "cpu"]


@dataclass
class CameraConfig:
    """Configuração de uma câmera"""
    id: int
    name: str
    source: str = "0"  # URL ou índice ("0", "1", ...)
    description: str = ""
    enabled: bool = True


@dataclass
class DetectionConfig:
    """Configuração de detecção com aceleração de hardware"""
    model_path: str = "modelos/best.pt"
    confidence_threshold: float = 0.5
    show_window: bool = False
    tracking_enabled: bool = True
    count_line_position: float = 0.5
    count_line_width_percent: float = 1.0
    preferred_backend: BackendOption = "auto"
    model_path_tensorrt: str = "modelos/best.engine"
    model_path_openvino: str = "modelos/best_openvino_model"
    auto_optimize: bool = True
    prefer_gpu: bool = True
    max_detection_failures: int = 150


@dataclass
class UIConfig:
    """Configuração da interface"""
    theme: str = "dark"
    language: str = "pt-BR"
    window_width: int = 1280
    window_height: int = 720


@dataclass
class AppConfig:
    """Configuração completa da aplicação"""
    cameras: Dict[int, CameraConfig] = field(default_factory=dict)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    # Adiciona a URL base da API, vazia por padrão
    api_base_url: str = ""  # Default vazio, requer configuração manual


class ConfigManager:
    """Gerenciador de configurações"""

    def __init__(self, config_file: Path = CONFIG_FILE_PATH):  # Usa o path do AppData
        self.config_file = config_file
        self.config: AppConfig = AppConfig()
        self._load_config()

    def _load_config(self) -> None:
        """Carrega configuração do arquivo JSON"""
        if not self.config_file.exists():
            log_system_event("CONFIG_NOT_FOUND_CREATING_DEFAULT")
            self._create_default_config()  # Cria e salva o padrão
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Carrega Câmeras
            cameras = {}
            for cam_id, cam_data in data.get('cameras', {}).items():
                try:
                    valid_keys = CameraConfig.__annotations__.keys()
                    filtered_cam_data = {k: v for k, v in cam_data.items() if k in valid_keys}
                    cameras[int(cam_id)] = CameraConfig(**filtered_cam_data)
                except Exception as cam_e:
                    log_error("ConfigManager", cam_e, f"Erro dados Câmera ID {cam_id}")

            # Carrega Detecção
            detection_data = data.get('detection', {})
            valid_det_keys = DetectionConfig.__annotations__.keys()
            filtered_det = {k: v for k, v in detection_data.items() if k in valid_det_keys}
            detection = DetectionConfig(**filtered_det)

            # Carrega UI
            ui_data = data.get('ui', {})
            valid_ui_keys = UIConfig.__annotations__.keys()
            filtered_ui = {k: v for k, v in ui_data.items() if k in valid_ui_keys}
            ui = UIConfig(**filtered_ui)

            # Carrega api_base_url
            api_base_url = data.get('api_base_url', self.config.api_base_url)  # Usa default se não existir

            self.config = AppConfig(
                cameras=cameras,
                detection=detection,
                ui=ui,
                api_base_url=api_base_url
            )
            log_system_event("CONFIG_LOADED_SUCCESSFULLY")

        except Exception as e:
            log_error("ConfigManager", e, "Erro ao carregar config, recriando padrão")
            self._create_default_config()

    def _create_default_config(self) -> bool:  # Retorna bool
        """Cria configuração padrão e TENTA salvar."""
        try:
            default_cameras = {
                0: CameraConfig(id=0, name="Webcam Principal", source="0", description="Webcam integrada ou USB",
                                enabled=True),
                1: CameraConfig(id=1, name="Câmera IP Entrada", source="rtsp://admin:admin@192.168.0.100:554/stream1",
                                description="Câmera IP", enabled=True),
                2: CameraConfig(id=2, name="Câmera IP Saida", source="rtsp://admin:admin@192.168.0.101:554/stream1",
                                description="Câmera IP", enabled=False)
            }
            # Cria AppConfig com defaults (api_base_url="" será usado)
            self.config = AppConfig(cameras=default_cameras)

            if self._save_config():
                log_system_event("DEFAULT_CONFIG_CREATED_AND_SAVED")
                return True
            else:
                log_error("ConfigManager", None, "Falha ao salvar config padrão inicial")
                return False
        except Exception as e:
            log_error("ConfigManager", e, "Erro crítico ao criar config padrão")
            return False

    def _save_config(self) -> bool:
        """Salva a configuração completa (incluindo api_base_url) no JSON."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            config_dict = asdict(self.config)
            # Converte chaves de câmera para string para JSON
            config_dict['cameras'] = {str(k): v for k, v in config_dict.get('cameras', {}).items()}

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)

            log_system_event("CONFIG_SAVED_TO_FILE")
            return True
        except Exception as e:
            log_error("ConfigManager", e, "Erro crítico ao salvar configuração no arquivo JSON")
            return False

    # --- ADICIONADO: Método para Restaurar Padrões ---
    def restore_defaults(self) -> bool:
        """
        Substitui a configuração atual em memória e no disco pela padrão.
        """
        log_system_event("CONFIG_RESTORE_DEFAULTS_REQUESTED")
        # _create_default_config agora cria e salva, retornando sucesso
        return self._create_default_config()

    # --- FIM ADIÇÃO ---


    def update_camera_config(self, camera_id: int, **kwargs) -> bool:
        """Atualiza configuração de uma câmera"""
        camera_id = int(camera_id)
        if camera_id not in self.config.cameras:
            log_error("ConfigManager", None, f"Tentativa update câmera inexistente: {camera_id}")
            return False
        try:
            camera = self.config.cameras[camera_id]
            updated = False
            for key, value in kwargs.items():
                if hasattr(camera, key) and getattr(camera, key) != value:
                    setattr(camera, key, value)
                    updated = True

            if updated:
                if self._save_config():
                    log_system_event(f"CAMERA_CONFIG_UPDATED_SAVED: ID={camera_id}")
                    return True
                else:
                    return False  # Erro no save
            else:
                return True  # Nada mudou
        except Exception as e:
            log_error("ConfigManager", e, f"Erro ao atualizar câmera {camera_id}")
            return False

    def add_camera(self, camera: CameraConfig) -> bool:
        """Adiciona nova câmera"""
        try:
            camera_id = int(camera.id)
            if camera_id in self.config.cameras:
                log_error("ConfigManager", None, f"Tentativa add câmera ID já existente: {camera_id}")
                return False
            self.config.cameras[camera_id] = camera
            if self._save_config():
                log_system_event(f"CAMERA_ADDED_SAVED: ID={camera_id}, Name={camera.name}")
                return True
            else:
                del self.config.cameras[camera_id]  # Reverte
                return False
        except Exception as e:
            log_error("ConfigManager", e, "Erro ao adicionar câmera")
            return False

    def remove_camera(self, camera_id: int) -> bool:
        """Remove câmera"""
        camera_id = int(camera_id)
        if camera_id not in self.config.cameras:
            log_error("ConfigManager", None, f"Tentativa remove câmera inexistente: {camera_id}")
            return False
        try:
            removed_camera = self.config.cameras.pop(camera_id)
            if self._save_config():
                log_system_event(f"CAMERA_REMOVED_SAVED: ID={camera_id}")
                return True
            else:
                self.config.cameras[camera_id] = removed_camera  # Reverte
                return False
        except Exception as e:
            log_error("ConfigManager", e, f"Erro ao remover câmera {camera_id}")
            if 'removed_camera' in locals():
                self.config.cameras[camera_id] = removed_camera
            return False

    def get_camera(self, camera_id: int) -> Optional[CameraConfig]:
        """Retorna configuração de uma câmera"""
        return self.config.cameras.get(int(camera_id))

    def reload(self) -> None:
        """Recarrega configuração do arquivo"""
        self._load_config()


# Instância global
config_manager = ConfigManager()