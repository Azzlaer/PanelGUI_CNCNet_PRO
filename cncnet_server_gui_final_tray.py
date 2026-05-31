# -*- coding: utf-8 -*-
"""
CnCNet Tunnel Server GUI TABPAGE FIX URLACL
Autor: ChatGPT OpenAI + Azzlaer para LatinBattle.com

Panel GUI para administrar cncnet-server.exe / cncnet-server-core.exe con pestañas:

    INICIO:
        - Iniciar / Detener
        - Detectar proceso
        - Detener procesos detectados
        - Estado, PID, proceso, puertos principales
        - Comando resumido generado

    OPCIONES:
        - Ejecutable
        - Nombre del servidor
        - Puertos
        - Máximo de clientes
        - Límites por IP
        - Flags --nomaster y --nop2p

    MASTER / SEGURIDAD:
        - Master URL
        - Master password
        - Maintenance password

    HERRAMIENTAS:
        - Probar puertos
        - Ejecutar --help
        - Ejecutar --version
        - Copiar comando
        - Abrir carpeta
        - Guardar / restaurar configuración

    CONSOLA:
        - Log en vivo del proceso
        - Eventos del panel
        - Limpiar consola
        - Auto-scroll

    ACERCA DE:
        - Resumen del proyecto
        - Consejos de firewall/router

Argumentos soportados:
    --port
    --portv2
    --name
    --maxclients
    --nomaster
    --masterpw
    --maintpw
    --master
    --iplimit
    --iplimitv2
    --nop2p
    --help
    --version

Requisitos:
    Python 3.10+
    Windows recomendado
    No requiere librerías externas

Uso:
    python cncnet_server_gui_tabpage.py

Recomendación:
    Coloca este script en la misma carpeta que cncnet-server.exe,
    o usa el botón "Buscar EXE".
"""

import configparser
import ctypes
import os
import queue
import shlex
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except Exception:
    pystray = None
    Image = None
    ImageDraw = None
    HAS_TRAY = False


APP_TITLE = "CnCNet Tunnel Server GUI FINAL - LatinBattle"
CONFIG_FILE = "cncnet_server_gui.ini"

PROCESS_NAMES = [
    "cncnet-server.exe",
    "cncnet-server-core.exe",
]


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = app_dir()
CONFIG_PATH = BASE_DIR / CONFIG_FILE


DEFAULTS = {
    "exe_path": str(BASE_DIR / "cncnet-server.exe"),
    "process_name": "cncnet-server.exe",
    "port": "50001",
    "portv2": "50000",
    "name": "LatinBattle Tunnel Server",
    "maxclients": "200",
    "nomaster": "false",
    "masterpw": "",
    "maintpw": "",
    "master": "http://cncnet.org/master-announce",
    "iplimit": "8",
    "iplimitv2": "4",
    "nop2p": "false",
    "auto_scroll": "true",
    "auto_detect": "true",
    "monitor_interval": "3000",
    "minimize_to_tray": "true",
    "always_on_top": "false",
}


class ToolTip:
    """Tooltip simple para orientar al usuario novato."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip or not self.text:
            return

        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8

        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tip,
            text=self.text,
            justify="left",
            bg="#111827",
            fg="#f9fafb",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=5,
            font=("Segoe UI", 9),
            wraplength=340,
        )
        label.pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class CnCNetServerGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(1040, 680)
        self.configure(bg="#0f172a")

        self.process = None
        self.reader_thread = None
        self.output_queue = queue.Queue()
        self.stop_reader = threading.Event()

        self.detected_pids = []
        self.last_detected_pids = []

        self.tray_icon = None
        self.tray_thread = None
        self.force_exit = False
        self._minimize_event_guard = False

        self.vars = {}
        self.load_config()
        self.build_style()
        self.build_ui()
        self.refresh_checkboxes_from_vars()
        self.apply_always_on_top(log=False)
        self.refresh_command()
        self.refresh_home_cards()
        self.after(150, self.drain_output_queue)
        self.after(700, self.monitor_process_loop)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Unmap>", self.on_window_unmap)

    # ============================================================
    # CONFIG
    # ============================================================

    def load_config(self):
        self.config_parser = configparser.ConfigParser()
        self.config_parser["server"] = DEFAULTS.copy()

        if CONFIG_PATH.exists():
            self.config_parser.read(CONFIG_PATH, encoding="utf-8")

        server = self.config_parser["server"]
        for key, default in DEFAULTS.items():
            self.vars[key] = tk.StringVar(value=server.get(key, default))

    def save_config(self):
        self.sync_checkboxes_to_vars()

        if "server" not in self.config_parser:
            self.config_parser["server"] = {}

        for key, var in self.vars.items():
            self.config_parser["server"][key] = str(var.get())

        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            self.config_parser.write(f)

        self.log(f"[CONFIG] Guardado en: {CONFIG_PATH}")
        self.refresh_home_cards()

    def reset_defaults(self):
        if not messagebox.askyesno("Restaurar", "¿Restaurar todos los valores por defecto?"):
            return

        for key, value in DEFAULTS.items():
            self.vars[key].set(value)

        self.refresh_checkboxes_from_vars()
        self.refresh_command()
        self.refresh_home_cards()
        self.log("[CONFIG] Valores por defecto restaurados.")

    # ============================================================
    # STYLE
    # ============================================================

    def build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Root.TFrame", background="#0f172a")
        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#1e293b", relief="flat")
        style.configure("SoftCard.TFrame", background="#111827", relief="flat")
        style.configure("TLabel", background="#0f172a", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.configure("Card.TLabel", background="#1e293b", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.configure("SoftCard.TLabel", background="#111827", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#0f172a", foreground="#ffffff", font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background="#0f172a", foreground="#9ca3af", font=("Segoe UI", 10))
        style.configure("BigValue.TLabel", background="#1e293b", foreground="#ffffff", font=("Segoe UI", 15, "bold"))
        style.configure("Muted.TLabel", background="#1e293b", foreground="#94a3b8", font=("Segoe UI", 9))
        style.configure("Ok.TLabel", background="#1e293b", foreground="#34d399", font=("Segoe UI", 11, "bold"))
        style.configure("Warn.TLabel", background="#1e293b", foreground="#fbbf24", font=("Segoe UI", 11, "bold"))
        style.configure("Bad.TLabel", background="#1e293b", foreground="#f87171", font=("Segoe UI", 11, "bold"))

        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=9)
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=9)

        style.configure("TEntry", padding=6)
        style.configure("TCombobox", padding=6)

        style.configure("TCheckbutton", background="#1e293b", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.map(
            "TCheckbutton",
            background=[("active", "#1e293b")],
            foreground=[("active", "#ffffff")],
        )

        style.configure(
            "Dark.TNotebook",
            background="#0f172a",
            borderwidth=0,
        )
        style.configure(
            "Dark.TNotebook.Tab",
            background="#111827",
            foreground="#d1d5db",
            padding=(18, 9),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", "#2563eb"), ("active", "#1d4ed8")],
            foreground=[("selected", "#ffffff"), ("active", "#ffffff")],
        )

    # ============================================================
    # UI
    # ============================================================

    def build_ui(self):
        root = ttk.Frame(self, style="Root.TFrame", padding=14)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="Root.TFrame")
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(header, text="🌐 CnCNet Tunnel Server GUI", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Panel con pestañas para iniciar, detectar, configurar argumentos y ver consola del cncnet-server.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        self.notebook = ttk.Notebook(root, style="Dark.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        self.tab_home = ttk.Frame(self.notebook, style="Root.TFrame", padding=14)
        self.tab_options = ttk.Frame(self.notebook, style="Root.TFrame", padding=14)
        self.tab_master = ttk.Frame(self.notebook, style="Root.TFrame", padding=14)
        self.tab_tools = ttk.Frame(self.notebook, style="Root.TFrame", padding=14)
        self.tab_console = ttk.Frame(self.notebook, style="Root.TFrame", padding=14)
        self.tab_about = ttk.Frame(self.notebook, style="Root.TFrame", padding=14)

        self.notebook.add(self.tab_home, text="🏠 INICIO")
        self.notebook.add(self.tab_options, text="⚙️ OPCIONES")
        self.notebook.add(self.tab_master, text="🔐 MASTER / SEGURIDAD")
        self.notebook.add(self.tab_tools, text="🧰 HERRAMIENTAS")
        self.notebook.add(self.tab_console, text="🖥️ CONSOLA")
        self.notebook.add(self.tab_about, text="ℹ️ ACERCA DE")

        self.build_home_tab()
        self.build_options_tab()
        self.build_master_tab()
        self.build_tools_tab()
        self.build_console_tab()
        self.build_about_tab()

    def make_card(self, parent, padding=14):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=padding)
        return frame

    def build_home_tab(self):
        top = ttk.Frame(self.tab_home, style="Root.TFrame")
        top.pack(fill="x")

        left = self.make_card(top)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right = self.make_card(top)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ttk.Label(left, text="🚀 Control principal", style="Card.TLabel", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            left,
            text="Desde aquí puedes iniciar, detener y revisar si el servidor ya está abierto.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 14))

        control_grid = ttk.Frame(left, style="Card.TFrame")
        control_grid.pack(fill="x")

        btn_start = ttk.Button(control_grid, text="▶ Iniciar servidor", style="Accent.TButton", command=self.start_server)
        btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=5)

        btn_stop = ttk.Button(control_grid, text="■ Detener GUI", style="Danger.TButton", command=self.stop_server)
        btn_stop.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=5)

        btn_detect = ttk.Button(control_grid, text="🔎 Detectar proceso", command=self.detect_process_manual)
        btn_detect.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=5)

        btn_kill = ttk.Button(control_grid, text="🧨 Detener detectado", command=self.stop_detected_processes)
        btn_kill.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=5)

        control_grid.grid_columnconfigure(0, weight=1)
        control_grid.grid_columnconfigure(1, weight=1)

        ToolTip(btn_stop, "Detiene solamente el proceso iniciado por este panel.")
        ToolTip(btn_kill, "Intenta cerrar también procesos externos detectados con taskkill.")

        self.status_label = ttk.Label(left, text="Estado: detenido", style="Bad.TLabel")
        self.status_label.pack(anchor="w", pady=(16, 4))

        self.pid_label = ttk.Label(left, text="PID: ninguno", style="Card.TLabel")
        self.pid_label.pack(anchor="w", pady=(0, 4))

        self.detect_label = ttk.Label(left, text="Detección: sin revisar", style="Card.TLabel")
        self.detect_label.pack(anchor="w", pady=(0, 4))

        self.process_label = ttk.Label(left, text="Proceso: cncnet-server.exe", style="Card.TLabel")
        self.process_label.pack(anchor="w", pady=(0, 4))

        ttk.Separator(left).pack(fill="x", pady=14)

        ttk.Label(left, text="📋 Comando generado", style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w")

        self.home_command_box = ScrolledText(
            left,
            height=5,
            wrap="word",
            bg="#0b1220",
            fg="#d1d5db",
            insertbackground="#ffffff",
            relief="flat",
            font=("Consolas", 10),
        )
        self.home_command_box.pack(fill="x", pady=(8, 0))
        self.home_command_box.configure(state="disabled")

        ttk.Label(right, text="📊 Resumen rápido", style="Card.TLabel", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(right, text="Valores principales cargados desde cncnet_server_gui.ini.", style="Muted.TLabel").pack(
            anchor="w", pady=(2, 14)
        )

        cards = ttk.Frame(right, style="Card.TFrame")
        cards.pack(fill="x")

        self.card_server_name = self.summary_card(cards, "Nombre", "-")
        self.card_server_name.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=6)

        self.card_ports = self.summary_card(cards, "Puertos", "-")
        self.card_ports.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=6)

        self.card_clients = self.summary_card(cards, "Clientes", "-")
        self.card_clients.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=6)

        self.card_master = self.summary_card(cards, "Master", "-")
        self.card_master.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=6)

        cards.grid_columnconfigure(0, weight=1)
        cards.grid_columnconfigure(1, weight=1)

        ttk.Separator(right).pack(fill="x", pady=14)

        ttk.Label(right, text="🧠 Tips rápidos", style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tips = (
            "• Si quieres que sea público, abre/redirige los puertos del servidor.\n"
            "• --port usa por defecto 50001.\n"
            "• --portv2 usa por defecto 50000.\n"
            "• Si NO activas --nop2p, revisa NAT traversal UDP 8054 y 3478.\n"
            "• Si activas --nomaster, el servidor no se registrará en el master."
        )
        ttk.Label(right, text=tips, style="Card.TLabel", justify="left", wraplength=460).pack(anchor="w")

    def summary_card(self, parent, title, value):
        frame = ttk.Frame(parent, style="SoftCard.TFrame", padding=12)
        ttk.Label(frame, text=title, style="SoftCard.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        label = ttk.Label(frame, text=value, style="SoftCard.TLabel", font=("Segoe UI", 12, "bold"), wraplength=190)
        label.pack(anchor="w", pady=(4, 0))
        frame.value_label = label
        return frame

    def build_options_tab(self):
        body = ttk.Frame(self.tab_options, style="Root.TFrame")
        body.pack(fill="both", expand=True)

        left = self.make_card(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right = self.make_card(body)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ttk.Label(left, text="⚙️ Opciones principales", style="Card.TLabel", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        row = 1
        self.add_file_row(left, row, "Ejecutable", "exe_path")
        row += 1

        self.add_entry(left, row, "Proceso a detectar", "process_name")
        ttk.Button(left, text="Auto", command=self.set_process_name_from_exe).grid(row=row, column=2, sticky="ew", pady=5, padx=(8, 0))
        row += 1

        self.add_entry(left, row, "Nombre servidor --name", "name")
        row += 1

        self.add_entry(left, row, "Puerto túnel --port", "port")
        row += 1

        self.add_entry(left, row, "Puerto V2 --portv2", "portv2")
        row += 1

        self.add_entry(left, row, "Máximo clientes --maxclients", "maxclients")
        row += 1

        self.add_entry(left, row, "Límite por IP --iplimit", "iplimit")
        row += 1

        self.add_entry(left, row, "Límite IP V2 --iplimitv2", "iplimitv2")
        row += 1

        for col in range(3):
            left.grid_columnconfigure(col, weight=1)

        ttk.Label(right, text="🔘 Flags", style="Card.TLabel", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 12))

        self.nomaster_bool = tk.BooleanVar(value=False)
        self.nop2p_bool = tk.BooleanVar(value=False)
        self.autodetect_bool = tk.BooleanVar(value=True)
        self.minimize_to_tray_bool = tk.BooleanVar(value=True)
        self.always_on_top_bool = tk.BooleanVar(value=False)

        cb1 = ttk.Checkbutton(
            right,
            text="No registrar en master --nomaster",
            variable=self.nomaster_bool,
            command=self.on_check_change,
        )
        cb1.pack(anchor="w", pady=5)

        cb2 = ttk.Checkbutton(
            right,
            text="Desactivar NAT traversal --nop2p",
            variable=self.nop2p_bool,
            command=self.on_check_change,
        )
        cb2.pack(anchor="w", pady=5)

        cb3 = ttk.Checkbutton(
            right,
            text="Auto-detectar proceso abierto",
            variable=self.autodetect_bool,
            command=self.on_check_change,
        )
        cb3.pack(anchor="w", pady=5)

        cb4 = ttk.Checkbutton(
            right,
            text="Minimizar a bandeja de Windows",
            variable=self.minimize_to_tray_bool,
            command=self.on_check_change,
        )
        cb4.pack(anchor="w", pady=5)

        cb5 = ttk.Checkbutton(
            right,
            text="Mantener ventana siempre encima",
            variable=self.always_on_top_bool,
            command=self.on_check_change,
        )
        cb5.pack(anchor="w", pady=5)

        ToolTip(cb4, "Al minimizar o cerrar con X, el panel se ocultará en la bandeja si pystray + pillow están instalados.")
        ToolTip(cb5, "Si está activo, cuando el panel esté visible quedará por encima de otras ventanas.")

        ttk.Separator(right).pack(fill="x", pady=16)

        self.add_pack_entry(right, "Intervalo monitor ms", "monitor_interval")

        ttk.Separator(right).pack(fill="x", pady=16)

        ttk.Label(right, text="📌 Explicación", style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            right,
            text=(
                "--nomaster:\n"
                "Evita registrar el servidor en el master público.\n\n"
                "--nop2p:\n"
                "Desactiva los puertos de NAT traversal 8054 y 3478 UDP.\n\n"
                "Auto-detectar:\n"
                "Busca el proceso aunque haya sido abierto fuera de este panel.\n\n"
                "Minimizar a bandeja:\n"
                "Oculta el panel al área de notificación de Windows. Requiere pystray + pillow.\n\n"
                "Siempre encima:\n"
                "Mantiene el GUI visible por encima de otras ventanas cuando no está minimizado."
            ),
            style="Card.TLabel",
            justify="left",
            wraplength=440,
        ).pack(anchor="w", pady=(8, 0))

    def build_master_tab(self):
        body = ttk.Frame(self.tab_master, style="Root.TFrame")
        body.pack(fill="both", expand=True)

        left = self.make_card(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right = self.make_card(body)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ttk.Label(left, text="🔐 Master / Seguridad", style="Card.TLabel", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        row = 1
        self.add_entry(left, row, "Master URL --master", "master")
        row += 1

        self.add_entry(left, row, "Master password --masterpw", "masterpw", show="*")
        row += 1

        self.add_entry(left, row, "Maintenance password --maintpw", "maintpw", show="*")
        row += 1

        left.grid_columnconfigure(0, weight=0)
        left.grid_columnconfigure(1, weight=1)

        ttk.Label(right, text="🛡️ Recomendaciones", style="Card.TLabel", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            right,
            text=(
                "• No compartas públicamente masterpw ni maintpw.\n"
                "• Si el servidor será privado, puedes usar --nomaster.\n"
                "• Si usas una URL master personalizada, revisa que esté activa.\n"
                "• Guarda la configuración después de cambiar claves.\n"
                "• Si publicas capturas, oculta las contraseñas."
            ),
            style="Card.TLabel",
            justify="left",
            wraplength=460,
        ).pack(anchor="w", pady=(12, 0))

    def build_tools_tab(self):
        body = ttk.Frame(self.tab_tools, style="Root.TFrame")
        body.pack(fill="both", expand=True)

        left = self.make_card(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right = self.make_card(body)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ttk.Label(left, text="🧰 Herramientas", style="Card.TLabel", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(left, text="Acciones útiles para diagnosticar y administrar el servidor.", style="Muted.TLabel").pack(
            anchor="w", pady=(2, 14)
        )

        buttons = ttk.Frame(left, style="Card.TFrame")
        buttons.pack(fill="x")

        actions = [
            ("🧪 Probar puertos", self.test_ports),
            ("🛡️ Ver permisos Admin", self.check_admin_status),
            ("🔓 Crear URLACL V2", self.add_urlacl_v2),
            ("🔒 Eliminar URLACL V2", self.delete_urlacl_v2),
            ("🚀 Reiniciar GUI como Admin", self.restart_as_admin),
            ("📥 Probar bandeja", self.minimize_to_tray),
            ("📌 Aplicar siempre encima", self.apply_always_on_top),
            ("❔ Ejecutar --help", lambda: self.run_info_command("--help")),
            ("🏷️ Ejecutar --version", lambda: self.run_info_command("--version")),
            ("📋 Copiar comando", self.copy_command),
            ("📂 Abrir carpeta del panel", self.open_app_folder),
            ("💾 Guardar configuración", self.save_config),
            ("🔄 Restaurar defaults", self.reset_defaults),
        ]

        for i, (text, cmd) in enumerate(actions):
            btn = ttk.Button(buttons, text=text, command=cmd)
            btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=6, pady=6)

        buttons.grid_columnconfigure(0, weight=1)
        buttons.grid_columnconfigure(1, weight=1)

        ttk.Label(right, text="📋 Comando completo", style="Card.TLabel", font=("Segoe UI", 15, "bold")).pack(anchor="w")

        self.tools_command_box = ScrolledText(
            right,
            height=12,
            wrap="word",
            bg="#0b1220",
            fg="#d1d5db",
            insertbackground="#ffffff",
            relief="flat",
            font=("Consolas", 10),
        )
        self.tools_command_box.pack(fill="both", expand=True, pady=(12, 0))
        self.tools_command_box.configure(state="disabled")

    def build_console_tab(self):
        top = ttk.Frame(self.tab_console, style="Root.TFrame")
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(top, text="🖥️ Consola / Log", style="Title.TLabel").pack(side="left")

        self.autoscroll_bool = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(
            top,
            text="Auto-scroll",
            variable=self.autoscroll_bool,
            command=self.on_check_change_console,
        )
        cb.pack(side="right", padx=(8, 0))

        ttk.Button(top, text="🧹 Limpiar consola", command=self.clear_console).pack(side="right")

        self.console = ScrolledText(
            self.tab_console,
            wrap="word",
            bg="#030712",
            fg="#e5e7eb",
            insertbackground="#ffffff",
            relief="flat",
            font=("Consolas", 10),
        )
        self.console.pack(fill="both", expand=True)

        self.log("Listo. Panel Tabpage iniciado.")
        self.log("Usa INICIO para iniciar/detener/detectar, OPCIONES para editar argumentos y CONSOLA para ver logs.")
        if self.is_admin():
            self.log("[ADMIN] El panel se está ejecutando con privilegios de administrador.")
        else:
            self.log("[ADMIN] El panel NO está como administrador. Si aparece Access is denied en TunnelV2, usa Herramientas > Crear URLACL V2 o reinicia como Admin.")
        if HAS_TRAY:
            self.log("[TRAY] Soporte de bandeja disponible: pystray + pillow detectados.")
        else:
            self.log("[TRAY] Soporte de bandeja no disponible. Instala con: pip install pystray pillow")

    def build_about_tab(self):
        body = self.make_card(self.tab_about)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="ℹ️ Acerca del proyecto", style="Card.TLabel", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            body,
            text=(
                "Este panel fue creado para administrar cncnet-server.exe de forma más cómoda, "
                "sin tener que escribir todos los argumentos manualmente cada vez."
            ),
            style="Card.TLabel",
            wraplength=900,
        ).pack(anchor="w", pady=(10, 16))

        text = (
            "Características:\n"
            "• Panel con pestañas tipo Tabpage.\n"
            "• Inicio rápido para iniciar, detener y detectar procesos.\n"
            "• Opciones separadas para argumentos del servidor.\n"
            "• Master URL y contraseñas en sección independiente.\n"
            "• Herramientas de diagnóstico.\n"
            "• Consola integrada con salida del proceso.\n"
            "• Guardado en cncnet_server_gui.ini.\n"
            "• Detección de procesos abiertos fuera del panel.\n"
            "• Minimizar a bandeja de Windows.\n"
            "• Opción para mantener la ventana siempre encima.\n\n"
            "Dependencias opcionales para bandeja:\n"
            "pip install pystray pillow\n\n"
            "Consejos:\n"
            "• Ejecuta el panel como administrador si necesitas cerrar procesos externos.\n"
            "• Abre los puertos en Firewall de Windows.\n"
            "• Si estás detrás de router, haz port forwarding.\n"
            "• Para aparecer públicamente, no actives --nomaster.\n"
            "• Si aparece System.Net.HttpListenerException: Access is denied, ejecuta como administrador o crea la URLACL del puerto V2.\n• Si hay problemas de conexión, prueba primero con --nop2p desactivado.\n\n"
            "Créditos:\n"
            "ChatGPT OpenAI y Azzlaer para LatinBattle.com"
        )

        info = ScrolledText(
            body,
            wrap="word",
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10),
        )
        info.pack(fill="both", expand=True)
        info.insert("end", text)
        info.configure(state="disabled")

    # ============================================================
    # UI HELPERS
    # ============================================================

    def add_file_row(self, parent, row, label, key):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        entry = ttk.Entry(parent, textvariable=self.vars[key])
        entry.grid(row=row, column=1, sticky="ew", pady=5, padx=(8, 8))
        entry.bind("<KeyRelease>", lambda _e: self.on_config_changed())
        ttk.Button(parent, text="Buscar", command=self.browse_exe).grid(row=row, column=2, sticky="ew", pady=5)

    def add_entry(self, parent, row, label, key, show=None):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=5)
        entry = ttk.Entry(parent, textvariable=self.vars[key], show=show)
        entry.grid(row=row, column=1, sticky="ew", pady=5, padx=(8, 0))
        entry.bind("<KeyRelease>", lambda _e: self.on_config_changed())
        return entry

    def add_pack_entry(self, parent, label, key, show=None):
        ttk.Label(parent, text=label, style="Card.TLabel").pack(anchor="w", pady=(0, 5))
        entry = ttk.Entry(parent, textvariable=self.vars[key], show=show)
        entry.pack(fill="x")
        entry.bind("<KeyRelease>", lambda _e: self.on_config_changed())
        return entry

    def on_config_changed(self):
        self.refresh_command()
        self.refresh_home_cards()

    def sync_checkboxes_to_vars(self):
        if hasattr(self, "nomaster_bool"):
            self.vars["nomaster"].set("true" if self.nomaster_bool.get() else "false")
        if hasattr(self, "nop2p_bool"):
            self.vars["nop2p"].set("true" if self.nop2p_bool.get() else "false")
        if hasattr(self, "autoscroll_bool"):
            self.vars["auto_scroll"].set("true" if self.autoscroll_bool.get() else "false")
        if hasattr(self, "autodetect_bool"):
            self.vars["auto_detect"].set("true" if self.autodetect_bool.get() else "false")
        if hasattr(self, "minimize_to_tray_bool"):
            self.vars["minimize_to_tray"].set("true" if self.minimize_to_tray_bool.get() else "false")
        if hasattr(self, "always_on_top_bool"):
            self.vars["always_on_top"].set("true" if self.always_on_top_bool.get() else "false")

    def refresh_checkboxes_from_vars(self):
        if hasattr(self, "nomaster_bool"):
            self.nomaster_bool.set(self.vars["nomaster"].get().lower() == "true")
        if hasattr(self, "nop2p_bool"):
            self.nop2p_bool.set(self.vars["nop2p"].get().lower() == "true")
        if hasattr(self, "autoscroll_bool"):
            self.autoscroll_bool.set(self.vars["auto_scroll"].get().lower() == "true")
        if hasattr(self, "autodetect_bool"):
            self.autodetect_bool.set(self.vars["auto_detect"].get().lower() == "true")
        if hasattr(self, "minimize_to_tray_bool"):
            self.minimize_to_tray_bool.set(self.vars["minimize_to_tray"].get().lower() == "true")
        if hasattr(self, "always_on_top_bool"):
            self.always_on_top_bool.set(self.vars["always_on_top"].get().lower() == "true")
            self.apply_always_on_top(log=False)

    def on_check_change(self):
        self.sync_checkboxes_to_vars()
        self.refresh_command()
        self.refresh_home_cards()
        self.apply_always_on_top(log=False)

    def on_check_change_console(self):
        self.sync_checkboxes_to_vars()

    def browse_exe(self):
        filetypes = [("Ejecutable", "*.exe"), ("Todos los archivos", "*.*")]
        current = self.vars["exe_path"].get().strip()
        initial = str(Path(current).parent) if current else str(BASE_DIR)

        path = filedialog.askopenfilename(
            title="Seleccionar cncnet-server.exe",
            filetypes=filetypes,
            initialdir=initial,
        )
        if path:
            self.vars["exe_path"].set(path)
            self.set_process_name_from_exe(silent=True)
            self.refresh_command()
            self.refresh_home_cards()

    def set_process_name_from_exe(self, silent=False):
        exe_name = Path(self.vars["exe_path"].get().strip()).name
        if exe_name:
            self.vars["process_name"].set(exe_name)
            if not silent:
                self.log(f"[CONFIG] Proceso a detectar configurado como: {exe_name}")
        self.refresh_home_cards()

    def refresh_home_cards(self):
        if hasattr(self, "card_server_name"):
            self.card_server_name.value_label.configure(text=self.vars["name"].get().strip() or "-")

        if hasattr(self, "card_ports"):
            self.card_ports.value_label.configure(
                text=f"{self.vars['port'].get().strip()} / V2 {self.vars['portv2'].get().strip()}"
            )

        if hasattr(self, "card_clients"):
            self.card_clients.value_label.configure(text=self.vars["maxclients"].get().strip() or "-")

        if hasattr(self, "card_master"):
            nomaster = self.vars["nomaster"].get().lower() == "true"
            self.card_master.value_label.configure(text="Desactivado" if nomaster else "Activo")

        if hasattr(self, "process_label"):
            self.process_label.configure(text=f"Proceso: {self.vars['process_name'].get().strip() or '-'}")

    def clear_console(self):
        if hasattr(self, "console"):
            self.console.delete("1.0", "end")

    def open_app_folder(self):
        try:
            os.startfile(str(BASE_DIR))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def copy_command(self):
        command = self.get_command_text()
        self.clipboard_clear()
        self.clipboard_append(command)
        self.log("[CLIPBOARD] Comando copiado al portapapeles.")

    # ============================================================
    # COMMAND
    # ============================================================

    def build_args(self, include_exe=True):
        self.sync_checkboxes_to_vars()

        exe = self.vars["exe_path"].get().strip()
        args = []

        if include_exe:
            args.append(exe)

        def add_value(flag, key):
            value = self.vars[key].get().strip()
            if value != "":
                args.extend([flag, value])

        add_value("--port", "port")
        add_value("--portv2", "portv2")
        add_value("--name", "name")
        add_value("--maxclients", "maxclients")

        if self.vars["nomaster"].get().lower() == "true":
            args.append("--nomaster")

        add_value("--masterpw", "masterpw")
        add_value("--maintpw", "maintpw")
        add_value("--master", "master")
        add_value("--iplimit", "iplimit")
        add_value("--iplimitv2", "iplimitv2")

        if self.vars["nop2p"].get().lower() == "true":
            args.append("--nop2p")

        return args

    def quote_command(self, args):
        if os.name == "nt":
            return subprocess.list2cmdline(args)
        return " ".join(shlex.quote(a) for a in args)

    def get_command_text(self):
        return self.quote_command(self.build_args(include_exe=True))

    def refresh_command(self):
        command = self.get_command_text()

        for box_name in ("home_command_box", "tools_command_box"):
            box = getattr(self, box_name, None)
            if box:
                box.configure(state="normal")
                box.delete("1.0", "end")
                box.insert("end", command)
                box.configure(state="disabled")

    def validate_form(self):
        exe = Path(self.vars["exe_path"].get().strip())
        if not exe.exists():
            messagebox.showerror("Ejecutable no encontrado", f"No existe el archivo:\n{exe}")
            return False

        int_fields = {
            "port": "Puerto",
            "portv2": "Puerto V2",
            "maxclients": "Máx. clientes",
            "iplimit": "Límite por IP",
            "iplimitv2": "Límite IP V2",
            "monitor_interval": "Intervalo monitor ms",
        }

        for key, label in int_fields.items():
            value = self.vars[key].get().strip()
            try:
                number = int(value)
            except ValueError:
                messagebox.showerror("Valor inválido", f"{label} debe ser numérico.")
                return False

            if key in ("port", "portv2") and not (1 <= number <= 65535):
                messagebox.showerror("Puerto inválido", f"{label} debe estar entre 1 y 65535.")
                return False

            if key == "monitor_interval" and number < 1000:
                messagebox.showerror("Intervalo inválido", "El intervalo de monitor debe ser mínimo 1000 ms.")
                return False

            if key not in ("port", "portv2", "monitor_interval") and number < 0:
                messagebox.showerror("Valor inválido", f"{label} no puede ser negativo.")
                return False

        return True

    # ============================================================
    # PROCESS CONTROL
    # ============================================================

    def start_server(self):
        if self.process and self.process.poll() is None:
            messagebox.showinfo("Servidor activo", "El servidor ya está iniciado desde este GUI.")
            return

        already = self.find_processes()
        if already:
            answer = messagebox.askyesno(
                "Proceso detectado",
                "Ya existe un proceso cncnet-server abierto.\n\n"
                f"PID(s): {', '.join(map(str, already))}\n\n"
                "¿Quieres iniciar otra instancia de todas formas?",
            )
            if not answer:
                self.log(f"[START] Cancelado. Ya existe proceso detectado: {already}")
                return

        if not self.validate_form():
            return

        self.save_config()
        args = self.build_args(include_exe=True)
        exe_path = Path(self.vars["exe_path"].get().strip())

        self.log("[START] Ejecutando:")
        self.log(self.quote_command(args))

        try:
            self.stop_reader.clear()
            self.process = subprocess.Popen(
                args,
                cwd=str(exe_path.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as e:
            self.process = None
            messagebox.showerror("Error al iniciar", str(e))
            self.log(f"[ERROR] {e}")
            self.set_status("Estado: error al iniciar", "Bad.TLabel")
            return

        self.set_status(f"Estado: iniciado por GUI | PID: {self.process.pid}", "Ok.TLabel")
        self.set_pid_text([self.process.pid])

        self.reader_thread = threading.Thread(target=self.read_process_output, daemon=True)
        self.reader_thread.start()

    def read_process_output(self):
        if not self.process or not self.process.stdout:
            return

        try:
            for line in self.process.stdout:
                if self.stop_reader.is_set():
                    break
                self.output_queue.put(line.rstrip("\n"))
        except Exception as e:
            self.output_queue.put(f"[READER ERROR] {e}")

        code = self.process.poll()
        if code is not None:
            self.output_queue.put(f"[EXIT] Proceso finalizado con código: {code}")

    def stop_server(self):
        if not self.process or self.process.poll() is not None:
            self.log("[STOP] No hay proceso iniciado por este GUI.")
            self.refresh_process_status()
            return

        self.log("[STOP] Deteniendo servidor iniciado por GUI...")
        self.stop_reader.set()

        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.log("[STOP] No respondió a terminate(); forzando kill().")
                self.process.kill()
                self.process.wait(timeout=5)
        except Exception as e:
            self.log(f"[ERROR STOP] {e}")

        self.refresh_process_status()

    def run_info_command(self, flag):
        exe = Path(self.vars["exe_path"].get().strip())
        if not exe.exists():
            messagebox.showerror("Ejecutable no encontrado", f"No existe el archivo:\n{exe}")
            return

        self.log(f"[INFO] Ejecutando {flag}...")
        try:
            result = subprocess.run(
                [str(exe), flag],
                cwd=str(exe.parent),
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            output = (result.stdout or "") + (result.stderr or "")
            if output.strip():
                self.log(output.strip())
            else:
                self.log(f"[INFO] Sin salida para {flag}. Código: {result.returncode}")
        except Exception as e:
            self.log(f"[ERROR INFO] {e}")

    # ============================================================
    # PROCESS DETECTION
    # ============================================================

    def monitor_process_loop(self):
        if hasattr(self, "autodetect_bool") and self.autodetect_bool.get():
            self.refresh_process_status(log_changes_only=True)

        try:
            interval = int(self.vars["monitor_interval"].get().strip())
        except Exception:
            interval = 3000

        self.after(max(interval, 1000), self.monitor_process_loop)

    def detect_process_manual(self):
        pids = self.find_processes()
        self.detected_pids = pids
        self.last_detected_pids = pids.copy()

        if pids:
            self.log(f"[DETECT] Proceso detectado PID(s): {', '.join(map(str, pids))}")
        else:
            self.log("[DETECT] No se encontró proceso activo.")

        self.refresh_process_status(log_changes_only=False)

    def refresh_process_status(self, log_changes_only=False):
        pids = self.find_processes()
        self.detected_pids = pids

        gui_pid = None
        gui_running = False
        if self.process and self.process.poll() is None:
            gui_pid = self.process.pid
            gui_running = True

        external_pids = [pid for pid in pids if pid != gui_pid]

        if gui_running:
            self.set_status(f"Estado: iniciado por GUI | PID: {gui_pid}", "Ok.TLabel")
            self.set_pid_text([gui_pid] + external_pids)
            if external_pids:
                self.detect_label.configure(text=f"Detección: además hay proceso externo PID(s): {', '.join(map(str, external_pids))}")
            else:
                self.detect_label.configure(text="Detección: proceso activo controlado por GUI")
        elif external_pids:
            self.set_status("Estado: detectado externo", "Warn.TLabel")
            self.set_pid_text(external_pids)
            self.detect_label.configure(text=f"Detección: abierto fuera del GUI | PID(s): {', '.join(map(str, external_pids))}")
        else:
            self.set_status("Estado: detenido", "Bad.TLabel")
            self.set_pid_text([])
            self.detect_label.configure(text="Detección: no hay proceso activo")

        if log_changes_only and pids != self.last_detected_pids:
            if pids:
                self.log(f"[MONITOR] Cambio detectado. PID(s) activos: {', '.join(map(str, pids))}")
            else:
                self.log("[MONITOR] Cambio detectado. Ya no hay proceso activo.")
            self.last_detected_pids = pids.copy()

    def find_processes(self):
        names = self.get_process_names_to_check()

        if os.name == "nt":
            return self.find_processes_windows(names)

        return self.find_processes_unix(names)

    def get_process_names_to_check(self):
        configured = self.vars["process_name"].get().strip()
        exe_name = Path(self.vars["exe_path"].get().strip()).name

        names = []
        for item in [configured, exe_name, *PROCESS_NAMES]:
            item = item.strip()
            if item and item.lower() not in [n.lower() for n in names]:
                names.append(item)
        return names

    def find_processes_windows(self, names):
        pids = []

        for name in names:
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                output = (result.stdout or "").strip()

                if not output or "No tasks are running" in output or "INFO:" in output:
                    continue

                for line in output.splitlines():
                    parts = self.parse_tasklist_csv_line(line)
                    if len(parts) >= 2:
                        image_name = parts[0]
                        pid_text = parts[1]
                        if image_name.lower() == name.lower() and pid_text.isdigit():
                            pid = int(pid_text)
                            if pid not in pids:
                                pids.append(pid)
            except Exception:
                continue

        return sorted(pids)

    def parse_tasklist_csv_line(self, line):
        line = line.strip()
        if not line:
            return []

        items = []
        current = ""
        inside_quotes = False

        for char in line:
            if char == '"':
                inside_quotes = not inside_quotes
            elif char == "," and not inside_quotes:
                items.append(current)
                current = ""
            else:
                current += char

        items.append(current)
        return [x.strip().strip('"') for x in items]

    def find_processes_unix(self, names):
        pids = []

        try:
            result = subprocess.run(
                ["ps", "-ax", "-o", "pid=,comm="],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue

                parts = line.split(None, 1)
                if len(parts) != 2:
                    continue

                pid_text, command = parts
                for name in names:
                    if Path(command).name.lower() == name.lower() and pid_text.isdigit():
                        pid = int(pid_text)
                        if pid not in pids:
                            pids.append(pid)
        except Exception:
            pass

        return sorted(pids)

    def stop_detected_processes(self):
        pids = self.find_processes()

        gui_pid = None
        if self.process and self.process.poll() is not None:
            self.process = None
        elif self.process and self.process.poll() is None:
            gui_pid = self.process.pid

        external_pids = [pid for pid in pids if pid != gui_pid]

        if not external_pids and not gui_pid:
            messagebox.showinfo("Sin proceso", "No hay procesos detectados para detener.")
            return

        text = []
        if gui_pid:
            text.append(f"Proceso iniciado por GUI: {gui_pid}")
        if external_pids:
            text.append(f"Proceso(s) externo(s): {', '.join(map(str, external_pids))}")

        if not messagebox.askyesno(
            "Detener procesos",
            "Se intentará detener:\n\n" + "\n".join(text) + "\n\n¿Continuar?",
        ):
            return

        if gui_pid:
            self.stop_server()

        for pid in external_pids:
            self.kill_pid(pid)

        self.refresh_process_status(log_changes_only=False)

    def kill_pid(self, pid):
        self.log(f"[KILL] Intentando detener PID {pid}...")

        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                result = subprocess.run(
                    ["kill", "-TERM", str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

            output = ((result.stdout or "") + (result.stderr or "")).strip()
            if output:
                self.log(output)

            self.log(f"[KILL] Código resultado PID {pid}: {result.returncode}")
        except Exception as e:
            self.log(f"[KILL ERROR] PID {pid}: {e}")


    # ============================================================
    # ADMIN / URLACL
    # ============================================================

    def is_admin(self):
        """Devuelve True si el proceso actual tiene privilegios de administrador."""
        if os.name != "nt":
            return os.geteuid() == 0 if hasattr(os, "geteuid") else False

        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def check_admin_status(self):
        if self.is_admin():
            self.log("[ADMIN] OK: El GUI está ejecutándose como administrador.")
            messagebox.showinfo("Permisos", "El GUI está ejecutándose como administrador.")
        else:
            self.log("[ADMIN] AVISO: El GUI NO está ejecutándose como administrador.")
            messagebox.showwarning(
                "Permisos",
                "El GUI NO está ejecutándose como administrador.\n\n"
                "Para solucionar System.Net.HttpListenerException: Access is denied, "
                "puedes usar 'Reiniciar GUI como Admin' o ejecutar manualmente la reserva URLACL.",
            )

    def restart_as_admin(self):
        """Reinicia este script con elevación UAC en Windows."""
        if os.name != "nt":
            messagebox.showinfo("No disponible", "Esta función de elevación automática está pensada para Windows.")
            return

        if self.is_admin():
            messagebox.showinfo("Administrador", "El GUI ya está ejecutándose como administrador.")
            return

        if not messagebox.askyesno(
            "Reiniciar como administrador",
            "El panel se cerrará y Windows pedirá permiso UAC para volver a abrirlo como administrador.\n\n"
            "¿Continuar?",
        ):
            return

        try:
            script = Path(__file__).resolve()
            if getattr(sys, "frozen", False):
                params = ""
                executable = str(Path(sys.executable).resolve())
            else:
                params = f'"{script}"'
                executable = str(Path(sys.executable).resolve())

            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                executable,
                params,
                str(BASE_DIR),
                1,
            )
            self.destroy()
        except Exception as e:
            self.log(f"[ADMIN ERROR] No se pudo reiniciar como administrador: {e}")
            messagebox.showerror("Error", str(e))

    def get_urlacl_url_v2(self):
        try:
            port = int(self.vars["portv2"].get().strip())
        except Exception:
            port = 50000
        return f"http://+:{port}/"

    def add_urlacl_v2(self):
        """
        Crea una reserva URLACL para que HttpListener pueda escuchar en el puerto V2
        sin lanzar System.Net.HttpListenerException: Access is denied.
        """
        if os.name != "nt":
            messagebox.showinfo("No disponible", "URLACL con netsh http aplica a Windows.")
            return

        url = self.get_urlacl_url_v2()
        user = os.environ.get("USERNAME", "")
        domain = os.environ.get("USERDOMAIN", "")
        full_user = f"{domain}\\{user}" if domain and user else user

        if not full_user:
            full_user = "Everyone"

        if not self.is_admin():
            if not messagebox.askyesno(
                "Requiere administrador",
                "Para crear URLACL normalmente necesitas ejecutar el GUI como administrador.\n\n"
                "¿Quieres intentar reiniciar el GUI como administrador ahora?",
            ):
                self.log("[URLACL] Cancelado: el GUI no está como administrador.")
                return
            self.restart_as_admin()
            return

        cmd = ["netsh", "http", "add", "urlacl", f"url={url}", f"user={full_user}"]
        self.log("[URLACL] Ejecutando:")
        self.log(" ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            output = ((result.stdout or "") + (result.stderr or "")).strip()
            if output:
                self.log(output)

            if result.returncode == 0:
                self.log(f"[URLACL] OK: Reserva creada para {url} usuario {full_user}")
                messagebox.showinfo("URLACL creada", f"Reserva creada:\n{url}\n\nUsuario:\n{full_user}")
            else:
                self.log(f"[URLACL] Código: {result.returncode}")
                messagebox.showwarning(
                    "URLACL",
                    "No se pudo crear la URLACL o ya existe.\n\n"
                    "Revisa la consola del panel para ver el mensaje de netsh.",
                )
        except Exception as e:
            self.log(f"[URLACL ERROR] {e}")
            messagebox.showerror("URLACL error", str(e))

    def delete_urlacl_v2(self):
        """Elimina la reserva URLACL del puerto V2 configurado."""
        if os.name != "nt":
            messagebox.showinfo("No disponible", "URLACL con netsh http aplica a Windows.")
            return

        url = self.get_urlacl_url_v2()

        if not self.is_admin():
            if not messagebox.askyesno(
                "Requiere administrador",
                "Para eliminar URLACL normalmente necesitas ejecutar el GUI como administrador.\n\n"
                "¿Quieres intentar reiniciar el GUI como administrador ahora?",
            ):
                self.log("[URLACL] Cancelado: el GUI no está como administrador.")
                return
            self.restart_as_admin()
            return

        if not messagebox.askyesno("Eliminar URLACL", f"¿Eliminar la reserva URLACL?\n\n{url}"):
            return

        cmd = ["netsh", "http", "delete", "urlacl", f"url={url}"]
        self.log("[URLACL] Ejecutando:")
        self.log(" ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            output = ((result.stdout or "") + (result.stderr or "")).strip()
            if output:
                self.log(output)

            if result.returncode == 0:
                self.log(f"[URLACL] OK: Reserva eliminada para {url}")
                messagebox.showinfo("URLACL eliminada", f"Reserva eliminada:\n{url}")
            else:
                self.log(f"[URLACL] Código: {result.returncode}")
                messagebox.showwarning(
                    "URLACL",
                    "No se pudo eliminar la URLACL.\n\n"
                    "Revisa la consola del panel para ver el mensaje de netsh.",
                )
        except Exception as e:
            self.log(f"[URLACL ERROR] {e}")
            messagebox.showerror("URLACL error", str(e))


    # ============================================================
    # TOOLS
    # ============================================================

    def test_ports(self):
        ports = []

        for key in ("port", "portv2"):
            try:
                ports.append(int(self.vars[key].get().strip()))
            except ValueError:
                pass

        if self.vars["nop2p"].get().lower() != "true":
            ports.extend([8054, 3478])

        self.log("[PORT TEST] Revisando si los puertos locales parecen libres...")

        for port in sorted(set(ports)):
            free = self.is_tcp_port_free(port)
            if free:
                self.log(f"[OK] TCP {port} parece libre para escuchar.")
            else:
                self.log(f"[WARN] TCP {port} parece ocupado localmente o bloqueado.")

        if self.vars["nop2p"].get().lower() != "true":
            self.log("[INFO] NAT traversal usa UDP 8054 y 3478; esta prueba TCP solo orienta.")
        self.log("[INFO] Para servidor público, abre/redirige puertos en Firewall/Router/VPS.")

    def is_tcp_port_free(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)

        try:
            sock.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False
        finally:
            try:
                sock.close()
            except Exception:
                pass


    # ============================================================
    # TRAY / ALWAYS ON TOP
    # ============================================================

    def apply_always_on_top(self, log=True):
        """Aplica o quita el modo siempre encima."""
        enabled = self.vars.get("always_on_top", tk.StringVar(value="false")).get().lower() == "true"
        try:
            self.attributes("-topmost", bool(enabled))
            if enabled:
                self.lift()
            if log:
                self.log("[WINDOW] Siempre encima activado." if enabled else "[WINDOW] Siempre encima desactivado.")
        except Exception as e:
            if log:
                self.log(f"[WINDOW ERROR] No se pudo aplicar siempre encima: {e}")

    def on_window_unmap(self, _event=None):
        """
        Cuando el usuario minimiza la ventana, si la opción está activa,
        la mandamos a la bandeja.
        """
        if self._minimize_event_guard:
            return

        try:
            is_iconic = self.state() == "iconic"
        except Exception:
            is_iconic = False

        enabled = self.vars.get("minimize_to_tray", tk.StringVar(value="false")).get().lower() == "true"

        if enabled and is_iconic:
            self.after(150, self.minimize_to_tray)

    def create_tray_image(self):
        """Crea un icono simple para la bandeja."""
        if not HAS_TRAY:
            return None

        image = Image.new("RGBA", (64, 64), (15, 23, 42, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((6, 6, 58, 58), radius=12, fill=(37, 99, 235, 255))
        draw.ellipse((20, 14, 44, 38), fill=(255, 255, 255, 255))
        draw.rectangle((16, 40, 48, 48), fill=(255, 255, 255, 255))
        draw.text((22, 48), "CN", fill=(255, 255, 255, 255))
        return image

    def minimize_to_tray(self):
        """Oculta la ventana y crea icono en bandeja."""
        if not HAS_TRAY:
            self.log("[TRAY] No disponible. Instala dependencias con: pip install pystray pillow")
            messagebox.showwarning(
                "Bandeja no disponible",
                "Para minimizar a la bandeja necesitas instalar:\n\n"
                "pip install pystray pillow\n\n"
                "Luego vuelve a abrir el panel.",
            )
            return

        if self.tray_icon is None:
            self.create_tray_icon()

        self._minimize_event_guard = True
        try:
            self.withdraw()
            self.log("[TRAY] Panel minimizado a la bandeja de Windows.")
        finally:
            self.after(300, self.clear_minimize_guard)

    def clear_minimize_guard(self):
        self._minimize_event_guard = False

    def create_tray_icon(self):
        if not HAS_TRAY:
            return

        def show_action(_icon=None, _item=None):
            self.after(0, self.show_from_tray)

        def start_action(_icon=None, _item=None):
            self.after(0, self.start_server)

        def stop_action(_icon=None, _item=None):
            self.after(0, self.stop_detected_processes)

        def exit_action(_icon=None, _item=None):
            self.after(0, self.exit_from_tray)

        menu = pystray.Menu(
            pystray.MenuItem("Mostrar panel", show_action),
            pystray.MenuItem("Iniciar servidor", start_action),
            pystray.MenuItem("Detener detectado", stop_action),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", exit_action),
        )

        self.tray_icon = pystray.Icon(
            "CnCNet Tunnel Server GUI",
            self.create_tray_image(),
            "CnCNet Tunnel Server GUI",
            menu,
        )

        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def show_from_tray(self):
        """Restaura el panel desde la bandeja."""
        try:
            self.deiconify()
            self.state("normal")
            self.lift()
            self.focus_force()
            self.apply_always_on_top(log=False)
            self.log("[TRAY] Panel restaurado desde la bandeja.")
        except Exception as e:
            self.log(f"[TRAY ERROR] No se pudo restaurar: {e}")

    def stop_tray_icon(self):
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None

    def exit_from_tray(self):
        self.force_exit = True
        self.stop_tray_icon()
        self.on_close()


    # ============================================================
    # LOG / STATUS
    # ============================================================

    def set_status(self, text, style_name="Card.TLabel"):
        if hasattr(self, "status_label"):
            self.status_label.configure(text=text, style=style_name)

    def set_pid_text(self, pids):
        if hasattr(self, "pid_label"):
            if pids:
                self.pid_label.configure(text=f"PID: {', '.join(map(str, pids))}")
            else:
                self.pid_label.configure(text="PID: ninguno")

    def log(self, text):
        if not hasattr(self, "console"):
            return

        timestamp = time.strftime("%H:%M:%S")

        for line in str(text).splitlines() or [""]:
            self.console.insert("end", f"[{timestamp}] {line}\n")

        if hasattr(self, "autoscroll_bool") and self.autoscroll_bool.get():
            self.console.see("end")

    def drain_output_queue(self):
        try:
            while True:
                line = self.output_queue.get_nowait()
                self.log(line)
        except queue.Empty:
            pass

        if self.process and self.process.poll() is not None:
            self.refresh_process_status(log_changes_only=False)

        self.after(150, self.drain_output_queue)

    def on_close(self):
        self.sync_checkboxes_to_vars()

        tray_enabled = self.vars.get("minimize_to_tray", tk.StringVar(value="false")).get().lower() == "true"

        if tray_enabled and not self.force_exit:
            self.minimize_to_tray()
            return

        if self.process and self.process.poll() is None:
            if not messagebox.askyesno(
                "Servidor activo",
                "El servidor iniciado por este GUI sigue activo.\n\n¿Deseas detenerlo y salir?",
            ):
                return
            self.stop_server()

        self.save_config()
        self.stop_tray_icon()
        self.destroy()


if __name__ == "__main__":
    app = CnCNetServerGUI()
    app.mainloop()
