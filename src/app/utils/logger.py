"""
Sistema de logging centralizado do LAS Cams System
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional
import os


class LoggerManager:
    """Gerenciador de logs do sistema"""

    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        self._loggers: dict = {}
        self._setup_root_logger()

    def _setup_root_logger(self) -> None:
        """Configura o logger raiz"""
        # Formato das mensagens de log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler para arquivo principal
        main_log_file = self.logs_dir / f"las_cams_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO) # Mostra INFO ou superior no console

        # Configuração do logger raiz
        root_logger = logging.getLogger()
        # Define o nível MÍNIMO que o logger raiz processará
        # (mesmo que os handlers tenham níveis mais altos)
        root_logger.setLevel(logging.DEBUG)

        # Evita adicionar handlers duplicados se a função for chamada novamente
        if not root_logger.hasHandlers():
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)
        else:
             # Garante que os handlers existentes estejam configurados
             # (útil em alguns cenários de recarregamento)
            for handler in root_logger.handlers:
                 handler.setFormatter(formatter)
                 if isinstance(handler, logging.StreamHandler):
                     handler.setLevel(logging.INFO)
                 elif isinstance(handler, logging.handlers.RotatingFileHandler):
                     handler.setLevel(logging.INFO)


    def get_logger(self, name: str) -> logging.Logger:
        """Retorna um logger específico"""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            # Define o nível do logger específico (pode ser diferente do root)
            logger.setLevel(logging.DEBUG)

            # --- Handler específico para arquivo deste logger ---
            log_file = self.logs_dir / f"{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.log"
            handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=5*1024*1024,  # 5MB por arquivo específico
                backupCount=3,
                encoding='utf-8'
            )

            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            handler.setLevel(logging.DEBUG) # Grava DEBUG ou superior no arquivo específico

            # Adiciona handler apenas se ainda não tiver um similar
            # (previne duplicação se get_logger for chamado múltiplas vezes)
            has_similar_handler = any(
                isinstance(h, logging.handlers.RotatingFileHandler) and h.baseFilename == str(log_file.resolve())
                for h in logger.handlers
            )
            if not has_similar_handler:
                logger.addHandler(handler)

            # --- Controle de propagação para o root logger ---
            # Define como False para evitar que logs deste logger
            # apareçam DUAS VEZES (uma pelo seu handler, outra pelo root)
            # no arquivo principal e no console.
            logger.propagate = True # Mudado para True - Deixa o root logger controlar console/arquivo principal

            self._loggers[name] = logger

        return self._loggers[name]

    def log_detection_event(self, camera_id: int, event_type: str, details: str) -> None:
        """Log específico para eventos de detecção"""
        logger = self.get_logger("detection")
        logger.info(f"Camera {camera_id} - {event_type}: {details}")

    def log_user_action(self, username: str, action: str, details: str = "") -> None:
        """Log específico para ações do usuário"""
        logger = self.get_logger("user_actions")
        logger.info(f"User '{username}' - {action}: {details}") # Adicionado aspas no username

    def log_system_event(self, event: str, details: str = "") -> None:
        """Log específico para eventos do sistema"""
        logger = self.get_logger("system")
        logger.info(f"System - {event}: {details}")

    def log_error(self, component: str, error: Exception, details: str = "") -> None:
        """Log específico para erros"""
        logger = self.get_logger("errors")
        # Usa exc_info=True para incluir o traceback completo no log de erro
        logger.error(f"{component} - {type(error).__name__}: {str(error)} - {details}", exc_info=True)

    # --- FUNÇÃO ADICIONADA ---
    def log_warning(self, component: str, details: str = "") -> None:
        """Log específico para avisos"""
        logger = self.get_logger("warnings") # Cria/Usa logger 'warnings'
        logger.warning(f"{component} - {details}")
    # --- FIM DA ADIÇÃO ---


# Instância global do gerenciador de logs
logger_manager = LoggerManager()


# Funções de conveniência (wrappers)
def get_logger(name: str) -> logging.Logger:
    """Retorna um logger específico"""
    return logger_manager.get_logger(name)


def log_detection(camera_id: int, event_type: str, details: str) -> None:
    """Log de evento de detecção"""
    logger_manager.log_detection_event(camera_id, event_type, details)


def log_user_action(username: str, action: str, details: str = "") -> None:
    """Log de ação do usuário"""
    logger_manager.log_user_action(username, action, details)


def log_system_event(event: str, details: str = "") -> None:
    """Log de evento do sistema"""
    logger_manager.log_system_event(event, details)


def log_error(component: str, error: Exception, details: str = "") -> None:
    """Log de erro"""
    logger_manager.log_error(component, error, details)


# --- FUNÇÃO ADICIONADA ---
def log_warning(component: str, details: str = "") -> None:
    """Log de aviso"""
    logger_manager.log_warning(component, details)
# --- FIM DA ADIÇÃO ---
