"""
Gerenciamento de configurações da aplicação
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, Optional, Literal # Importa Literal
from ..utils.logger import log_system_event, log_error

# Define os tipos de backend permitidos
BackendOption = Literal["auto", "tensorrt", "directml", "openvino", "cpu"]

@dataclass
class CameraConfig:
    # ... (sem mudanças)
    id: int
    name: str
    rtsp_url: str = ""
    description: str = ""
    enabled: bool = True
    username: Optional[str] = None
    password: Optional[str] = None

@dataclass
class DetectionConfig:
    """Configuração de detecção com aceleração de hardware"""
    model_path: str
    confidence_threshold: float
    show_window: bool
    tracking_enabled: bool = True
    count_line_position: float = 0.5
    count_line_width_percent: float = 1.0

    # --- NOVO CAMPO ---
    preferred_backend: BackendOption = "auto" # Opções: "auto", "tensorrt", "directml", "openvino", "cpu"
    # --- FIM NOVO CAMPO ---

    # Caminhos dos modelos otimizados
    model_path_tensorrt: str = "modelos/best.engine"
    model_path_openvino: str = "modelos/best_openvino_model"

    # Configurações adicionais
    auto_optimize: bool = True
    prefer_gpu: bool = True # Mantido, mas a preferência manual tem prioridade
    max_detection_failures: int = 150

@dataclass
class UIConfig:
    # ... (sem mudanças)
    theme: str = "dark"
    language: str = "pt-BR"
    window_width: int = 1280
    window_height: int = 720

@dataclass
class AppConfig:
    """Configuração completa da aplicação"""
    cameras: Dict[int, CameraConfig] = field(default_factory=dict)
    detection: DetectionConfig = field(default_factory=lambda: DetectionConfig(
        model_path="modelos/best.pt",
        confidence_threshold=0.5,
        show_window=False
        # preferred_backend usará o default "auto"
    ))
    ui: UIConfig = field(default_factory=UIConfig)

class ConfigManager:
    # ... (__init__, _load_config permanecem os mesmos,
    # eles já carregam/usam defaults para novos campos) ...
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config: AppConfig = AppConfig()
        self._load_config()

    def _load_config(self) -> None:
        """Carrega configuração do arquivo JSON"""
        if not self.config_file.exists():
            log_system_event("CONFIG_NOT_FOUND_CREATING_DEFAULT")
            self._create_default_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cameras = {}
            for cam_id, cam_data in data.get('cameras', {}).items():
                # Validação básica de tipo (opcional, mas bom)
                try:
                    cameras[int(cam_id)] = CameraConfig(**cam_data)
                except (TypeError, ValueError) as cam_e:
                     log_error("ConfigManager", cam_e, f"Erro ao carregar dados da câmera ID {cam_id}")

            detection_data = data.get('detection', {})
            # Garante que apenas campos válidos sejam passados
            valid_detection_keys = DetectionConfig.__annotations__.keys()
            filtered_detection_data = {k: v for k, v in detection_data.items() if k in valid_detection_keys}
            detection = DetectionConfig(**filtered_detection_data)


            ui_data = data.get('ui', {})
            valid_ui_keys = UIConfig.__annotations__.keys()
            filtered_ui_data = {k: v for k, v in ui_data.items() if k in valid_ui_keys}
            ui = UIConfig(**filtered_ui_data)


            self.config = AppConfig(
                cameras=cameras,
                detection=detection,
                ui=ui
            )

            log_system_event("CONFIG_LOADED_SUCCESSFULLY")

        except Exception as e:
            log_error("ConfigManager", e, "Erro ao carregar configuração, criando padrão")
            self._create_default_config()


    def _create_default_config(self) -> None:
        """Cria configuração padrão"""
        default_cameras = {
            1: CameraConfig(id=1, name="Câmera 1", rtsp_url=""),
            # Adicione mais câmeras padrão se desejar
        }

        # Cria config com defaults, incluindo preferred_backend="auto"
        self.config = AppConfig(cameras=default_cameras)

        if self._save_config():
            log_system_event("DEFAULT_CONFIG_CREATED_AND_SAVED")
        else:
             log_error("ConfigManager", None, "Falha ao salvar config padrão inicial")

    def _save_config(self) -> bool:
        """Salva configuração no arquivo JSON (sobrescrevendo)"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            # asdict incluirá o novo campo preferred_backend
            config_dict = {
                'cameras': {str(k): asdict(v) for k, v in self.config.cameras.items()},
                'detection': asdict(self.config.detection),
                'ui': asdict(self.config.ui)
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            log_error("ConfigManager", e, "Erro ao salvar configuração")
            return False

    # (update_camera_config, add_camera, remove_camera, get_camera, reload - sem mudanças)
    def update_camera_config(self, camera_id: int, **kwargs) -> bool:
        """Atualiza configuração de uma câmera"""
        camera_id = int(camera_id)
        if camera_id not in self.config.cameras:
            log_error("ConfigManager", None, f"Tentativa de atualizar câmera inexistente: {camera_id}")
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
                else: return False
            else: return True
        except Exception as e:
            log_error("ConfigManager", e, f"Erro ao atualizar câmera {camera_id}")
            return False

    def add_camera(self, camera: CameraConfig) -> bool:
        """Adiciona nova câmera"""
        try:
            camera_id = int(camera.id)
            if camera_id in self.config.cameras:
                log_error("ConfigManager", None, f"Tentativa de adicionar câmera com ID já existente: {camera_id}")
                return False
            self.config.cameras[camera_id] = camera
            if self._save_config():
                log_system_event(f"CAMERA_ADDED_SAVED: ID={camera_id}, Name={camera.name}")
                return True
            else:
                del self.config.cameras[camera_id]
                return False
        except Exception as e:
            log_error("ConfigManager", e, "Erro ao adicionar câmera")
            return False

    def remove_camera(self, camera_id: int) -> bool:
        """Remove câmera"""
        camera_id = int(camera_id)
        if camera_id not in self.config.cameras:
            log_error("ConfigManager", None, f"Tentativa de remover câmera inexistente: {camera_id}")
            return False
        try:
            removed_camera = self.config.cameras.pop(camera_id)
            if self._save_config():
                 log_system_event(f"CAMERA_REMOVED_SAVED: ID={camera_id}")
                 return True
            else:
                 self.config.cameras[camera_id] = removed_camera
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