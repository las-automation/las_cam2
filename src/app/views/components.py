"""
Componentes de UI reutilizáveis
"""
import customtkinter as ctk
from typing import Optional, Callable, Any
from tkinter import messagebox


class ModernButton(ctk.CTkButton):
    """Botão moderno com estilos pré-definidos"""
    
    STYLES = {
        "primary": {"fg_color": "#4A90A4", "hover_color": "#5BA8B5"},
        "success": {"fg_color": "#3BA776", "hover_color": "#4FC48C"},
        "warning": {"fg_color": "#E8A23B", "hover_color": "#F2B84D"},
        "danger": {"fg_color": "#C24E4E", "hover_color": "#E57373"},
        "secondary": {"fg_color": "#555555", "hover_color": "#666666"},
        "outline": {"fg_color": "transparent", "border_color": "#4A90A4", "border_width": 2}
    }
    
    def __init__(self, master, text: str, style: str = "primary", 
                 command: Optional[Callable] = None, **kwargs):
        
        # Aplica estilo
        style_config = self.STYLES.get(style, self.STYLES["primary"])
        kwargs.update(style_config)
        
        # Configurações padrão
        default_config = {
            "text": text,
            "command": command,
            "font": ("Arial", 14, "bold"),
            "text_color": "white",
            "corner_radius": 8,
            "height": 40
        }
        default_config.update(kwargs)
        
        super().__init__(master, **default_config)


class ModernEntry(ctk.CTkEntry):
    """Campo de entrada moderno"""
    
    def __init__(self, master, placeholder_text: str = "", **kwargs):
        default_config = {
            "placeholder_text": placeholder_text,
            "font": ("Arial", 14),
            "height": 40,
            "corner_radius": 8,
            "border_width": 2,
            "border_color": "#555555"
        }
        default_config.update(kwargs)
        
        super().__init__(master, **default_config)


class ModernLabel(ctk.CTkLabel):
    """Label moderno"""
    
    STYLES = {
        "title": {"font": ("Arial", 32, "bold"), "text_color": "#FDFDFD"},
        "subtitle": {"font": ("Arial", 26, "bold"), "text_color": "#FDFDFD"},
        "heading": {"font": ("Arial", 20, "bold"), "text_color": "#FDFDFD"},
        "body": {"font": ("Arial", 16), "text_color": "#FDFDFD"},
        "caption": {"font": ("Arial", 14), "text_color": "#CCCCCC"},
        "success": {"font": ("Arial", 16), "text_color": "#3BA776"},
        "warning": {"font": ("Arial", 16), "text_color": "#E8A23B"},
        "error": {"font": ("Arial", 16), "text_color": "#C24E4E"}
    }
    
    def __init__(self, master, text: str, style: str = "body", **kwargs):
        style_config = self.STYLES.get(style, self.STYLES["body"])
        kwargs.update(style_config)
        kwargs["text"] = text
        
        super().__init__(master, **kwargs)


class CameraCard(ctk.CTkFrame):
    """Card de câmera com informações e controles"""
    
    def __init__(self, master, camera_id: int, camera_name: str, 
                 on_click: Optional[Callable] = None, **kwargs):
        
        super().__init__(master, fg_color="#4A90A4", corner_radius=10, 
                        border_width=2, **kwargs)
        
        self.camera_id = camera_id
        self.on_click = on_click
        
        # Configuração do grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Label principal
        self.title_label = ModernLabel(
            self, text=f"Câmera {camera_id}", 
            style="subtitle"
        )
        self.title_label.grid(row=0, column=0, pady=20, sticky="nsew")
        
        # Label de nome
        self.name_label = ModernLabel(
            self, text=camera_name, 
            style="caption"
        )
        self.name_label.grid(row=1, column=0, pady=(0, 10), sticky="nsew")
        
        # Status label
        self.status_label = ModernLabel(
            self, text="Desconectada", 
            style="warning"
        )
        self.status_label.grid(row=2, column=0, pady=(0, 20), sticky="nsew")
        
        # Bind click events
        self.bind("<Button-1>", self._on_click)
        self.title_label.bind("<Button-1>", self._on_click)
        self.name_label.bind("<Button-1>", self._on_click)
        self.status_label.bind("<Button-1>", self._on_click)
        
        # Cursor pointer
        self.configure(cursor="hand2")
        self.title_label.configure(cursor="hand2")
        self.name_label.configure(cursor="hand2")
        self.status_label.configure(cursor="hand2")
    
    def _on_click(self, event):
        """Callback para clique no card"""
        if self.on_click:
            self.on_click(self.camera_id)
    
    def update_status(self, status: str, status_type: str = "warning"):
        """Atualiza status da câmera"""
        self.status_label.configure(text=status)
        
        # Atualiza cor baseada no tipo
        colors = {
            "success": "#3BA776",
            "warning": "#E8A23B", 
            "error": "#C24E4E",
            "info": "#4A90A4"
        }
        
        color = colors.get(status_type, "#E8A23B")
        self.status_label.configure(text_color=color)


class StatusBar(ctk.CTkFrame):
    """Barra de status do sistema"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="#555555", height=30, **kwargs)
        
        self.pack(fill="x", side="bottom")
        
        # Status do sistema
        self.system_status = ModernLabel(
            self, text="Sistema iniciado", 
            style="caption"
        )
        self.system_status.pack(side="left", padx=10, pady=5)
        
        # Usuário atual
        self.user_label = ModernLabel(
            self, text="", 
            style="caption"
        )
        self.user_label.pack(side="right", padx=10, pady=5)
    
    def update_system_status(self, status: str):
        """Atualiza status do sistema"""
        self.system_status.configure(text=status)
    
    def update_user(self, username: str):
        """Atualiza usuário atual"""
        self.user_label.configure(text=f"Usuário: {username}")


class LoadingSpinner(ctk.CTkFrame):
    """Spinner de carregamento"""
    
    def __init__(self, master, text: str = "Carregando...", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.label = ModernLabel(self, text=text, style="body")
        self.label.pack(pady=20)
        
        # Animação simples (pode ser melhorada)
        self.animation_id = None
        self._animate()
    
    def _animate(self):
        """Animação do spinner"""
        current_text = self.label.cget("text")
        if current_text.endswith("..."):
            new_text = current_text[:-3]
        else:
            new_text = current_text + "."
        
        self.label.configure(text=new_text)
        self.animation_id = self.after(500, self._animate)
    
    def destroy(self):
        """Destrói o spinner"""
        if self.animation_id:
            self.after_cancel(self.animation_id)
        super().destroy()


class NotificationToast(ctk.CTkToplevel):
    """Toast de notificação"""
    
    def __init__(self, master, message: str, notification_type: str = "info", 
                 duration: int = 3000):
        
        super().__init__(master)
        
        self.duration = duration
        
        # Configuração da janela
        self.title("")
        self.configure(fg_color="#2B2B2B")
        self.overrideredirect(True)
        
        # Cores baseadas no tipo
        colors = {
            "success": "#3BA776",
            "error": "#C24E4E",
            "warning": "#E8A23B",
            "info": "#4A90A4"
        }
        
        color = colors.get(notification_type, "#4A90A4")
        
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color=color, corner_radius=8)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Mensagem
        message_label = ModernLabel(
            main_frame, text=message, 
            style="body"
        )
        message_label.pack(pady=15, padx=20)
        
        # Posiciona no canto superior direito
        self.geometry("300x80+{}+{}".format(
            master.winfo_screenwidth() - 320,
            50
        ))
        
        # Auto-destruição
        self.after(duration, self.destroy)
        
        # Fade in effect
        self.attributes("-alpha", 0)
        self._fade_in()
    
    def _fade_in(self):
        """Efeito de fade in"""
        alpha = self.attributes("-alpha")
        if alpha < 1.0:
            alpha += 0.1
            self.attributes("-alpha", alpha)
            self.after(50, self._fade_in)


def show_notification(master, message: str, notification_type: str = "info", 
                     duration: int = 3000):
    """Função helper para mostrar notificação"""
    toast = NotificationToast(master, message, notification_type, duration)
    return toast


def show_error_dialog(title: str, message: str):
    """Mostra diálogo de erro"""
    messagebox.showerror(title, message)


def show_success_dialog(title: str, message: str):
    """Mostra diálogo de sucesso"""
    messagebox.showinfo(title, message)


def show_warning_dialog(title: str, message: str):
    """Mostra diálogo de aviso"""
    messagebox.showwarning(title, message)

