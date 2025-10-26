# main.py
import customtkinter as ctk
import json, os, hashlib, time, threading
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from tkinter import messagebox, filedialog
import cv2

# Importa setup YOLO e RTSP
from config import modelo_yolo, RTSP_LINKS, CONFIDENCE_THRESHOLD, SHOW_WINDOW

# ---------- CONFIGURAÇÃO VISUAL ----------
ctk.set_appearance_mode("dark")

CORES = {
    "fundo": "#1C1C1C", "branco": "#FDFDFD", "primaria": "#4A90A4",
    "primaria_hover": "#5BA8B5", "sucesso": "#3BA776", "sucesso_hover": "#4FC48C",
    "aviso": "#E8A23B", "cinza": "#555555", "perigo": "#C24E4E", "perigo_hover": "#E57373"
}
FONTS = {
    "titulo": ("Arial", 32, "bold"), "subtitulo": ("Arial", 26, "bold"),
    "botao_grande": ("Arial", 18, "bold"), "texto_geral": ("Arial", 16),
    "label_info": ("Arial", 14)
}

# ---------- PROCESSOS DE CONTAGEM ----------
processos_contagem = {}

def loop_contagem(numero_camera, stop_event, label_contagem):
    print(f"✅ Iniciando detecção na Câmera {numero_camera}")

    # Fonte de vídeo (int = local / str = RTSP)
    camera_fonte = RTSP_LINKS.get(numero_camera)
    if camera_fonte is None:
        label_contagem.set("Câmera não configurada.")
        print(f"⚠️ Nenhuma fonte configurada para a Câmera {numero_camera}")
        return

    cap = cv2.VideoCapture(camera_fonte)
    if not cap.isOpened():
        tipo = "local" if isinstance(camera_fonte, int) else "RTSP"
        label_contagem.set("Erro ao abrir câmera.")
        print(f"❌ Falha ao abrir a câmera {numero_camera} ({tipo}) → {camera_fonte}")
        return

    largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if largura == 0 or altura == 0:
        largura, altura = 640, 480

    linha_y = altura // 2
    margem = 10
    contador = 0
    rastreador_objetos = {}
    falhas_consecutivas = 0  # Contador de falhas
    max_falhas = 150         # 150 * 0.2s = 30s de falha antes de desistir

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret or frame is None:
            falhas_consecutivas += 1
            print(f"⚠️ [Câmera {numero_camera}] Falha ao ler frame ({falhas_consecutivas}/{max_falhas})")

            if falhas_consecutivas > max_falhas:
                print(f"❌ [Câmera {numero_camera}] Stream perdido ou câmera desconectada. Encerrando thread.")
                label_contagem.set("Stream perdido.")
                break  # Sai do loop while e encerra a thread

            time.sleep(0.2)  # Espera um pouco antes de tentar de novo
            continue

        # Se chegou aqui, o frame é bom, então zera o contador de falhas
        falhas_consecutivas = 0

        # --- DETECÇÃO COM YOLO ---
        # NÃO passa device= aqui! O modelo JÁ está na GPU (config.py fez isso)
        resultados = modelo_yolo.track(frame, conf=CONFIDENCE_THRESHOLD, persist=True, verbose=False)
        deteccoes = resultados[0].boxes

        if deteccoes.id is not None:
            for box, obj_id, cls, conf in zip(
                deteccoes.xyxy, deteccoes.id.tolist(), deteccoes.cls.tolist(), deteccoes.conf.tolist()
            ):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                # --- desenha bounding box e label ---
                label = f"{modelo_yolo.names[int(cls)]} {conf:.2f}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)

                # --- lógica de contagem com 70% ---
                altura_objeto = y2 - y1
                if altura_objeto <= 0:
                    continue

                parte_abaixo = max(0, y2 - linha_y)
                frac_abaixo = parte_abaixo / altura_objeto

                # Atualiza histórico
                y_ant = rastreador_objetos.get(obj_id, cy)
                rastreador_objetos[obj_id] = cy

                # Só conta se cruzou a linha e 70% do objeto passou
                if frac_abaixo >= 0.2:
                    if (y_ant < linha_y - margem and cy >= linha_y + margem) or \
                       (y_ant > linha_y + margem and cy <= linha_y - margem):
                        contador += 1
                        label_contagem.set(f"Contagem: {contador}")
                        print(f"[Câmera {numero_camera}] Objeto cruzou (70%). Total: {contador}")

        # --- desenha linha vermelha ---
        cv2.line(frame, (0, linha_y), (largura, linha_y), (0, 0, 255), 2)
        cv2.putText(frame, f"Contagem: {contador}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # --- mostra se habilitado ---
        if SHOW_WINDOW:
            cv2.imshow(f"Câmera {numero_camera}", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    if SHOW_WINDOW:
        cv2.destroyWindow(f"Câmera {numero_camera}")
    print(f"❌ Encerrando detecção da câmera {numero_camera}")


# ---------- FUNÇÕES UTILITÁRIAS ----------
def centralizar_janela(janela, largura, altura):
    largura_tela = janela.winfo_screenwidth()
    altura_tela = janela.winfo_screenheight()
    x = int((largura_tela / 2) - (largura / 2))
    y = int((altura_tela / 2) - (altura / 2))
    janela.geometry(f"{largura}x{altura}+{x}+{y}")


# ---------- INICIALIZAÇÃO DO APP ----------
app = ctk.CTk()
app.title("LAS Cams System")
app.minsize(800, 600)
centralizar_janela(app, 1280, 720)

# ---------- LOGIN E USUÁRIOS ----------
ARQUIVO_USUARIOS = "usuarios.json"

def carregar_usuarios():
    """Lê usuarios.json de forma robusta."""
    if not os.path.exists(ARQUIVO_USUARIOS):
        return {}
    try:
        with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}
    except Exception as e:
        print(f"⚠️ Erro ao carregar usuários: {e}")
        return {}

def salvar_usuarios(dados):
    """Salva de forma segura (usa arquivo temporário)."""
    try:
        temp_path = ARQUIVO_USUARIOS + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, ARQUIVO_USUARIOS)
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar usuários: {e}")
        return False

def gerar_hash(senha):
    """Gera hash de senha com PBKDF2 (compatível)."""
    sal = os.urandom(16)
    senha_hasheada = hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), sal, 100000)
    return sal.hex() + ':' + senha_hasheada.hex()

def verificar_hash(senha_armazenada, senha_fornecida):
    try:
        sal_hex, hash_hex = senha_armazenada.split(':', 1)
        sal = bytes.fromhex(sal_hex)
        hash_fornecido = hashlib.pbkdf2_hmac('sha256', senha_fornecida.encode('utf-8'), sal, 100000)
        return hash_fornecido == bytes.fromhex(hash_hex)
    except Exception:
        return False

dados_usuarios = carregar_usuarios()

# ---------- RELATÓRIO ----------
def gerar_relatorio_pdf(usuario, camera):
    agora = datetime.now()
    nome_sugerido = f"relatorio_{usuario}_cam{camera}_{agora.strftime('%d-%m-%Y_%H-%M-%S')}.pdf"
    nome_pdf = filedialog.asksaveasfilename(initialfile=nome_sugerido, defaultextension=".pdf",
                                            filetypes=[("PDF Documents", "*.pdf")])
    if not nome_pdf:
        return
    try:
        c = canvas.Canvas(nome_pdf, pagesize=A4)
        width, height = A4
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width / 2.0, height - 100, "Relatório de Monitoramento")
        c.setFont("Helvetica", 14)
        c.drawString(100, height - 150, f"Usuário: {usuario}")
        c.drawString(100, height - 170, f"Câmera: {camera}")
        c.drawString(100, height - 190, f"Data e Hora: {agora.strftime('%d/%m/%Y %H:%M:%S')}")
        c.showPage()
        c.save()
        messagebox.showinfo("Relatório Gerado", f"PDF criado com sucesso:\n{nome_pdf}")
    except Exception as e:
        messagebox.showerror("Erro ao Gerar PDF", str(e))


# ---------- POP-UP DE CÂMERA ----------
def abrir_camera_popup(usuario_logado, numero_camera):
    popup = ctk.CTkToplevel(app)
    popup.title(f"Câmera {numero_camera}")
    popup.configure(fg_color=CORES["fundo"])
    popup.grab_set()
    centralizar_janela(popup, 900, 650)

    ctk.CTkLabel(popup, text=f"Visão Ampliada - Câmera {numero_camera}",
                 font=FONTS["subtitulo"], text_color=CORES["branco"]).pack(pady=25)

    contagem_var = ctk.StringVar(value="Contagem: 0")
    label_contagem = ctk.CTkLabel(popup, textvariable=contagem_var,
                                  font=FONTS["texto_geral"], text_color=CORES["sucesso"])
    label_contagem.pack(pady=10)

    botoes_frame = ctk.CTkFrame(popup, fg_color="transparent")
    botoes_frame.pack(pady=20)

    status_label = ctk.CTkLabel(popup, text="", font=FONTS["texto_geral"])
    status_label.pack()

    def alternar_contagem():
        if numero_camera in processos_contagem:
            stop_event = processos_contagem[numero_camera]['stop_event']
            stop_event.set()
            del processos_contagem[numero_camera]
            btn_contagem.configure(text="Ativar Contagem", fg_color=CORES["sucesso"])
            status_label.configure(text="Contagem: INATIVA", text_color=CORES["aviso"])
        else:
            stop_event = threading.Event()
            thread = threading.Thread(target=loop_contagem,
                                      args=(numero_camera, stop_event, contagem_var))
            processos_contagem[numero_camera] = {'thread': thread, 'stop_event': stop_event}
            thread.start()
            btn_contagem.configure(text="Desativar Contagem", fg_color=CORES["perigo"])
            status_label.configure(text="Contagem: ATIVA", text_color=CORES["sucesso"])

    ctk.CTkButton(botoes_frame, text="Gerar Relatório", font=FONTS["botao_grande"],
                  fg_color=CORES["primaria"], hover_color=CORES["primaria_hover"],
                  command=lambda: gerar_relatorio_pdf(usuario_logado, numero_camera)).grid(row=0, column=0, padx=10)

    btn_contagem = ctk.CTkButton(botoes_frame, text="Ativar Contagem",
                                 font=FONTS["botao_grande"], fg_color=CORES["sucesso"],
                                 hover_color=CORES["sucesso_hover"], command=alternar_contagem)
    btn_contagem.grid(row=0, column=1, padx=10)

    ctk.CTkButton(popup, text="Fechar", fg_color=CORES["cinza"], command=popup.destroy).pack(pady=10)


# ---------- TELAS ----------
class TelaLogin(ctk.CTkFrame):
    def __init__(self, master, trocar_tela_callback):
        super().__init__(master, fg_color=CORES["fundo"])
        self.trocar_tela_callback = trocar_tela_callback
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(frame, text="Login do Sistema", font=FONTS["titulo"],
                     text_color=CORES["branco"]).pack(pady=40)
        self.username_entry = ctk.CTkEntry(frame, placeholder_text="Usuário", width=350, height=45)
        self.username_entry.pack(pady=10)
        self.password_entry = ctk.CTkEntry(frame, placeholder_text="Senha", show="*", width=350, height=45)
        self.password_entry.pack(pady=10)
        ctk.CTkButton(frame, text="Entrar", width=350, height=45, font=FONTS["botao_grande"],
                      fg_color=CORES["primaria"], hover_color=CORES["primaria_hover"],
                      command=self.login).pack(pady=20)
        ctk.CTkButton(frame, text="Cadastrar-se", width=350, height=35,
                      font=FONTS["label_info"], fg_color="transparent",
                      border_color=CORES["primaria"], border_width=2,
                      command=lambda: trocar_tela_callback("cadastro")).pack(pady=5)

    def login(self):
        usuario = self.username_entry.get().strip()
        senha = self.password_entry.get()
        if not usuario or not senha:
            messagebox.showwarning("Campos Vazios", "Preencha usuário e senha.")
            return

        global dados_usuarios
        dados_usuarios = carregar_usuarios()

        if usuario not in dados_usuarios:
            messagebox.showerror("Erro de Login", "Usuário não encontrado.")
            return

        registro = dados_usuarios.get(usuario)
        if not registro or "senha_hash" not in registro:
            messagebox.showerror("Erro de Login", "Registro de usuário inválido. Contate o administrador.")
            return

        if verificar_hash(registro["senha_hash"], senha):
            self.trocar_tela_callback("dashboard", usuario=usuario)
        else:
            messagebox.showerror("Erro de Login", "Senha incorreta.")


class TelaCadastro(ctk.CTkFrame):
    def __init__(self, master, trocar_tela_callback):
        super().__init__(master, fg_color=CORES["fundo"])
        self.trocar_tela_callback = trocar_tela_callback
        frame_central = ctk.CTkFrame(self, fg_color="transparent")
        frame_central.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(frame_central, text="Cadastro de Usuário", font=FONTS["titulo"],
                     text_color=CORES["branco"]).pack(pady=40)
        self.username_entry = ctk.CTkEntry(frame_central, placeholder_text="Novo usuário",
                                           width=350, height=45, font=FONTS["texto_geral"])
        self.username_entry.pack(pady=10)
        self.password_entry = ctk.CTkEntry(frame_central, placeholder_text="Senha",
                                           show="*", width=350, height=45, font=FONTS["texto_geral"])
        self.password_entry.pack(pady=10)
        ctk.CTkButton(frame_central, text="Cadastrar", width=350, height=45, font=FONTS["botao_grande"],
                      fg_color=CORES["primaria"], hover_color=CORES["primaria_hover"],
                      command=self.cadastrar).pack(pady=20)
        ctk.CTkButton(frame_central, text="Voltar ao Login", width=350, height=35, font=FONTS["label_info"],
                      fg_color="transparent", border_color=CORES["cinza"], border_width=2,
                      command=lambda: trocar_tela_callback("login")).pack(pady=10)

    def cadastrar(self):
        usuario = self.username_entry.get().strip()
        senha = self.password_entry.get()
        if not usuario or not senha:
            messagebox.showwarning("Campos Vazios", "Por favor, preencha todos os campos.")
            return

        global dados_usuarios
        dados_usuarios = carregar_usuarios()

        if usuario in dados_usuarios:
            messagebox.showerror("Erro de Cadastro", "Este nome de usuário já existe!")
            return

        try:
            senha_h = gerar_hash(senha)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar hash da senha: {e}")
            return

        dados_usuarios[usuario] = {"senha_hash": senha_h}
        if salvar_usuarios(dados_usuarios):
            messagebox.showinfo("Cadastro Concluído", "Usuário cadastrado com sucesso! Você já pode fazer o login.")
            self.trocar_tela_callback("login")
        else:
            messagebox.showerror("Erro", "Não foi possível salvar o cadastro.")


class TelaDashboard(ctk.CTkFrame):
    def __init__(self, master, trocar_tela_callback):
        super().__init__(master, fg_color=CORES["fundo"])
        self.trocar_tela_callback = trocar_tela_callback
        self.usuario_logado = ""

        top_bar = ctk.CTkFrame(self, fg_color=CORES["primaria"], height=60)
        top_bar.pack(fill="x", side="top")
        ctk.CTkLabel(top_bar, text="LAS Cams System", font=FONTS["botao_grande"],
                     text_color=CORES["branco"]).pack(side="left", padx=20)
        self.label_usuario = ctk.CTkLabel(top_bar, text="", font=FONTS["texto_geral"],
                                          text_color=CORES["branco"])
        self.label_usuario.pack(side="left", expand=True)
        ctk.CTkButton(top_bar, text="Logout", width=120, fg_color=CORES["branco"],
                      text_color=CORES["fundo"], command=self.logout).pack(side="right", padx=20)

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(expand=True, fill="both", padx=20, pady=20)
        grid.grid_rowconfigure((0, 1), weight=1)
        grid.grid_columnconfigure((0, 1, 2), weight=1)

        for i in range(2):
            for j in range(3):
                n = i * 3 + j + 1
                frame = ctk.CTkFrame(grid, fg_color=CORES["primaria"], corner_radius=10, border_width=2)
                frame.grid(row=i, column=j, padx=10, pady=10, sticky="nsew")
                lbl = ctk.CTkLabel(frame, text=f"Câmera {n}", font=FONTS["subtitulo"], text_color=CORES["branco"])
                lbl.place(relx=0.5, rely=0.5, anchor="center")
                frame.bind("<Button-1>", lambda _, cam=n: abrir_camera_popup(self.usuario_logado, cam))
                lbl.bind("<Button-1>", lambda _, cam=n: abrir_camera_popup(self.usuario_logado, cam))

    def atualizar_usuario(self, nome):
        self.usuario_logado = nome
        self.label_usuario.configure(text=f"Bem-vindo, {nome}")

    def logout(self):
        self.trocar_tela_callback("login")


# ---------- GERENCIADOR DE TELAS ----------
telas = {}
frame_atual = None

def trocar_tela(nome, usuario=None):
    global frame_atual
    if frame_atual:
        frame_atual.pack_forget()
    frame_atual = telas[nome]
    frame_atual.pack(expand=True, fill="both")
    if nome == "dashboard" and usuario:
        telas["dashboard"].atualizar_usuario(usuario)

telas["login"] = TelaLogin(app, trocar_tela)
telas["cadastro"] = TelaCadastro(app, trocar_tela)
telas["dashboard"] = TelaDashboard(app, trocar_tela)
trocar_tela("login")
app.mainloop()

# Finaliza threads
for cam, proc in processos_contagem.items():
    proc["stop_event"].set()