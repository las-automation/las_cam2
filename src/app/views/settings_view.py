# Salve como: app/views/settings_view.py

import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, Optional
import math

# Importa o controller e componentes
from ..controllers.app_controller import AppController
from .components import (
    ModernButton, ModernEntry, ModernLabel,
    show_notification, show_error_dialog
)

# Importa o config_manager, CameraConfig e BackendOption
from ..config.settings import config_manager, CameraConfig, BackendOption


class SettingsView(ctk.CTkFrame):
    """Tela de Configurações do Sistema"""

    def __init__(self, master, controller: AppController, on_back: Callable):
        super().__init__(master, fg_color="#1C1C1C")

        self.controller = controller
        self.on_back = on_back
        self.current_selected_cam_id: Optional[int] = None
        self.camera_list_buttons: list[ModernButton] = []

        self._create_ui()

    def _create_ui(self):
        """Cria a interface principal da tela"""

        # --- Frame Superior (Título e Botões) ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(20, 10))

        ModernLabel(top_frame, text="Configurações", style="title").pack(side="left")

        ModernButton(
            top_frame, text="Voltar ao Dashboard", command=self.on_back,
            style="secondary", width=180
        ).pack(side="right", padx=10)

        ModernButton(
            top_frame, text="Salvar (Detecção/UI)", command=self._save_other_settings,
            style="primary", width=180
        ).pack(side="right")

        # --- Sistema de Abas ---
        self.tab_view = ctk.CTkTabview(self, fg_color="#242424")
        self.tab_view.pack(expand=True, fill="both", padx=20, pady=10)

        self.tab_view.add("Câmeras")
        self.tab_view.add("Detecção")
        self.tab_view.add("Geral & UI")

        # Cria o conteúdo de cada aba
        self._create_cameras_tab(self.tab_view.tab("Câmeras"))
        self._create_detection_tab(self.tab_view.tab("Detecção"))
        self._create_geral_tab(self.tab_view.tab("Geral & UI"))

    # --- Aba de Câmeras ---
    # (Nenhuma mudança nesta seção)
    def _create_cameras_tab(self, tab):
        """Cria a UI da aba de Câmeras"""
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=3)
        tab.grid_rowconfigure(0, weight=1)
        left_frame = ctk.CTkFrame(tab, fg_color="#2D2D2D", width=200)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        ModernLabel(left_frame, text="Câmeras", style="heading").pack(pady=10)
        self.camera_list_frame = ctk.CTkScrollableFrame(left_frame, fg_color="transparent")
        self.camera_list_frame.pack(expand=True, fill="both", padx=5)
        cam_buttons_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        cam_buttons_frame.pack(fill="x", pady=10, padx=5)
        ModernButton(cam_buttons_frame, text="Adicionar", command=self._add_camera, style="success").pack(side="left",
                                                                                                          expand=True,
                                                                                                          padx=5)
        self.remove_cam_btn = ModernButton(cam_buttons_frame, text="Remover", command=self._remove_camera,
                                           style="danger")
        self.remove_cam_btn.pack(side="right", expand=True, padx=5)
        right_frame = ctk.CTkFrame(tab, fg_color="#2D2D2D")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.camera_detail_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.camera_detail_frame.pack(expand=True, fill="both", padx=20, pady=20)
        ModernLabel(self.camera_detail_frame, text="ID: (Não editável)", style="body").pack(anchor="w", pady=(10, 0))
        self.cam_id_entry = ModernEntry(self.camera_detail_frame)
        self.cam_id_entry.configure(state="disabled")
        self.cam_id_entry.pack(fill="x", pady=(0, 10))
        ModernLabel(self.camera_detail_frame, text="Nome:", style="body").pack(anchor="w")
        self.cam_name_entry = ModernEntry(self.camera_detail_frame)
        self.cam_name_entry.pack(fill="x", pady=(0, 10))
        ModernLabel(self.camera_detail_frame, text="Fonte (URL RTSP ou Índice):", style="body").pack(anchor="w")
        self.cam_source_entry = ModernEntry(self.camera_detail_frame)
        self.cam_source_entry.pack(fill="x", pady=(0, 10))
        ModernLabel(self.camera_detail_frame, text="Descrição:", style="body").pack(anchor="w")
        self.cam_desc_entry = ModernEntry(self.camera_detail_frame)
        self.cam_desc_entry.pack(fill="x", pady=(0, 10))
        self.cam_enabled_check = ctk.CTkCheckBox(self.camera_detail_frame, text="Habilitada", font=("", 14))
        self.cam_enabled_check.pack(anchor="w", pady=15)
        self._disable_camera_form()

    # --- Aba de Detecção ---
    def _create_detection_tab(self, tab):
        """Cria a UI da aba de Detecção"""
        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        cfg = config_manager.config.detection

        # --- ADICIONADO: Seleção de Backend ---
        ModernLabel(frame, text="Backend de Detecção Preferido:", style="body").pack(anchor="w", pady=(10, 0))
        self.det_backend_combo = ctk.CTkComboBox(
            frame,
            values=["auto", "tensorrt", "directml", "openvino", "cpu"],
            font=("", 14),
            height=40
        )
        self.det_backend_combo.pack(fill="x", pady=(0, 15))
        # --- FIM ADIÇÃO ---

        # --- Caminhos dos Modelos ---
        ModernLabel(frame, text="Caminho do Modelo Base (.pt)", style="body").pack(anchor="w", pady=(10, 0))
        model_frame = ctk.CTkFrame(frame, fg_color="transparent")
        model_frame.pack(fill="x", pady=(0, 10))
        self.det_model_path = ModernEntry(model_frame)
        self.det_model_path.pack(side="left", expand=True, fill="x", padx=(0, 10))
        ModernButton(model_frame, text="Procurar...", width=100, command=lambda: self._browse_file(self.det_model_path),
                     style="secondary").pack(side="left")

        if hasattr(cfg, 'model_path_tensorrt'):
            ModernLabel(frame, text="Caminho do Modelo TensorRT (.engine)", style="body").pack(anchor="w", pady=(10, 0))
            model_frame_trt = ctk.CTkFrame(frame, fg_color="transparent")
            model_frame_trt.pack(fill="x", pady=(0, 10))
            self.det_model_path_tensorrt = ModernEntry(model_frame_trt)
            self.det_model_path_tensorrt.pack(side="left", expand=True, fill="x", padx=(0, 10))
            ModernButton(model_frame_trt, text="Procurar...", width=100,
                         command=lambda: self._browse_file(self.det_model_path_tensorrt), style="secondary").pack(
                side="left")

        if hasattr(cfg, 'model_path_openvino'):
            ModernLabel(frame, text="Caminho do Modelo OpenVINO (pasta)", style="body").pack(anchor="w", pady=(10, 0))
            model_frame_ov = ctk.CTkFrame(frame, fg_color="transparent")
            model_frame_ov.pack(fill="x", pady=(0, 10))
            self.det_model_path_openvino = ModernEntry(model_frame_ov)
            self.det_model_path_openvino.pack(side="left", expand=True, fill="x", padx=(0, 10))
            ModernButton(model_frame_ov, text="Procurar...", width=100,
                         command=lambda: self._browse_dir(self.det_model_path_openvino), style="secondary").pack(
                side="left")

        # --- Sliders e Checkboxes ---
        ModernLabel(frame, text="Threshold de Confiança:", style="body").pack(anchor="w", pady=(10, 0))
        conf_frame = ctk.CTkFrame(frame, fg_color="transparent")
        conf_frame.pack(fill="x", pady=(0, 10))
        self.det_conf_label = ModernLabel(conf_frame, text="0.50", style="body", width=40)
        self.det_conf_label.pack(side="left", padx=(0, 10))
        self.det_conf_slider = ctk.CTkSlider(conf_frame, from_=0.0, to=1.0, command=self._update_slider_label)
        self.det_conf_slider.pack(side="left", expand=True, fill="x")

        ModernLabel(frame, text="Posição da Linha de Contagem (Y):", style="body").pack(anchor="w", pady=(10, 0))
        line_frame = ctk.CTkFrame(frame, fg_color="transparent")
        line_frame.pack(fill="x", pady=(0, 10))
        self.det_line_label = ModernLabel(line_frame, text="0.50", style="body", width=40)
        self.det_line_label.pack(side="left", padx=(0, 10))
        self.det_line_slider = ctk.CTkSlider(line_frame, from_=0.0, to=1.0, command=self._update_slider_label)
        self.det_line_slider.pack(side="left", expand=True, fill="x")

        ModernLabel(frame, text="Largura da Linha de Contagem (%):", style="body").pack(anchor="w", pady=(10, 0))
        width_frame = ctk.CTkFrame(frame, fg_color="transparent")
        width_frame.pack(fill="x", pady=(0, 10))
        self.det_width_label = ModernLabel(width_frame, text="100%", style="body", width=40)
        self.det_width_label.pack(side="left", padx=(0, 10))
        self.det_width_slider = ctk.CTkSlider(width_frame, from_=0.0, to=1.0, command=self._update_slider_label)
        self.det_width_slider.pack(side="left", expand=True, fill="x")

        self.det_show_window = ctk.CTkCheckBox(frame, text="Exibir janela de detecção (debug)", font=("", 14))
        self.det_show_window.pack(anchor="w", pady=10)
        self.det_tracking = ctk.CTkCheckBox(frame, text="Habilitar rastreamento (tracking)", font=("", 14))
        self.det_tracking.pack(anchor="w", pady=10)

    # --- Aba Geral & UI ---
    # (Permanece igual)
    def _create_geral_tab(self, tab):
        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        frame.pack(expand=True, fill="both", padx=20, pady=20)
        ModernLabel(frame, text="Interface (UI)", style="heading").pack(anchor="w", pady=(10, 5))
        ModernLabel(frame, text="Tema:", style="body").pack(anchor="w", pady=(10, 0))
        self.ui_theme = ctk.CTkComboBox(frame, values=["dark", "light", "system"], font=("", 14), height=40)
        self.ui_theme.pack(fill="x", pady=(0, 10))
        ModernLabel(frame, text="Idioma:", style="body").pack(anchor="w", pady=(10, 0))
        self.ui_lang = ctk.CTkComboBox(frame, values=["pt_BR", "en_US"], font=("", 14), height=40)
        self.ui_lang.pack(fill="x", pady=(0, 10))

    # --- Lógica de Carregamento de Dados ---
    def load_settings_to_ui(self):
        """Carrega dados do config_manager para a UI"""
        cfg = config_manager.config

        # Carrega Aba de Detecção
        # --- ADICIONADO ---
        self.det_backend_combo.set(cfg.detection.preferred_backend)
        # --- FIM ADIÇÃO ---

        self.det_model_path.delete(0, "end");
        self.det_model_path.insert(0, cfg.detection.model_path)
        if hasattr(self, 'det_model_path_tensorrt'): self.det_model_path_tensorrt.delete(0,
                                                                                         "end"); self.det_model_path_tensorrt.insert(
            0, cfg.detection.model_path_tensorrt)
        if hasattr(self, 'det_model_path_openvino'): self.det_model_path_openvino.delete(0,
                                                                                         "end"); self.det_model_path_openvino.insert(
            0, cfg.detection.model_path_openvino)

        self.det_conf_slider.set(cfg.detection.confidence_threshold)
        self.det_line_slider.set(cfg.detection.count_line_position)
        self.det_width_slider.set(cfg.detection.count_line_width_percent)
        self._update_slider_label(None)

        if cfg.detection.show_window:
            self.det_show_window.select()
        else:
            self.det_show_window.deselect()
        if cfg.detection.tracking_enabled:
            self.det_tracking.select()
        else:
            self.det_tracking.deselect()

        # Carrega Aba Geral & UI
        self.ui_theme.set(cfg.ui.theme)
        self.ui_lang.set(cfg.ui.language)

        # Carrega Câmeras
        self._load_camera_list()
        if cfg.cameras:
            first_cam_id = sorted(int(k) for k in cfg.cameras.keys())[0]
            self._select_camera(first_cam_id)
        else:
            self._disable_camera_form()

    # (Métodos _load_camera_list, _select_camera, _populate_camera_form, _disable_camera_form, _enable_camera_form
    # permanecem os mesmos)
    def _load_camera_list(self):
        for btn in self.camera_list_buttons: btn.destroy()
        self.camera_list_buttons.clear()
        cameras = config_manager.config.cameras
        for cam_id, cam in sorted(cameras.items()):
            int_cam_id = int(cam_id)
            btn = ModernButton(self.camera_list_frame, text=f"{cam.id}: {cam.name}", style="outline",
                               fg_color="transparent", command=lambda c_id=int_cam_id: self._select_camera(c_id))
            btn.pack(fill="x", pady=2, padx=5)
            self.camera_list_buttons.append(btn)

    def _select_camera(self, cam_id: int):
        if self.current_selected_cam_id is not None and self.current_selected_cam_id != cam_id:
            self._save_current_camera_details()
        self.current_selected_cam_id = cam_id
        for btn in self.camera_list_buttons:
            if btn.cget("text").startswith(f"{cam_id}:"):
                btn.configure(fg_color="#4A90A4")
            else:
                btn.configure(fg_color="transparent")
        self._populate_camera_form(cam_id)

    def _populate_camera_form(self, cam_id: int):
        cam = config_manager.get_camera(cam_id)
        if not cam: self._disable_camera_form(); return
        self._enable_camera_form()
        self.cam_id_entry.configure(state="normal");
        self.cam_id_entry.delete(0, "end");
        self.cam_id_entry.insert(0, str(cam.id));
        self.cam_id_entry.configure(state="disabled")
        self.cam_name_entry.delete(0, "end");
        self.cam_name_entry.insert(0, cam.name)
        self.cam_source_entry.delete(0, "end");
        self.cam_source_entry.insert(0, getattr(cam, 'rtsp_url', ''))
        self.cam_desc_entry.delete(0, "end");
        self.cam_desc_entry.insert(0, cam.description)
        if cam.enabled:
            self.cam_enabled_check.select()
        else:
            self.cam_enabled_check.deselect()

    def _disable_camera_form(self):
        self.cam_id_entry.configure(state="normal");
        self.cam_id_entry.delete(0, "end");
        self.cam_id_entry.configure(state="disabled")
        self.cam_name_entry.delete(0, "end");
        self.cam_name_entry.configure(state="disabled")
        self.cam_source_entry.delete(0, "end");
        self.cam_source_entry.configure(state="disabled")
        self.cam_desc_entry.delete(0, "end");
        self.cam_desc_entry.configure(state="disabled")
        self.cam_enabled_check.deselect();
        self.cam_enabled_check.configure(state="disabled")
        self.remove_cam_btn.configure(state="disabled");
        self.current_selected_cam_id = None

    def _enable_camera_form(self):
        self.cam_name_entry.configure(state="normal");
        self.cam_source_entry.configure(state="normal")
        self.cam_desc_entry.configure(state="normal");
        self.cam_enabled_check.configure(state="normal")
        self.remove_cam_btn.configure(state="normal")

    # --- Lógica de Salvamento ---
    def _save_other_settings(self):
        """Salva as abas 'Detecção' e 'Geral' via config_manager"""
        try:
            cfg = config_manager.config

            # Salva Aba de Detecção
            # --- ADICIONADO ---
            cfg.detection.preferred_backend = self.det_backend_combo.get()  # Pega valor do ComboBox
            # --- FIM ADIÇÃO ---

            cfg.detection.model_path = self.det_model_path.get()
            if hasattr(self,
                       'det_model_path_tensorrt'): cfg.detection.model_path_tensorrt = self.det_model_path_tensorrt.get()
            if hasattr(self,
                       'det_model_path_openvino'): cfg.detection.model_path_openvino = self.det_model_path_openvino.get()

            cfg.detection.confidence_threshold = self.det_conf_slider.get()
            cfg.detection.count_line_position = self.det_line_slider.get()
            cfg.detection.count_line_width_percent = self.det_width_slider.get()
            cfg.detection.show_window = bool(self.det_show_window.get())
            cfg.detection.tracking_enabled = bool(self.det_tracking.get())

            # Salva Aba Geral & UI
            cfg.ui.theme = self.ui_theme.get()
            cfg.ui.language = self.ui_lang.get()

            # Salva no arquivo
            if config_manager._save_config():
                show_notification(self, "Configurações (Detecção/UI) salvas!", "success")
                # Recarrega a configuração no DetectionService
                if hasattr(self.controller, 'detection_service') and hasattr(self.controller.detection_service,
                                                                             '_get_best_backend'):
                    print("🔄 Recarregando backend no DetectionService...")
                    self.controller.detection_service._get_best_backend()
                    # Idealmente, as threads ativas deveriam ser reiniciadas aqui
                    # print("⚠️ Por favor, reinicie as detecções ativas para aplicar a mudança de backend.")
            else:
                show_error_dialog("Erro", "Não foi possível salvar as configurações de Detecção/UI.")

        except Exception as e:
            show_error_dialog("Erro Fatal", f"Ocorreu um erro ao salvar: {e}");
            import traceback;
            traceback.print_exc()

    # (Métodos _save_current_camera_details, _add_camera, _remove_camera permanecem os mesmos)
    def _save_current_camera_details(self):
        if self.current_selected_cam_id is None: return
        try:
            updates = {"name": self.cam_name_entry.get(), "rtsp_url": self.cam_source_entry.get(),
                       "description": self.cam_desc_entry.get(), "enabled": bool(self.cam_enabled_check.get())}
            if self.controller.update_camera_config(self.current_selected_cam_id, **updates):
                for btn in self.camera_list_buttons:
                    if btn.cget("text").startswith(f"{self.current_selected_cam_id}:"): btn.configure(
                        text=f"{self.current_selected_cam_id}: {updates['name']}"); break
            else:
                show_error_dialog("Erro", "Não foi possível salvar a câmera.")
        except Exception as e:
            show_error_dialog("Erro ao Salvar Câmera", f"Erro: {e}");
            import traceback;
            traceback.print_exc()

    def _add_camera(self):
        self._save_current_camera_details()
        new_id = 1
        if config_manager.config.cameras: new_id = max(int(k) for k in config_manager.config.cameras.keys()) + 1
        new_cam = CameraConfig(id=new_id, name=f"Nova Câmera {new_id}", rtsp_url="", description="Insira a descrição")
        if self.controller.add_camera(new_cam):
            self._load_camera_list(); self._select_camera(new_id)
        else:
            show_error_dialog("Erro", "Não foi possível adicionar a câmera.")

    def _remove_camera(self):
        if self.current_selected_cam_id is None: return
        cam_id_to_remove = self.current_selected_cam_id
        # TODO: Add confirmation popup
        if self.controller.remove_camera(cam_id_to_remove):
            show_notification(self, f"Câmera {cam_id_to_remove} removida.", "info")
            self._disable_camera_form();
            self._load_camera_list()
            cfg = config_manager.config
            if cfg.cameras: first_cam_id = sorted(int(k) for k in cfg.cameras.keys())[0]; self._select_camera(
                first_cam_id)
        else:
            show_error_dialog("Erro", f"Não foi possível remover a Câmera {cam_id_to_remove}.")

    # (Métodos _browse_file, _browse_dir permanecem os mesmos)
    def _browse_file(self, entry_widget: ctk.CTkEntry):
        filepath = filedialog.askopenfilename(title="Selecionar Modelo",
                                              filetypes=(("Modelos", "*.pt *.engine"), ("Todos os arquivos", "*.*")))
        if filepath: entry_widget.delete(0, "end"); entry_widget.insert(0, filepath)

    def _browse_dir(self, entry_widget: ctk.CTkEntry):
        dirpath = filedialog.askdirectory(title="Selecionar Pasta")
        if dirpath: entry_widget.delete(0, "end"); entry_widget.insert(0, dirpath)

    # (Método _update_slider_label permanece o mesmo)
    def _update_slider_label(self, value=None):
        conf_val = math.floor(self.det_conf_slider.get() * 100) / 100
        self.det_conf_label.configure(text=f"{conf_val:.2f}")
        line_val = math.floor(self.det_line_slider.get() * 100) / 100
        self.det_line_label.configure(text=f"{line_val:.2f}")
        width_val = int(self.det_width_slider.get() * 100)
        self.det_width_label.configure(text=f"{width_val}%")