"""
Serviço de detecção com seleção inteligente de backend (TensorRT/DirectML/OpenVINO/CPU)
"""
import threading
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import cv2
import torch
import numpy as np

from ultralytics import YOLO
from ..models.entities import DetectionSession, CameraStatus, CargoType
from ..config.settings import config_manager, BackendOption, CameraConfig
from ..utils.logger import log_system_event, log_error, log_user_action


class DetectionService:
    """Serviço de detecção de objetos com aceleração de hardware"""

    def __init__(self, trigger_ui_event_func: Callable):
        """
        Inicializa o serviço de detecção.

        Args:
            trigger_ui_event_func: Função (geralmente AppController.trigger_ui_event)
                                   para notificar a UI sobre eventos.
        """
        self.config = config_manager
        self._active_sessions: Dict[int, DetectionSession] = {}
        self._detection_threads: Dict[int, threading.Thread] = {}
        self._stop_events: Dict[int, threading.Event] = {}
        self.trigger_ui_event = trigger_ui_event_func
        self.selected_model_path: str = ""
        self.selected_device_args: dict = {}
        self.backend_name: str = "N/A"

        # Chama o método para determinar o backend
        self._get_best_backend() # Agora este método deve existir na classe

        if self.backend_name != "N/A":
            log_system_event(f"DETECTION_SERVICE_INITIALIZED_BACKEND_{self.backend_name.upper()}")
        else:
            log_error("DetectionService", None, "Falha crítica ao inicializar qualquer backend de detecção.")
            self.trigger_ui_event("error", "Falha ao inicializar backend de IA.")

    # --- MÉTODO _get_best_backend CORRIGIDO (INDENTAÇÃO CORRETA) ---
    def _get_best_backend(self) -> None:
        """
        Detecta ou usa o backend preferido, com fallback automático.
        Define self.selected_device_args corretamente para cada backend.
        """
        cfg = self.config.config.detection
        preference: BackendOption = getattr(cfg, 'preferred_backend', 'auto')
        print("-" * 60 + f"\n⚙️  Selecionando Backend (Preferência: {preference.upper()})\n" + "-" * 60)
        preferred_backend_set = False

        # --- Tenta usar o Backend Preferido ---
        if preference != "auto":
            if preference == "tensorrt":
                if torch.cuda.is_available() and Path(cfg.model_path_tensorrt).exists():
                    self.backend_name = "TensorRT"; self.selected_model_path = cfg.model_path_tensorrt
                    self.selected_device_args = {'device': 0}; preferred_backend_set = True
                    print(f"👍 Usando preferência: {self.backend_name} (NVIDIA GPU)")
                else: print(f"⚠️ Preferência TensorRT falhou (CUDA indisponível ou {cfg.model_path_tensorrt} não encontrado)")
            elif preference == "directml":
                try:
                    import torch_directml
                    if torch_directml.is_available():
                        self.backend_name = "DirectML"; self.selected_model_path = cfg.model_path
                        self.selected_device_args = {}; preferred_backend_set = True
                        print(f"👍 Usando preferência: {self.backend_name} (GPU AMD/Outra)")
                        try: print(f"   Device: {torch_directml.device()}")
                        except: pass
                    else: print(f"⚠️ Preferência DirectML falhou (DirectML indisponível)")
                except (ImportError, AttributeError): print(f"⚠️ Preferência DirectML falhou (torch_directml não instalado)")
            elif preference == "openvino":
                if Path(cfg.model_path_openvino).exists():
                    self.backend_name = "OpenVINO"; self.selected_model_path = cfg.model_path_openvino
                    self.selected_device_args = {}; preferred_backend_set = True
                    print(f"👍 Usando preferência: {self.backend_name} (Intel CPU/iGPU)")
                else: print(f"⚠️ Preferência OpenVINO falhou ({cfg.model_path_openvino} não encontrado)")
            elif preference == "cpu":
                self.backend_name = "CPU"; self.selected_model_path = cfg.model_path
                self.selected_device_args = {'device': 'cpu'}; preferred_backend_set = True
                print(f"👍 Usando preferência: {self.backend_name} (PyTorch CPU)")
            if preferred_backend_set: return # Sai se a preferência funcionou
            print(f"   ➡️ Preferência '{preference}' falhou. Tentando detecção automática...")

        # --- Lógica Automática (Fallback) ---
        print("🤖 Iniciando detecção automática de backend...")
        if torch.cuda.is_available() and Path(cfg.model_path_tensorrt).exists():
            self.backend_name = "TensorRT"; self.selected_model_path = cfg.model_path_tensorrt; self.selected_device_args = {'device': 0}
            print(f"   🥇 Detectado: {self.backend_name} (NVIDIA GPU)")
            try: print(f"      GPU: {torch.cuda.get_device_name(0)}")
            except: pass # Apenas ignora erro de impressão
            return # Sai da função após configurar TensorRT
        try:
            import torch_directml
            if torch_directml.is_available():
                self.backend_name = "DirectML"; self.selected_model_path = cfg.model_path; self.selected_device_args = {}
                print(f"   🥈 Detectado: {self.backend_name} (GPU AMD/Outra)")
                try: print(f"      Device: {torch_directml.device()}") # Apenas info
                except: pass
                return # Sai após configurar DirectML
        except (ImportError, AttributeError): pass
        if Path(cfg.model_path_openvino).exists():
            self.backend_name = "OpenVINO"; self.selected_model_path = cfg.model_path_openvino; self.selected_device_args = {}
            print(f"   🥉 Detectado: {self.backend_name} (Intel CPU/iGPU)"); return
        self.backend_name = "CPU"; self.selected_model_path = cfg.model_path; self.selected_device_args = {'device': 'cpu'}
        print(f"   🐢 Fallback: {self.backend_name} (PyTorch CPU Padrão)")
        if preference == 'auto': print("      💡 Para melhor performance, considere instalar dependências de aceleração.")
    # --- FIM DO MÉTODO _get_best_backend ---


    def start_detection(
            self,
            camera_id: int,
            username: str,
            cargo_type: CargoType,
            callback: Optional[Callable[[int, int, np.ndarray], None]] = None
    ) -> bool:
        """Inicia detecção em uma câmera."""
        if self.is_detection_active(camera_id): log_error("DetectionService", None, f"Câmera {camera_id} já está ativa"); self.trigger_ui_event("detection_failed", camera_id, "Detecção já está ativa."); return False
        camera_config = self.config.get_camera(camera_id)
        if not camera_config or not camera_config.enabled: error_msg = f"Câmera {camera_id} não encontrada ou desabilitada"; log_error("DetectionService", None, error_msg); self.trigger_ui_event("detection_failed", camera_id, error_msg); return False
        if not camera_config.rtsp_url: error_msg = f"Câmera {camera_id} não possui URL RTSP configurada."; log_error("DetectionService", None, error_msg); self.trigger_ui_event("detection_failed", camera_id, error_msg); return False
        if self.backend_name == "N/A": error_msg = "Nenhum backend de detecção inicializado."; log_error("DetectionService", None, error_msg + f" Não é possível iniciar a câmera {camera_id}."); self.trigger_ui_event("detection_failed", camera_id, error_msg); return False
        session = DetectionSession(camera_id=camera_id, user=username, model_version=self.backend_name, cargo_type=cargo_type)
        stop_event = threading.Event(); thread = threading.Thread(target=self._run_detection_thread, args=(camera_id, session, camera_config, stop_event, callback), daemon=True, name=f"Detection-Cam-{camera_id}")
        self._active_sessions[camera_id] = session; self._stop_events[camera_id] = stop_event; self._detection_threads[camera_id] = thread
        self.trigger_ui_event("detection_starting", camera_id); thread.start()
        log_user_action(username, f"DETECTION_STARTED_CAMERA_{camera_id}_TYPE_{cargo_type.value}_BACKEND_{self.backend_name}"); return True

    def _run_detection_thread(
            self,
            camera_id: int,
            session: DetectionSession,
            camera_config: CameraConfig,
            stop_event: threading.Event,
            callback: Optional[Callable[[int, int, np.ndarray], None]]
    ) -> None:
        """Thread principal de detecção."""
        thread_name = threading.current_thread().name
        log_system_event(f"THREAD_STARTED: {thread_name}", camera_id); print(f"✅ [{thread_name}] Iniciada")
        print(f"   Backend: {self.backend_name}, Modelo: {self.selected_model_path}")
        cap = None; model = None
        try:
            log_system_event(f"LOADING_MODEL: {thread_name}", camera_id); print(f"🔄 [{thread_name}] Carregando modelo YOLO...")
            model = YOLO(self.selected_model_path); log_system_event(f"MODEL_LOADED: {thread_name}", camera_id); print(f"✅ [{thread_name}] Modelo carregado")
            log_system_event(f"CONNECTING_RTSP: {thread_name}", camera_id); print(f"🔄 [{thread_name}] Conectando a {camera_config.rtsp_url}...")
            cap = cv2.VideoCapture(camera_config.rtsp_url, cv2.CAP_FFMPEG)
            if not cap.isOpened(): raise ConnectionError(f"Falha ao abrir stream RTSP: {camera_config.rtsp_url}")
            log_system_event(f"RTSP_CONNECTED: {thread_name}", camera_id); print(f"✅ [{thread_name}] Conectado ao stream")
            cfg = self.config.config.detection; linha_y_pos = max(0.0, min(1.0, cfg.count_line_position)); crossing_threshold = 0.70
            contador = 0; rastreador_estado: Dict[int, Dict[str, Any]] = {}; falhas_consecutivas = 0; max_falhas = cfg.max_detection_failures
            self.trigger_ui_event("detection_started", camera_id); log_system_event(f"DETECTION_LOOP_STARTING: {thread_name}", camera_id); print(f"🎬 [{thread_name}] Iniciando loop...")
            while not stop_event.is_set():
                if stop_event.is_set(): break
                ret, frame = cap.read()
                if stop_event.is_set(): break
                if not ret or frame is None:
                    falhas_consecutivas += 1
                    if falhas_consecutivas > max_falhas: log_error(thread_name, None, f"Stream perdido após {max_falhas} falhas."); self.trigger_ui_event("detection_failed", camera_id, "Stream perdido"); break
                    stop_event.wait(0.1); continue
                falhas_consecutivas = 0
                frame_height, frame_width = frame.shape[:2]; linha_y_pixel = int(frame_height * linha_y_pos)
                line_width_percent = max(0.0, min(1.0, cfg.count_line_width_percent)); line_pixel_width = frame_width * line_width_percent
                x_start = int((frame_width - line_pixel_width) / 2); x_end = int(x_start + line_pixel_width)
                if stop_event.is_set(): break
                track_args = {'conf': cfg.confidence_threshold, 'persist': True, 'verbose': False, 'tracker': 'bytetrack.yaml'}
                if self.selected_device_args: track_args.update(self.selected_device_args)
                resultados = model.track(frame, **track_args)
                if stop_event.is_set(): break
                deteccoes = resultados[0].boxes if resultados and len(resultados) > 0 else None
                frame_anotado = frame.copy(); current_ids_on_frame = set()
                if deteccoes is not None and deteccoes.id is not None:
                    frame_anotado = resultados[0].plot(line_width=1, font_size=0.4)
                    for box, obj_id_tensor in zip(deteccoes.xyxy, deteccoes.id):
                        obj_id = int(obj_id_tensor.cpu().item()); current_ids_on_frame.add(obj_id)
                        x1, y1, x2, y2 = map(int, box.cpu().numpy()); cx = (x1 + x2) // 2; height = y2 - y1
                        if height > 0:
                            pixels_below = max(0, y2 - linha_y_pixel); current_fraction_below = np.clip(pixels_below / height, 0.0, 1.0)
                            if obj_id not in rastreador_estado: rastreador_estado[obj_id] = {'previous_fraction_below': None, 'counted_this_crossing': False}
                            state = rastreador_estado[obj_id]; previous_fraction_below = state['previous_fraction_below']; dentro_limites_x = (x_start <= cx <= x_end)
                            if (previous_fraction_below is not None and previous_fraction_below < crossing_threshold and current_fraction_below >= crossing_threshold and not state['counted_this_crossing'] and dentro_limites_x):
                                contador += 1; state['counted_this_crossing'] = True; session.detection_count = contador
                                log_system_event(f"OBJECT_CROSSED: Cam={camera_id}, ID={obj_id}, Count={contador}", camera_id)
                                print(f"✅ [{thread_name}] ID {obj_id} CRUZOU ({current_fraction_below:.2f} abaixo)! Total: {contador}")
                            elif current_fraction_below < crossing_threshold: state['counted_this_crossing'] = False
                            state['previous_fraction_below'] = current_fraction_below
                ids_to_remove = set(rastreador_estado.keys()) - current_ids_on_frame
                for tid in ids_to_remove: del rastreador_estado[tid]
                cv2.line(frame_anotado, (x_start, linha_y_pixel), (x_end, linha_y_pixel), (0, 0, 255), 2)
                cv2.putText(frame_anotado, f"Contagem: {contador}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                if stop_event.is_set(): break
                if callback:
                    try: callback(camera_id, contador, frame_anotado)
                    except Exception as e: log_error(thread_name, e, f"Erro no callback")
                if cfg.show_window:
                    cv2.imshow(f"Camera {camera_id} - {self.backend_name}", frame_anotado)
                    if cv2.waitKey(1) & 0xFF == ord('q'): stop_event.set(); break
        except ConnectionError as conn_e:
             log_error(thread_name, conn_e, "Erro de conexão RTSP"); self.trigger_ui_event("detection_failed", camera_id, f"Erro de conexão: {conn_e}")
        except Exception as e:
            log_error(thread_name, e, f"Erro fatal na thread"); self.trigger_ui_event("detection_failed", camera_id, f"Erro fatal na thread: {e}")
        finally:
            log_system_event(f"CLEANING_UP_THREAD: {thread_name}", camera_id); print(f"🧹 [{thread_name}] Limpando recursos...")
            try: # Libera câmera
                if cap is not None and cap.isOpened(): cap.release(); log_system_event(f"RTSP_RELEASED: {thread_name}", camera_id)
            except Exception as cap_e: log_error(thread_name, cap_e, "Erro ao liberar captura de vídeo")
            try: # Fecha janela OpenCV
                cfg = self.config.config.detection # Garante que cfg esteja definida
                if cfg.show_window: cv2.waitKey(10); cv2.destroyWindow(f"Camera {camera_id} - {self.backend_name}"); cv2.waitKey(10)
            except Exception as win_e: log_error(thread_name, win_e, "Erro ao fechar janela OpenCV")
            if session.end_time is None: session.end_session() # Garante end_time
            log_system_event(f"DETECTION_THREAD_ENDED: {thread_name}", camera_id); print(f"❌ [{thread_name}] Encerrada. Total: {session.detection_count}")
            if not stop_event.is_set(): # Limpa refs APENAS se a thread parou sozinha
                 log_system_event(f"THREAD_ENDED_UNEXPECTEDLY: {thread_name}, notifying UI and cleaning up.", camera_id)
                 self.trigger_ui_event("detection_stopped", camera_id)
                 self._active_sessions.pop(camera_id, None); self._stop_events.pop(camera_id, None); self._detection_threads.pop(camera_id, None)

    # (stop_detection e stop_all_detections permanecem os mesmos)
    def stop_detection(self, camera_id: int) -> bool:
        if camera_id not in self._stop_events and camera_id not in self._detection_threads: return False
        log_system_event(f"STOPPING_DETECTION_REQUESTED: Camera ID: {camera_id}", camera_id); print(f"⏳ [{threading.current_thread().name}] Solicitando parada da Câmera {camera_id}...")
        stop_event = self._stop_events.get(camera_id)
        if stop_event: stop_event.set()
        thread = self._detection_threads.get(camera_id); stopped_cleanly = False
        if thread and thread.is_alive():
            print(f"   Aguardando thread {thread.name} finalizar..."); thread.join(timeout=7.0)
            if thread.is_alive(): log_error("DetectionService", None, f"Thread {thread.name} não finalizou no timeout!")
            else: stopped_cleanly = True; print(f"   Thread {thread.name} finalizada.")
        else: stopped_cleanly = True
        self._active_sessions.pop(camera_id, None); self._stop_events.pop(camera_id, None); self._detection_threads.pop(camera_id, None)
        log_system_event(f"DETECTION_STOPPED_CONFIRMED: Camera ID: {camera_id}", camera_id); print(f"🛑 [{threading.current_thread().name}] Detecção da Câmera {camera_id} confirmada como parada.")
        if stopped_cleanly: self.trigger_ui_event("detection_stopped", camera_id) # Notifica UI
        return stopped_cleanly

    def stop_all_detections(self) -> None:
        camera_ids = list(self._detection_threads.keys())
        if not camera_ids: log_system_event("STOP_ALL_DETECTIONS: Nenhuma detecção ativa."); return
        log_system_event(f"STOPPING_ALL_DETECTIONS: Cameras {camera_ids}"); print(f"⏳ [{threading.current_thread().name}] Solicitando parada de todas as {len(camera_ids)} detecções...")
        threads_to_join = []
        for camera_id in camera_ids:
             stop_event = self._stop_events.get(camera_id);
             if stop_event: stop_event.set()
             thread = self._detection_threads.get(camera_id)
             if thread and thread.is_alive(): threads_to_join.append(thread)
        print(f"   Aguardando {len(threads_to_join)} threads finalizarem..."); [t.join(timeout=7.0) for t in threads_to_join]; print(f"   Threads finalizadas (ou timeout).")
        self._active_sessions.clear(); self._stop_events.clear(); self._detection_threads.clear()
        log_system_event("ALL_DETECTIONS_STOPPED_CONFIRMED"); print(f"🛑 [{threading.current_thread().name}] Todas as detecções confirmadas como paradas.")


    # (is_detection_active, get_detection_count, reset_count, get_session permanecem os mesmos)
    def is_detection_active(self, camera_id: int) -> bool:
        thread = self._detection_threads.get(camera_id); return thread is not None and thread.is_alive()
    def get_detection_count(self, camera_id: int) -> int:
        session = self._active_sessions.get(camera_id); return session.detection_count if session else 0
    def reset_count(self, camera_id: int) -> bool:
        session = self._active_sessions.get(camera_id)
        if session:
            session.detection_count = 0; print(f"⚠️ [{threading.current_thread().name}] Contagem resetada para Cam {camera_id}, mas estado interno da thread pode não ter sido limpo.")
            log_system_event(f"COUNT_RESET_CAMERA_{camera_id}", camera_id); self.trigger_ui_event("count_reset", camera_id); return True
        log_error("DetectionService", None, f"Tentativa de resetar contagem para câmera inativa: {camera_id}"); return False
    def get_session(self, camera_id: int) -> Optional[DetectionSession]:
        return self._active_sessions.get(camera_id)

    # (get_camera_status e get_backend_info permanecem os mesmos)
    def get_camera_status(self, camera_id: int) -> Optional[CameraStatus]:
        is_active = self.is_detection_active(camera_id); session = self._active_sessions.get(camera_id); thread_exists = camera_id in self._detection_threads
        if not thread_exists and not session: return None;
        if not is_active and not session and not thread_exists: return None
        count = session.detection_count if session else 0; start = session.start_time if session else None
        return CameraStatus(camera_id=camera_id, is_active=is_active, detection_count=count, session_start=start, backend=self.backend_name)
    def get_backend_info(self) -> dict:
        active_count = sum(1 for cam_id in self._detection_threads if self.is_detection_active(cam_id))
        return {'backend_name': self.backend_name, 'model_path': self.selected_model_path, 'device_args': self.selected_device_args, 'active_sessions': active_count}