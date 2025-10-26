"""
Tela de câmera individual refatorada
"""
import customtkinter as ctk
from typing import Callable, Optional
import cv2
from PIL import Image, ImageTk
from tkinter import messagebox

from ..models.entities import CargoType
from .components import (
    ModernButton, ModernLabel, show_notification, show_error_dialog
)


class CameraView(ctk.CTkToplevel):
    """Tela de câmera individual"""

    def __init__(self, master, camera_id: int, camera_name: str,
                 on_start_detection: Callable[[int, CargoType], None],
                 on_stop_detection: Callable[[int], None],
                 on_generate_report: Callable[[int], None]):
        super().__init__(master)

        self.camera_id = camera_id
        self.camera_name = camera_name
        self.on_start_detection = on_start_detection
        self.on_stop_detection = on_stop_detection
        self.on_generate_report = on_generate_report

        self.is_detection_active = False
        self.current_count = 0

        self._create_ui()
        self._center_window()

        # Intercepta o evento de fechar a janela
        self.protocol("WM_DELETE_WINDOW", self._on_closing_attempt)

    def _create_ui(self):
        """Cria interface do usuário"""
        self.title(f"Câmera {self.camera_id} - {self.camera_name}")
        self.configure(fg_color="#1C1C1C")
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)

        # Título
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="ew")

        self.title_label = ModernLabel(
            title_frame,
            text=f"Câmera {self.camera_id}",
            style="subtitle"
        )
        self.title_label.pack(side="left", padx=(0, 10))

        self.name_label = ModernLabel(
            title_frame,
            text=self.camera_name,
            style="caption"
        )
        self.name_label.pack(side="left")

        # Frame de vídeo
        self.video_frame = ctk.CTkFrame(self, fg_color="#2B2B2B", corner_radius=10)
        self.video_frame.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")

        self.video_label = ModernLabel(
            self.video_frame,
            text="Aguardando conexão...",
            style="body"
        )
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)

        # Controles (Contagem, Status, Tipo de Carga)
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.controls_frame.grid_columnconfigure(0, weight=1)
        self.controls_frame.grid_columnconfigure(1, weight=0)
        self.controls_frame.grid_columnconfigure(2, weight=1)

        # Info (Contagem + Status)
        info_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w")

        self.count_label = ModernLabel(
            info_frame,
            text="Contagem: 0",
            style="success",
            font=("", 16, "bold")
        )
        self.count_label.pack(side="left", padx=(0, 20))

        self.status_label = ModernLabel(
            info_frame,
            text="Status: Inativo",
            style="warning",
            font=("", 16)
        )
        self.status_label.pack(side="left")

        # Tipo de Carga
        ModernLabel(
            self.controls_frame,
            text="Tipo Carga:",
            font=("", 14)
        ).grid(row=0, column=1, padx=(10, 5), sticky="e")

        self.cargo_type_combo = ctk.CTkComboBox(
            self.controls_frame,
            values=CargoType.get_display_names(),
            width=200,
            height=35,
            font=("", 14)
        )
        self.cargo_type_combo.grid(row=0, column=2, padx=(0, 10), sticky="w")
        self.cargo_type_combo.set(CargoType.DESCONHECIDO.value)

        # Botões
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.buttons_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.detection_button = ModernButton(
            self.buttons_frame,
            text="Iniciar Detecção",
            style="success",
            command=self._handle_detection_toggle
        )
        self.detection_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.manual_report_button = ModernButton(
            self.buttons_frame,
            text="Relatório Manual*",
            style="primary",
            command=self._handle_generate_report,
            state="disabled"
        )
        self.manual_report_button.grid(row=0, column=1, padx=5, sticky="ew")

        self.reset_button = ModernButton(
            self.buttons_frame,
            text="Reset Contagem",
            style="warning",
            command=self._handle_reset_count,
            state="disabled"
        )
        self.reset_button.grid(row=0, column=2, padx=5, sticky="ew")

        self.close_button = ModernButton(
            self.buttons_frame,
            text="Fechar",
            style="secondary",
            command=self._on_closing_attempt
        )
        self.close_button.grid(row=0, column=3, padx=5, sticky="ew")

    def _center_window(self):
        """Centraliza a janela"""
        w, h = 1000, 700
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2)
        self.geometry(f'{w}x{h}+{int(x)}+{int(y)}')
        self.minsize(800, 600)

    def _handle_detection_toggle(self):
        """Alterna detecção, validando o tipo de carga ao iniciar"""
        if self.is_detection_active:
            # Para a detecção
            self.on_stop_detection(self.camera_id)
        else:
            # Valida tipo de carga antes de iniciar
            selected_cargo_str = self.cargo_type_combo.get()

            try:
                selected_cargo_type = CargoType(selected_cargo_str)

                # Valida se o tipo foi selecionado
                if selected_cargo_type == CargoType.DESCONHECIDO:
                    show_notification(
                        self,
                        "❌ Selecione um Tipo de Carga antes de iniciar!",
                        "error"
                    )
                    self.cargo_type_combo.focus_set()
                    return  # Impede o início da detecção

            except ValueError:
                # Tipo inválido
                show_notification(
                    self,
                    f"Tipo de carga inválido: {selected_cargo_str}",
                    "error"
                )
                return

            # Inicia detecção com tipo válido
            self.on_start_detection(self.camera_id, selected_cargo_type)

    def _handle_generate_report(self):
        """Gera relatório manualmente"""
        show_notification(
            self,
            "Geração manual de relatório ainda não implementada.",
            "info"
        )

    def _handle_reset_count(self):
        """Reseta contagem"""
        # TODO: Implementar reset no backend via controller
        self.update_count(0)
        show_notification(
            self,
            "Contagem resetada na UI (implementar backend)",
            "info"
        )

    def update_detection_status(self, is_active: bool):
        """
        Atualiza status da detecção e estado dos botões/widgets.
        CORRIGIDO: Remove 'style=' e usa 'fg_color=' e 'hover_color='
        """
        self.is_detection_active = is_active

        if is_active:
            # Detecção ATIVA - Botão vermelho (Parar)
            self.detection_button.configure(
                text="Parar Detecção",
                state="normal",
                fg_color="#C24E4E",  # Vermelho (perigo)
                hover_color="#E57373"
            )
            self.status_label.configure(
                text="Status: Ativo",
                text_color="#3BA776"  # Verde
            )
            self.reset_button.configure(state="normal")
            self.manual_report_button.configure(state="disabled")
            self.cargo_type_combo.configure(state="disabled")
        else:
            # Detecção INATIVA - Botão verde (Iniciar)
            self.detection_button.configure(
                text="Iniciar Detecção",
                state="normal",
                fg_color="#3BA776",  # Verde (sucesso)
                hover_color="#4FC48C"
            )
            self.status_label.configure(
                text="Status: Inativo",
                text_color="#E8A23B"  # Laranja/Amarelo
            )
            self.reset_button.configure(state="disabled")

            # Habilita relatório manual só se houver contagem
            manual_report_state = "normal" if self.current_count > 0 else "disabled"
            self.manual_report_button.configure(state=manual_report_state)

            self.cargo_type_combo.configure(state="normal")

    def update_count(self, count: int):
        """Atualiza contagem"""
        self.current_count = count
        self.count_label.configure(text=f"Contagem: {count}")

    def update_video_frame(self, frame):
        """Atualiza frame de vídeo"""
        try:
            # Valida frame
            if frame is None or frame.size == 0:
                self.video_label.configure(image=None, text="Frame inválido")
                self.video_label.image = None
                return

            # Converte BGR (OpenCV) para RGB (PIL)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_pil = Image.fromarray(frame_rgb)

            # Remove texto se existir
            if self.video_label.cget("text"):
                self.video_label.configure(text="")

            # Obtém dimensões do label
            label_width = self.video_label.winfo_width()
            label_height = self.video_label.winfo_height()

            # Se o label ainda não foi renderizado, agenda nova tentativa
            if label_width <= 1 or label_height <= 1:
                self.after(50, lambda: self.update_video_frame(frame))
                return

            # Calcula proporção para manter aspect ratio
            img_width, img_height = frame_pil.size

            if img_width > 0 and img_height > 0:
                ratio = min(label_width / img_width, label_height / img_height)
            else:
                ratio = 1

            new_width = max(1, int(img_width * ratio))
            new_height = max(1, int(img_height * ratio))

            # Redimensiona imagem
            frame_pil_resized = frame_pil.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )

            # Converte para PhotoImage
            frame_tk = ImageTk.PhotoImage(frame_pil_resized)

            # Atualiza label
            self.video_label.configure(image=frame_tk)
            self.video_label.image = frame_tk  # Mantém referência

        except Exception as e:
            error_text = f"Erro ao atualizar frame:\n{e}"
            self.video_label.configure(image=None, text=error_text)
            self.video_label.image = None
            print(f"[CameraView {self.camera_id}] {error_text}")

    def _on_closing_attempt(self):
        """
        Chamado quando o usuário tenta fechar a janela (X ou botão Fechar).
        Impede o fechamento se a detecção estiver ativa.
        """
        if self.is_detection_active:
            # Mostra aviso
            messagebox.showwarning(
                "Detecção Ativa",
                "Por favor, pare a detecção antes de fechar a janela.",
                parent=self
            )
            # Não fecha a janela
        else:
            # Permite fechar
            self.destroy()  # Aciona o callback do ScreenManager