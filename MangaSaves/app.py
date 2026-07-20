import sqlite3
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime
import sys
import ctypes
import re

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppLectura(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # === CONFIGURACIÓN DE LA VENTANA ===
        self.title("Control de Progreso de Lectura")
        self.geometry("1100x620")
        self.minsize(950, 450)
        
        # === PARCHE DE ÍCONO PARA WINDOWS (BARRA DE TAREAS) ===
        if sys.platform.startswith("win"):
            id_app = "lzndr.mangasaves.control.1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(id_app)
        
        try:
            self.iconbitmap("mangasaves.ico")
        except Exception:
            try:
                self.iconphoto(False, tk.PhotoImage(file="mangasaves.png"))
            except Exception:
                pass
        
        # Diccionario para controlar la dirección del orden de cada columna
        self.direcciones_orden = {
            "nombre": "ASC",
            "capitulo": "ASC",
            "pagina": "ASC",
            "estado": "ASC",
            "fecha": "ASC"
        }
        # Columna activa por defecto al iniciar
        self.columna_activa = "id" 
        
        # Ancho inicial óptimo
        self.anchos = {
            "nombre": 300,
            "capitulo": 65,
            "pagina": 160,
            "estado": 150,
            "fecha": 160
        }
        
        # === CONTROL DE VISTA INICIAL ===
        # "ultimos" = Muestra los 5 más recientes modificado, "todos" = Muestra el listado completo
        self.modo_vista = "ultimos"
        
        # === NUEVO: Variables para navegación alfabética y paginación ===
        self.letra_actual = None
        self.pagina_actual = 1
        self.total_paginas = 0
        self.registros_por_pagina = 10
        
        self.init_db()
        
        # Grid Estructural Principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # 1. BARRA SUPERIOR (Agregar, Buscar y Alternar Vista)
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        
        self.entry_nombre = ctk.CTkEntry(self.top_frame, placeholder_text="Nombre de lectura", width=200)
        self.entry_nombre.pack(side="left", padx=10, pady=10)
        
        self.entry_capitulo = ctk.CTkEntry(self.top_frame, placeholder_text="Cap. (ej: 2.3)", width=65)
        self.entry_capitulo.pack(side="left", padx=5, pady=10)
        
        self.entry_pagina = ctk.CTkEntry(self.top_frame, placeholder_text="Página / Web", width=140)
        self.entry_pagina.pack(side="left", padx=5, pady=10)
        
        self.btn_agregar = ctk.CTkButton(self.top_frame, text="＋ Agregar", width=95, command=self.agregar_registro)
        self.btn_agregar.pack(side="left", padx=10, pady=10)
        
        lbl_sep = ctk.CTkLabel(self.top_frame, text="|", text_color="gray40")
        lbl_sep.pack(side="left", padx=5)
        
        # === NUEVO: Sistema de búsqueda mejorado ===
        self.search_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.search_frame.pack(side="left", padx=5, pady=10)
        
        self.entry_buscar = ctk.CTkEntry(self.search_frame, placeholder_text="Buscar...", width=150)
        self.entry_buscar.pack(side="left", padx=(0, 5))
        self.entry_buscar.bind("<Return>", self.ejecutar_busqueda)
        
        self.btn_buscar = ctk.CTkButton(self.search_frame, text="🔍 Buscar", width=70, command=self.ejecutar_busqueda)
        self.btn_buscar.pack(side="left")
        
        lbl_sep2 = ctk.CTkLabel(self.top_frame, text="|", text_color="gray40")
        lbl_sep2.pack(side="left", padx=5)
        
        # Botón dinámico para alternar entre ver los últimos 5 o la lista alfabética
        self.btn_vista = ctk.CTkButton(self.top_frame, text="📋 Ver Lista Completa", fg_color="#1F538D", hover_color="#2A6BB2", command=self.alternar_modo_vista)
        self.btn_vista.pack(side="left", padx=10, pady=10)
        
        # 2. PANEL ALFABÉTICO (nuevo)
        self.alfabetico_frame = ctk.CTkFrame(self, fg_color="transparent", height=35)
        self.alfabetico_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        self.alfabetico_frame.grid_propagate(False)
        self.alfabetico_frame.grid_remove()  # Oculto por defecto
        
        # 3. CONTENEDOR DE LA TABLA
        self.table_container = ctk.CTkFrame(self, fg_color="transparent")
        self.table_container.grid(row=2, column=0, sticky="nsew", padx=15, pady=5)
        self.table_container.grid_columnconfigure(0, weight=1)
        self.table_container.grid_rowconfigure(1, weight=1)
        
        # Contenedor para las Cabeceras Modificables
        self.header_frame = ctk.CTkFrame(self.table_container, fg_color="transparent", height=35)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=(5, 20))
        self.header_frame.grid_propagate(False)
        
        # Cuerpo con Scroll para las filas
        self.canvas_frame = ctk.CTkScrollableFrame(self.table_container, fg_color="transparent")
        self.canvas_frame.grid(row=1, column=0, sticky="nsew")
        
        # 4. BARRA DE PAGINACIÓN (nueva)
        self.paginacion_frame = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.paginacion_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=5)
        self.paginacion_frame.grid_propagate(False)
        self.paginacion_frame.grid_remove()  # Oculto por defecto
        
        # 5. BARRA INFERIOR DE ACCIONES
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(5, 15))
        
        self.btn_eliminar = ctk.CTkButton(self.action_frame, text="Eliminar Seleccionado", fg_color="#A30000", hover_color="#D30000", command=self.eliminar_registro)
        self.btn_eliminar.pack(side="left")
        
        self.label_hint = ctk.CTkLabel(self.action_frame, text="✨ Haz clic en cualquier título superior para ordenar. Clic en Estado para cambiarlo rápido.", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray60")
        self.label_hint.pack(side="left", padx=15)
        
        self.registro_seleccionado_id = None
        self.lista_frames_filas = {}
        
        self.configurar_columnas_grid(self.header_frame)
        self.dibujar_cabeceras()
        self.cargar_datos()

    def configurar_columnas_grid(self, contenedor):
        """ Controla el ancho de las columnas de la grilla de forma estricta """
        contenedor.grid_columnconfigure(0, minsize=self.anchos["nombre"], weight=0)
        contenedor.grid_columnconfigure(1, minsize=15, weight=0) 
        contenedor.grid_columnconfigure(2, minsize=self.anchos["capitulo"], weight=0)
        contenedor.grid_columnconfigure(3, minsize=15, weight=0) 
        contenedor.grid_columnconfigure(4, minsize=self.anchos["pagina"], weight=0)
        contenedor.grid_columnconfigure(5, minsize=15, weight=0) 
        contenedor.grid_columnconfigure(6, minsize=self.anchos["estado"], weight=0)
        contenedor.grid_columnconfigure(7, minsize=15, weight=0) 
        contenedor.grid_columnconfigure(8, minsize=self.anchos["fecha"], weight=0)

    def dibujar_cabeceras(self):
        """ Renderiza los títulos interactivos superiores para ordenar al hacer clic """
        for w in self.header_frame.winfo_children():
            w.destroy()
            
        columnas = [
            ("nombre", "Nombre", 0),
            ("capitulo", "Capítulo", 2),
            ("pagina", "Página / Plataforma", 4),
            ("estado", "Estado de Lectura", 6),
            ("fecha", "Última Modificación", 8)
        ]
        
        for idx, (clave, texto_base, col_pos) in enumerate(columnas):
            align = "center" if clave in ["capitulo", "estado", "fecha"] else "w"
            sticky_val = "ew" if align == "w" else ""
            
            if self.columna_activa == clave:
                flecha = " ▲" if self.direcciones_orden[clave] == "ASC" else " ▼"
                texto_final = f"{texto_base}{flecha}"
                color_titulo = "#1F538D"
            else:
                texto_final = texto_base
                color_titulo = "#FFFFFF"
                
            lbl = ctk.CTkButton(
                self.header_frame, 
                text=texto_final, 
                font=ctk.CTkFont(weight="bold"),
                fg_color="transparent",
                text_color=color_titulo,
                hover_color="#2B2B2B",
                anchor=align,
                command=lambda k=clave: self.procesar_orden_columna(k)
            )
            lbl.grid(row=0, column=col_pos, sticky=sticky_val, padx=2)
            
            if idx < len(columnas) - 1:
                separador = ctk.CTkLabel(self.header_frame, text="│", text_color="gray40", cursor="sb_h_double_arrow")
                separador.grid(row=0, column=col_pos + 1, sticky="ns")
                separador.bind("<B1-Motion>", lambda e, k=clave: self.cambiar_tamano_columna(e, k))

    def cambiar_tamano_columna(self, event, clave):
        nuevo_ancho = self.anchos[clave] + event.x
        limite_minimo = 45 if clave == "capitulo" else 50
        
        if nuevo_ancho > limite_minimo: 
            self.anchos[clave] = nuevo_ancho
            self.header_frame.after_cancel(id(self)) if hasattr(self, '_after_id') else None
            self.configurar_columnas_grid(self.header_frame)
            self.actualizar_anchos_filas()

    def actualizar_anchos_filas(self):
        for f_id, widgets in self.lista_frames_filas.items():
            self.configurar_columnas_grid(widgets["frame"])
            widgets["capitulo"].configure(width=max(25, self.anchos["capitulo"] - 10))
            widgets["pagina"].configure(width=max(50, self.anchos["pagina"] - 10))
            widgets["estado"].configure(width=max(50, self.anchos["estado"] - 10))

    def init_db(self):
        self.conn = sqlite3.connect("progreso_lectura.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS lecturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                capitulo TEXT NOT NULL,
                pagina TEXT NOT NULL,
                terminado TEXT DEFAULT 'No',
                fecha_mod TEXT
            )
        """)
        self.conn.commit()

    # === NUEVO: Sistema de navegación alfabética ===
    def crear_panel_alfabetico(self):
        """Crea el panel con las letras del alfabeto"""
        for w in self.alfabetico_frame.winfo_children():
            w.destroy()
        
        letras = ['A','B','C','D','E','F','G','H','I','J','K','L','M',
                  'N','O','P','Q','R','S','T','U','V','W','X','Y','Z','#']
        
        for letra in letras:
            btn = ctk.CTkButton(
                self.alfabetico_frame,
                text=letra,
                width=30,
                height=28,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#1F538D" if letra == 'A' else "transparent",
                text_color="#FFFFFF" if letra == 'A' else "gray70",
                hover_color="#2A6BB2",
                command=lambda l=letra: self.seleccionar_letra(l)
            )
            btn.pack(side="left", padx=1, pady=2)
        
        # Seleccionar 'A' por defecto
        self.letra_actual = 'A'
        self.mostrar_pagina(1)

    def seleccionar_letra(self, letra):
        """Selecciona una letra y carga su contenido"""
        # Actualizar estilo de botones
        for child in self.alfabetico_frame.winfo_children():
            if isinstance(child, ctk.CTkButton):
                if child.cget("text") == letra:
                    child.configure(fg_color="#1F538D", text_color="#FFFFFF")
                else:
                    child.configure(fg_color="transparent", text_color="gray70")
        
        self.letra_actual = letra
        self.pagina_actual = 1
        self.mostrar_pagina(1)

    def calcular_total_paginas(self):
        """Calcula el total de páginas para la letra actual"""
        if not self.letra_actual:
            return 0
        
        # Construir condición WHERE según la letra
        if self.letra_actual == '#':
            where_condition = "nombre GLOB '[0-9]*' OR nombre GLOB '[^A-Za-z0-9]*'"
        else:
            where_condition = f"nombre LIKE '{self.letra_actual}%'"
        
        query = f"SELECT COUNT(*) FROM lecturas WHERE {where_condition}"
        self.cursor.execute(query)
        total = self.cursor.fetchone()[0]
        
        self.total_paginas = (total + self.registros_por_pagina - 1) // self.registros_por_pagina
        if self.total_paginas == 0:
            self.total_paginas = 1
        return self.total_paginas

    def mostrar_pagina(self, pagina):
        """Muestra una página específica de la letra actual"""
        if not self.letra_actual:
            return
        
        self.pagina_actual = pagina
        
        # Calcular total de páginas
        self.calcular_total_paginas()
        
        # Construir consulta SQL
        if self.letra_actual == '#':
            where_condition = "nombre GLOB '[0-9]*' OR nombre GLOB '[^A-Za-z0-9]*'"
        else:
            where_condition = f"nombre LIKE '{self.letra_actual}%'"
        
        offset = (pagina - 1) * self.registros_por_pagina
        
        # Obtener registros con paginación
        query = f"""
            SELECT id, nombre, capitulo, pagina, terminado, fecha_mod 
            FROM lecturas 
            WHERE {where_condition}
            ORDER BY nombre COLLATE NOCASE, id
            LIMIT ? OFFSET ?
        """
        self.cargar_datos(query_custom=query, params_custom=(self.registros_por_pagina, offset))
        
        # Actualizar controles de paginación
        self.actualizar_controles_paginacion()

    def actualizar_controles_paginacion(self):
        """Actualiza los botones de paginación"""
        for w in self.paginacion_frame.winfo_children():
            w.destroy()
        
        if self.total_paginas <= 1:
            return
        
        # Botón Anterior
        if self.pagina_actual > 1:
            btn_prev = ctk.CTkButton(
                self.paginacion_frame,
                text="◀",
                width=30,
                height=28,
                command=lambda: self.mostrar_pagina(self.pagina_actual - 1)
            )
            btn_prev.pack(side="left", padx=2)
        
        # Números de página
        rango = range(
            max(1, self.pagina_actual - 2),
            min(self.total_paginas + 1, self.pagina_actual + 3)
        )
        
        for num in rango:
            btn = ctk.CTkButton(
                self.paginacion_frame,
                text=str(num),
                width=30,
                height=28,
                fg_color="#1F538D" if num == self.pagina_actual else "transparent",
                text_color="#FFFFFF" if num == self.pagina_actual else "gray70",
                hover_color="#2A6BB2",
                command=lambda n=num: self.mostrar_pagina(n)
            )
            btn.pack(side="left", padx=2)
        
        # Botón Siguiente
        if self.pagina_actual < self.total_paginas:
            btn_next = ctk.CTkButton(
                self.paginacion_frame,
                text="▶",
                width=30,
                height=28,
                command=lambda: self.mostrar_pagina(self.pagina_actual + 1)
            )
            btn_next.pack(side="left", padx=2)

    def alternar_modo_vista(self):
        """ Cambia la lógica de renderizado principal """
        if self.modo_vista == "ultimos":
            self.modo_vista = "todos"
            self.btn_vista.configure(text="🕒 Ver Últimos 5", fg_color="#1E8449", hover_color="#239B56")
            # Mostrar panel alfabético y paginación
            self.alfabetico_frame.grid()
            self.paginacion_frame.grid()
            self.crear_panel_alfabetico()
            # Limpiar búsqueda
            self.entry_buscar.delete(0, tk.END)
        else:
            self.modo_vista = "ultimos"
            self.btn_vista.configure(text="📋 Ver Lista Completa", fg_color="#1F538D", hover_color="#2A6BB2")
            # Ocultar paneles
            self.alfabetico_frame.grid_remove()
            self.paginacion_frame.grid_remove()
            # Limpiar búsqueda
            self.entry_buscar.delete(0, tk.END)
            self.cargar_datos()

    def cargar_datos(self, query_custom=None, params_custom=()):
        # 1. Limpieza total de widgets huerfanos del canvas
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        self.lista_frames_filas.clear()
            
        if query_custom:
            self.cursor.execute(query_custom, params_custom)
        else:
            # Si estamos en modo "ultimos", ignoramos el ordenamiento por clicks 
            # y forzamos por diseño el traer los 5 cambios más recientes.
            if self.modo_vista == "ultimos":
                query = """
                    SELECT id, nombre, capitulo, pagina, terminado, fecha_mod 
                    FROM lecturas 
                    ORDER BY datetime(
                        substr(fecha_mod, 7, 4) || '-' || 
                        substr(fecha_mod, 4, 2) || '-' || 
                        substr(fecha_mod, 1, 2) || ' ' || 
                        substr(fecha_mod, 12, 5)
                    ) DESC, id DESC 
                    LIMIT 5
                """
            else:
                # Ordenamiento dinámico base integrado en la carga para la lista completa
                direccion = self.direcciones_orden.get(self.columna_activa, "ASC")
                campo_sql = self.columna_activa
                if self.columna_activa == "estado": campo_sql = "terminado"
                elif self.columna_activa == "fecha": campo_sql = "fecha_mod"
                
                if self.columna_activa == "capitulo":
                    query = f"SELECT id, nombre, capitulo, pagina, terminado, fecha_mod FROM lecturas ORDER BY CAST(capitulo AS REAL) {direccion}"
                elif self.columna_activa in ["nombre", "pagina"]:
                    query = f"SELECT id, nombre, capitulo, pagina, terminado, fecha_mod FROM lecturas ORDER BY {campo_sql} COLLATE NOCASE {direccion}"
                elif self.columna_activa == "id":
                    query = "SELECT id, nombre, capitulo, pagina, terminado, fecha_mod FROM lecturas ORDER BY id DESC"
                else:
                    query = f"SELECT id, nombre, capitulo, pagina, terminado, fecha_mod FROM lecturas ORDER BY {campo_sql} {direccion}"
                
            self.cursor.execute(query)
            
        filas = self.cursor.fetchall()

        for fila in filas:
            f_id, nombre, capitulo, pagina, terminado, fecha_mod = fila
            es_terminado = (terminado in ["Sí", "✅ Terminado"])
            
            bg_fila = "#2B2B2B" if self.registro_seleccionado_id == f_id else "transparent"
            
            item_frame = ctk.CTkFrame(self.canvas_frame, fg_color=bg_fila, height=46)
            item_frame.pack(fill="x", pady=3, padx=2)
            self.configurar_columnas_grid(item_frame)
            
            color_texto = "#A0A0A0" if es_terminado else "#FFFFFF"
            fuente_nombre = ctk.CTkFont(slant="italic") if es_terminado else ctk.CTkFont()
            
            # Nombre adaptable recortado limpio
            nombre_container = ctk.CTkFrame(item_frame, fg_color="transparent", height=30)
            nombre_container.grid(row=0, column=0, sticky="ew", padx=4, pady=8)
            nombre_container.pack_propagate(False)
            
            lbl_nom = ctk.CTkLabel(nombre_container, text=nombre, text_color=color_texto, font=fuente_nombre, anchor="w", cursor="hand2")
            lbl_nom.pack(side="left", fill="both", expand=True)
            lbl_nom.bind("<Button-1>", lambda e, txt=nombre, idx=f_id: self.copiar_y_seleccionar(txt, idx))
            
            ctk.CTkLabel(item_frame, text="").grid(row=0, column=1)
            
            # Input de Capítulo directo
            cap_var = tk.StringVar(value=str(capitulo))
            entry_cap = ctk.CTkEntry(item_frame, textvariable=cap_var, width=self.anchos["capitulo"] - 10, justify="center")
            entry_cap.grid(row=0, column=2, sticky="ns", padx=4, pady=8)
            entry_cap.bind("<Return>", lambda e, idx=f_id, var=cap_var: self.actualizar_capitulo_inline(idx, var))
            entry_cap.bind("<FocusOut>", lambda e, idx=f_id, var=cap_var: self.actualizar_capitulo_inline(idx, var))
            
            ctk.CTkLabel(item_frame, text="").grid(row=0, column=3)
            
            # === NUEVO: Página editable ===
            pag_var = tk.StringVar(value=str(pagina))
            entry_pag = ctk.CTkEntry(item_frame, textvariable=pag_var, width=self.anchos["pagina"] - 10, justify="left")
            entry_pag.grid(row=0, column=4, sticky="ew", padx=4, pady=8)
            entry_pag.bind("<Return>", lambda e, idx=f_id, var=pag_var: self.actualizar_pagina_inline(idx, var))
            entry_pag.bind("<FocusOut>", lambda e, idx=f_id, var=pag_var: self.actualizar_pagina_inline(idx, var))
            
            ctk.CTkLabel(item_frame, text="").grid(row=0, column=5)
            
            # Botón de Estado
            estado_actual = "✅ Terminado" if es_terminado else "📖 Leyendo"
            color_btn = "#1E8449" if es_terminado else "#1F538D"
            
            btn_estado = ctk.CTkButton(
                item_frame, 
                text=estado_actual,
                width=self.anchos["estado"] - 10,
                fg_color=color_btn,
                hover_color="gray40",
                command=lambda idx=f_id, est=estado_actual: self.alternar_estado_click(idx, est)
            )
            btn_estado.grid(row=0, column=6, sticky="ns", padx=4, pady=8)
            
            ctk.CTkLabel(item_frame, text="").grid(row=0, column=7)
            
            # Timestamp
            if not fecha_mod: fecha_mod = "Sin datos"
            lbl_fecha = ctk.CTkLabel(item_frame, text=fecha_mod, text_color="#888888", font=ctk.CTkFont(size=11), anchor="center")
            lbl_fecha.grid(row=0, column=8, sticky="ew", padx=4, pady=8)
            lbl_fecha.bind("<Button-1>", lambda e, idx=f_id: self.seleccionar_fila(idx))
            
            self.lista_frames_filas[f_id] = {
                "frame": item_frame,
                "nombre": lbl_nom,
                "capitulo": entry_cap,
                "pagina": entry_pag,
                "estado": btn_estado,
                "fecha": lbl_fecha
            }

    def alternar_estado_click(self, registro_id, estado_actual):
        nuevo_estado_db = "Sí" if "Leyendo" in estado_actual else "No"
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        self.cursor.execute("UPDATE lecturas SET terminado = ?, fecha_mod = ? WHERE id = ?", (nuevo_estado_db, fecha_actual, registro_id))
        self.conn.commit()
        
        # Refrescar según modo actual
        if self.modo_vista == "ultimos":
            self.cargar_datos()
        else:
            self.mostrar_pagina(self.pagina_actual)

    def procesar_orden_columna(self, clave_columna):
        """ Solo procesa el orden por clicks si está el listado completo activo """
        if self.modo_vista == "ultimos":
            self.label_hint.configure(text="⚠ Pasa al modo 'Lista Completa' para usar el ordenamiento por columnas.", text_color="#A30000")
            self.after(3000, lambda: self.label_hint.configure(text="✨ Haz clic en cualquier título superior para ordenar. Clic en Estado para cambiarlo rápido.", text_color="gray60"))
            return

        self.columna_activa = clave_columna
        self.direcciones_orden[clave_columna] = "DESC" if self.direcciones_orden[clave_columna] == "ASC" else "ASC"
        
        self.dibujar_cabeceras()
        # Cargar datos con el nuevo orden
        if self.modo_vista == "todos":
            self.mostrar_pagina(self.pagina_actual)

    def copiar_y_seleccionar(self, texto, registro_id):
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.seleccionar_fila(registro_id)
        self.label_hint.configure(text=f"📋 ¡Copiado al portapapeles!: '{texto}'", text_color="#1F538D")
        self.after(2500, lambda: self.label_hint.configure(text="✨ Haz clic en cualquier título superior para ordenar. Clic en Estado para cambiarlo rápido.", text_color="gray60"))

    def seleccionar_fila(self, registro_id):
        self.registro_seleccionado_id = registro_id
        for f_id, widgets in self.lista_frames_filas.items():
            widgets["frame"].configure(fg_color="#2B2B2B" if f_id == registro_id else "transparent")

    def validar_numero_decimal(self, valor):
        if not valor:
            return False
        patron = r'^\d+(\.\d+)?$'
        return re.match(patron, valor) is not None

    def actualizar_capitulo_inline(self, registro_id, string_var):
        nuevo_val = string_var.get().strip()
        
        if not self.validar_numero_decimal(nuevo_val):
            self.cursor.execute("SELECT capitulo FROM lecturas WHERE id = ?", (registro_id,))
            resultado = self.cursor.fetchone()
            if resultado:
                string_var.set(str(resultado[0]))
            return
        
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cursor.execute("UPDATE lecturas SET capitulo = ?, fecha_mod = ? WHERE id = ?", (nuevo_val, fecha_actual, registro_id))
        self.conn.commit()
        
        # Refrescar según modo actual
        if self.modo_vista == "ultimos":
            self.cargar_datos()
        else:
            self.mostrar_pagina(self.pagina_actual)

    # === NUEVO: Actualizar página inline ===
    def actualizar_pagina_inline(self, registro_id, string_var):
        """Actualiza el campo página/plataforma con edición inline"""
        nuevo_val = string_var.get().strip()
        
        if not nuevo_val:
            # Si está vacío, restaurar valor anterior
            self.cursor.execute("SELECT pagina FROM lecturas WHERE id = ?", (registro_id,))
            resultado = self.cursor.fetchone()
            if resultado:
                string_var.set(str(resultado[0]))
            return
        
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cursor.execute("UPDATE lecturas SET pagina = ?, fecha_mod = ? WHERE id = ?", (nuevo_val, fecha_actual, registro_id))
        self.conn.commit()
        
        # Refrescar según modo actual
        if self.modo_vista == "ultimos":
            self.cargar_datos()
        else:
            self.mostrar_pagina(self.pagina_actual)

    def agregar_registro(self):
        nombre = self.entry_nombre.get().strip()
        capitulo = self.entry_capitulo.get().strip()
        pagina = self.entry_pagina.get().strip()
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")

        if not nombre or not capitulo or not pagina:
            messagebox.showwarning("Campos vacíos", "Completa la fila superior antes de agregar.")
            return
        
        if not self.validar_numero_decimal(capitulo):
            messagebox.showerror("Error", "El capítulo debe ser un número válido (ej: 2, 2.3, 0.5)")
            return

        self.cursor.execute("INSERT INTO lecturas (nombre, capitulo, pagina, terminado, fecha_mod) VALUES (?, ?, ?, 'No', ?)", (nombre, capitulo, pagina, fecha_actual))
        self.conn.commit()
        self.entry_nombre.delete(0, tk.END)
        self.entry_capitulo.delete(0, tk.END)
        self.entry_pagina.delete(0, tk.END)
        
        # Refrescar según modo actual
        if self.modo_vista == "ultimos":
            self.cargar_datos()
        else:
            self.mostrar_pagina(self.pagina_actual)

    def eliminar_registro(self):
        if self.registro_seleccionado_id is None:
            messagebox.showwarning("Selección vacía", "Selecciona una fila primero.")
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar esta lectura?"):
            self.cursor.execute("DELETE FROM lecturas WHERE id = ?", (self.registro_seleccionado_id,))
            self.conn.commit()
            self.registro_seleccionado_id = None
            
            # Refrescar según modo actual
            if self.modo_vista == "ultimos":
                self.cargar_datos()
            else:
                self.mostrar_pagina(self.pagina_actual)

    # === NUEVO: Sistema de búsqueda mejorado ===
    def ejecutar_busqueda(self, event=None):
        """Ejecuta la búsqueda solo cuando se presiona Enter o el botón"""
        texto = self.entry_buscar.get().strip()
        
        # Si el campo está vacío, volver a la vista correspondiente
        if not texto:
            if self.modo_vista == "ultimos":
                self.cargar_datos()
            else:
                self.mostrar_pagina(self.pagina_actual)
            return
        
        # Si estamos en modo "últimos", cambiar temporalmente a búsqueda
        # Pero mostramos todos los resultados de búsqueda, no solo 5
        query = """
            SELECT id, nombre, capitulo, pagina, terminado, fecha_mod 
            FROM lecturas 
            WHERE nombre LIKE ? OR pagina LIKE ? 
            ORDER BY id DESC
        """
        self.cargar_datos(query_custom=query, params_custom=(f"%{texto}%", f"%{texto}%"))
        
        # Ocultar paneles durante la búsqueda
        if self.modo_vista == "todos":
            self.alfabetico_frame.grid_remove()
            self.paginacion_frame.grid_remove()

if __name__ == "__main__":
    app = AppLectura()
    app.mainloop()