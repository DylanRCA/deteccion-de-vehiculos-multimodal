import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas
import cv2
from PIL import Image, ImageTk
import threading
import os
import sys
import time
import traceback
from datetime import datetime

# Agregar src al path para importar modulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import config
from src.pipeline import VehicleDetectionPipeline


class VehicleListRow(ctk.CTkFrame):
    """Fila individual en la lista de vehiculos detectados."""
    
    def __init__(self, parent, vehicle_data, on_click_callback, is_odd=False):
        super().__init__(parent, fg_color=("#2B2B2B" if is_odd else "#333333"), corner_radius=0)
        
        self.vehicle_data = vehicle_data
        self.on_click_callback = on_click_callback
        self.is_selected = False
        
        # Frame interno para padding
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=8, pady=4)
        
        # ID
        id_label = ctk.CTkLabel(
            content,
            text=f"#{vehicle_data['id']:02d}",
            width=35,
            font=("Consolas", 12, "bold"),
            anchor="w",
            text_color="white"
        )
        id_label.pack(side="left", padx=(0, 5))
        
        # Placa
        plate = vehicle_data['plate']
        if len(plate) > 10:
            plate = plate[:8] + ".."
        
        plate_label = ctk.CTkLabel(
            content,
            text=plate,
            width=90,
            font=("Consolas", 11),
            anchor="w",
            text_color="white"
        )
        plate_label.pack(side="left", padx=(0, 5))
        
        # Tiempo
        time_text = vehicle_data.get('time_range', 'N/A')
        time_label = ctk.CTkLabel(
            content,
            text=time_text,
            width=120,
            font=("Consolas", 10),
            anchor="w",
            text_color="#AAAAAA"
        )
        time_label.pack(side="left")
        
        # Bind click en todo el frame
        self.bind("<Button-1>", self._on_click)
        content.bind("<Button-1>", self._on_click)
        for widget in content.winfo_children():
            widget.bind("<Button-1>", self._on_click)
    
    def _on_click(self, event):
        """Maneja el click en la fila."""
        self.on_click_callback(self.vehicle_data['id'])
    
    def set_selected(self, selected):
        """Resalta o desresalta la fila."""
        self.is_selected = selected
        if selected:
            self.configure(fg_color="#2E7D32")  # Verde oscuro
            # Texto ya es blanco, mantener
        else:
            # Restaurar color original oscuro
            is_odd = self.vehicle_data['id'] % 2 == 1
            self.configure(fg_color=("#2B2B2B" if is_odd else "#333333"))


class VehicleDetectorApp:
    def __init__(self):
        """
        Inicializa la aplicacion de deteccion de vehiculos.
        """
        print("\n" + "="*80)
        print("[APP-INIT] Iniciando aplicacion de deteccion de vehiculos")
        print("="*80 + "\n")
        
        self.root = ctk.CTk()
        self.root.title("Detector de Vehiculos - Peru")
        self.root.geometry("1600x900")
        
        # Configurar tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Inicializar pipeline
        self.pipeline = None
        self.current_image = None
        self.camera_active = False
        self.video_capture = None
        
        # Estado de modo (para saber si mostrar stats de video o BD)
        self.current_mode = None  # 'camera', 'video', o 'image'
        
        # Contador de frames para actualizar stats
        self.frame_counter = 0
        self.stats_update_interval = 30
        
        # Almacenar stats por frame para reproduccion en tiempo real
        self.video_stats_history = []
        
        # Almacenar frames procesados para replay
        self.processed_frames = []
        self.video_fps = 30.0
        
        # Acumulador de vehiculos unicos detectados en video
        self.video_vehicles_summary = {}  # track_id -> vehicle_info
        
        # Estado de seleccion
        self.selected_vehicle_id = None
        self.vehicle_list_rows = {}  # track_id -> VehicleListRow widget
        
        # Detecciones actuales (para click en canvas)
        self.current_detections = []
        self.current_image_original = None  # Imagen original sin resize
        self.current_image_display_size = (0, 0)  # Tamano mostrado
        
        # Crear interfaz
        self._create_widgets()
        
        # Inicializar pipeline en thread separado
        threading.Thread(target=self._init_pipeline, daemon=True).start()
    
    def _init_pipeline(self):
        """
        Inicializa el pipeline de procesamiento en background.
        """
        self.status_label.configure(text="Cargando modelos... (puede tardar 30-60 seg)")
        
        try:
            print("\n[APP-INIT] Iniciando carga del pipeline...")
            
            # Por defecto video (para imagenes y videos)
            self.pipeline = VehicleDetectionPipeline(
                enable_database=True,
                enable_events=True,
                mode='video'
            )
            
            print("[APP-INIT] Pipeline cargado exitosamente\n")
            self.status_label.configure(text="Modelos cargados. Listo para usar.")
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"\n[APP-ERROR] Error completo al cargar modelos:\n{error_msg}\n")
            self.status_label.configure(text=f"Error: Ver consola para detalles")
            messagebox.showerror("Error de Carga", 
                               f"Error al cargar modelos:\n{str(e)}\n\nRevisa la consola para mas detalles.")
    
    def _create_widgets(self):
        """
        Crea los widgets de la interfaz grafica.
        """
        # Frame principal con 3 columnas
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === COLUMNA IZQUIERDA: Controles + Estadisticas ===
        control_frame = ctk.CTkFrame(main_frame, width=250)
        control_frame.pack(side="left", fill="y", padx=(0, 10))
        control_frame.pack_propagate(False)
        
        # Titulo
        title_label = ctk.CTkLabel(
            control_frame,
            text="Detector de Vehiculos",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=15)
        
        # Botones de control
        self.btn_image = ctk.CTkButton(
            control_frame,
            text="Subir Imagen",
            command=self._load_image,
            height=35
        )
        self.btn_image.pack(pady=8, padx=20, fill="x")
        
        self.btn_video = ctk.CTkButton(
            control_frame,
            text="Subir Video",
            command=self._load_video,
            height=35
        )
        self.btn_video.pack(pady=8, padx=20, fill="x")
        
        self.btn_camera = ctk.CTkButton(
            control_frame,
            text="Activar Camara",
            command=self._toggle_camera,
            height=35
        )
        self.btn_camera.pack(pady=8, padx=20, fill="x")
        
        self.btn_process = ctk.CTkButton(
            control_frame,
            text="Procesar",
            command=self._process_current,
            height=35,
            fg_color="green"
        )
        self.btn_process.pack(pady=8, padx=20, fill="x")
        
        self.btn_replay = ctk.CTkButton(
            control_frame,
            text="Reproducir Video",
            command=self._replay_video,
            height=35,
            fg_color="#FF9800",
            state="disabled"
        )
        self.btn_replay.pack(pady=8, padx=20, fill="x")
        
        # Barra de progreso
        self.progress = ctk.CTkProgressBar(control_frame, width=200)
        self.progress.set(0)
        self.progress.pack(pady=5, padx=20)
        self.progress_label = ctk.CTkLabel(control_frame, text="", font=("Arial", 9))
        self.progress_label.pack(pady=(0, 10))
        
        # Separador
        separator = ctk.CTkFrame(control_frame, height=2, fg_color="gray")
        separator.pack(pady=15, padx=20, fill="x")
        
        # === ESTADISTICAS (NUEVO: en parte inferior de controles) ===
        stats_title = ctk.CTkLabel(
            control_frame,
            text="ESTADISTICAS",
            font=("Arial", 14, "bold")
        )
        stats_title.pack(pady=(10, 5))
        
        self.stats_mode_label = ctk.CTkLabel(
            control_frame,
            text="",
            font=("Arial", 9),
            text_color="gray"
        )
        self.stats_mode_label.pack(pady=(0, 8))
        
        # Stats compactas
        self.stats_labels = {}
        
        stats_container = ctk.CTkFrame(control_frame, fg_color="transparent")
        stats_container.pack(fill="x", padx=15)
        
        # DENTRO
        self.stats_labels['inside'] = ctk.CTkLabel(
            stats_container,
            text="DENTRO: 0",
            font=("Arial", 13, "bold"),
            text_color="#4CAF50",
            anchor="w"
        )
        self.stats_labels['inside'].pack(pady=3, anchor="w")
        
        # ENTRADAS/SALIDAS
        self.stats_labels['entries'] = ctk.CTkLabel(
            stats_container,
            text="ENTRADAS: 0",
            font=("Arial", 11),
            anchor="w"
        )
        self.stats_labels['entries'].pack(pady=2, anchor="w")
        
        self.stats_labels['exits'] = ctk.CTkLabel(
            stats_container,
            text="SALIDAS: 0",
            font=("Arial", 11),
            anchor="w"
        )
        self.stats_labels['exits'].pack(pady=2, anchor="w")
        
        # Mini separador
        ctk.CTkFrame(stats_container, height=1, fg_color="gray").pack(fill="x", pady=8)
        
        # ULTIMA ENTRADA
        ctk.CTkLabel(
            stats_container,
            text="ULTIMA ENTRADA:",
            font=("Arial", 10, "bold"),
            anchor="w"
        ).pack(pady=(5, 2), anchor="w")
        
        self.stats_labels['last_entry_plate'] = ctk.CTkLabel(
            stats_container,
            text="---",
            font=("Arial", 10),
            anchor="w"
        )
        self.stats_labels['last_entry_plate'].pack(pady=1, anchor="w")
        
        self.stats_labels['last_entry_time'] = ctk.CTkLabel(
            stats_container,
            text="",
            font=("Arial", 9),
            text_color="gray",
            anchor="w"
        )
        self.stats_labels['last_entry_time'].pack(pady=1, anchor="w")
        
        # ULTIMA SALIDA
        ctk.CTkLabel(
            stats_container,
            text="ULTIMA SALIDA:",
            font=("Arial", 10, "bold"),
            anchor="w"
        ).pack(pady=(8, 2), anchor="w")
        
        self.stats_labels['last_exit_plate'] = ctk.CTkLabel(
            stats_container,
            text="---",
            font=("Arial", 10),
            anchor="w"
        )
        self.stats_labels['last_exit_plate'].pack(pady=1, anchor="w")
        
        self.stats_labels['last_exit_time'] = ctk.CTkLabel(
            stats_container,
            text="",
            font=("Arial", 9),
            text_color="gray",
            anchor="w"
        )
        self.stats_labels['last_exit_time'].pack(pady=1, anchor="w")
        
        # Estado (al final)
        self.status_label = ctk.CTkLabel(
            control_frame,
            text="Inicializando...",
            font=("Arial", 9),
            wraplength=220
        )
        self.status_label.pack(side="bottom", pady=10)
        
        # === COLUMNA CENTRO: Visualizacion (Canvas) ===
        display_frame = ctk.CTkFrame(main_frame)
        display_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Usar Canvas de tkinter en lugar de CTkLabel para permitir clicks
        self.canvas = Canvas(
            display_frame,
            bg="#2B2B2B",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Texto inicial
        self.canvas_text_id = self.canvas.create_text(
            400, 300,
            text="Cargue una imagen, video o active la camara",
            fill="white",
            font=("Arial", 16)
        )
        
        # Bind click
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
        # === COLUMNA DERECHA: Lista + Detalle ===
        right_panel = ctk.CTkFrame(main_frame, width=320)
        right_panel.pack(side="right", fill="y")
        right_panel.pack_propagate(False)
        
        # Panel superior: Lista de vehiculos
        list_header = ctk.CTkFrame(right_panel, fg_color="#1E1E1E", corner_radius=0)
        list_header.pack(fill="x", pady=(0, 0))
        
        self.list_title = ctk.CTkLabel(
            list_header,
            text="VEHICULOS DETECTADOS (0)",
            font=("Arial", 13, "bold"),
            text_color="#4CAF50"
        )
        self.list_title.pack(pady=10)
        
        # ScrollableFrame para lista
        self.vehicle_list_frame = ctk.CTkScrollableFrame(
            right_panel,
            height=300,
            fg_color="#2B2B2B"
        )
        self.vehicle_list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Separador
        ctk.CTkFrame(right_panel, height=2, fg_color="gray").pack(fill="x", pady=0)
        
        # Panel inferior: Detalle del vehiculo
        detail_header = ctk.CTkFrame(right_panel, fg_color="#1E1E1E", corner_radius=0)
        detail_header.pack(fill="x")
        
        self.detail_title = ctk.CTkLabel(
            detail_header,
            text="DETALLE VEHICULO",
            font=("Arial", 12, "bold")
        )
        self.detail_title.pack(pady=8)
        
        self.detail_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.detail_frame.pack(fill="both", padx=15, pady=10)
        
        # Mensaje inicial
        self.detail_empty_label = ctk.CTkLabel(
            self.detail_frame,
            text="Seleccione un vehiculo\npara ver detalles",
            font=("Arial", 11),
            text_color="gray"
        )
        self.detail_empty_label.pack(expand=True)
        
        # Inicializar stats vacias
        self._clear_stats()
    
    def _load_image(self):
        """
        Carga una imagen desde el sistema de archivos.
        """
        print("\n[APP-IMAGE] Usuario seleccionando imagen...")
        
        file_path = filedialog.askopenfilename(
            title="Seleccionar Imagen",
            filetypes=[
                ("Imagenes", "*.jpg *.jpeg *.png *.bmp"),
                ("Todos", "*.*")
            ]
        )
        
        if file_path:
            try:
                print(f"[APP-IMAGE] Cargando imagen: {file_path}")
                self.current_image = cv2.imread(file_path)
                
                if self.current_image is None:
                    print(f"[APP-ERROR] No se pudo cargar la imagen")
                    messagebox.showerror("Error", "No se pudo cargar la imagen")
                    return
                
                print(f"[APP-IMAGE] Imagen cargada - Dimensiones: {self.current_image.shape}")
                
                self.current_mode = 'image'
                
                # Limpiar datos previos
                self.current_detections = []
                self.current_image_original = None
                self.selected_vehicle_id = None
                self._clear_vehicle_list()
                self._clear_detail_panel()
                
                self._display_image(self.current_image)
                self.status_label.configure(text="Imagen cargada")
                
                # Limpiar stats en modo imagen
                self._clear_stats()
                
            except Exception as e:
                error_msg = traceback.format_exc()
                print(f"[APP-ERROR] Error al cargar imagen:\n{error_msg}")
                messagebox.showerror("Error", f"Error al cargar imagen: {str(e)}")
    
    def _load_video(self):
        """
        Carga y procesa un video desde el sistema de archivos.
        """
        print("\n[APP-VIDEO] Usuario seleccionando video...")
        
        file_path = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[
                ("Videos", "*.mp4 *.avi *.mov *.mkv"),
                ("Todos", "*.*")
            ]
        )
        
        if file_path:
            # Cambiar modo a video
            self.current_mode = 'video'
            self._update_stats_mode_label()
            
            # Limpiar datos de video anterior
            self.processed_frames = []
            self.video_stats_history = []
            self.video_vehicles_summary = {}
            self._clear_vehicle_list()
            self._clear_detail_panel()
            self.btn_replay.configure(state="disabled")
            
            # NUEVO: Limpiar datos de imagen/video anterior
            self.current_detections = []
            self.current_image_original = None
            self.selected_vehicle_id = None
            
            # Reset pipeline antes de procesar nuevo video
            if self.pipeline:
                self.pipeline.reset()
                self.pipeline.mode = 'video'
                self.pipeline.redetection_interval = getattr(config, 'REDETECTION_INTERVAL_VIDEO', 5)
                print(f"[APP-VIDEO] Modo video activado - Intervalo: {self.pipeline.redetection_interval}")
            
            # Limpiar stats al inicio
            self._clear_stats()
            
            print(f"[APP-VIDEO] Iniciando procesamiento de video: {file_path}")
            threading.Thread(
                target=self._process_video,
                args=(file_path,),
                daemon=True
            ).start()
    
    def _process_video(self, video_path):
        """
        Procesa un video frame por frame.
        """
        print(f"\n[APP-VIDEO] Abriendo video: {video_path}")
        
        try:
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                print("[APP-ERROR] No se pudo abrir el video")
                self.status_label.configure(text="Error al abrir video")
                return
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or None
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            
            print(f"[APP-VIDEO] Video abierto - Total frames: {total_frames}, FPS: {fps}")
            
            self.status_label.configure(text="Procesando video...")
            
            annotated_frames = []
            self.video_stats_history = []
            self.video_vehicles_summary = {}
            frame_idx = 0
            self.progress.set(0)
            self.progress_label.configure(text="0%")

            print("[APP-VIDEO] Iniciando procesamiento frame por frame...\n")
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_idx += 1
                
                # Procesar frame
                try:
                    if self.pipeline:
                        result = self.pipeline.process_video_frame(frame)
                        annotated = result['annotated_image']
                        detections = result['detections']
                        
                        # Acumular informacion de vehiculos unicos
                        self._accumulate_vehicle_info(detections, frame_idx, fps)
                        
                        # Guardar stats de este frame para reproduccion
                        current_stats = self.pipeline.get_video_stats().copy()
                        self.video_stats_history.append(current_stats)
                    else:
                        print(f"[APP-WARNING] Pipeline no inicializado en frame {frame_idx}")
                        annotated = frame
                        detections = []
                        self.video_stats_history.append({
                            'inside': 0, 'entries': 0, 'exits': 0, 'last_entry': None
                        })
                    
                    annotated_frames.append(annotated)
                    
                except Exception as e:
                    print(f"[APP-ERROR] Error procesando frame {frame_idx}: {str(e)}")
                    annotated_frames.append(frame.copy())
                    self.video_stats_history.append({
                        'inside': 0, 'entries': 0, 'exits': 0, 'last_entry': None
                    })

                # Actualizar progreso
                if total_frames:
                    progress = frame_idx / total_frames
                    self.progress.set(progress)
                    self.progress_label.configure(text=f"{progress*100:5.1f}%")

                # Pausa minima
                time.sleep(0.001)
            
            cap.release()
            
            print(f"\n[APP-VIDEO] Procesamiento completado - {frame_idx} frames procesados")
            print(f"[APP-VIDEO] Stats history: {len(self.video_stats_history)} registros")
            print(f"[APP-VIDEO] Vehiculos unicos detectados: {len(self.video_vehicles_summary)}")
            
            # Guardar frames procesados para replay
            self.processed_frames = annotated_frames
            self.video_fps = fps
            
            # Habilitar boton de replay
            self.btn_replay.configure(state="normal")
            
            self.progress.set(1)
            self.progress_label.configure(text="100%")
            self.status_label.configure(text="Video procesado, reproduciendo...")
            
            # Mostrar lista de vehiculos
            self._populate_vehicle_list()

            print("[APP-VIDEO] Iniciando reproduccion con stats en tiempo real...\n")
            self._play_processed_frames(annotated_frames, fps)
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"[APP-ERROR] Error critico en procesamiento de video:\n{error_msg}")
            self.status_label.configure(text=f"Error en video: {str(e)}")
    
    def _accumulate_vehicle_info(self, detections, frame_idx, fps):
        """
        Acumula informacion de vehiculos unicos durante el video.
        
        Args:
            detections (list): Detecciones del frame actual
            frame_idx (int): Numero de frame actual
            fps (float): Frames por segundo del video
        """
        for det in detections:
            track_id = det['id']
            
            # Si es la primera vez que vemos este vehiculo
            if track_id not in self.video_vehicles_summary:
                self.video_vehicles_summary[track_id] = {
                    'id': track_id,
                    'plate': det.get('Numero-Placa', '------'),
                    'brand': det.get('brand', 'DESCONOCIDA'),
                    'color': det.get('color', 'DESCONOCIDO'),
                    'class': det.get('class', 'car'),
                    'confidence': det.get('confidence', 0.0),
                    'first_frame': frame_idx,
                    'last_frame': frame_idx,
                    'fps': fps
                }
            else:
                # Actualizar ultimo frame visto
                self.video_vehicles_summary[track_id]['last_frame'] = frame_idx
    
    def _frames_to_time(self, frame, fps):
        """
        Convierte numero de frame a formato HH:MM:SS.
        
        Args:
            frame (int): Numero de frame
            fps (float): Frames por segundo
            
        Returns:
            str: Tiempo en formato HH:MM:SS
        """
        seconds = frame / fps
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _populate_vehicle_list(self):
        """
        Puebla la lista de vehiculos detectados.
        """
        self._clear_vehicle_list()
        
        if not self.video_vehicles_summary:
            return
        
        # Ordenar por ID
        sorted_vehicles = sorted(self.video_vehicles_summary.items(), key=lambda x: x[0])
        
        # Actualizar titulo
        self.list_title.configure(text=f"VEHICULOS DETECTADOS ({len(sorted_vehicles)})")
        
        # Crear filas
        for idx, (track_id, vehicle) in enumerate(sorted_vehicles):
            # Calcular tiempo
            fps = vehicle.get('fps', 30.0)
            time_start = self._frames_to_time(vehicle['first_frame'], fps)
            time_end = self._frames_to_time(vehicle['last_frame'], fps)
            time_range = f"{time_start} - {time_end}"
            
            vehicle_data = {
                'id': track_id,
                'plate': vehicle['plate'],
                'time_range': time_range,
                **vehicle
            }
            
            # Crear fila
            row = VehicleListRow(
                self.vehicle_list_frame,
                vehicle_data,
                self._on_vehicle_selected,
                is_odd=(idx % 2 == 1)
            )
            row.pack(fill="x", pady=0)
            
            self.vehicle_list_rows[track_id] = row
    
    def _clear_vehicle_list(self):
        """
        Limpia la lista de vehiculos.
        """
        for widget in self.vehicle_list_frame.winfo_children():
            widget.destroy()
        
        self.vehicle_list_rows = {}
        self.list_title.configure(text="VEHICULOS DETECTADOS (0)")
    
    def _on_vehicle_selected(self, vehicle_id):
        """
        Maneja la seleccion de un vehiculo de la lista.
        
        Args:
            vehicle_id (int): ID del vehiculo seleccionado
        """
        print(f"[APP-UI] Vehiculo seleccionado: #{vehicle_id}")
        
        # Desseleccionar anterior
        if self.selected_vehicle_id is not None:
            if self.selected_vehicle_id in self.vehicle_list_rows:
                self.vehicle_list_rows[self.selected_vehicle_id].set_selected(False)
        
        # Seleccionar nuevo
        self.selected_vehicle_id = vehicle_id
        if vehicle_id in self.vehicle_list_rows:
            self.vehicle_list_rows[vehicle_id].set_selected(True)
        
        # Mostrar detalle
        self._show_vehicle_detail(vehicle_id)
        
        # Redibujar imagen con bbox resaltado SOLO en modo imagen
        # En modo video, la imagen se actualiza constantemente durante reproduccion
        if self.current_mode == 'image' and self.current_detections and self.current_image_original is not None:
            self._redraw_image_with_highlight(vehicle_id)
    
    def _show_vehicle_detail(self, vehicle_id):
        """
        Muestra el detalle de un vehiculo en el panel inferior.
        
        Args:
            vehicle_id (int): ID del vehiculo
        """
        # Limpiar panel
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
        
        # Buscar vehiculo
        vehicle = None
        if self.current_mode == 'video':
            vehicle = self.video_vehicles_summary.get(vehicle_id)
        elif self.current_mode in ['image', 'camera']:
            # Buscar en detecciones actuales
            for det in self.current_detections:
                if det['id'] == vehicle_id:
                    vehicle = det
                    break
        
        if not vehicle:
            return
        
        # Actualizar titulo
        self.detail_title.configure(text=f"DETALLE VEHICULO #{vehicle_id}")
        
        # Crear grid de detalles
        details_grid = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        details_grid.pack(fill="both", expand=True, pady=5)
        
        row = 0
        
        # Placa
        ctk.CTkLabel(
            details_grid,
            text="Placa:",
            font=("Arial", 11, "bold"),
            anchor="e",
            width=100
        ).grid(row=row, column=0, sticky="e", padx=5, pady=3)
        
        plate = vehicle.get('plate', vehicle.get('Numero-Placa', '------'))
        ctk.CTkLabel(
            details_grid,
            text=plate,
            font=("Consolas", 11),
            anchor="w"
        ).grid(row=row, column=1, sticky="w", padx=5, pady=3)
        row += 1
        
        # Marca
        ctk.CTkLabel(
            details_grid,
            text="Marca:",
            font=("Arial", 11, "bold"),
            anchor="e",
            width=100
        ).grid(row=row, column=0, sticky="e", padx=5, pady=3)
        
        ctk.CTkLabel(
            details_grid,
            text=vehicle.get('brand', 'DESCONOCIDA'),
            font=("Arial", 11),
            anchor="w"
        ).grid(row=row, column=1, sticky="w", padx=5, pady=3)
        row += 1
        
        # Color
        ctk.CTkLabel(
            details_grid,
            text="Color:",
            font=("Arial", 11, "bold"),
            anchor="e",
            width=100
        ).grid(row=row, column=0, sticky="e", padx=5, pady=3)
        
        ctk.CTkLabel(
            details_grid,
            text=vehicle.get('color', 'DESCONOCIDO'),
            font=("Arial", 11),
            anchor="w"
        ).grid(row=row, column=1, sticky="w", padx=5, pady=3)
        row += 1
        
        # Tipo
        ctk.CTkLabel(
            details_grid,
            text="Tipo:",
            font=("Arial", 11, "bold"),
            anchor="e",
            width=100
        ).grid(row=row, column=0, sticky="e", padx=5, pady=3)
        
        ctk.CTkLabel(
            details_grid,
            text=vehicle.get('class', 'car'),
            font=("Arial", 11),
            anchor="w"
        ).grid(row=row, column=1, sticky="w", padx=5, pady=3)
        row += 1
        
        # Confianza
        ctk.CTkLabel(
            details_grid,
            text="Confianza:",
            font=("Arial", 11, "bold"),
            anchor="e",
            width=100
        ).grid(row=row, column=0, sticky="e", padx=5, pady=3)
        
        conf = vehicle.get('confidence', 0.0)
        ctk.CTkLabel(
            details_grid,
            text=f"{conf:.2f}",
            font=("Arial", 11),
            anchor="w"
        ).grid(row=row, column=1, sticky="w", padx=5, pady=3)
        row += 1
        
        # Tiempo en video (solo si es video)
        if self.current_mode == 'video' and 'first_frame' in vehicle:
            # Separador
            ctk.CTkFrame(
                details_grid,
                height=1,
                fg_color="gray"
            ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
            row += 1
            
            ctk.CTkLabel(
                details_grid,
                text="Tiempo en video:",
                font=("Arial", 11, "bold"),
                anchor="w"
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 3))
            row += 1
            
            fps = vehicle.get('fps', 30.0)
            time_start = self._frames_to_time(vehicle['first_frame'], fps)
            time_end = self._frames_to_time(vehicle['last_frame'], fps)
            duration_frames = vehicle['last_frame'] - vehicle['first_frame']
            duration_seconds = duration_frames / fps
            
            # Entrada
            ctk.CTkLabel(
                details_grid,
                text="  Entrada:",
                font=("Arial", 10),
                anchor="e",
                width=100
            ).grid(row=row, column=0, sticky="e", padx=5, pady=2)
            
            ctk.CTkLabel(
                details_grid,
                text=time_start,
                font=("Consolas", 10),
                anchor="w"
            ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
            row += 1
            
            # Salida
            ctk.CTkLabel(
                details_grid,
                text="  Salida:",
                font=("Arial", 10),
                anchor="e",
                width=100
            ).grid(row=row, column=0, sticky="e", padx=5, pady=2)
            
            ctk.CTkLabel(
                details_grid,
                text=time_end,
                font=("Consolas", 10),
                anchor="w"
            ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
            row += 1
            
            # Duracion
            ctk.CTkLabel(
                details_grid,
                text="  Duracion:",
                font=("Arial", 10),
                anchor="e",
                width=100
            ).grid(row=row, column=0, sticky="e", padx=5, pady=2)
            
            ctk.CTkLabel(
                details_grid,
                text=f"{duration_seconds:.1f} seg",
                font=("Consolas", 10),
                anchor="w"
            ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
    
    def _clear_detail_panel(self):
        """
        Limpia el panel de detalle.
        """
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
        
        self.detail_title.configure(text="DETALLE VEHICULO")
        
        self.detail_empty_label = ctk.CTkLabel(
            self.detail_frame,
            text="Seleccione un vehiculo\npara ver detalles",
            font=("Arial", 11),
            text_color="gray"
        )
        self.detail_empty_label.pack(expand=True)
    
    def _on_canvas_click(self, event):
        """
        Maneja el click en el canvas.
        
        Args:
            event: Evento de click
        """
        if not self.current_detections or self.current_image_original is None:
            return
        
        # Obtener coordenadas del click
        click_x = event.x
        click_y = event.y
        
        # Convertir a coordenadas de imagen original
        display_w, display_h = self.current_image_display_size
        if display_w == 0 or display_h == 0:
            return
        
        orig_h, orig_w = self.current_image_original.shape[:2]
        
        scale_x = orig_w / display_w
        scale_y = orig_h / display_h
        
        orig_x = click_x * scale_x
        orig_y = click_y * scale_y
        
        # Buscar vehiculo clickeado
        for det in self.current_detections:
            x1, y1, x2, y2 = det['bbox']
            
            if x1 <= orig_x <= x2 and y1 <= orig_y <= y2:
                print(f"[APP-UI] Click en vehiculo #{det['id']}")
                self._on_vehicle_selected(det['id'])
                return
    
    def _draw_bboxes_on_image(self, image, detections, highlight_id=None):
        """
        Dibuja los bounding boxes sobre una imagen.
        
        Args:
            image: Imagen base (numpy array BGR)
            detections: Lista de detecciones
            highlight_id: ID del vehiculo a resaltar (None = ninguno)
            
        Returns:
            Imagen con bboxes dibujados
        """
        output = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            
            if det['id'] == highlight_id:
                # Resaltado: amarillo grueso
                cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 255), 4)
                cv2.putText(
                    output,
                    f"ID: {det['id']}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2
                )
            else:
                # Normal: verde
                cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    output,
                    f"ID: {det['id']}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1
                )
        
        return output
    
    def _redraw_image_with_highlight(self, vehicle_id):
        """
        Redibuja la imagen con el vehiculo seleccionado resaltado.
        
        Args:
            vehicle_id (int): ID del vehiculo a resaltar
        """
        if self.current_image_original is None or not self.current_detections:
            return
        
        # Dibujar bboxes con resaltado
        image_with_bboxes = self._draw_bboxes_on_image(
            self.current_image_original,
            self.current_detections,
            highlight_id=vehicle_id
        )
        
        # Mostrar (sin guardar como original)
        self._display_image(image_with_bboxes, save_as_original=False)
    
    def _toggle_camera(self):
        """
        Activa o desactiva la camara.
        """
        if not self.camera_active:
            print("\n[APP-CAMERA] Activando camara...")

            # Cambiar modo a camara
            self.current_mode = 'camera'
            self._update_stats_mode_label()

            # Limpiar estado previo para no mostrar lista/detalle de imagen/video
            self.selected_vehicle_id = None
            self.current_detections = []
            self.current_image_original = None
            self._clear_vehicle_list()
            self._clear_detail_panel()

            # Reset pipeline Y cambiar a modo camara
            if self.pipeline:
                self.pipeline.reset()
                self.pipeline.mode = 'camera'
                self.pipeline.redetection_interval = getattr(config, 'REDETECTION_INTERVAL_CAMERA', 30)
                print(f"[APP-CAMERA] Modo camara activado - Intervalo: {self.pipeline.redetection_interval}")
            
            self.camera_active = True
            self.btn_camera.configure(text="Detener Camara", fg_color="red")
            threading.Thread(target=self._camera_loop, daemon=True).start()
        else:
            print("[APP-CAMERA] Deteniendo camara...")
            self.camera_active = False
            self.btn_camera.configure(text="Activar Camara", fg_color="#1f6aa5")
            if self.video_capture:
                self.video_capture.release()
    
    def _camera_loop(self):
        """
        Loop principal de captura de camara.
        """
        try:
            self.video_capture = cv2.VideoCapture(0)
            
            if not self.video_capture.isOpened():
                print("[APP-ERROR] No se pudo abrir la camara")
                self.status_label.configure(text="No se pudo abrir la camara")
                self.camera_active = False
                return
            
            print("[APP-CAMERA] Camara abierta, iniciando captura...\n")
            
            while self.camera_active:
                ret, frame = self.video_capture.read()
                if not ret:
                    break
                
                try:
                    if self.pipeline:
                        result = self.pipeline.process_video_frame(frame)
                        # Guardar detecciones actuales para lista/detalle
                        self.current_detections = result.get('detections', [])
                        self.current_image_original = frame.copy()

                        self._display_image(result['annotated_image'])

                        # Actualizar stats cada 30 frames
                        self.frame_counter += 1
                        if self.frame_counter >= self.stats_update_interval:
                            self._update_stats()
                            self.frame_counter = 0

                        # Refrescar lista de vehiculos cada vez que se actualizan stats
                        if self.frame_counter == 0:
                            self._populate_vehicle_list_from_detections(self.current_detections)
                            # Mantener seleccion si sigue presente
                            if (self.selected_vehicle_id is not None and
                                any(det['id'] == self.selected_vehicle_id for det in self.current_detections)):
                                self._on_vehicle_selected(self.selected_vehicle_id)
                    else:
                        self._display_image(frame)
                except Exception as e:
                    print(f"[APP-ERROR] Error en frame de camara: {str(e)}")
                
                time.sleep(0.03)
            
            self.video_capture.release()
            print("[APP-CAMERA] Camara detenida\n")
            self.status_label.configure(text="Camara detenida")
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"[APP-ERROR] Error en camara:\n{error_msg}")
            self.status_label.configure(text=f"Error de camara: {str(e)}")
            self.camera_active = False
    
    def _process_current(self):
        """
        Procesa la imagen actual cargada.
        """
        if self.current_image is None:
            messagebox.showinfo("Info", "Cargue una imagen primero")
            return
        
        if not self.pipeline:
            messagebox.showinfo("Info", "Modelos aun cargando...")
            return
        
        print("\n[APP-PROCESS] Procesando imagen actual...")
        threading.Thread(target=self._process_image_thread, daemon=True).start()
    
    def _process_image_thread(self):
        """
        Procesa la imagen en un thread separado.
        """
        try:
            self.status_label.configure(text="Procesando...")
            
            result = self.pipeline.process_image(self.current_image)
            
            # Guardar detecciones
            self.current_detections = result['detections']
            
            # Guardar imagen SIN bboxes para permitir redibujo
            self.current_image_original = self.current_image.copy()
            
            # Dibujar bboxes sobre imagen original (sin highlight inicial)
            image_with_bboxes = self._draw_bboxes_on_image(
                self.current_image_original,
                self.current_detections,
                highlight_id=None
            )
            
            # Mostrar imagen CON bboxes dibujados
            self._display_image(image_with_bboxes, save_as_original=False)
            
            # Poblar lista de vehiculos
            self._populate_vehicle_list_from_detections(result['detections'])
            
            num_detections = len(result['detections'])
            print(f"[APP-PROCESS] Procesamiento completado - {num_detections} vehiculos detectados\n")
            
            self.status_label.configure(
                text=f"Procesado: {num_detections} vehiculos detectados"
            )
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"[APP-ERROR] Error en procesamiento:\n{error_msg}")
            self.status_label.configure(text=f"Error: {str(e)}")
    
    def _populate_vehicle_list_from_detections(self, detections):
        """
        Puebla la lista de vehiculos desde detecciones de imagen.
        
        Args:
            detections (list): Lista de detecciones
        """
        self._clear_vehicle_list()
        
        if not detections:
            return
        
        # Ordenar por ID
        sorted_detections = sorted(detections, key=lambda x: x['id'])
        
        # Actualizar titulo
        self.list_title.configure(text=f"VEHICULOS DETECTADOS ({len(sorted_detections)})")
        
        # Crear filas
        for idx, det in enumerate(sorted_detections):
            vehicle_data = {
                'id': det['id'],
                'plate': det.get('Numero-Placa', '------'),
                'time_range': 'N/A',  # No aplica en imagen
                **det
            }
            
            # Crear fila
            row = VehicleListRow(
                self.vehicle_list_frame,
                vehicle_data,
                self._on_vehicle_selected,
                is_odd=(idx % 2 == 1)
            )
            row.pack(fill="x", pady=0)
            
            self.vehicle_list_rows[det['id']] = row
    
    def _display_image(self, image, save_as_original=False):
        """
        Muestra una imagen en el canvas.
        
        Args:
            image: Imagen en formato numpy array (BGR)
            save_as_original: Si True, guarda esta imagen como original (sin bboxes)
        """
        try:
            # Guardar imagen original solo si se solicita explicitamente
            if save_as_original:
                self.current_image_original = image.copy()
            
            # Convertir BGR a RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Redimensionar manteniendo aspect ratio
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 800
                canvas_height = 600
            
            h, w = image_rgb.shape[:2]
            
            scale = min(canvas_width/w, canvas_height/h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # Guardar tamano mostrado
            self.current_image_display_size = (new_w, new_h)
            
            image_resized = cv2.resize(image_rgb, (new_w, new_h))
            
            # Convertir a formato PIL luego a PhotoImage
            pil_image = Image.fromarray(image_resized)
            self.photo_image = ImageTk.PhotoImage(pil_image)
            
            # Limpiar canvas
            self.canvas.delete("all")
            
            # Centrar imagen en canvas
            x = (canvas_width - new_w) // 2
            y = (canvas_height - new_h) // 2
            
            self.canvas.create_image(x, y, anchor="nw", image=self.photo_image)
            
        except Exception as e:
            print(f"[APP-WARNING] Error mostrando imagen: {str(e)}")
    
    def _update_stats_mode_label(self):
        """
        Actualiza el label que indica el modo de stats.
        """
        if self.current_mode == 'video':
            self.stats_mode_label.configure(text="(Video - Temporal)")
        elif self.current_mode == 'camera':
            self.stats_mode_label.configure(text="(Camara - Base de Datos)")
        else:
            self.stats_mode_label.configure(text="")
    
    def _clear_stats(self):
        """
        Limpia el panel de estadisticas.
        """
        self.stats_labels['inside'].configure(text="DENTRO: 0")
        self.stats_labels['entries'].configure(text="ENTRADAS: 0")
        self.stats_labels['exits'].configure(text="SALIDAS: 0")
        self.stats_labels['last_entry_plate'].configure(text="---")
        self.stats_labels['last_entry_time'].configure(text="")
        self.stats_labels['last_exit_plate'].configure(text="---")
        self.stats_labels['last_exit_time'].configure(text="")
    
    def _update_stats_from_dict(self, stats):
        """
        Actualiza el panel de estadisticas desde un diccionario de stats.
        
        Args:
            stats (dict): {'inside': int, 'entries': int, 'exits': int, 'last_entry': dict, 'last_exit': dict}
        """
        try:
            self.stats_labels['inside'].configure(text=f"DENTRO: {stats['inside']}")
            self.stats_labels['entries'].configure(text=f"ENTRADAS: {stats['entries']}")
            self.stats_labels['exits'].configure(text=f"SALIDAS: {stats['exits']}")
            
            # Ultima entrada
            if stats.get('last_entry'):
                plate = stats['last_entry'].get('plate', '---')
                entry_time = stats['last_entry'].get('timestamp')
                
                if entry_time:
                    now = datetime.now()
                    diff = now - entry_time
                    minutes_ago = int(diff.total_seconds() / 60)
                    
                    if minutes_ago < 1:
                        time_str = "hace <1 min"
                    elif minutes_ago < 60:
                        time_str = f"hace {minutes_ago} min"
                    else:
                        hours = minutes_ago // 60
                        time_str = f"hace {hours}h {minutes_ago % 60}min"
                else:
                    time_str = ""
                
                if len(plate) > 15:
                    plate = plate[:13] + ".."
                
                self.stats_labels['last_entry_plate'].configure(text=plate)
                self.stats_labels['last_entry_time'].configure(text=time_str)
            else:
                self.stats_labels['last_entry_plate'].configure(text="---")
                self.stats_labels['last_entry_time'].configure(text="")
            
            # Ultima salida
            if stats.get('last_exit'):
                plate = stats['last_exit'].get('plate', '---')
                exit_time = stats['last_exit'].get('timestamp')
                
                if exit_time:
                    now = datetime.now()
                    diff = now - exit_time
                    minutes_ago = int(diff.total_seconds() / 60)
                    
                    if minutes_ago < 1:
                        time_str = "hace <1 min"
                    elif minutes_ago < 60:
                        time_str = f"hace {minutes_ago} min"
                    else:
                        hours = minutes_ago // 60
                        time_str = f"hace {hours}h {minutes_ago % 60}min"
                else:
                    time_str = ""
                
                if len(plate) > 15:
                    plate = plate[:13] + ".."
                
                self.stats_labels['last_exit_plate'].configure(text=plate)
                self.stats_labels['last_exit_time'].configure(text=time_str)
            else:
                self.stats_labels['last_exit_plate'].configure(text="---")
                self.stats_labels['last_exit_time'].configure(text="")
            
        except Exception as e:
            print(f"[APP-WARNING] Error actualizando stats desde dict: {str(e)}")
    
    def _update_stats(self):
        """
        Actualiza el panel de estadisticas segun el modo actual.
        """
        try:
            if not self.pipeline:
                self._clear_stats()
                return
            
            # Modo VIDEO: Stats temporales en memoria
            if self.current_mode == 'video':
                stats = self.pipeline.get_video_stats()
                self._update_stats_from_dict(stats)
            
            # Modo CAMARA: Stats de BD
            elif self.current_mode == 'camera':
                if not self.pipeline.enable_database or not self.pipeline.db:
                    self._clear_stats()
                    return
                
                stats = self.pipeline.db.get_today_stats()
                
                self.stats_labels['inside'].configure(text=f"DENTRO: {stats['inside']}")
                self.stats_labels['entries'].configure(text=f"ENTRADAS: {stats['entries_today']}")
                self.stats_labels['exits'].configure(text=f"SALIDAS: {stats['exits_today']}")
                
                # Ultima entrada
                if stats['last_entry']:
                    plate = stats['last_entry']['plate']
                    entry_time = datetime.fromisoformat(stats['last_entry']['entry_time'])
                    
                    now = datetime.now()
                    diff = now - entry_time
                    minutes_ago = int(diff.total_seconds() / 60)
                    
                    if minutes_ago < 1:
                        time_str = "hace <1 min"
                    elif minutes_ago < 60:
                        time_str = f"hace {minutes_ago} min"
                    else:
                        hours = minutes_ago // 60
                        time_str = f"hace {hours}h {minutes_ago % 60}min"
                    
                    if len(plate) > 15:
                        plate = plate[:13] + ".."
                    
                    self.stats_labels['last_entry_plate'].configure(text=plate)
                    self.stats_labels['last_entry_time'].configure(text=time_str)
                else:
                    self.stats_labels['last_entry_plate'].configure(text="---")
                    self.stats_labels['last_entry_time'].configure(text="")
                
                # Ultima salida
                if stats.get('last_exit'):
                    plate = stats['last_exit']['plate']
                    exit_time = datetime.fromisoformat(stats['last_exit']['exit_time'])
                    
                    now = datetime.now()
                    diff = now - exit_time
                    minutes_ago = int(diff.total_seconds() / 60)
                    
                    if minutes_ago < 1:
                        time_str = "hace <1 min"
                    elif minutes_ago < 60:
                        time_str = f"hace {minutes_ago} min"
                    else:
                        hours = minutes_ago // 60
                        time_str = f"hace {hours}h {minutes_ago % 60}min"
                    
                    if len(plate) > 15:
                        plate = plate[:13] + ".."
                    
                    self.stats_labels['last_exit_plate'].configure(text=plate)
                    self.stats_labels['last_exit_time'].configure(text=time_str)
                else:
                    self.stats_labels['last_exit_plate'].configure(text="---")
                    self.stats_labels['last_exit_time'].configure(text="")
            
            # Modo IMAGEN o SIN MODO: Limpiar
            else:
                self._clear_stats()
            
        except Exception as e:
            print(f"[APP-WARNING] Error actualizando estadisticas: {str(e)}")

    def _play_processed_frames(self, frames, fps):
        """
        Reproduce en la UI la lista de frames procesados respetando el FPS.
        Actualiza estadisticas en tiempo real segun el frame actual.
        """
        if not frames:
            print("[APP-WARNING] Sin frames para reproducir")
            self.status_label.configure(text="Sin frames para reproducir")
            return

        delay_ms = int(1000 / fps) if fps and fps > 0 else 33
        
        print(f"[APP-PLAY] Reproduciendo {len(frames)} frames a {fps} FPS")
        print(f"[APP-PLAY] Stats history disponible: {len(self.video_stats_history)} registros")

        def show_frame(i):
            if i >= len(frames):
                print("[APP-PLAY] Reproduccion finalizada\n")
                self.status_label.configure(text="Reproduccion finalizada")
                return
            
            try:
                # Mostrar frame
                self._display_image(frames[i])
                
                # Actualizar estadisticas del frame actual (tiempo real)
                if i < len(self.video_stats_history):
                    self._update_stats_from_dict(self.video_stats_history[i])
                
            except Exception as e:
                print(f"[APP-WARNING] Error mostrando frame {i}: {str(e)}")
            
            self.root.after(delay_ms, lambda: show_frame(i + 1))

        # Iniciar desde stats en 0
        self._clear_stats()
        show_frame(0)
    
    def _replay_video(self):
        """
        Reproduce nuevamente el video procesado con sus estadisticas.
        """
        if not self.processed_frames:
            messagebox.showinfo("Info", "No hay video procesado para reproducir")
            return
        
        print(f"\n[APP-REPLAY] Reproduciendo video guardado ({len(self.processed_frames)} frames)")
        self.status_label.configure(text="Reproduciendo video...")
        
        # Limpiar stats y reproducir desde el inicio
        self._clear_stats()
        self._play_processed_frames(self.processed_frames, self.video_fps)
    
    def run(self):
        """
        Inicia la aplicacion.
        """
        print("\n[APP-RUN] Iniciando loop principal de la aplicacion\n")
        self.root.mainloop()


def main():
    app = VehicleDetectorApp()
    app.run()


if __name__ == "__main__":
    main()
