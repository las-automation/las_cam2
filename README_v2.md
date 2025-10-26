# 🚀 LAS Cams System v2.0 - Aceleração de Hardware

## 📌 Resumo das Mudanças

Esta atualização implementa **detecção automática e otimização de hardware**, permitindo que o sistema use:

- ⚡ **TensorRT** (GPUs NVIDIA) - Performance máxima
- 🎮 **DirectML** (GPUs AMD/Intel) - Boa performance no Windows
- 🔧 **OpenVINO** (CPUs/iGPUs Intel) - Otimizado para Intel
- 💻 **CPU PyTorch** (Fallback) - Funciona em qualquer hardware

## 📁 Arquivos Criados/Modificados

### ✅ Novos Arquivos
```
app/
├── utils/
│   └── model_optimizer.py          # Exporta modelos otimizados
├── config/
│   └── settings.py (ATUALIZADO)    # Novas configurações
├── services/
│   └── detection_service.py (ATUALIZADO)  # Seleção inteligente de backend
├── models/
│   └── entities.py (ATUALIZADO)    # Backend info nas entidades
└── main_refactored.py (ATUALIZADO) # Inicialização com otimização
```

## 🔧 Instalação

### 1. Dependências Base (já instaladas)
```bash
pip install ultralytics opencv-python customtkinter reportlab
```

### 2. Dependências Opcionais (para aceleração)

#### Para GPUs NVIDIA (TensorRT):
```bash
# Instalar CUDA Toolkit 11.8 ou 12.x
# Download: https://developer.nvidia.com/cuda-downloads

# Instalar PyTorch com CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

#### Para GPUs AMD no Windows (DirectML):
```bash
pip install torch-directml
```

#### Para CPUs Intel (OpenVINO):
```bash
pip install openvino-dev
```

## 🚀 Como Usar

### 1. Primeira Execução (Otimização Automática)

Execute a aplicação normalmente:

```bash
python src/main_refactored.py
```

**O que acontece:**
1. O sistema detecta seu hardware
2. Se tiver GPU NVIDIA → Exporta modelo TensorRT (`.engine`)
3. Se tiver GPU AMD → Usa DirectML automaticamente
4. Se tiver CPU Intel → Exporta modelo OpenVINO (`_openvino_model/`)
5. Sempre mantém o modelo base PyTorch (`.pt`) como fallback

⚠️ **IMPORTANTE:** A primeira execução demora ~5-10 minutos (exportação dos modelos). Após isso, é instantâneo!

### 2. Execuções Seguintes

Nas próximas execuções, o sistema:
- Detecta os modelos já exportados
- Carrega o melhor automaticamente
- Inicia em segundos

## 📊 Configuração Manual (config.json)

Se quiser ajustar as configurações de hardware:

```json
{
  "detection": {
    "model_path": "modelos/best.pt",
    "model_path_tensorrt": "modelos/best.engine",
    "model_path_openvino": "modelos/best_openvino_model",
    "auto_optimize": true,
    "prefer_gpu": true,
    "confidence_threshold": 0.5,
    "max_detection_failures": 150
  }
}
```

### Opções:
- `auto_optimize`: Se `true`, exporta modelos automaticamente na primeira execução
- `prefer_gpu`: Se `true`, prioriza GPU sobre CPU
- `max_detection_failures`: Número de falhas antes de encerrar thread

## 🎯 Prioridade de Backends

O sistema escolhe nesta ordem:

1. **TensorRT** (NVIDIA CUDA)
   - ✅ Mais rápido (~100+ FPS)
   - ✅ Melhor para múltiplas câmeras
   - ⚠️ Requer GPU NVIDIA

2. **DirectML** (AMD/Intel Windows)
   - ✅ Rápido (~30-60 FPS)
   - ✅ Funciona com qualquer GPU no Windows
   - ⚠️ Requer `torch-directml`

3. **OpenVINO** (Intel CPU/iGPU)
   - ✅ Otimizado para CPUs Intel (~15-30 FPS)
   - ✅ Usa iGPU Intel se disponível
   - ⚠️ Melhor que PyTorch puro

4. **CPU PyTorch** (Fallback)
   - ✅ Funciona em qualquer hardware
   - ⚠️ Mais lento (~5-15 FPS)

## 🐛 Troubleshooting

### Erro: "Modelo base não encontrado"
```
❌ [ModelOptimizer] Modelo base não encontrado: modelos/best.pt
```
**Solução:** Coloque seu arquivo `best.pt` na pasta `modelos/`

### Erro: "CUDA not available"
```
ℹ️ [TensorRT] GPU NVIDIA não detectada (CUDA não disponível)
```
**Solução:** 
1. Verifique se sua GPU é NVIDIA
2. Instale CUDA Toolkit
3. Reinstale PyTorch com suporte CUDA

### Erro: "Cannot set version_counter"
```
RuntimeError: Cannot set version_counter for inference tensor
```
**Solução:** Este erro foi **corrigido** na v2.0! O sistema agora:
- Não passa `device=` para DirectML
- Carrega o modelo corretamente em cada backend

### Performance baixa
Se o sistema estiver lento:

1. **Verifique qual backend está sendo usado:**
   - Olhe no console: `🚀 [DetectionService] Usando ...`

2. **Force exportação dos modelos:**
   ```bash
   python -m app.utils.model_optimizer
   ```

3. **Reduza a resolução:**
   ```python
   # No detection_service.py, adicione antes do track:
   frame = cv2.resize(frame, (640, 480))
   ```

## 📈 Performance Esperada

| Hardware | Backend | FPS Esperado | Múltiplas Câmeras |
|----------|---------|--------------|-------------------|
| RTX 3060 | TensorRT | 100-150 | ✅ Excelente (4-6 câmeras) |
| RX 6600 | DirectML | 30-60 | ✅ Bom (2-3 câmeras) |
| i7-12700 | OpenVINO | 15-30 | ⚠️ Moderado (1-2 câmeras) |
| i5-8400 | CPU | 5-15 | ❌ Limitado (1 câmera) |

## 🔍 Logs e Debug

Para ver informações detalhadas:

```python
# Ativar verbose no YOLO (detection_service.py)
resultados = model.track(
    frame,
    conf=cfg.confidence_threshold,
    persist=True,
    verbose=True  # Mude para True
)
```

Para ver logs do sistema:
```bash
# Os logs ficam em: logs/app.log
tail -f logs/app.log
```

## 📞 Suporte

Se encontrar problemas:

1. Verifique os logs em `logs/app.log`
2. Execute o teste de hardware:
   ```bash
   python -m app.utils.model_optimizer
   ```
3. Compartilhe a saída no console

## 🎉 Próximos Passos

Agora que o sistema está otimizado:

1. ✅ Teste com suas câmeras RTSP reais
2. ✅ Ajuste o `confidence_threshold` no config.json
3. ✅ Configure múltiplas câmeras
4. ✅ Monitore a performance

**Aproveite a velocidade da GPU! 🚀**