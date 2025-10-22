# 📘 Documentação simples — Entendendo o arquivo config.py

O arquivo **`config.py`** é o centro de **configuração do sistema de detecção e contagem**.  
Ele define qual modelo YOLO será usado, quais câmeras o sistema vai acessar e como a detecção será exibida.

---

## 🧩 Estrutura básica do arquivo

```python
from ultralytics import YOLO

# ============ CONFIGURAÇÕES DO MODELO ============
YOLO_MODEL_PATH = "modelos/meu_modelo_yolo.pt"
CONFIDENCE_THRESHOLD = 0.5
SHOW_WINDOW = True

# ============ CÂMERAS CONFIGURADAS ============
RTSP_LINKS = {
    1: 0,  # Câmera do notebook
    2: "rtsp://usuario:senha@192.168.0.102:554/stream1",
    3: "rtsp://usuario:senha@192.168.0.103:554/stream1"
}

# ============ CARREGAMENTO DO MODELO ============
print("🔄 Carregando modelo YOLO...")
modelo_yolo = YOLO(YOLO_MODEL_PATH)
print("✅ Modelo carregado com sucesso!")
```

---

## 🧠 Explicando cada parte

### 1️⃣ Importação do YOLO
```python
from ultralytics import YOLO
```
Essa linha importa o pacote **Ultralytics YOLO**, que é o modelo de visão computacional responsável por detectar objetos nas imagens.

---

### 2️⃣ Caminho do modelo YOLO
```python
YOLO_MODEL_PATH = "modelos/meu_modelo_yolo.pt"
```
- Indica o **arquivo `.pt`** do modelo YOLO que você treinou ou baixou.  
- O modelo precisa estar dentro da pasta `modelos/`.  
- Você pode usar qualquer nome, contanto que o caminho esteja correto.

> Exemplo: se o arquivo se chama `pessoas.pt`, troque para:
> ```python
> YOLO_MODEL_PATH = "modelos/pessoas.pt"
> ```

---

### 3️⃣ Nível de confiança da detecção
```python
CONFIDENCE_THRESHOLD = 0.5
```
- Define a **confiança mínima** para considerar uma detecção válida.  
- Vai de `0.0` (muito permissivo) a `1.0` (muito rigoroso).  
- Valores comuns: **0.4 a 0.6**.

> 🔹 Se o sistema detectar coisas erradas, aumente o valor (ex: `0.7`).  
> 🔹 Se o sistema estiver perdendo objetos, diminua (ex: `0.4`).

---

### 4️⃣ Mostrar ou ocultar janela de vídeo
```python
SHOW_WINDOW = True
```
- Se for **True**, o sistema abre uma janela do OpenCV mostrando:
  - O vídeo em tempo real;  
  - As bounding boxes dos objetos;  
  - A linha de contagem e o total.
- Se for **False**, o vídeo **não é exibido** (útil em servidores sem monitor).

---

### 5️⃣ Configuração das câmeras
```python
RTSP_LINKS = {
    1: 0,
    2: "rtsp://usuario:senha@192.168.0.102:554/stream1",
    3: "rtsp://usuario:senha@192.168.0.103:554/stream1"
}
```
Cada chave (1, 2, 3...) representa o número da câmera.

#### ➜ Exemplos de valores:
| Tipo de câmera | Valor em `RTSP_LINKS` | Descrição |
|----------------|------------------------|------------|
| **Webcam local** | `0` | Usa a câmera interna do notebook |
| **Segunda webcam** | `1` | Se tiver duas webcams conectadas |
| **Câmera IP** | `"rtsp://usuario:senha@ip:porta/stream"` | Conecta via rede (RTSP) |

> 📌 Se você quiser apenas a webcam do notebook, pode deixar:
> ```python
> RTSP_LINKS = { 1: 0 }
> ```

---

### 6️⃣ Carregamento do modelo YOLO
```python
modelo_yolo = YOLO(YOLO_MODEL_PATH)
```
- Aqui o modelo YOLO é carregado na memória.  
- Quando o sistema é iniciado, você verá no terminal:
  ```
  🔄 Carregando modelo YOLO...
  ✅ Modelo carregado com sucesso!
  ```

> Se houver erro aqui, verifique se o arquivo `.pt` existe no caminho especificado.

---

## 🧩 Resumo rápido

| Item | Função | Valor padrão | Pode alterar? |
|------|--------|---------------|----------------|
| `YOLO_MODEL_PATH` | Caminho do modelo `.pt` | `"modelos/meu_modelo_yolo.pt"` | ✅ |
| `CONFIDENCE_THRESHOLD` | Confiança mínima | `0.5` | ✅ |
| `SHOW_WINDOW` | Exibir vídeo ao vivo | `True` | ✅ |
| `RTSP_LINKS` | Fontes de vídeo (câmeras) | `{1: 0, ...}` | ✅ |
| `modelo_yolo` | Modelo carregado | automático | ⚠️ (não altere manualmente) |

---

## ⚙️ Dica de uso rápido
1. Coloque o modelo YOLO `.pt` dentro da pasta `modelos/`.  
2. Ajuste `RTSP_LINKS` conforme suas câmeras.  
3. Rode `python main.py`.  
4. O sistema usa as configurações do `config.py` automaticamente.

---

## 💬 Exemplo real de uso

```python
# Usar webcam local e uma câmera IP externa
RTSP_LINKS = {
    1: 0,  # webcam do notebook
    2: "rtsp://admin:12345@192.168.1.20:554/live"
}
CONFIDENCE_THRESHOLD = 0.6
SHOW_WINDOW = True
```

Resultado:  
- A câmera 1 será a webcam local.  
- A câmera 2 será acessada via RTSP.  
- Apenas detecções com confiança ≥ 60% serão consideradas.  
- O vídeo de ambas será mostrado com caixas e contagens.

---

✅ **Em resumo:**  
O arquivo `config.py` é o painel de controle do sistema —  
você não precisa alterar o código principal (`main.py`),  
basta ajustar esse arquivo para configurar **modelo**, **câmeras** e **parâmetros** de detecção.
