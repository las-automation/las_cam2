# config.py
from ultralytics import YOLO

# ============ CONFIGURAÇÕES ============
YOLO_MODEL_PATH = "modelos/best.pt"
CONFIDENCE_THRESHOLD = 0.5
SHOW_WINDOW = True   # coloque True para visualizar a janela com a webcam

# ============ CÂMERAS ============
# Substitua o link RTSP pela câmera local (0 = webcam interna)
RTSP_LINKS = {
    1: 0,  # Webcam do notebook
    2: "rtsp://admin:admin@192.168.0.5:554/1/2",
    3: "rtsp://usuario:senha@192.168.0.103:554/stream1"
}

# ============ CARREGAMENTO DO MODELO ============
print("🔄 Carregando modelo YOLO...")

# IMPORTANTE: DirectML com YOLO tracking causa o erro "Cannot set version_counter"
# Por isso, estamos usando CPU para tracking (mais estável)
print("ℹ️ Usando CPU para inferência (mais estável com tracking)")
modelo_yolo = YOLO(YOLO_MODEL_PATH)

print("✅ Modelo carregado com sucesso!")