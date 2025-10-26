"""
Script de teste para verificar a instalação do LAS Cams System v2.0
"""
import sys
import importlib
from pathlib import Path


def test_imports():
    """Testa se todas as dependências estão instaladas"""
    print("🔍 Testando imports...")
    
    required_modules = [
        'customtkinter',
        'cv2',
        'ultralytics',
        'reportlab',
        'PIL',
        'numpy'
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    return len(failed_imports) == 0


def test_project_structure():
    """Testa se a estrutura do projeto está correta"""
    print("\n🏗️ Testando estrutura do projeto...")
    
    required_paths = [
        "src/app/models/entities.py",
        "src/app/services/auth_service.py",
        "src/app/services/detection_service.py",
        "src/app/services/report_service.py",
        "src/app/controllers/app_controller.py",
        "src/app/views/components.py",
        "src/app/views/login_view.py",
        "src/app/views/dashboard_view.py",
        "src/app/config/settings.py",
        "src/app/utils/logger.py",
        "src/main_refactored.py"
    ]
    
    missing_files = []
    
    for path in required_paths:
        if Path(path).exists():
            print(f"✅ {path}")
        else:
            print(f"❌ {path}")
            missing_files.append(path)
    
    return len(missing_files) == 0


def test_config_system():
    """Testa o sistema de configuração"""
    print("\n⚙️ Testando sistema de configuração...")
    
    try:
        sys.path.insert(0, str(Path("src")))
        from app.config.settings import config_manager
        
        config = config_manager.config
        print(f"✅ Configuração carregada")
        print(f"   - Câmeras: {len(config.cameras)}")
        print(f"   - Modelo: {config.detection.model_path}")
        print(f"   - Threshold: {config.detection.confidence_threshold}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no sistema de configuração: {e}")
        return False


def test_logging_system():
    """Testa o sistema de logging"""
    print("\n📝 Testando sistema de logging...")
    
    try:
        sys.path.insert(0, str(Path("src")))
        from app.utils.logger import get_logger, log_system_event
        
        logger = get_logger("test")
        logger.info("Teste de logging")
        
        log_system_event("TEST_EVENT", "Teste do sistema de logging")
        
        print("✅ Sistema de logging funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro no sistema de logging: {e}")
        return False


def test_services():
    """Testa os serviços principais"""
    print("\n🔧 Testando serviços...")
    
    try:
        sys.path.insert(0, str(Path("src")))
        
        # Testa AuthService
        from app.services.auth_service import AuthService
        auth_service = AuthService()
        print("✅ AuthService inicializado")
        
        # Testa ReportService
        from app.services.report_service import ReportService
        report_service = ReportService()
        print("✅ ReportService inicializado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos serviços: {e}")
        return False


def test_ui_components():
    """Testa componentes de UI"""
    print("\n🎨 Testando componentes de UI...")
    
    try:
        sys.path.insert(0, str(Path("src")))
        
        import customtkinter as ctk
        from app.views.components import ModernButton, ModernLabel, ModernEntry
        
        # Cria janela de teste
        test_window = ctk.CTk()
        test_window.withdraw()  # Esconde a janela
        
        # Testa componentes
        button = ModernButton(test_window, text="Teste", style="primary")
        label = ModernLabel(test_window, text="Teste", style="body")
        entry = ModernEntry(test_window, placeholder_text="Teste")
        
        test_window.destroy()
        
        print("✅ Componentes de UI funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro nos componentes de UI: {e}")
        return False


def main():
    """Função principal de teste"""
    print("🧪 LAS Cams System v2.0 - Teste de Instalação")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Estrutura do Projeto", test_project_structure),
        ("Sistema de Configuração", test_config_system),
        ("Sistema de Logging", test_logging_system),
        ("Serviços", test_services),
        ("Componentes de UI", test_ui_components)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 40)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("📊 RESULTADOS DOS TESTES")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 Resumo: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 Todos os testes passaram! O sistema está pronto para uso.")
        print("\n🚀 Para executar a aplicação:")
        print("   python src/main_refactored.py")
    else:
        print(f"\n⚠️ {total - passed} teste(s) falharam. Verifique os erros acima.")
        print("\n🔧 Possíveis soluções:")
        print("   1. Instale as dependências: pip install -r requirements.txt")
        print("   2. Execute o script de migração: python migrate_to_v2.py")
        print("   3. Verifique se todos os arquivos estão no lugar correto")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

