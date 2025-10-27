import os
from pathlib import Path


def get_user_data_path() -> Path:
    """
    Retorna o caminho para a pasta de dados do usuário (ex: AppData/Roaming).
    Cria a pasta se ela não existir.
    """
    # Nossas conversas indicam que estamos em 2025,
    # então 'os.getenv("APPDATA")' é a variável de ambiente correta no Windows.
    # Para compatibilidade com Linux/macOS, usaríamos outras lógicas.
    app_data_dir = os.getenv("APPDATA")

    if app_data_dir:
        # Caminho: C:\Users\<user>\AppData\Roaming\LASCamsSystem
        user_data_path = Path(app_data_dir) / "LASCamsSystem"
    else:
        # Fallback para Linux/macOS ou se APPDATA não estiver definida
        user_data_path = Path.home() / ".LASCamsSystem"

    # Cria a pasta de dados se ela não existir
    try:
        user_data_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"ERRO CRÍTICO: Não foi possível criar o diretório de dados em {user_data_path}: {e}")
        # Se não puder criar, usa a pasta atual como último recurso
        return Path(".")

    return user_data_path


# Define o caminho base para dados do usuário
# Esta variável será importada por outros serviços
USER_DATA_PATH = get_user_data_path()

# Define caminhos específicos
CONFIG_FILE_PATH = USER_DATA_PATH / "config.json"
USERS_FILE_PATH = USER_DATA_PATH / "usuarios.json"
REPORTS_DIR_PATH = USER_DATA_PATH / "reports"
LOG_DIR_PATH = USER_DATA_PATH / "logs"