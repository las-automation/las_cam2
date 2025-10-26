"""
Otimizador de modelos YOLO para aceleração de hardware
Exporta modelos para TensorRT (NVIDIA) e OpenVINO (Intel)
"""
import torch
from pathlib import Path
from typing import Optional
from ultralytics import YOLO

from ..config.settings import config_manager
from ..utils.logger import log_system_event, log_error


def check_and_export_models() -> dict:
    """
    Verifica hardware disponível e exporta modelos otimizados se necessário.

    Returns:
        dict: Informações sobre os modelos exportados
    """
    cfg = config_manager.config.detection
    results = {
        'tensorrt': False,
        'openvino': False,
        'directml': False,
        'base_model': False
    }

    # Verifica se o modelo base existe
    model_path = Path(cfg.model_path)
    if not model_path.exists():
        print(f"❌ [ModelOptimizer] Modelo base não encontrado: {cfg.model_path}")
        print(f"   Por favor, coloque o arquivo 'best.pt' na pasta 'modelos/'")
        return results

    results['base_model'] = True
    print(f"✅ [ModelOptimizer] Modelo base encontrado: {cfg.model_path}")

    # Se auto_optimize estiver desabilitado, pula exportação
    if not cfg.auto_optimize:
        print("ℹ️ [ModelOptimizer] Auto-otimização desabilitada no config.json")
        return results

    # 1. Verifica e exporta TensorRT (NVIDIA CUDA)
    if _check_and_export_tensorrt(cfg, model_path):
        results['tensorrt'] = True

    # 2. Verifica e exporta OpenVINO (Intel)
    if _check_and_export_openvino(cfg, model_path):
        results['openvino'] = True

    # 3. Verifica DirectML (AMD/Outras GPUs no Windows)
    if _check_directml():
        results['directml'] = True

    return results


def _check_and_export_tensorrt(cfg, model_path: Path) -> bool:
    """Verifica GPU NVIDIA e exporta modelo para TensorRT"""
    tensorrt_path = Path(cfg.model_path_tensorrt)

    # Verifica se CUDA está disponível
    if not torch.cuda.is_available():
        print("ℹ️ [TensorRT] GPU NVIDIA não detectada (CUDA não disponível)")
        return False

    # Verifica se o modelo já existe
    if tensorrt_path.exists():
        print(f"✅ [TensorRT] Modelo otimizado já existe: {tensorrt_path}")
        return True

    # Exporta modelo para TensorRT
    try:
        print("🚀 [TensorRT] GPU NVIDIA detectada! Exportando modelo...")
        print("   ⚠️ Isso pode levar alguns minutos na primeira execução...")

        model = YOLO(str(model_path))
        model.export(format='engine', device=0)  # TensorRT export

        # Verifica se a exportação foi bem-sucedida
        if tensorrt_path.exists():
            print(f"✅ [TensorRT] Modelo exportado com sucesso: {tensorrt_path}")
            log_system_event("TENSORRT_MODEL_EXPORTED")
            return True
        else:
            print("⚠️ [TensorRT] Exportação concluída mas arquivo não encontrado")
            return False

    except Exception as e:
        log_error("ModelOptimizer", e, "Erro ao exportar para TensorRT")
        print(f"❌ [TensorRT] Falha na exportação: {str(e)}")
        print("   Continuando com CPU/DirectML...")
        return False


def _check_and_export_openvino(cfg, model_path: Path) -> bool:
    """Verifica CPU Intel e exporta modelo para OpenVINO"""
    openvino_path = Path(cfg.model_path_openvino)

    # Verifica se o modelo já existe
    if openvino_path.exists() and openvino_path.is_dir():
        print(f"✅ [OpenVINO] Modelo otimizado já existe: {openvino_path}")
        return True

    # Exporta modelo para OpenVINO
    # Nota: OpenVINO é útil principalmente para CPUs Intel e iGPUs
    try:
        print("🚀 [OpenVINO] Exportando modelo para otimização de CPU/Intel...")
        print("   ⚠️ Isso pode levar alguns minutos na primeira execução...")

        model = YOLO(str(model_path))
        model.export(format='openvino')

        # Verifica se a exportação foi bem-sucedida
        if openvino_path.exists():
            print(f"✅ [OpenVINO] Modelo exportado com sucesso: {openvino_path}")
            log_system_event("OPENVINO_MODEL_EXPORTED")
            return True
        else:
            print("⚠️ [OpenVINO] Exportação concluída mas pasta não encontrada")
            return False

    except Exception as e:
        log_error("ModelOptimizer", e, "Erro ao exportar para OpenVINO")
        print(f"❌ [OpenVINO] Falha na exportação: {str(e)}")
        print("   Continuando com CPU padrão...")
        return False


def _check_directml() -> bool:
    """Verifica se DirectML está disponível (AMD/Outras GPUs no Windows)"""
    try:
        import torch_directml
        if torch_directml.is_available():
            device = torch_directml.device()
            print(f"✅ [DirectML] GPU AMD/Outra detectada: {device}")
            log_system_event("DIRECTML_AVAILABLE")
            return True
    except ImportError:
        print("ℹ️ [DirectML] torch-directml não instalado")
        print("   Para usar GPUs AMD no Windows, instale: pip install torch-directml")
    except Exception as e:
        print(f"ℹ️ [DirectML] Não disponível: {e}")

    return False


def get_hardware_info() -> dict:
    """
    Retorna informações sobre o hardware disponível.

    Returns:
        dict: Informações detalhadas do hardware
    """
    info = {
        'cuda_available': False,
        'cuda_devices': 0,
        'cuda_version': None,
        'directml_available': False,
        'cpu_count': 0,
        'recommended_backend': 'cpu'
    }

    # CUDA (NVIDIA)
    if torch.cuda.is_available():
        info['cuda_available'] = True
        info['cuda_devices'] = torch.cuda.device_count()
        info['cuda_version'] = torch.version.cuda
        info['recommended_backend'] = 'tensorrt'

        for i in range(info['cuda_devices']):
            device_name = torch.cuda.get_device_name(i)
            print(f"   GPU {i}: {device_name}")

    # DirectML (AMD/Outras)
    try:
        import torch_directml
        if torch_directml.is_available():
            info['directml_available'] = True
            if not info['cuda_available']:
                info['recommended_backend'] = 'directml'
    except:
        pass

    # CPU
    info['cpu_count'] = torch.get_num_threads()

    return info


def print_optimization_summary(results: dict) -> None:
    """Imprime resumo da otimização"""
    print("\n" + "=" * 60)
    print("📊 RESUMO DA OTIMIZAÇÃO DE MODELOS")
    print("=" * 60)

    if results.get('base_model'):
        print("✅ Modelo Base (PyTorch): Disponível")
    else:
        print("❌ Modelo Base (PyTorch): NÃO ENCONTRADO")
        return

    if results.get('tensorrt'):
        print("✅ TensorRT (NVIDIA): Exportado e pronto")
    else:
        print("⏭️  TensorRT (NVIDIA): Não disponível")

    if results.get('openvino'):
        print("✅ OpenVINO (Intel): Exportado e pronto")
    else:
        print("⏭️  OpenVINO (Intel): Não exportado")

    if results.get('directml'):
        print("✅ DirectML (AMD/Outras): Disponível")
    else:
        print("⏭️  DirectML (AMD/Outras): Não disponível")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Teste standalone
    print("🔍 Verificando hardware e modelos...\n")

    # Mostra informações do hardware
    hw_info = get_hardware_info()
    print(f"\n💻 Backend recomendado: {hw_info['recommended_backend'].upper()}")

    # Verifica e exporta modelos
    results = check_and_export_models()

    # Mostra resumo
    print_optimization_summary(results)