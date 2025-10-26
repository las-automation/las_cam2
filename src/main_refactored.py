"""
LAS Cams System - Aplicação Principal Refatorada
Sistema de monitoramento por câmeras com detecção de objetos
Versão com aceleração de hardware (TensorRT/DirectML/OpenVINO)
"""
import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk


# Importa apenas quando necessário para evitar erros circulares
def import_components():
    """Importa componentes após configurar o path"""
    from app.controllers.app_controller import AppController
    from app.views.screen_manager import ScreenManager
    from app.utils.model_optimizer import (
        check_and_export_models,
        print_optimization_summary,
        get_hardware_info
    )
    from app.utils.logger import log_system_event

    return AppController, ScreenManager, check_and_export_models, print_optimization_summary, get_hardware_info, log_system_event


class LASApp:
    """Aplicação principal do LAS Cams System"""

    def __init__(self, log_system_event):
        self.log_system_event = log_system_event
        log_system_event("APPLICATION_STARTUP")

        # Configuração do CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Cria janela principal
        self.root = ctk.CTk()
        self.root.title("LAS Cams System - Monitoramento Inteligente")
        self.root.geometry("1280x720")

        # Centraliza janela
        self._center_window()

        # Importa componentes
        AppController, ScreenManager, _, _, _, _ = import_components()

        # Inicializa controller e gerenciador de telas
        self.controller = AppController()
        self.screen_manager = ScreenManager(self.root, self.controller)

        # Configura evento de fechamento
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        log_system_event("APPLICATION_INITIALIZED")

    def _center_window(self):
        """Centraliza janela na tela"""
        width = 1280
        height = 720
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    def _on_closing(self):
        """Callback quando janela é fechada"""
        self.log_system_event("APPLICATION_CLOSING")

        # Encerra todos os serviços
        try:
            self.screen_manager.shutdown()
            self.controller.shutdown()
        except Exception as e:
            print(f"⚠️ Erro ao encerrar serviços: {e}")

        # Fecha janela
        self.root.destroy()

        self.log_system_event("APPLICATION_CLOSED")

    def run(self):
        """Inicia loop principal da aplicação"""
        self.log_system_event("APPLICATION_MAINLOOP_START")
        self.root.mainloop()


def print_startup_banner():
    """Imprime banner de inicialização"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║              🎥 LAS CAMS SYSTEM v2.0 🎥                      ║
    ║                                                              ║
    ║           Sistema de Monitoramento Inteligente              ║
    ║        com Aceleração de Hardware Automática                ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def initialize_system():
    """
    Inicializa o sistema completo:
    1. Verifica hardware
    2. Otimiza modelos
    3. Prepara detecção
    """
    # Importa funções necessárias
    _, _, check_and_export_models, print_optimization_summary, get_hardware_info, _ = import_components()

    print("\n" + "=" * 60)
    print("🔍 FASE 1: ANÁLISE DE HARDWARE")
    print("=" * 60)

    # Detecta hardware
    hw_info = get_hardware_info()

    print(f"\n💻 Sistema detectado:")
    print(f"   • CUDA (NVIDIA): {'✅ Disponível' if hw_info['cuda_available'] else '❌ Não disponível'}")
    print(f"   • DirectML (AMD): {'✅ Disponível' if hw_info['directml_available'] else '❌ Não disponível'}")
    print(f"   • CPU Threads: {hw_info['cpu_count']}")
    print(f"   • Backend Recomendado: {hw_info['recommended_backend'].upper()}")

    print("\n" + "=" * 60)
    print("🚀 FASE 2: OTIMIZAÇÃO DE MODELOS")
    print("=" * 60)
    print("\n⚠️  ATENÇÃO: A primeira execução pode levar alguns minutos")
    print("   Os modelos serão exportados apenas uma vez.\n")

    # Verifica e exporta modelos
    results = check_and_export_models()

    # Mostra resumo
    print_optimization_summary(results)

    if not results.get('base_model'):
        print("❌ ERRO CRÍTICO: Modelo base não encontrado!")
        print("   Por favor, coloque o arquivo 'best.pt' na pasta 'modelos/'")
        return False

    print("=" * 60)
    print("✅ SISTEMA PRONTO PARA USO")
    print("=" * 60 + "\n")

    return True


def main():
    """Função principal"""
    try:
        # Banner de inicialização
        print_startup_banner()

        # Inicializa sistema (hardware + modelos)
        if not initialize_system():
            print("\n❌ Falha na inicialização do sistema. Encerrando...")
            sys.exit(1)

        # Importa logger
        _, _, _, _, _, log_system_event = import_components()

        # Cria e executa aplicação
        print("🚀 Iniciando interface gráfica...\n")
        app = LASApp(log_system_event)
        app.run()

    except KeyboardInterrupt:
        print("\n\n⚠️  Aplicação interrompida pelo usuário")
        try:
            _, _, _, _, _, log_system_event = import_components()
            log_system_event("APPLICATION_INTERRUPTED")
        except:
            pass

    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        try:
            _, _, _, _, _, log_system_event = import_components()
            log_system_event(f"APPLICATION_FATAL_ERROR: {e}")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()