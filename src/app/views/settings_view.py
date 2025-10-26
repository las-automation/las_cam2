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
        # --- Frame Superior ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(20, 10))
        ModernLabel(top_frame, text="Configurações", style="title").pack(side="left")
        ModernButton(top_frame, text="Voltar ao Dashboard", command=self.on_back, style="secondary", width=180).pack(side="right", padx=10)
        ModernButton(top_frame, text="Salvar Tudo", command=self._save_all_settings, style="primary", width=180).pack(side="right") # Usa _save_all_settings

        # --- Abas ---
        self.tab_view = ctk.CTkTabview(self, fg_color="#242424")
        self.tab_view.pack(expand=True, fill="both", padx=20, pady=10)
        self.tab_view.add("Câmeras")
        self.tab_view.add("Detecção")
        self.tab_view.add("Geral & UI")
        self._create_cameras_tab(self.tab_view.tab("Câmeras"))
        self._create_detection_tab(self.tab_view.tab("Detecção"))
        self._create_geral_tab(self.tab_view.tab("Geral & UI"))

    # --- Aba de Câmeras ---
    def _create_cameras_tab(self, tab):
        """Cria a UI da aba de Câmeras"""
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=3)
        tab.grid_rowconfigure(0, weight=1)
        # Esquerda
        left_frame = ctk.CTkFrame(tab, fg_color="#2D2D2D", width=200); left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        ModernLabel(left_frame, text="Câmeras", style="heading").pack(pady=10)
        self.camera_list_frame = ctk.CTkScrollableFrame(left_frame, fg_color="transparent"); self.camera_list_frame.pack(expand=True, fill="both", padx=5)
        cam_buttons_frame = ctk.CTkFrame(left_frame, fg_color="transparent"); cam_buttons_frame.pack(fill="x", pady=10, padx=5)
        ModernButton(cam_buttons_frame, text="Adicionar", command=self._add_camera, style="success").pack(side="left", expand=True, padx=5)
        self.remove_cam_btn = ModernButton(cam_buttons_frame, text="Remover", command=self._remove_camera, style="danger"); self.remove_cam_btn.pack(side="right", expand=True, padx=5)
        # Direita
        right_frame = ctk.CTkFrame(tab, fg_color="#2D2D2D"); right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.camera_detail_frame = ctk.CTkFrame(right_frame, fg_color="transparent"); self.camera_detail_frame.pack(expand=True, fill="both", padx=20, pady=20)
        ModernLabel(self.camera_detail_frame, text="ID: (Não editável)", style="body").pack(anchor="w", pady=(10, 0))
        self.cam_id_entry = ModernEntry(self.camera_detail_frame); self.cam_id_entry.configure(state="disabled"); self.cam_id_entry.pack(fill="x", pady=(0, 10))
        ModernLabel(self.camera_detail_frame, text="Nome:", style="body").pack(anchor="w")
        self.cam_name_entry = ModernEntry(self.camera_detail_frame); self.cam_name_entry.pack(fill="x", pady=(0, 10))
        ModernLabel(self.camera_detail_frame, text="Fonte (URL RTSP ou Índice Webcam):", style="body").pack(anchor="w")
        self.cam_source_entry = ModernEntry(self.camera_detail_frame); self.cam_source_entry.pack(fill="x", pady=(0, 10))
        ModernLabel(self.camera_detail_frame, text="Descrição:", style="body").pack(anchor="w")
        self.cam_desc_entry = ModernEntry(self.camera_detail_frame); self.cam_desc_entry.pack(fill="x", pady=(0, 10))
        self.cam_enabled_check = ctk.CTkCheckBox(self.camera_detail_frame, text="Habilitada", font=("", 14)); self.cam_enabled_check.pack(anchor="w", pady=15)
        self._disable_camera_form()

    # --- Aba de Detecção ---
    def _create_detection_tab(self, tab):
        """Cria a UI da aba de Detecção"""
        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent"); frame.pack(expand=True, fill="both", padx=20, pady=20)
        cfg = config_manager.config.detection
        ModernLabel(frame, text="Backend de Detecção Preferido:", style="body").pack(anchor="w", pady=(10, 0))
        self.det_backend_combo = ctk.CTkComboBox(frame, values=["auto", "tensorrt", "directml", "openvino", "cpu"], font=("", 14), height=40)
        self.det_backend_combo.pack(fill="x", pady=(0, 15))
        ModernLabel(frame, text="Caminho do Modelo Base (.pt)", style="body").pack(anchor="w", pady=(10, 0))
        model_frame = ctk.CTkFrame(frame, fg_color="transparent"); model_frame.pack(fill="x", pady=(0, 10))
        self.det_model_path = ModernEntry(model_frame); self.det_model_path.pack(side="left", expand=True, fill="x", padx=(0, 10))
        ModernButton(model_frame, text="Procurar...", width=100, command=lambda: self._browse_file(self.det_model_path), style="secondary").pack(side="left")
        if hasattr(cfg, 'model_path_tensorrt'):
            ModernLabel(frame, text="Caminho do Modelo TensorRT (.engine)", style="body").pack(anchor="w", pady=(10, 0))
            model_frame_trt = ctk.CTkFrame(frame, fg_color="transparent"); model_frame_trt.pack(fill="x", pady=(0, 10))
            self.det_model_path_tensorrt = ModernEntry(model_frame_trt); self.det_model_path_tensorrt.pack(side="left", expand=True, fill="x", padx=(0, 10))
            ModernButton(model_frame_trt, text="Procurar...", width=100, command=lambda: self._browse_file(self.det_model_path_tensorrt), style="secondary").pack(side="left")
        if hasattr(cfg, 'model_path_openvino'):
            ModernLabel(frame, text="Caminho do Modelo OpenVINO (pasta)", style="body").pack(anchor="w", pady=(10, 0))
            model_frame_ov = ctk.CTkFrame(frame, fg_color="transparent"); model_frame_ov.pack(fill="x", pady=(0, 10))
            self.det_model_path_openvino = ModernEntry(model_frame_ov); self.det_model_path_openvino.pack(side="left", expand=True, fill="x", padx=(0, 10))
            ModernButton(model_frame_ov, text="Procurar...", width=100, command=lambda: self._browse_dir(self.det_model_path_openvino), style="secondary").pack(side="left")
        ModernLabel(frame, text="Threshold de Confiança:", style="body").pack(anchor="w", pady=(10, 0))
        conf_frame = ctk.CTkFrame(frame, fg_color="transparent"); conf_frame.pack(fill="x", pady=(0, 10))
        self.det_conf_label = ModernLabel(conf_frame, text="0.50", style="body", width=40); self.det_conf_label.pack(side="left", padx=(0, 10))
        self.det_conf_slider = ctk.CTkSlider(conf_frame, from_=0.0, to=1.0, command=self._update_slider_label); self.det_conf_slider.pack(side="left", expand=True, fill="x")
        ModernLabel(frame, text="Posição da Linha de Contagem (Y):", style="body").pack(anchor="w", pady=(10, 0))
        line_frame = ctk.CTkFrame(frame, fg_color="transparent"); line_frame.pack(fill="x", pady=(0, 10))
        self.det_line_label = ModernLabel(line_frame, text="0.50", style="body", width=40); self.det_line_label.pack(side="left", padx=(0, 10))
        self.det_line_slider = ctk.CTkSlider(line_frame, from_=0.0, to=1.0, command=self._update_slider_label); self.det_line_slider.pack(side="left", expand=True, fill="x")
        ModernLabel(frame, text="Largura da Linha de Contagem (%):", style="body").pack(anchor="w", pady=(10, 0))
        width_frame = ctk.CTkFrame(frame, fg_color="transparent"); width_frame.pack(fill="x", pady=(0, 10))
        self.det_width_label = ModernLabel(width_frame, text="100%", style="body", width=40); self.det_width_label.pack(side="left", padx=(0, 10))
        self.det_width_slider = ctk.CTkSlider(width_frame, from_=0.0, to=1.0, command=self._update_slider_label); self.det_width_slider.pack(side="left", expand=True, fill="x")
        self.det_show_window = ctk.CTkCheckBox(frame, text="Exibir janela de detecção (debug)", font=("", 14)); self.det_show_window.pack(anchor="w", pady=10)
        self.det_tracking = ctk.CTkCheckBox(frame, text="Habilitar rastreamento (tracking)", font=("", 14)); self.det_tracking.pack(anchor="w", pady=10)

    # --- Aba Geral & UI ---
    def _create_geral_tab(self, tab):
        """Cria a UI da aba Geral"""
        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent"); frame.pack(expand=True, fill="both", padx=20, pady=20)
        ModernLabel(frame, text="Interface (UI)", style="heading").pack(anchor="w", pady=(10, 5))
        ModernLabel(frame, text="Tema:", style="body").pack(anchor="w", pady=(10, 0))
        self.ui_theme = ctk.CTkComboBox(frame, values=["dark", "light", "system"], font=("", 14), height=40); self.ui_theme.pack(fill="x", pady=(0, 10))
        ModernLabel(frame, text="Idioma:", style="body").pack(anchor="w", pady=(10, 0))
        self.ui_lang = ctk.CTkComboBox(frame, values=["pt_BR", "en_US"], font=("", 14), height=40); self.ui_lang.pack(fill="x", pady=(0, 10))

    # --- Lógica de Carregamento de Dados (CORRIGIDO) ---
    def load_settings_to_ui(self):
        """Carrega dados do config_manager para a UI"""
        cfg = config_manager.config
        self.det_backend_combo.set(cfg.detection.preferred_backend)
        self.det_model_path.delete(0, "end")
        self.det_model_path.insert(0, cfg.detection.model_path)
        if hasattr(self, 'det_model_path_tensorrt') and hasattr(cfg.detection, 'model_path_tensorrt'):
            self.det_model_path_tensorrt.delete(0, "end")
            self.det_model_path_tensorrt.insert(0, cfg.detection.model_path_tensorrt)
        if hasattr(self, 'det_model_path_openvino') and hasattr(cfg.detection, 'model_path_openvino'):
            self.det_model_path_openvino.delete(0, "end")
            self.det_model_path_openvino.insert(0, cfg.detection.model_path_openvino)
        self.det_conf_slider.set(cfg.detection.confidence_threshold)
        self.det_line_slider.set(cfg.detection.count_line_position)
        self.det_width_slider.set(cfg.detection.count_line_width_percent)
        self._update_slider_label(None)
        if cfg.detection.show_window: self.det_show_window.select()
        else: self.det_show_window.deselect()
        if cfg.detection.tracking_enabled: self.det_tracking.select()
        else: self.det_tracking.deselect()
        self.ui_theme.set(cfg.ui.theme)
        self.ui_lang.set(cfg.ui.language)
        self._load_camera_list()
        if cfg.cameras:
            try: # Adiciona try/except para caso cameras esteja vazio após filtragem
                 first_cam_id = sorted(int(k) for k in cfg.cameras.keys())[0]
                 self._select_camera(first_cam_id)
            except IndexError:
                 self._disable_camera_form() # Nenhuma câmera válida
        else: self._disable_camera_form()

    # (Método _load_camera_list permanece igual)
    def _load_camera_list(self):
        for btn in self.camera_list_buttons: btn.destroy(); self.camera_list_buttons.clear()
        cameras = config_manager.config.cameras
        for cam_id, cam in sorted(cameras.items()):
            int_cam_id = int(cam_id); btn = ModernButton(self.camera_list_frame, text=f"{cam.id}: {cam.name}", style="outline", fg_color="transparent", command=lambda c_id=int_cam_id: self._select_camera(c_id))
            btn.pack(fill="x", pady=2, padx=5); self.camera_list_buttons.append(btn)

    # (Método _select_camera permanece igual)
    def _select_camera(self, cam_id: int):
        if self.current_selected_cam_id is not None and self.current_selected_cam_id != cam_id: self._save_current_camera_details()
        self.current_selected_cam_id = cam_id
        for btn in self.camera_list_buttons:
            if btn.cget("text").startswith(f"{cam_id}:"): btn.configure(fg_color="#4A90A4")
            else: btn.configure(fg_color="transparent")
        self._populate_camera_form(cam_id)

    # --- MÉTODO _populate_camera_form (CORRIGIDO) ---
    def _populate_camera_form(self, cam_id: int):
        """Preenche o formulário com dados da câmera selecionada"""
        cam = config_manager.get_camera(cam_id)
        if not cam:
            self._disable_camera_form()
            return

        self._enable_camera_form()
        # Popula os campos um por um
        self.cam_id_entry.configure(state="normal")
        self.cam_id_entry.delete(0, "end")
        self.cam_id_entry.insert(0, str(cam.id))
        self.cam_id_entry.configure(state="disabled")
        self.cam_name_entry.delete(0, "end")
        self.cam_name_entry.insert(0, cam.name)
        self.cam_source_entry.delete(0, "end")
        self.cam_source_entry.insert(0, getattr(cam, 'source', ''))
        self.cam_desc_entry.delete(0, "end")
        self.cam_desc_entry.insert(0, cam.description)
        if cam.enabled: self.cam_enabled_check.select()
        else: self.cam_enabled_check.deselect()
    # --- FIM CORREÇÃO ---

    # --- MÉTODO _disable_camera_form (CORRIGIDO) ---
    def _disable_camera_form(self):
        """Desabilita o formulário de detalhes da câmera"""
        self.cam_id_entry.configure(state="normal")
        self.cam_id_entry.delete(0, "end")
        self.cam_id_entry.configure(state="disabled")
        self.cam_name_entry.configure(state="normal") # Precisa estar normal para limpar
        self.cam_name_entry.delete(0, "end")
        self.cam_name_entry.configure(state="disabled")
        self.cam_source_entry.configure(state="normal")
        self.cam_source_entry.delete(0, "end")
        self.cam_source_entry.configure(state="disabled")
        self.cam_desc_entry.configure(state="normal")
        self.cam_desc_entry.delete(0, "end")
        self.cam_desc_entry.configure(state="disabled")
        self.cam_enabled_check.deselect()
        self.cam_enabled_check.configure(state="disabled")
        self.remove_cam_btn.configure(state="disabled")
        self.current_selected_cam_id = None
    # --- FIM CORREÇÃO ---

    # --- MÉTODO _enable_camera_form (CORRIGIDO) ---
    def _enable_camera_form(self):
        """Habilita o formulário de detalhes da câmera"""
        self.cam_name_entry.configure(state="normal")
        self.cam_source_entry.configure(state="normal")
        self.cam_desc_entry.configure(state="normal")
        self.cam_enabled_check.configure(state="normal")
        self.remove_cam_btn.configure(state="normal")
    # --- FIM CORREÇÃO ---

    # --- Lógica de Salvamento ---
    # --- MÉTODO _save_all_settings (CORRIGIDO) ---
    def _save_all_settings(self):
        """Salva TODAS as configurações: Câmera atual, Detecção e Geral."""
        try:
            # --- ADICIONADO: Salva a câmera atual PRIMEIRO ---
            print("INFO: Tentando salvar detalhes da câmera atual...")
            self._save_current_camera_details() # Chama o método que usa o controller
            # --- FIM ADIÇÃO ---

            # Pega a instância atualizada do config (pode ter mudado ao salvar câmera)
            cfg = config_manager.config # Recarrega a referência

            # Salva Aba de Detecção
            print("INFO: Tentando salvar configurações de Detecção...")
            cfg.detection.preferred_backend = self.det_backend_combo.get()
            cfg.detection.model_path = self.det_model_path.get()
            if hasattr(self, 'det_model_path_tensorrt') and hasattr(cfg.detection, 'model_path_tensorrt'):
                cfg.detection.model_path_tensorrt = self.det_model_path_tensorrt.get()
            if hasattr(self, 'det_model_path_openvino') and hasattr(cfg.detection, 'model_path_openvino'):
                cfg.detection.model_path_openvino = self.det_model_path_openvino.get()
            cfg.detection.confidence_threshold = self.det_conf_slider.get()
            cfg.detection.count_line_position = self.det_line_slider.get()
            cfg.detection.count_line_width_percent = self.det_width_slider.get()
            cfg.detection.show_window = bool(self.det_show_window.get())
            cfg.detection.tracking_enabled = bool(self.det_tracking.get())

            # Salva Aba Geral & UI
            print("INFO: Tentando salvar configurações de UI...")
            cfg.ui.theme = self.ui_theme.get()
            cfg.ui.language = self.ui_lang.get()

            # Salva TODAS as alterações no arquivo (usando método privado do config_manager)
            print("INFO: Chamando config_manager._save_config() para Detecção/UI...")
            if config_manager._save_config(): # Chama o método privado
                show_notification(self, "Todas as configurações foram salvas!", "success")
                # Recarrega config no DetectionService APÓS salvar
                if hasattr(self.controller, 'detection_service') and hasattr(self.controller.detection_service, '_get_best_backend'):
                     print("🔄 Recarregando configuração e backend no DetectionService...")
                     config_manager.reload() # Recarrega do disco
                     self.controller.detection_service._get_best_backend() # Reavalia backend
                     print("⚠️ Backend reavaliado. Pode ser necessário reiniciar detecções ativas.")
            else:
                show_error_dialog("Erro", "Não foi possível salvar as configurações de Detecção/UI no arquivo.")

        except Exception as e:
            show_error_dialog("Erro Fatal", f"Ocorreu um erro ao salvar configurações: {e}")
            import traceback; traceback.print_exc()
    # --- FIM CORREÇÃO ---

    # --- MÉTODO _save_current_camera_details (CORRIGIDO) ---
    def _save_current_camera_details(self):
        """Salva os dados do formulário da câmera atual via CONTROLLER"""
        if self.current_selected_cam_id is None:
            return # Nada selecionado, nada a fazer

        print(f"INFO: Salvando detalhes para Câmera ID: {self.current_selected_cam_id}")
        try:
            updates = {
                "name": self.cam_name_entry.get(),
                "source": self.cam_source_entry.get(), # Usa 'source'
                "description": self.cam_desc_entry.get(),
                "enabled": bool(self.cam_enabled_check.get())
            }
            # Chama o controller, que chama config_manager.update_camera_config
            # O update_camera_config já chama _save_config internamente
            if self.controller.update_camera_config(self.current_selected_cam_id, **updates):
                print(f"INFO: Câmera ID {self.current_selected_cam_id} salva via controller.")
                # Atualiza nome na lista UI
                for btn in self.camera_list_buttons:
                    if btn.cget("text").startswith(f"{self.current_selected_cam_id}:"):
                        btn.configure(text=f"{self.current_selected_cam_id}: {updates['name']}")
                        break
            else:
                 # Erro já logado pelo Controller/ConfigManager
                 show_error_dialog("Erro", f"Não foi possível salvar as alterações da Câmera {self.current_selected_cam_id}.")
        except Exception as e:
             show_error_dialog("Erro", f"Erro inesperado ao salvar Câmera {self.current_selected_cam_id}: {e}")
             import traceback; traceback.print_exc()
    # --- FIM CORREÇÃO ---


    # --- MÉTODO _add_camera (CORRIGIDO) ---
    def _add_camera(self):
        """Adiciona uma nova câmera via CONTROLLER"""
        # Salva a câmera atual ANTES de adicionar uma nova, para não perder edições
        self._save_current_camera_details()

        new_id = 0 # Default inicial
        try:
             # Calcula próximo ID disponível
             if config_manager.config.cameras:
                 new_id = max(int(k) for k in config_manager.config.cameras.keys()) + 1
             else:
                  new_id = 0 # Primeira câmera será ID 0 (webcam padrão)
        except ValueError:
             # Se houver chaves não numéricas (improvável), define um ID alto
             new_id = 999
             log_error("SettingsView", None, "Erro ao calcular próximo ID de câmera, usando 999.")


        # Cria nova config com source='0' (webcam) por padrão
        new_cam = CameraConfig(id=new_id, name=f"Nova Câmera {new_id}", source="0", description="Insira a descrição")

        if self.controller.add_camera(new_cam):
            self._load_camera_list() # Recarrega lista da UI
            self._select_camera(new_id) # Seleciona a nova câmera
        else:
            show_error_dialog("Erro", "Não foi possível adicionar a câmera.")
    # --- FIM CORREÇÃO ---

        # --- MÉTODO _remove_camera CORRIGIDO E OTIMIZADO ---
    def _remove_camera(self):
            """Remove a câmera selecionada via CONTROLLER e atualiza a UI diretamente."""
            if self.current_selected_cam_id is None:
                show_notification(self, "Selecione uma câmera para remover.", "warning")
                return

            cam_id_to_remove = self.current_selected_cam_id
            cam_name = f"Câmera {cam_id_to_remove}"  # Nome genérico
            cam = config_manager.get_camera(cam_id_to_remove)
            if cam: cam_name = cam.name

            # Adiciona confirmação
            from tkinter import messagebox
            confirm = messagebox.askyesno(
                "Confirmar Remoção",
                f"Tem certeza que deseja remover a '{cam_name}' (ID: {cam_id_to_remove})?\nEsta ação não pode ser desfeita.",
                parent=self
            )
            if not confirm:
                return  # Usuário cancelou

            # Chama controller para remover do backend (config.json)
            if self.controller.remove_camera(cam_id_to_remove):
                show_notification(self, f"Câmera {cam_id_to_remove} removida.", "info")

                # --- ATUALIZAÇÃO DIRETA DA UI ---
                button_to_remove = None
                # Encontra o botão correspondente na lista da UI
                for i, btn in enumerate(self.camera_list_buttons):
                    # Compara o ID no texto do botão
                    if btn.cget("text").startswith(f"{cam_id_to_remove}:"):
                        button_to_remove = btn
                        # Remove a referência da nossa lista interna
                        del self.camera_list_buttons[i]
                        break  # Sai do loop após encontrar

                # Destrói o widget do botão encontrado
                if button_to_remove:
                    button_to_remove.destroy()
                else:
                    # Se não encontrou o botão (estranho), recarrega a lista como fallback
                    print(f"AVISO: Botão para câmera {cam_id_to_remove} não encontrado na UI, recarregando lista.")
                    self._load_camera_list()
                # --- FIM ATUALIZAÇÃO DIRETA ---

                self._disable_camera_form()  # Limpa e desabilita o formulário da direita

                # Seleciona a próxima câmera (se houver alguma restante)
                cfg = config_manager.config
                if self.camera_list_buttons:  # Verifica se a lista de botões não está vazia
                    # Tenta pegar o ID da primeira câmera restante na lista da UI
                    try:
                        next_cam_id_text = self.camera_list_buttons[0].cget("text").split(":")[0]
                        next_cam_id = int(next_cam_id_text)
                        self._select_camera(next_cam_id)
                    except (IndexError, ValueError):
                        print("Erro ao tentar selecionar a próxima câmera após remoção.")
                        # Fallback: Recarrega a lista inteira se falhar ao selecionar
                        self._load_camera_list()
                        if cfg.cameras:
                            first_cam_id = sorted(int(k) for k in cfg.cameras.keys())[0]
                            self._select_camera(first_cam_id)

                # else: Nenhuma câmera restante, o formulário já foi desabilitado

            else:
                show_error_dialog("Erro", f"Não foi possível remover a Câmera {cam_id_to_remove} (ver logs).")
        # --- FIM CORREÇÃO ---


    # --- Métodos Auxiliares (CORRIGIDOS) ---
    def _browse_file(self, entry_widget: ctk.CTkEntry):
        """Abre diálogo para selecionar um ARQUIVO"""
        filepath = filedialog.askopenfilename(title="Selecionar Modelo", filetypes=(("Modelos", "*.pt *.engine"), ("Todos os arquivos", "*.*")))
        if filepath:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, filepath)

    def _browse_dir(self, entry_widget: ctk.CTkEntry):
        """Abre diálogo para selecionar uma PASTA"""
        dirpath = filedialog.askdirectory(title="Selecionar Pasta")
        if dirpath:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, dirpath)

    def _update_slider_label(self, value=None):
        """Atualiza os labels dos sliders de valor"""
        # Usa try/except para evitar erros se widgets ainda não foram criados
        try:
            conf_val = math.floor(self.det_conf_slider.get() * 100) / 100
            self.det_conf_label.configure(text=f"{conf_val:.2f}")
        except Exception: pass
        try:
            line_val = math.floor(self.det_line_slider.get() * 100) / 100
            self.det_line_label.configure(text=f"{line_val:.2f}")
        except Exception: pass
        try:
            width_val = int(self.det_width_slider.get() * 100)
            self.det_width_label.configure(text=f"{width_val}%")
        except Exception: pass
    # --- FIM CORREÇÃO ---