"""
Tela de câmera individual refatorada
"""
import customtkinter as ctk
from typing import Callable, Optional
import cv2
from PIL import Image, ImageTk
from tkinter import messagebox

# Importa o Enum para o ComboBox e Type Hinting
from ..models.entities import CargoType
from .components import (
    ModernButton, ModernLabel, show_notification, show_error_dialog
)


class CameraView(ctk.CTkToplevel):
    """Tela de câmera individual"""

    def __init__(self, master, camera_id: int, camera_name: str,
                 on_start_detection: Callable[[int, CargoType], None],
                 on_stop_detection: Callable[[int], None],
                 # --- MODIFICADO: Callback para Finalizar/Enviar ---
                 on_finalize_session: Callable[[int], None]):
        # --- FIM MODIFICAÇÃO ---
        super().__init__(master)

        self.camera_id = camera_id
        self.camera_name = camera_name
        self.on_start_detection = on_start_detection
        self.on_stop_detection = on_stop_detection
        # --- MODIFICADO: Salva o novo callback ---
        self.on_finalize_session = on_finalize_session
        # --- FIM MODIFICAÇÃO ---

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
        self.grid_rowconfigure(1, weight=1)  # Vídeo expande
        self.grid_rowconfigure(2, weight=0)  # Controles
        self.grid_rowconfigure(3, weight=0)  # Botões inferiores

        # Título
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.title_label = ModernLabel(title_frame, text=f"Câmera {self.camera_id}", style="subtitle")
        self.title_label.pack(side="left", padx=(0, 10))
        self.name_label = ModernLabel(title_frame, text=self.camera_name, style="caption")
        self.name_label.pack(side="left")

        # Frame de vídeo
        self.video_frame = ctk.CTkFrame(self, fg_color="#2B2B2B", corner_radius=10)
        self.video_frame.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")
        self.video_label = ModernLabel(self.video_frame, text="Aguardando conexão...", style="body")
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)

        # Controles (Contagem, Status, Tipo de Carga)
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.controls_frame.grid_columnconfigure(0, weight=1)  # Info
        self.controls_frame.grid_columnconfigure(1, weight=0)  # Label Tipo
        self.controls_frame.grid_columnconfigure(2, weight=1)  # ComboBox Tipo

        # Info (Contagem + Status)
        info_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w")
        self.count_label = ModernLabel(info_frame, text="Contagem: 0", style="success", font=("", 16, "bold"))
        self.count_label.pack(side="left", padx=(0, 20))
        self.status_label = ModernLabel(info_frame, text="Status: Inativo", style="warning", font=("", 16))
        self.status_label.pack(side="left")

        # Tipo de Carga
        ModernLabel(self.controls_frame, text="Tipo Carga:", font=("", 14)).grid(row=0, column=1, padx=(10, 5),
                                                                                 sticky="e")
        self.cargo_type_combo = ctk.CTkComboBox(
            self.controls_frame, values=CargoType.get_display_names(),
            width=200, height=35, font=("", 14)
        )
        self.cargo_type_combo.grid(row=0, column=2, padx=(0, 10), sticky="w")
        self.cargo_type_combo.set(CargoType.DESCONHECIDO.value)

        # Botões
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.buttons_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.detection_button = ModernButton(
            self.buttons_frame, text="Iniciar Detecção", style="success",
            command=self._handle_detection_toggle
        )
        self.detection_button.grid(row=0, column=0, padx=5, sticky="ew")

        # --- MODIFICADO: Botão Finalizar Sessão (Relatório + API) ---
        self.finalize_button = ModernButton(
            self.buttons_frame,
            text="Finalizar e Enviar",  # Novo texto
            style="primary",
            command=self._handle_finalize_session,  # Novo método
            state="disabled"  # Começa desabilitado
        )
        self.finalize_button.grid(row=0, column=1, padx=5, sticky="ew")
        # --- FIM MODIFICAÇÃO ---

        self.reset_button = ModernButton(
            self.buttons_frame, text="Reset Contagem", style="warning",
            command=self._handle_reset_count, state="disabled"
        )
        self.reset_button.grid(row=0, column=2, padx=5, sticky="ew")

        self.close_button = ModernButton(
            self.buttons_frame, text="Fechar", style="secondary",
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
            # Apenas para a detecção. Não gera relatório/envia API.
            self.on_stop_detection(self.camera_id)
        else:
            # Valida tipo de carga antes de iniciar
            selected_cargo_str = self.cargo_type_combo.get()
            try:
                selected_cargo_type = CargoType(selected_cargo_str)
                # Valida se o tipo foi selecionado
                if selected_cargo_type == CargoType.DESCONHECIDO:
                    show_notification(self, "❌ Selecione um Tipo de Carga antes de iniciar!", "error")
                    self.cargo_type_combo.focus_set()
                    return  # Impede o início
            except ValueError:
                show_notification(self, f"Tipo de carga inválido: {selected_cargo_str}", "error")
                return  # Impede o início

            # Inicia detecção com tipo válido
            self.on_start_detection(self.camera_id, selected_cargo_type)

    # --- MODIFICADO: Renomeado de _handle_generate_report ---
    def _handle_finalize_session(self):
        """
        Chamado pelo botão "Finalizar e Enviar".
        Gera o relatório PDF e envia para a API.
        """
        if self.is_detection_active:
            show_error_dialog("Erro", "Pare a detecção antes de finalizar e enviar o relatório.", parent=self)
            return

        # Confirmação do usuário
        count = self.get_current_count()
        msg = f"Você confirma o envio da contagem final de {count}?"
        if count == 0:
            msg = "A contagem é 0. Deseja finalizar e enviar mesmo assim?"

        confirm = messagebox.askyesno("Confirmar Envio", msg, parent=self)
        if not confirm:
            return  # Usuário cancelou

        # Desabilita botão para evitar cliques duplos
        self.finalize_button.configure(state="disabled", text="Enviando...")

        # Chama o callback do controller
        self.on_finalize_session(self.camera_id)

        # O estado do botão será reabilitado pelo update_detection_status
        # ou por um callback de sucesso/falha do envio.
        # Por ora, reabilitamos após um tempo (simples)
        self.after(3000, self._reenable_finalize_button)

    def _reenable_finalize_button(self):
        """Reabilita o botão Finalizar após uma tentativa de envio."""
        # Garante que só reabilita se a detecção estiver parada
        if not self.is_detection_active:
            self.finalize_button.configure(state="normal", text="Finalizar e Enviar")

    # --- FIM MODIFICAÇÃO ---

    def _handle_reset_count(self):
        """Reseta contagem"""
        # TODO: Implementar chamada ao controller para resetar no backend
        # self.controller.reset_detection_count(self.camera_id)
        self.update_count(0)  # Atualização visual imediata
        show_notification(self, "Contagem resetada na UI (backend TODO)", "info")

    def update_detection_status(self, is_active: bool):
        """Atualiza status da detecção e estado dos botões/widgets."""
        self.is_detection_active = is_active

        if is_active:
            # Detecção ATIVA
            self.detection_button.configure(
                text="Parar Detecção", state="normal",
                fg_color="#C24E4E", hover_color="#E57373"  # Vermelho
            )
            self.status_label.configure(text="Status: Ativo", text_color="#3BA776")  # Verde
            self.reset_button.configure(state="normal")
            self.finalize_button.configure(state="disabled")  # Desabilita Finalizar
            self.cargo_type_combo.configure(state="disabled")  # Bloqueia tipo
        else:
            # Detecção INATIVA
            self.detection_button.configure(
                text="Iniciar Detecção", state="normal",
                fg_color="#3BA776", hover_color="#4FC48C"  # Verde
            )
            self.status_label.configure(text="Status: Inativo", text_color="#E8A23B")  # Laranja
            self.reset_button.configure(state="disabled")

            # Habilita botão Finalizar pois a detecção está parada
            self.finalize_button.configure(state="normal", text="Finalizar e Enviar")

            self.cargo_type_combo.configure(state="normal")  # Libera tipo

    def update_count(self, count: int):
        """Atualiza contagem"""
        self.current_count = count
        self.count_label.configure(text=f"Contagem: {count}")

    def get_current_count(self) -> int:
        """Pega o valor numérico da contagem atual do label."""
        try:
            return int(self.count_label.cget("text").split(":")[1].strip())
        except (IndexError, ValueError, TypeError):
            return 0  # Retorna 0 se falhar ao parsear

    def update_video_frame(self, frame):
        """Atualiza frame de vídeo"""
        try:
            if frame is None or frame.size == 0:
                self.video_label.configure(image=None, text="Frame inválido")
                self.video_label.image = None
                return

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_pil = Image.fromarray(frame_rgb)

            if self.video_label.cget("text"): self.video_label.configure(text="")

            label_width = self.video_label.winfo_width()
            label_height = self.video_label.winfo_height()

            if label_width <= 1 or label_height <= 1:
                self.after(50, lambda: self.update_video_frame(frame))
                return

            img_width, img_height = frame_pil.size
            ratio = min(label_width / img_width, label_height / img_height) if img_width > 0 and img_height > 0 else 1
            new_width = max(1, int(img_width * ratio))
            new_height = max(1, int(img_height * ratio))

            frame_pil_resized = frame_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
            frame_tk = ImageTk.PhotoImage(frame_pil_resized)

            self.video_label.configure(image=frame_tk)
            self.video_label.image = frame_tk

        except Exception as e:
            # Evita spammar logs por erros de renderização (ex: janela fechando)
            if self.winfo_exists():  # Só loga se a janela ainda existir
                error_text = f"Erro ao atualizar frame:\n{e}"
                try:  # Tenta configurar label, mas pode falhar se estiver sendo destruído
                    self.video_label.configure(image=None, text=error_text)
                    self.video_label.image = None
                except:
                    pass
                print(f"[CameraView {self.camera_id}] {error_text}")

    def _on_closing_attempt(self):
        """Impede o fechamento se a detecção estiver ativa."""
        if self.is_detection_active:
            messagebox.showwarning(
                "Detecção Ativa",
                "Por favor, pare a detecção antes de fechar a janela.",
                parent=self
            )
        else:
            self.destroy()  # Aciona o callback do ScreenManager (protocol)

    # --- ADICIONADO: Métodos de feedback da API ---
    def show_notification(self, message: str, notification_type: str = "info"):
        """Exibe uma notificação (usado pelo ScreenManager)."""
        # Garante que a notificação apareça sobre esta Toplevel
        show_notification(self, message, notification_type)

    def show_error(self, message: str):
        """Exibe um diálogo de erro (usado pelo ScreenManager)."""
        show_error_dialog(f"Erro - Câmera {self.camera_id}", message, parent=self)
    # --- FIM ADIÇÃO ---