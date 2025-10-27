# Salve como: app/services/api_service.py

import requests
import json
from typing import Optional

from ..models.entities import DailyReport
# --- Importa config_manager ---
from ..config.settings import config_manager
# --- Fim Import ---
from ..utils.logger import log_system_event, log_error

# --- Endpoint Fixo ---
API_ENDPOINT = "/daily-reports"
REQUEST_TIMEOUT = 15 # Segundos
# --- Fim Endpoint Fixo ---


class ApiService:
    """Serviço para comunicação com a API externa de relatórios."""

    def _get_base_url(self) -> Optional[str]:
        """Obtém a URL base da API a partir do ConfigManager."""
        try:
            # Acessa a configuração carregada pelo ConfigManager
            base_url = config_manager.config.api_base_url
            if base_url and base_url.startswith("http"):
                return base_url.rstrip('/') # Remove barra final se houver
            else:
                log_error("ApiService", None, f"URL base da API inválida encontrada no config: '{base_url}'")
                return None
        except AttributeError:
            log_error("ApiService", None, "'api_base_url' não encontrado na configuração.")
            return None
        except Exception as e:
             log_error("ApiService", e, "Erro inesperado ao obter URL base da API.")
             return None

    def send_daily_report(self, report_data: DailyReport) -> bool:
        """
        Envia os dados do DailyReport para a API via POST.
        Lê a URL base do config_manager.
        """
        api_base_url = self._get_base_url()
        if not api_base_url:
            print("ERRO: URL base da API não configurada corretamente no arquivo config.json")
            return False # Erro já logado por _get_base_url

        url = f"{api_base_url}{API_ENDPOINT}" # Concatena com endpoint fixo

        payload = {
            "tipo": report_data.tipo.name,
            "total": report_data.total,
            "horaInicio": report_data.horaInicio.strftime("%H:%M:%S"),
            "horaTermino": report_data.horaTermino.strftime("%H:%M:%S"),
            "totalHoras": round(report_data.totalHoras, 2),
            "data": report_data.data.strftime("%Y-%m-%d")
        }
        headers = {'Content-Type': 'application/json'}

        log_system_event(f"API_SEND_REPORT_START: URL={url}")
        # print(f"DEBUG: Enviando payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            if response.status_code in [200, 201]:
                log_system_event(f"API_SEND_REPORT_SUCCESS: Status={response.status_code}")
                # print(f"DEBUG: Resposta API ({response.status_code}): {response.text[:200]}...")
                return True
            else:
                log_error("ApiService", None, f"API_SEND_REPORT_UNEXPECTED_STATUS: Status={response.status_code}, Response={response.text[:200]}...")
                return False

        except requests.exceptions.Timeout: log_error("ApiService", None, f"API_SEND_REPORT_TIMEOUT: URL={url} após {REQUEST_TIMEOUT}s"); return False
        except requests.exceptions.ConnectionError as conn_err: log_error("ApiService", conn_err, f"API_SEND_REPORT_CONNECTION_ERROR: URL={url}"); return False
        except requests.exceptions.HTTPError as http_err: log_error("ApiService", http_err, f"API_SEND_REPORT_HTTP_ERROR: Status={http_err.response.status_code}, Response={http_err.response.text[:500]}..."); return False
        except requests.exceptions.RequestException as req_err: log_error("ApiService", req_err, f"API_SEND_REPORT_REQUEST_ERROR: URL={url}"); return False
        except Exception as e: log_error("ApiService", e, f"API_SEND_REPORT_UNKNOWN_ERROR: URL={url}"); return False

api_service = ApiService()