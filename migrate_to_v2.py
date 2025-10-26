"""
Script de migração da versão antiga para a nova estrutura
"""
import json
import shutil
from pathlib import Path
from datetime import datetime


def migrate_config():
    """Migra configuração da versão antiga"""
    print("🔄 Migrando configuração...")
    
    # Verifica se existe config.py antigo
    old_config_path = Path("src/config.py")
    if not old_config_path.exists():
        print("❌ Arquivo config.py não encontrado")
        return False
    
    try:
        # Lê configuração antiga
        with open(old_config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove a linha que carrega o modelo YOLO para evitar erro
        content = content.replace('modelo_yolo = YOLO(YOLO_MODEL_PATH)', '# modelo_yolo = YOLO(YOLO_MODEL_PATH)  # Removido para migração')
        content = content.replace('print("🔄 Carregando modelo YOLO...")', '# print("🔄 Carregando modelo YOLO...")  # Removido para migração')
        content = content.replace('print("✅ Modelo carregado com sucesso!")', '# print("✅ Modelo carregado com sucesso!")  # Removido para migração')
        
        # Extrai configurações usando eval (cuidado em produção)
        exec(content)
        
        # Cria configuração nova
        new_config = {
            "cameras": {},
            "detection": {
                "model_path": "modelos/best.pt",
                "confidence_threshold": 0.5,
                "show_window": True,
                "tracking_enabled": True,
                "count_line_position": 0.5
            },
            "ui": {
                "theme": "dark",
                "window_width": 1280,
                "window_height": 720,
                "language": "pt_BR"
            },
            "users_file": "usuarios.json",
            "logs_dir": "logs",
            "reports_dir": "reports"
        }
        
        # Migra configurações de câmeras se existirem
        if 'RTSP_LINKS' in locals():
            for cam_id, source in RTSP_LINKS.items():
                new_config["cameras"][str(cam_id)] = {
                    "id": cam_id,
                    "name": f"Câmera {cam_id}",
                    "source": str(source),
                    "enabled": True,
                    "description": f"Câmera {cam_id} migrada"
                }
        
        # Migra outras configurações
        if 'CONFIDENCE_THRESHOLD' in locals():
            new_config["detection"]["confidence_threshold"] = CONFIDENCE_THRESHOLD
        
        if 'SHOW_WINDOW' in locals():
            new_config["detection"]["show_window"] = SHOW_WINDOW
        
        if 'YOLO_MODEL_PATH' in locals():
            new_config["detection"]["model_path"] = YOLO_MODEL_PATH
        
        # Salva nova configuração
        with open("config.json", 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=4, ensure_ascii=False)
        
        print("✅ Configuração migrada com sucesso para config.json")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao migrar configuração: {e}")
        return False


def migrate_users():
    """Migra usuários da versão antiga"""
    print("🔄 Migrando usuários...")
    
    old_users_path = Path("src/usuarios.json")
    if not old_users_path.exists():
        print("⚠️ Arquivo usuarios.json não encontrado, será criado automaticamente")
        return True
    
    try:
        # Copia arquivo de usuários
        shutil.copy2(old_users_path, "usuarios.json")
        print("✅ Usuários migrados com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao migrar usuários: {e}")
        return False


def migrate_models():
    """Migra modelos YOLO"""
    print("🔄 Migrando modelos...")
    
    old_models_path = Path("src/modelos")
    if not old_models_path.exists():
        print("⚠️ Pasta de modelos não encontrada")
        return True
    
    try:
        # Cria pasta modelos na raiz se não existir
        new_models_path = Path("modelos")
        new_models_path.mkdir(exist_ok=True)
        
        # Copia arquivos de modelo
        for model_file in old_models_path.glob("*.pt"):
            shutil.copy2(model_file, new_models_path / model_file.name)
            print(f"✅ Modelo {model_file.name} migrado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao migrar modelos: {e}")
        return False


def create_directories():
    """Cria diretórios necessários"""
    print("🔄 Criando diretórios...")
    
    directories = ["logs", "reports"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Diretório {directory} criado")
    
    return True


def backup_old_files():
    """Faz backup dos arquivos antigos"""
    print("🔄 Fazendo backup dos arquivos antigos...")
    
    backup_dir = Path(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_dir.mkdir(exist_ok=True)
    
    files_to_backup = [
        "src/main.py",
        "src/config.py",
        "src/usuarios.json"
    ]
    
    for file_path in files_to_backup:
        if Path(file_path).exists():
            shutil.copy2(file_path, backup_dir / Path(file_path).name)
            print(f"✅ Backup de {file_path} criado")
    
    return True


def main():
    """Função principal de migração"""
    print("🚀 LAS Cams System - Migração para v2.0")
    print("=" * 50)
    
    success = True
    
    # Executa migrações
    success &= backup_old_files()
    success &= create_directories()
    success &= migrate_config()
    success &= migrate_users()
    success &= migrate_models()
    
    print("=" * 50)
    
    if success:
        print("🎉 Migração concluída com sucesso!")
        print("\n📋 Próximos passos:")
        print("1. Instale as dependências: pip install -r requirements.txt")
        print("2. Execute a nova versão: python src/main_refactored.py")
        print("3. Use as credenciais padrão: admin / admin123")
        print("4. Configure suas câmeras no arquivo config.json")
        print("\n📁 Arquivos importantes:")
        print("- config.json: Configurações do sistema")
        print("- usuarios.json: Usuários do sistema")
        print("- modelos/: Modelos YOLO treinados")
        print("- logs/: Logs do sistema")
        print("- reports/: Relatórios gerados")
    else:
        print("❌ Migração falhou. Verifique os erros acima.")
    
    return success


if __name__ == "__main__":
    main()
