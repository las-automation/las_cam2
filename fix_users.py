"""
Script para corrigir o arquivo usuarios.json para o novo formato
"""
import json
import os
from pathlib import Path


def fix_users_file():
    """Corrige o arquivo usuarios.json para o novo formato"""
    users_file = Path("usuarios.json")

    if not users_file.exists():
        print("✅ Arquivo usuarios.json não existe. Será criado automaticamente.")
        return

    print("🔄 Carregando usuarios.json antigo...")

    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            old_data = json.load(f)

        print(f"📊 Encontrados {len(old_data)} usuários")

        # Cria backup
        backup_file = users_file.with_suffix('.json.old')
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(old_data, f, indent=4, ensure_ascii=False)
        print(f"💾 Backup salvo em: {backup_file}")

        # Converte para novo formato
        new_data = {}
        for username, user_info in old_data.items():
            # Formato antigo pode ter 'password_hash' ou 'senha_hash'
            password_hash = user_info.get('password_hash') or user_info.get('senha_hash', '')

            new_data[username] = {
                'username': username,
                'password_hash': password_hash,
                'role': user_info.get('role', 'operator'),
                'created_at': user_info.get('created_at'),
                'last_login': user_info.get('last_login'),
                'is_active': True  # Todos ativos por padrão
            }

        # Salva novo formato
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=4, ensure_ascii=False)

        print(f"✅ Arquivo usuarios.json atualizado com sucesso!")
        print(f"   {len(new_data)} usuários migrados")

    except json.JSONDecodeError:
        print("❌ Erro: usuarios.json está corrompido")
        print("   Renomeando para usuarios.json.corrupted...")
        users_file.rename("usuarios.json.corrupted")
        print("✅ Um novo arquivo será criado automaticamente")

    except Exception as e:
        print(f"❌ Erro ao processar arquivo: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 CORREÇÃO DO ARQUIVO usuarios.json")
    print("=" * 60 + "\n")

    fix_users_file()

    print("\n" + "=" * 60)
    print("✅ PROCESSO CONCLUÍDO")
    print("=" * 60)
    print("\nAgora você pode executar: python src/main_refactored.py")