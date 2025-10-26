"""
Entidades de dados da aplicação
"""
from dataclasses import dataclass, field
# --- CORREÇÃO: Importa timedelta ---
from datetime import datetime, timedelta
# --- FIM CORREÇÃO ---
from typing import Optional, List
from enum import Enum


class CargoType(Enum):
    """Tipos de carga possíveis"""
    TORTA_NORMAL = "Torta Normal"
    TORTA_MOIDA = "Torta Moída"
    SOJA_SECA = "Soja Seca"
    SOJA_INTEGRAL = "Soja Integral"
    FARELO_MILHO_FINO = "Farelo de Milho Fino"
    FARELO_MILHO_GROSSO = "Farelo de Milho Grosso"
    DESCONHECIDO = "Não Especificado"  # Default ou erro

    # Helper para obter a lista de strings para ComboBox
    @classmethod
    def get_display_names(cls):
        return [item.value for item in cls]


class UserRole(Enum):
    """Papéis de usuário"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


@dataclass
class User:
    """Usuário do sistema"""
    username: str
    password_hash: str
    role: UserRole = UserRole.OPERATOR
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True  # CAMPO ADICIONADO

    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            'username': self.username,
            'password_hash': self.password_hash,
            'role': self.role.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Cria User a partir de dicionário"""
        return cls(
            username=data['username'],
            password_hash=data['password_hash'],
            role=UserRole(data.get('role', 'operator')),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            last_login=datetime.fromisoformat(data['last_login']) if data.get('last_login') else None,
            is_active=data.get('is_active', True)
        )


@dataclass
class DetectionEvent:
    """Evento de detecção"""
    timestamp: datetime
    camera_id: int
    object_class: str
    confidence: float
    bbox: tuple  # (x1, y1, x2, y2)
    crossed_line: bool = False


@dataclass
class DetectionSession:
    """Representa uma sessão de detecção ativa"""
    camera_id: int
    user: str
    model_version: str
    cargo_type: CargoType = CargoType.DESCONHECIDO  # Adiciona o tipo de carga
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    detection_count: int = 0

    # Adicionar outros campos se necessário (ex: lista de eventos)

    def end_session(self):
        self.end_time = datetime.now()

    def get_duration(self) -> timedelta:  # Agora timedelta está definido
        end = self.end_time or datetime.now()
        return end - self.start_time

    def to_dict(self) -> dict:
        duration = self.get_duration()
        return {
            "camera_id": self.camera_id,
            "user": self.user,
            "cargo_type": self.cargo_type.value,  # Usa o valor string do enum
            "model_version": self.model_version,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration.total_seconds(),
            "detection_count": self.detection_count,
        }


@dataclass
class CameraStatus:
    """Status atual de uma câmera"""
    camera_id: int
    is_active: bool
    detection_count: int
    session_start: Optional[datetime]  # Pode ser None se inativo
    last_update: datetime = field(default_factory=datetime.now)
    backend: str = "unknown"  # TensorRT, DirectML, OpenVINO, CPU

    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            'camera_id': self.camera_id,
            'is_active': self.is_active,
            'detection_count': self.detection_count,
            'session_start': self.session_start.isoformat() if self.session_start else None,
            'last_update': self.last_update.isoformat(),
            'backend': self.backend
        }


@dataclass
class DailyReport:
    """Dados para o relatório diário de uma sessão"""
    camera_name: str  # Adicionado para clareza no relatório
    tipo: CargoType
    total: int
    horaInicio: datetime
    horaTermino: datetime
    data: datetime.date = field(init=False)  # Data extraída do início
    totalHoras: float = field(init=False)  # Calculado

    def __post_init__(self):
        # Calcula data e duração após a inicialização
        self.data = self.horaInicio.date()
        duration_seconds = (self.horaTermino - self.horaInicio).total_seconds()
        # Garante que a duração seja não negativa
        self.totalHoras = max(0.0, duration_seconds / 3600.0)  # Converte segundos para horas


@dataclass
class ReportData:
    """Dados para geração de relatório (Estrutura anterior, manter se usada)"""
    user: str
    camera_id: int
    session: DetectionSession
    events: List[DetectionEvent]
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            'user': self.user,
            'camera_id': self.camera_id,
            'session': self.session.to_dict(),
            'events': [
                {
                    'timestamp': e.timestamp.isoformat(),
                    'object_class': e.object_class,
                    'confidence': e.confidence,
                    'crossed_line': e.crossed_line
                }
                for e in self.events
            ],
            'generated_at': self.generated_at.isoformat()
        }