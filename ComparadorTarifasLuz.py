import json
import os
import sys
import subprocess
import urllib.request
import threading
import ctypes
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- REPORTLAB PARA GENERACIÓN DE PDF ---
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- TRUCO PARA MOSTRAR ICONO PERSONALIZADO EN LA BARRA DE TAREAS DE WINDOWS ---
try:
    myappid = 'sokychan.energycompare.pro.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# --- CONFIGURACIÓN DE VERSIÓN Y RUTAS REMOTAS ---
VERSION_ACTUAL = "1.0.0"
URL_VERSION_REMOTA = "https://raw.githubusercontent.com/Sokychan/ComparadorTarifasLuz/main/version.json"
URL_TARIFAS_RAW = "https://raw.githubusercontent.com/Sokychan/ComparadorTarifasLuz/main/tarifas_mercado.json"

# --- PALETA DE COLORES MODERNA ---
COLOR_BG_MAIN = "#0F172A"       
COLOR_CARD_BG = "#1E293B"       
COLOR_CARD_BORDER = "#334155"   
COLOR_ACCENT_BLUE = "#1F6AA5"   
COLOR_ACCENT_GREEN = "#2FA572"  
COLOR_TEXT_MAIN = "#F8FAFC"     
COLOR_TEXT_MUTED = "#94A3B8"    
COLOR_ACCENT_GOLD = "#F59E0B"

DATA_FILE = "tarifas_mercado.json"

# --- COSTES REGULADOS NORMADOS ---
ALQUILER_DIARIO = 0.026562      # €/día equipo de medida
BONO_SOCIAL_DIARIO = 0.024688   # €/día financiación bono social

# --- DATOS DE SEMILLA (Fallback inicial) ---
DATOS_SEMILLA = [
    {"Comercializadora": "Endesa", "Nombre_Tarifa": "Conecta 24h", "Modalidad": "24h", "Potencia_P1": 0.0920, "Potencia_P2": 0.0120, "Precio_Energia_24h": 0.1160, "P1": 0.0, "P2": 0.0, "P3": 0.0},
    {"Comercializadora": "Nufri", "Nombre_Tarifa": "Transparente 24h", "Modalidad": "24h", "Potencia_P1": 0.0850, "Potencia_P2": 0.0140, "Precio_Energia_24h": 0.1170, "P1": 0.0, "P2": 0.0, "P3": 0.0},
    {"Comercializadora": "Octopus Energy", "Nombre_Tarifa": "Octopus Relax 24h", "Modalidad": "24h", "Potencia_P1": 0.0890, "Potencia_P2": 0.0220, "Precio_Energia_24h": 0.1180, "P1": 0.0, "P2": 0.0, "P3": 0.0},
    {"Comercializadora": "Iberdrola", "Nombre_Tarifa": "Plan Online 24h", "Modalidad": "24h", "Potencia_P1": 0.0821, "Potencia_P2": 0.0112, "Precio_Energia_24h": 0.1190, "P1": 0.0, "P2": 0.0, "P3": 0.0},
    {"Comercializadora": "TotalEnergies", "Nombre_Tarifa": "A Tu Aire 24h", "Modalidad": "24h", "Potencia_P1": 0.0875, "Potencia_P2": 0.0135, "Precio_Energia_24h": 0.1195, "P1": 0.0, "P2": 0.0, "P3": 0.0},
    {"Comercializadora": "Nufri", "Nombre_Tarifa": "Transparente Tramos", "Modalidad": "Tramos", "Potencia_P1": 0.0850, "Potencia_P2": 0.0140, "Precio_Energia_24h": 0.0, "P1": 0.1680, "P2": 0.1190, "P3": 0.0820},
    {"Comercializadora": "Octopus Energy", "Nombre_Tarifa": "Octopus 3 Tramos", "Modalidad": "Tramos", "Potencia_P1": 0.0890, "Potencia_P2": 0.0220, "Precio_Energia_24h": 0.0, "P1": 0.1690, "P2": 0.1210, "P3": 0.0850},
    {"Comercializadora": "Endesa", "Nombre_Tarifa": "One Luz Tramos", "Modalidad": "Tramos", "Potencia_P1": 0.0920, "Potencia_P2": 0.0120, "Precio_Energia_24h": 0.0, "P1": 0.1710, "P2": 0.1220, "P3": 0.0840},
    {"Comercializadora": "Iberdrola", "Nombre_Tarifa": "Plan Online 3 Periodos", "Modalidad": "Tramos", "Potencia_P1": 0.0821, "Potencia_P2": 0.0112, "Precio_Energia_24h": 0.0, "P1": 0.1780, "P2": 0.1290, "P3": 0.0890}
]

def inicializar_json_si_no_existe():
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DATOS_SEMILLA, f, ensure_ascii=False, indent=2)

# --- FUNCIONES DE ACTUALIZACIÓN AUTOMÁTICA DEL EJECUTABLE ---
def verificar_actualizacion_app(parent_window):
    """Lanza la comprobación de versión en un hilo secundario."""
    threading.Thread(target=_ejecutar_comprobacion_app, args=(parent_window,), daemon=True).start()

def _ejecutar_comprobacion_app(parent_window):
    try:
        req = urllib.request.Request(URL_VERSION_REMOTA, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))

        version_remota = data.get("version", VERSION_ACTUAL)
        download_url = data.get("download_url", "")
        changelog = data.get("changelog", "Mejoras generales y corrección de errores.")

        if version_remota > VERSION_ACTUAL:
            parent_window.after(0, lambda: _notificar_y_descargar(parent_window, version_remota, download_url, changelog))
    except Exception as e:
        print(f"No se pudo consultar el servidor de actualizaciones: {e}")

def _notificar_y_descargar(parent_window, nueva_version, download_url, changelog):
    respuesta = messagebox.askyesno(
        "Nueva actualización disponible 🚀",
        f"Se ha encontrado la versión v{nueva_version} de EnergyCompare Pro.\n\n"
        f"Novedades:\n{changelog}\n\n"
        f"¿Deseas descargar la actualización automáticamente ahora?"
    )

    if respuesta and download_url:
        _ejecutar_proceso_actualizacion(download_url)

def _ejecutar_proceso_actualizacion(download_url):
    try:
        exe_actual = sys.executable
        directorio_actual = os.path.dirname(exe_actual)
        nuevo_exe = os.path.join(directorio_actual, "EnergyCompare_nueva_version.exe")
        bat_updater = os.path.join(directorio_actual, "updater.bat")

        req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(nuevo_exe, 'wb') as out_file:
            out_file.write(response.read())

        contenido_bat = f"""@echo off
timeout /t 2 /nobreak > nul
move /y "{nuevo_exe}" "{exe_actual}"
start "" "{exe_actual}"
del "%~f0"
"""
        with open(bat_updater, "w") as f:
            f.write(contenido_bat)

        subprocess.Popen([bat_updater], shell=True)
        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Error al actualizar", f"Ocurrió un error al instalar la actualización:\n{e}")

ctk.set_appearance_mode("Dark")

class AppProDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("EnergyCompare Pro")
        self.geometry("1180x820")
        self.minsize(1000, 700)
        self.configure(fg_color=COLOR_BG_MAIN)

        if os.path.exists("icono.ico"):
            try:
                self.iconbitmap("icono.ico")
            except Exception:
                pass

        self.mostrar_tarifa_actual = False
        self.ultimos_resultados = []
        self.ultimos_consumos = {}
        inicializar_json_si_no_existe()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.crear_sidebar()
        self.crear_area_principal()
        
        # Sincronizar la base de datos de tarifas desde GitHub Actions
        self.sincronizar_tarifas_github()

        # Comprobar si existe un ejecutable más nuevo en GitHub
        verificar_actualizacion_app(self)

    def sincronizar_tarifas_github(self):
        """Baja la versión más reciente de tarifas_mercado.json desde GitHub Raw."""
        def _tarea_descarga():
            try:
                req = urllib.request.Request(URL_TARIFAS_RAW, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    datos = json.loads(response.read().decode('utf-8'))

                if datos:
                    with open(DATA_FILE, "w", encoding="utf-8") as f:
                        json.dump(datos, f, ensure_ascii=False, indent=2)

                    self.lbl_status_dot.configure(text_color=COLOR_ACCENT_GREEN)
                    self.lbl_status.configure(text="Tarifas sincronizadas desde GitHub")
            except Exception as e:
                self.lbl_status_dot.configure(text_color=COLOR_ACCENT_GOLD)
                self.lbl_status.configure(text="Modo offline (Tarifas locales)")

        threading.Thread(target=_tarea_descarga, daemon=True).start()

    def crear_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=320, corner_radius=0, 
            fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # 1. Cabecera
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=15, pady=(12, 8), sticky="w")
        
        ctk.CTkLabel(logo_frame, text="⚡", font=ctk.CTkFont(size=20)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            logo_frame, text="EnergyCompare", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), 
            text_color=COLOR_TEXT_MAIN
        ).pack(side="left")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_CARD_BORDER).grid(row=1, column=0, padx=15, pady=(0, 6), sticky="ew")

        # 2. CONTENEDOR CON SCROLL
        self.scroll_form = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
            scrollbar_button_color=COLOR_CARD_BORDER,
            scrollbar_button_hover_color=COLOR_ACCENT_BLUE
        )
        self.scroll_form.grid(row=2, column=0, padx=5, pady=0, sticky="nsew")
        self.scroll_form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.scroll_form, text="CONFIGURACIÓN DE CONSUMO", 
            font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", padx=10, pady=(2, 4))

        self.seg_modalidad = ctk.CTkSegmentedButton(
            self.scroll_form, values=["Tarifa 24h", "Por Tramos"], 
            selected_color=COLOR_ACCENT_BLUE, selected_hover_color="#144870",
            height=28, font=ctk.CTkFont(size=11),
            command=self.cambiar_modalidad
        )
        self.seg_modalidad.set("Tarifa 24h")
        self.seg_modalidad.pack(fill="x", padx=10, pady=(0, 6))

        # Inputs
        self.frame_inputs = ctk.CTkFrame(self.scroll_form, fg_color="transparent")
        self.frame_inputs.pack(fill="x", padx=10)

        self.crear_label_input(self.frame_inputs, "Días de Facturación")
        self.entry_dias_factura = self.crear_entry_estilizado(self.frame_inputs, "Ej: 30")

        self.crear_label_input(self.frame_inputs, "Potencia Contratada P1 (kW)")
        self.entry_potencia_p1 = self.crear_entry_estilizado(self.frame_inputs, "Ej: 3.3")

        self.crear_label_input(self.frame_inputs, "Potencia Contratada P2 (kW)")
        self.entry_potencia_p2 = self.crear_entry_estilizado(self.frame_inputs, "Ej: 3.3")

        # Consumo 24h
        self.frame_24h = ctk.CTkFrame(self.frame_inputs, fg_color="transparent")
        self.crear_label_input(self.frame_24h, "Consumo Total (kWh)")
        self.entry_energia_24h = self.crear_entry_estilizado(self.frame_24h, "Ej: 250")
        self.frame_24h.pack(fill="x")

        # Consumo Tramos
        self.frame_tramos = ctk.CTkFrame(self.frame_inputs, fg_color="transparent")
        self.crear_label_input(self.frame_tramos, "Consumo Punta - P1 (kWh)")
        self.entry_p1 = self.crear_entry_estilizado(self.frame_tramos, "Ej: 90")
        self.crear_label_input(self.frame_tramos, "Consumo Llano - P2 (kWh)")
        self.entry_p2 = self.crear_entry_estilizado(self.frame_tramos, "Ej: 80")
        self.crear_label_input(self.frame_tramos, "Consumo Valle - P3 (kWh)")
        self.entry_p3 = self.crear_entry_estilizado(self.frame_tramos, "Ej: 110")

        # Desplegable Tarifa Actual
        self.btn_toggle_actual = ctk.CTkButton(
            self.scroll_form, 
            text="▶  Comparar con mi Tarifa Actual", 
            fg_color="transparent", 
            hover_color=COLOR_CARD_BORDER,
            anchor="w", height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
            command=self.toggle_tarifa_actual
        )
        self.btn_toggle_actual.pack(fill="x", padx=5, pady=(8, 4))

        self.frame_tarifa_actual = ctk.CTkFrame(
            self.scroll_form, fg_color=COLOR_BG_MAIN, 
            border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=6
        )

        self.crear_label_input(self.frame_tarifa_actual, "Precio Potencia P1 (€/kW·día)", pad_x=10)
        self.entry_precio_potencia_p1 = self.crear_entry_estilizado(self.frame_tarifa_actual, "Ej: 0.084312", pad_x=10)

        self.crear_label_input(self.frame_tarifa_actual, "Precio Potencia P2 (€/kW·día)", pad_x=10)
        self.entry_precio_potencia_p2 = self.crear_entry_estilizado(self.frame_tarifa_actual, "Ej: 0.002815", pad_x=10)

        self.frame_actual_24h = ctk.CTkFrame(self.frame_tarifa_actual, fg_color="transparent")
        self.crear_label_input(self.frame_actual_24h, "Precio Energía 24h (€/kWh)", pad_x=10)
        self.entry_precio_energia_24h = self.crear_entry_estilizado(self.frame_actual_24h, "Ej: 0.1350", pad_x=10)
        self.frame_actual_24h.pack(fill="x", pady=(0, 4))

        self.frame_actual_tramos = ctk.CTkFrame(self.frame_tarifa_actual, fg_color="transparent")
        self.crear_label_input(self.frame_actual_tramos, "Precio Punta - P1 (€/kWh)", pad_x=10)
        self.entry_precio_p1 = self.crear_entry_estilizado(self.frame_actual_tramos, "Ej: 0.1820", pad_x=10)
        self.crear_label_input(self.frame_actual_tramos, "Precio Llano - P2 (€/kWh)", pad_x=10)
        self.entry_precio_p2 = self.crear_entry_estilizado(self.frame_actual_tramos, "Ej: 0.1340", pad_x=10)
        self.crear_label_input(self.frame_actual_tramos, "Precio Valle - P3 (€/kWh)", pad_x=10)
        self.entry_precio_p3 = self.crear_entry_estilizado(self.frame_actual_tramos, "Ej: 0.0950", pad_x=10)

        # 3. BOTÓN DE CÁLCULO PRINCIPAL
        btn_calcular = ctk.CTkButton(
            self.sidebar, text="Calcular Ahorro 🚀", 
            fg_color=COLOR_ACCENT_GREEN, hover_color="#1E6B49",
            height=36, font=ctk.CTkFont(size=13, weight="bold"), corner_radius=6,
            command=self.calcular_ahorro
        )
        btn_calcular.grid(row=3, column=0, padx=15, pady=(8, 6), sticky="ew")

        # Footer Status
        status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_frame.grid(row=4, column=0, padx=15, pady=(0, 8), sticky="s")
        
        self.lbl_status_dot = ctk.CTkLabel(status_frame, text="●", text_color=COLOR_ACCENT_GREEN, font=ctk.CTkFont(size=10))
        self.lbl_status_dot.pack(side="left", padx=(0, 4))
        
        self.lbl_status = ctk.CTkLabel(status_frame, text="Conectando...", font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED)
        self.lbl_status.pack(side="left")

    def toggle_tarifa_actual(self):
        self.mostrar_tarifa_actual = not self.mostrar_tarifa_actual
        if self.mostrar_tarifa_actual:
            self.btn_toggle_actual.configure(text="▼  Comparar con mi Tarifa Actual")
            self.frame_tarifa_actual.pack(fill="x", padx=5, pady=(0, 6))
        else:
            self.btn_toggle_actual.configure(text="▶  Comparar con mi Tarifa Actual")
            self.frame_tarifa_actual.pack_forget()

    def cambiar_modalidad(self, value):
        if value == "Tarifa 24h":
            self.frame_tramos.pack_forget()
            self.frame_24h.pack(fill="x")
            self.frame_actual_tramos.pack_forget()
            self.frame_actual_24h.pack(fill="x", pady=(0, 4))
        else:
            self.frame_24h.pack_forget()
            self.frame_tramos.pack(fill="x")
            self.frame_actual_24h.pack_forget()
            self.frame_actual_tramos.pack(fill="x", pady=(0, 4))

    def crear_area_principal(self):
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=15)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self.frame_kpis = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frame_kpis.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.frame_kpis.grid_columnconfigure((0, 1), weight=1, uniform="kpi")

        self.card_mejor = self.crear_card_kpi(self.frame_kpis, 0, "MEJOR TARIFA ENCONTRADA", "-- €", "Rellena los datos y calcula", color_val=COLOR_ACCENT_GREEN)
        self.card_ahorro = self.crear_card_kpi(self.frame_kpis, 1, "AHORRO ESTIMADO", "-- €/mes", "Ingresa tu tarifa actual", color_val=COLOR_ACCENT_BLUE)

        self.frame_resultados = ctk.CTkFrame(
            self.main_area, corner_radius=10, 
            fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1
        )
        self.frame_resultados.grid(row=1, column=0, sticky="nsew")

        header_frame = ctk.CTkFrame(self.frame_resultados, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(12, 8))

        ctk.CTkLabel(header_frame, text="Ranking de Comercializadoras", font=ctk.CTkFont(size=15, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(side="left")

        self.scroll_list = ctk.CTkScrollableFrame(self.frame_resultados, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def crear_card_kpi(self, parent, col, titulo, valor, subtitulo, color_val=COLOR_TEXT_MAIN):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1)
        card.grid(row=0, column=col, padx=5, sticky="ew")

        lbl_tit = ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED)
        lbl_tit.pack(anchor="w", padx=14, pady=(10, 2))
        
        lbl_val = ctk.CTkLabel(card, text=valor, font=ctk.CTkFont(size=20, weight="bold"), text_color=color_val)
        lbl_val.pack(anchor="w", padx=14, pady=0)
        
        lbl_sub = ctk.CTkLabel(card, text=subtitulo, font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED)
        lbl_sub.pack(anchor="w", padx=14, pady=(2, 10))
        return {"card": card, "val": lbl_val, "sub": lbl_sub}

    def crear_label_input(self, parent, texto, pad_x=0):
        lbl = ctk.CTkLabel(
            parent, text=texto, 
            font=ctk.CTkFont(size=11, weight="bold"), 
            text_color="#E2E8F0"
        )
        lbl.pack(anchor="w", pady=(3, 1), padx=pad_x)
        return lbl

    def crear_entry_estilizado(self, parent, placeholder, pad_x=0):
        entry = ctk.CTkEntry(
            parent, placeholder_text=placeholder,
            fg_color=COLOR_BG_MAIN, border_color=COLOR_CARD_BORDER, border_width=1,
            text_color=COLOR_TEXT_MAIN, placeholder_text_color="#64748B",
            height=28, corner_radius=5, font=ctk.CTkFont(size=11)
        )
        entry.pack(fill="x", padx=pad_x, pady=(0, 2))
        return entry

    # --- MOTOR DE CÁLCULO ---
    def calcular_ahorro(self):
        try:
            dias_raw = self.entry_dias_factura.get().strip()
            pot_p1_raw = self.entry_potencia_p1.get().strip()
            pot_p2_raw = self.entry_potencia_p2.get().strip()

            if not dias_raw or not pot_p1_raw or not pot_p2_raw:
                messagebox.showwarning("Campos obligatorios", "Por favor, introduce los 'Días de Facturación' y la 'Potencia Contratada' (P1 y P2).")
                return

            dias = int(dias_raw)
            pot_p1_kw = float(pot_p1_raw)
            pot_p2_kw = float(pot_p2_raw)

            if dias <= 0:
                messagebox.showwarning("Atención", "Los días de facturación deben ser mayores a 0.")
                return

            modalidad_usr = self.seg_modalidad.get()
            consumos = {}

            if modalidad_usr == "Tarifa 24h":
                c24_raw = self.entry_energia_24h.get().strip()
                if not c24_raw:
                    messagebox.showwarning("Campo obligatorio", "Introduce el 'Consumo Total (kWh)'.")
                    return
                consumos["24h"] = float(c24_raw)
            else:
                p1_raw = self.entry_p1.get().strip()
                p2_raw = self.entry_p2.get().strip()
                p3_raw = self.entry_p3.get().strip()
                if not p1_raw or not p2_raw or not p3_raw:
                    messagebox.showwarning("Campos obligatorios", "Introduce los tres tramos de consumo (P1, P2 y P3).")
                    return
                consumos["P1"] = float(p1_raw)
                consumos["P2"] = float(p2_raw)
                consumos["P3"] = float(p3_raw)

            if sum(consumos.values()) <= 0:
                messagebox.showwarning("Atención", "El consumo total introducido debe ser mayor que 0 kWh.")
                return

            if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
                inicializar_json_si_no_existe()

            with open(DATA_FILE, "r", encoding="utf-8") as f:
                tarifas = json.load(f)

            tax_rate = 5.11269632 / 100.0
            iva_rate = 0.21
            factor_impuestos = (1 + tax_rate) * (1 + iva_rate)

            resultados = []
            for t in tarifas:
                pot_p1_pr = t.get("Potencia_P1", 0.08)
                pot_p2_pr = t.get("Potencia_P2", 0.01)

                coste_pot_base = (pot_p1_kw * pot_p1_pr * dias) + (pot_p2_kw * pot_p2_pr * dias)
                
                if t.get("Modalidad") == "24h":
                    kwh_total = consumos["24h"] if modalidad_usr == "Tarifa 24h" else sum(consumos.values())
                    pr_24h = t.get("Precio_Energia_24h", 0.12)
                    coste_energ_base = kwh_total * pr_24h
                else:
                    if modalidad_usr == "Por Tramos":
                        cP1, cP2, cP3 = consumos["P1"], consumos["P2"], consumos["P3"]
                    else:
                        tot = consumos["24h"]
                        cP1, cP2, cP3 = tot * 0.30, tot * 0.25, tot * 0.45
                    
                    coste_energ_base = (cP1 * t.get("P1", 0)) + (cP2 * t.get("P2", 0)) + (cP3 * t.get("P3", 0))

                coste_alquiler_base = dias * ALQUILER_DIARIO
                coste_bono_social_base = dias * BONO_SOCIAL_DIARIO
                
                subtotal_base = coste_pot_base + coste_energ_base + coste_alquiler_base + coste_bono_social_base
                coste_total = subtotal_base * factor_impuestos

                coste_pot_tot = coste_pot_base * factor_impuestos
                coste_energ_tot = coste_energ_base * factor_impuestos

                resultados.append({
                    "Comercializadora": t.get("Comercializadora", "Desconocida"),
                    "Nombre_Tarifa": t.get("Nombre_Tarifa", "Tarifa"),
                    "Modalidad": t.get("Modalidad", "24h"),
                    "Potencia_P1": pot_p1_pr,
                    "Potencia_P2": pot_p2_pr,
                    "Precio_Energia_24h": t.get("Precio_Energia_24h", 0.0),
                    "P1": t.get("P1", 0.0),
                    "P2": t.get("P2", 0.0),
                    "P3": t.get("P3", 0.0),
                    "Coste_Potencia": round(coste_pot_tot, 2),
                    "Coste_Energia": round(coste_energ_tot, 2),
                    "Coste_Total": round(coste_total, 2),
                    "es_actual": False
                })

            # --- INCLUSIÓN DE TU TARIFA ACTUAL EN EL RANKING ---
            if self.mostrar_tarifa_actual:
                pr_pot_p1_s = self.entry_precio_potencia_p1.get().strip()
                pr_pot_p2_s = self.entry_precio_potencia_p2.get().strip()

                if pr_pot_p1_s and pr_pot_p2_s:
                    pr_pot_p1 = float(pr_pot_p1_s)
                    pr_pot_p2 = float(pr_pot_p2_s)
                    coste_pot_usr_base = (pot_p1_kw * pr_pot_p1 * dias) + (pot_p2_kw * pr_pot_p2 * dias)

                    pr_eng_24h = 0.0
                    pr_p1_usr, pr_p2_usr, pr_p3_usr = 0.0, 0.0, 0.0
                    valido_usr = False

                    if modalidad_usr == "Tarifa 24h":
                        pr_e24_s = self.entry_precio_energia_24h.get().strip()
                        if pr_e24_s:
                            pr_eng_24h = float(pr_e24_s)
                            coste_energ_usr_base = consumos["24h"] * pr_eng_24h
                            valido_usr = True
                    else:
                        pr_p1_s = self.entry_precio_p1.get().strip()
                        pr_p2_s = self.entry_precio_p2.get().strip()
                        pr_p3_s = self.entry_precio_p3.get().strip()
                        if pr_p1_s and pr_p2_s and pr_p3_s:
                            pr_p1_usr = float(pr_p1_s)
                            pr_p2_usr = float(pr_p2_s)
                            pr_p3_usr = float(pr_p3_s)
                            coste_energ_usr_base = (consumos["P1"] * pr_p1_usr) + (consumos["P2"] * pr_p2_usr) + (consumos["P3"] * pr_p3_usr)
                            valido_usr = True

                    if valido_usr:
                        coste_alquiler_base = dias * ALQUILER_DIARIO
                        coste_bono_social_base = dias * BONO_SOCIAL_DIARIO
                        subtotal_usr_base = coste_pot_usr_base + coste_energ_usr_base + coste_alquiler_base + coste_bono_social_base
                        coste_usr_total = subtotal_usr_base * factor_impuestos

                        resultados.append({
                            "Comercializadora": "Tu Tarifa Actual",
                            "Nombre_Tarifa": "Configurada",
                            "Modalidad": modalidad_usr,
                            "Potencia_P1": pr_pot_p1,
                            "Potencia_P2": pr_pot_p2,
                            "Precio_Energia_24h": pr_eng_24h,
                            "P1": pr_p1_usr,
                            "P2": pr_p2_usr,
                            "P3": pr_p3_usr,
                            "Coste_Potencia": round(coste_pot_usr_base * factor_impuestos, 2),
                            "Coste_Energia": round(coste_energ_usr_base * factor_impuestos, 2),
                            "Coste_Total": round(coste_usr_total, 2),
                            "es_actual": True
                        })

            resultados = sorted(resultados, key=lambda x: x["Coste_Total"])
            self.ultimos_resultados = resultados
            self.ultimos_consumos = consumos

            self.actualizar_interfaz_resultados(resultados, dias)

        except ValueError:
            messagebox.showerror("Error", "Introduce únicamente valores numéricos en todos los campos.")
        except Exception as e:
            messagebox.showerror("Error", f"Detalle técnico del error: {e}")

    def actualizar_interfaz_resultados(self, resultados, dias=30):
        top = resultados[0]
        self.card_mejor["val"].configure(text=f"{top['Coste_Total']:.2f} € / {dias}d")
        self.card_mejor["sub"].configure(text=f"{top['Comercializadora']} ({top['Nombre_Tarifa']})")

        tarifa_usr_item = next((x for x in resultados if x.get("es_actual")), None)

        if tarifa_usr_item:
            coste_actual = tarifa_usr_item["Coste_Total"]
            ahorro = coste_actual - top["Coste_Total"]
            if top.get("es_actual"):
                self.card_ahorro["val"].configure(text="0.00 €", text_color=COLOR_ACCENT_GREEN)
                self.card_ahorro["sub"].configure(text=f"¡Tu tarifa actual ({coste_actual:.2f} €) ya es la más óptima!")
            elif ahorro > 0:
                pct = (ahorro / coste_actual) * 100
                self.card_ahorro["val"].configure(text=f"{ahorro:.2f} € ahorro", text_color=COLOR_ACCENT_GREEN)
                self.card_ahorro["sub"].configure(text=f"Ahorras un {pct:.1f}% respecto a tu tarifa ({coste_actual:.2f} €)")
            else:
                self.card_ahorro["val"].configure(text="0.00 €", text_color=COLOR_TEXT_MAIN)
                self.card_ahorro["sub"].configure(text=f"Tu tarifa actual ({coste_actual:.2f} €) es la mejor opción.")
        else:
            diff = resultados[-1]["Coste_Total"] - top["Coste_Total"]
            self.card_ahorro["val"].configure(text=f"Hasta {diff:.2f} € dif.", text_color=COLOR_ACCENT_BLUE)
            self.card_ahorro["sub"].configure(text="Diferencia entre la opción más barata y más cara")

        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        for rank, res in enumerate(resultados, start=1):
            self.agregar_fila_resultado(rank, res, es_mejor=(rank == 1))

    def agregar_fila_resultado(self, ranking, res, es_mejor=False):
        es_actual = res.get("es_actual", False)

        if es_actual and es_mejor:
            border_color = COLOR_ACCENT_GREEN
            bg_color = "#13231B"
        elif es_actual:
            border_color = COLOR_ACCENT_BLUE
            bg_color = "#1E293B"
        elif es_mejor:
            border_color = COLOR_ACCENT_GREEN
            bg_color = "#13231B"
        else:
            border_color = COLOR_CARD_BORDER
            bg_color = COLOR_BG_MAIN

        row_frame = ctk.CTkFrame(
            self.scroll_list, corner_radius=10, 
            fg_color=bg_color, border_color=border_color, border_width=1
        )
        row_frame.pack(fill="x", pady=4, padx=2)

        rank_color = COLOR_ACCENT_GOLD if ranking == 1 else COLOR_TEXT_MUTED
        lbl_rank = ctk.CTkLabel(row_frame, text=f"#{ranking}", font=ctk.CTkFont(size=14, weight="bold"), text_color=rank_color, width=40)
        lbl_rank.pack(side="left", padx=(10, 0))

        info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        title_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        title_frame.pack(anchor="w")

        nombre_completo = f"{res['Comercializadora']} - {res['Nombre_Tarifa']}"
        ctk.CTkLabel(title_frame, text=nombre_completo, font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MAIN).pack(side="left")

        if es_actual:
            badge_usr = ctk.CTkFrame(title_frame, fg_color="#1E3A8A", corner_radius=4)
            badge_usr.pack(side="left", padx=6)
            ctk.CTkLabel(badge_usr, text=" TU TARIFA ACTUAL ", font=ctk.CTkFont(size=9, weight="bold"), text_color="#60A5FA").pack(padx=4, pady=1)

        if es_mejor:
            badge_top = ctk.CTkFrame(title_frame, fg_color="#064E3B", corner_radius=4)
            badge_top.pack(side="left", padx=4)
            ctk.CTkLabel(badge_top, text=" MEJOR OPCIÓN ", font=ctk.CTkFont(size=9, weight="bold"), text_color=COLOR_ACCENT_GREEN).pack(padx=4, pady=1)

        txt_desglose = f"Modalidad: {res['Modalidad']}   |   Potencia: {res['Coste_Potencia']:.2f} €   |   Energía: {res['Coste_Energia']:.2f} €"
        ctk.CTkLabel(info_frame, text=txt_desglose, font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 0))

        precio_color = COLOR_ACCENT_GREEN if es_mejor else COLOR_TEXT_MAIN
        ctk.CTkLabel(row_frame, text=f"{res['Coste_Total']:.2f} €", font=ctk.CTkFont(size=16, weight="bold"), text_color=precio_color).pack(side="left", padx=15)

        btn_factura = ctk.CTkButton(
            row_frame, text="Generar PDF", width=95, height=30, 
            fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_BORDER,
            border_color=COLOR_CARD_BORDER, border_width=1,
            text_color=COLOR_TEXT_MAIN, corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda r=res: self.generar_pdf_tarifa(r)
        )
        btn_factura.pack(side="right", padx=12, pady=8)

    # --- GENERACIÓN DEL PDF ---
    def generar_pdf_tarifa(self, tarifa_data):
        try:
            filename_default = f"Factura_{tarifa_data['Comercializadora']}_{tarifa_data['Nombre_Tarifa']}".replace(" ", "_") + ".pdf"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=filename_default,
                filetypes=[("Archivos PDF", "*.pdf")]
            )
            if not filepath:
                return

            dias = int(self.entry_dias_factura.get().strip() or 30)
            pot_p1 = float(self.entry_potencia_p1.get().strip() or 0)
            pot_p2 = float(self.entry_potencia_p2.get().strip() or 0)
            modalidad_usr = self.seg_modalidad.get()

            doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
            styles = getSampleStyleSheet()

            style_title = ParagraphStyle('TitleStyle', fontName='Helvetica-Bold', fontSize=13, textColor=colors.white, leading=16)
            style_header = ParagraphStyle('HeaderStyle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#333333"))
            style_header_right = ParagraphStyle('HeaderRightStyle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#333333"), alignment=2)

            style_bold = ParagraphStyle('BoldStyle', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#111111"), leading=13)
            style_normal = ParagraphStyle('NormalStyle', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#333333"), leading=12)
            style_normal_right = ParagraphStyle('NormalRightStyle', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#111111"), leading=12, alignment=2)
            style_total_label = ParagraphStyle('TotalLabel', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#000000"))
            style_total_val = ParagraphStyle('TotalVal', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#000000"), alignment=2)

            elements = []

            # Banner de Encabezado
            title_text = f"Detalle Factura - {tarifa_data['Comercializadora']} ({tarifa_data['Nombre_Tarifa']})"
            title_p = Paragraph(title_text, style_title)
            banner_table = Table([[title_p]], colWidths=[522])
            banner_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E65100")),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ]))
            elements.append(banner_table)
            elements.append(Spacer(1, 10))

            table_data = [
                [Paragraph("Concepto", style_header), Paragraph("", style_header), Paragraph("Importe €", style_header_right)]
            ]

            subtotal = 0.0

            # 1. Término de Energía
            if tarifa_data.get("Modalidad") == "24h":
                kwh = self.ultimos_consumos.get("24h", sum(self.ultimos_consumos.values()))
                pr = tarifa_data.get("Precio_Energia_24h", 0.0)
                coste_energ = kwh * pr
                subtotal += coste_energ
                table_data.append([
                    Paragraph("Término de energía", style_bold),
                    Paragraph(f"24h: {kwh:.2f} kWh, Precio: {pr:.6f} €/kWh.", style_normal),
                    Paragraph(f"{coste_energ:.2f} €", style_normal_right)
                ])
            else:
                if modalidad_usr == "Por Tramos":
                    cp1, cp2, cp3 = self.ultimos_consumos.get("P1", 0), self.ultimos_consumos.get("P2", 0), self.ultimos_consumos.get("P3", 0)
                else:
                    tot = self.ultimos_consumos.get("24h", 0)
                    cp1, cp2, cp3 = tot * 0.30, tot * 0.25, tot * 0.45

                pr1, pr2, pr3 = tarifa_data.get("P1", 0.0), tarifa_data.get("P2", 0.0), tarifa_data.get("P3", 0.0)
                c1, c2, c3 = cp1 * pr1, cp2 * pr2, cp3 * pr3
                subtotal += (c1 + c2 + c3)

                table_data.append([
                    Paragraph("Término de energía", style_bold),
                    Paragraph(f"P1: {cp1:.2f} kWh, Precio: {pr1:.6f} €/kWh.", style_normal),
                    Paragraph(f"{c1:.2f} €", style_normal_right)
                ])
                table_data.append([
                    Paragraph("", style_normal),
                    Paragraph(f"P2: {cp2:.2f} kWh, Precio: {pr2:.6f} €/kWh.", style_normal),
                    Paragraph(f"{c2:.2f} €", style_normal_right)
                ])
                table_data.append([
                    Paragraph("", style_normal),
                    Paragraph(f"P3: {cp3:.2f} kWh, Precio: {pr3:.6f} €/kWh.", style_normal),
                    Paragraph(f"{c3:.2f} €", style_normal_right)
                ])

            # 2. Término de Potencia
            pot_pr1 = tarifa_data.get("Potencia_P1", 0.0)
            pot_pr2 = tarifa_data.get("Potencia_P2", 0.0)
            coste_pot1 = pot_p1 * pot_pr1 * dias
            coste_pot2 = pot_p2 * pot_pr2 * dias
            subtotal += (coste_pot1 + coste_pot2)

            table_data.append([
                Paragraph("Término de potencia", style_bold),
                Paragraph(f"P1: {pot_p1:.3f} kW x {dias} días x {pot_pr1:.6f} €/kW/día.", style_normal),
                Paragraph(f"{coste_pot1:.2f} €", style_normal_right)
            ])
            table_data.append([
                Paragraph("", style_normal),
                Paragraph(f"P2: {pot_p2:.3f} kW x {dias} días x {pot_pr2:.6f} €/kW/día.", style_normal),
                Paragraph(f"{coste_pot2:.2f} €", style_normal_right)
            ])

            # 3. Alquiler equipo de medida
            coste_alquiler = dias * ALQUILER_DIARIO
            subtotal += coste_alquiler
            table_data.append([
                Paragraph("Alquiler equipo de medida", style_bold),
                Paragraph(f"{dias} días x {ALQUILER_DIARIO:.6f} €/día", style_normal),
                Paragraph(f"{coste_alquiler:.2f} €", style_normal_right)
            ])

            # 4. Financiación Bono Social
            coste_bono_social = dias * BONO_SOCIAL_DIARIO
            subtotal += coste_bono_social
            table_data.append([
                Paragraph("Financiación Bono Social", style_bold),
                Paragraph(f"{dias} días x {BONO_SOCIAL_DIARIO:.6f} €/día", style_normal),
                Paragraph(f"{coste_bono_social:.2f} €", style_normal_right)
            ])

            # Suma e Impuestos
            tax_rate = 5.11269632
            impuesto_elec = subtotal * (tax_rate / 100.0)

            table_data.append([
                Paragraph("Impuestos eléctricos", style_bold),
                Paragraph(f"{subtotal:.2f} € x {tax_rate:.8f}%", style_normal),
                Paragraph(f"{impuesto_elec:.2f} €", style_normal_right)
            ])

            base_imponible = subtotal + impuesto_elec
            table_data.append([
                Paragraph("Base imponible", style_bold),
                Paragraph("", style_normal),
                Paragraph(f"{base_imponible:.2f} €", style_normal_right)
            ])

            iva = base_imponible * 0.21
            table_data.append([
                Paragraph("IVA 21%", style_bold),
                Paragraph("", style_normal),
                Paragraph(f"{iva:.2f} €", style_normal_right)
            ])

            total = base_imponible + iva
            table_data.append([
                Paragraph("TOTAL", style_total_label),
                Paragraph("", style_normal),
                Paragraph(f"{total:.2f} €", style_total_val)
            ])

            main_table = Table(table_data, colWidths=[150, 272, 100])
            main_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#FCE4D6")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING', (0,0), (-1,-1), 4),
                ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor("#E65100")),
                ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor("#111111")),
            ]))

            elements.append(main_table)
            doc.build(elements)

        except Exception as e:
            messagebox.showerror("Error al generar PDF", f"Ocurrió un detalle técnico: {e}")

if __name__ == "__main__":
    app = AppProDashboard()
    app.mainloop()