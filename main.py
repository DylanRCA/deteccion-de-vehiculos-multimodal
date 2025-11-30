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
    """Fila clickeable en la lista de vehiculos detectados."""
    
    def __init__(self, parent, vehicle_data, on_click_callback, is_selected=False):
        # Color de fondo segun seleccion
        bg_color = "#2E5A2E" if is_selected else "#2B2B2B"
        super().__init__(parent, fg_color=bg_color, corner_radius=5)
        
        self.vehicle_data = vehicle_data
        self.on_click_callback = on_click_callback
        self.is_selected = is_selected
        
        # Hacer clickeable todo el frame
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_hover_enter)
        self.bind("<Leave>", self._on_hover_leave)
        
        # Layout horizontal
        self.columnconfigure(0, weight=0)  # ID
        self.columnconfigure(1, weight=1)  # Placa
        self.columnconfigure(2, weight=0)  # Tiempo
        
        # ID
        id_label = ctk.CTkLabel(
            self,
            text=f"#{vehicle_data['id']:02d}",
            font=("Arial", 12, "bold"),
            text_color="#4CAF50",
            width=40
        )
        id_label.grid(row=0, column=0, padx=(8, 5), pady=6, sticky="w")
        id_label.bind("<Button-1>", self._on_click)
        
        # Placa
        plate = vehicle_data.get('plate', '------')
        if len(plate) > 12:
            plate = plate[:10] + ".."
        
        plate_label = ctk.CTkLabel(
            self,
            text=plate,
            font=("Consolas", 11),
            text_color="white"
        )
        plate_label.grid(row=0, column=1, padx=5, pady=6, sticky="w")
        plate_label.bind("<Button-1>", self._on_click)
        
        # Rango de tiempo
        time_range = vehicle_data.get('time_range', '')
        time_label = ctk.CTkLabel(
            self,
            text=time_range,
            font=("Arial", 9),
            text_color="#AAAAAA"
        )
        time_label.grid(row=0, column=2, padx=(5, 8), pady=6, sticky="e")
        time_label.bind("<Button-1>", self._on_click)
    
    def _on_click(self, event=None):
        """Maneja click en la fila."""
        if self.on_click_callback:
            self.on_click_callback(self.vehicle_data)
    
    def _on_hover_enter(self, event=None):
        """Hover enter - resaltar si no esta seleccionado."""
        if not self.is_selected:
            self.configure(fg_color="#3A3A3A")
    
    def _on_hover_leave(self, event=None):
        """Hover leave - restaurar color."""
        if not self.is_selected:
            self.configure(fg_color="#2B2B2B")
    
    def set_selected(self, selected):
        """Cambia estado de seleccion."""
        self.is_selected = selected
        if selected:
            self.configure(fg_color="#2E5A2E")
        else:
            self.configure(fg_color="#2B2B2B")


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
        self.root.geometry("1400x800")
        
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
        
        # Detecciones por frame para highlight preciso
        self.detections_per_frame = []  # [frame_idx] -> [detections]
        
        # Seleccion de vehiculo
        self.selected_vehicle_id = None
        self.vehicle_rows = {}  # track_id -> VehicleListRow widget
        
        # Control de reproduccion
        self.playback_active = False
        self.playback_stop_requested = False
        
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
        
        # === COLUMNA IZQUIERDA: Controles ===
        control_frame = ctk.CTkFrame(main_frame, width=220)
        control_frame.pack(side="left", fill="y", padx=(0, 10))
        control_frame.pack_propagate(False)
        
        # Titulo
        title_label = ctk.CTkLabel(
            control_frame,
            text="Detector de Vehiculos",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=15)
        
        # Botones de control
        self.btn_image = ctk.CTkButton(
            control_frame,
            text="Subir Imagen",
            command=self._load_image,
            height=35
        )
        self.btn_image.pack(pady=8, padx=15, fill="x")
        
        self.btn_video = ctk.CTkButton(
            control_frame,
            text="Subir Video",
            command=self._load_video,
            height=35
        )
        self.btn_video.pack(pady=8, padx=15, fill="x")
        
        self.btn_camera = ctk.CTkButton(
            control_frame,
            text="Activar Camara",
            command=self._toggle_camera,
            height=35
        )
        self.btn_camera.pack(pady=8, padx=15, fill="x")
        
        self.btn_process = ctk.CTkButton(
            control_frame,
            text="Procesar",
            command=self._process_current,
            height=35,
            fg_color="green"
        )
        self.btn_process.pack(pady=8, padx=15, fill="x")
        
        # Separador
        ctk.CTkFrame(control_frame, height=2, fg_color="gray").pack(pady=15, padx=15, fill="x")
        
        # Botones de reproduccion
        self.btn_replay = ctk.CTkButton(
            control_frame,
            text="Reproducir Todo",
            command=self._replay_video,
            height=35,
            fg_color="#FF9800",
            state="disabled"
        )
        self.btn_replay.pack(pady=8, padx=15, fill="x")
        
        self.btn_stop = ctk.CTkButton(
            control_frame,
            text="Detener",
            command=self._stop_playback,
            height=35,
            fg_color="#F44336",
            state="disabled"
        )
        self.btn_stop.pack(pady=8, padx=15, fill="x")
        
        # Barra de progreso
        self.progress = ctk.CTkProgressBar(control_frame, width=180)
        self.progress.set(0)
        self.progress.pack(pady=10, padx=15)
        self.progress_label = ctk.CTkLabel(control_frame, text="", font=("Arial", 9))
        self.progress_label.pack(pady=(0, 10))
        
        # Separador
        ctk.CTkFrame(control_frame, height=2, fg_color="gray").pack(pady=10, padx=15, fill="x")
        
        # === ESTADISTICAS COMPACTAS ===
        stats_title = ctk.CTkLabel(
            control_frame,
            text="ESTADISTICAS",
            font=("Arial", 12, "bold")
        )
        stats_title.pack(pady=(10, 5))
        
        self.stats_mode_label = ctk.CTkLabel(
            control_frame,
            text="",
            font=("Arial", 9),
            text_color="gray"
        )
        self.stats_mode_label.pack(pady=(0, 5))
        
        # Stats labels
        self.stats_labels = {}
        
        stats_container = ctk.CTkFrame(control_frame, fg_color="transparent")
        stats_container.pack(fill="x", padx=10)
        
        self.stats_labels['inside'] = ctk.CTkLabel(
            stats_container,
            text="DENTRO: 0",
            font=("Arial", 11, "bold"),
            text_color="#4CAF50"
        )
        self.stats_labels['inside'].pack(anchor="w", pady=2)
        
        self.stats_labels['entries'] = ctk.CTkLabel(
            stats_container,
            text="ENTRADAS: 0",
            font=("Arial", 10)
        )
        self.stats_labels['entries'].pack(anchor="w", pady=1)
        
        self.stats_labels['exits'] = ctk.CTkLabel(
            stats_container,
            text="SALIDAS: 0",
            font=("Arial", 10)
        )
        self.stats_labels['exits'].pack(anchor="w", pady=1)
        
        # Estado (al final)
        self.status_label = ctk.CTkLabel(
            control_frame,
            text="Inicializando...",
            font=("Arial", 9),
            wraplength=200
        )
        self.status_label.pack(side="bottom", pady=10)
        
        # === COLUMNA CENTRO: Visualizacion ===
        display_frame = ctk.CTkFrame(main_frame)
        display_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.canvas = Canvas(
            display_frame,
            bg="#1E1E1E",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Texto inicial
        self.canvas.create_text(
            400, 300,
            text="Cargue una imagen, video o active la camara",
            fill="white",
            font=("Arial", 14)
        )
        
        # === COLUMNA DERECHA: Lista de vehiculos ===
        right_frame = ctk.CTkFrame(main_frame, width=280)
        right_frame.pack(side="right", fill="y")
        right_frame.pack_propagate(False)
        
        # Titulo lista
        list_title_frame = ctk.CTkFrame(right_frame, fg_color="#1A1A1A")
        list_title_frame.pack(fill="x")
        
        self.list_title = ctk.CTkLabel(
            list_title_frame,
            text="VEHICULOS DETECTADOS",
            font=("Arial", 12, "bold"),
            text_color="#4CAF50"
        )
        self.list_title.pack(pady=10)
        
        # Subtitulo con instrucciones
        self.list_subtitle = ctk.CTkLabel(
            right_frame,
            text="Click para ver segmento",
            font=("Arial", 9),
            text_color="gray"
        )
        self.list_subtitle.pack(pady=(0, 5))
        
        # Lista scrolleable de vehiculos
        self.vehicle_list_frame = ctk.CTkScrollableFrame(
            right_frame,
            fg_color="#252525"
        )
        self.vehicle_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Separador
        ctk.CTkFrame(right_frame, height=2, fg_color="gray").pack(fill="x", pady=5)
        
        # Panel de detalle del vehiculo seleccionado
        detail_title = ctk.CTkLabel(
            right_frame,
            text="DETALLE",
            font=("Arial", 11, "bold")
        )
        detail_title.pack(pady=(5, 5))
        
        self.detail_frame = ctk.CTkFrame(right_frame, fg_color="#252525", height=180)
        self.detail_frame.pack(fill="x", padx=5, pady=(0, 10))
        self.detail_frame.pack_propagate(False)
        
        # Contenido inicial del detalle
        self.detail_labels = {}
        self._create_detail_labels()
    
    def _create_detail_labels(self):
        """Crea los labels del panel de detalle."""
        # Limpiar existentes
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
        
        self.detail_labels = {}
        
        # Placeholder
        self.detail_placeholder = ctk.CTkLabel(
            self.detail_frame,
            text="Seleccione un vehiculo",
            font=("Arial", 10),
            text_color="gray"
        )
        self.detail_placeholder.pack(expand=True)
    
    def _update_detail_panel(self, vehicle_data):
        """Actualiza el panel de detalle con info del vehiculo."""
        # Limpiar
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
        
        if not vehicle_data:
            self._create_detail_labels()
            return
        
        # Grid de detalles
        container = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        details = [
            ("ID:", f"#{vehicle_data['id']:02d}"),
            ("Placa:", vehicle_data.get('plate', '------')),
            ("Marca:", vehicle_data.get('brand', 'DESCONOCIDA')),
            ("Color:", vehicle_data.get('color', 'DESCONOCIDO')),
            ("Frames:", f"{vehicle_data.get('first_frame', 0)} - {vehicle_data.get('last_frame', 0)}"),
            ("Tiempo:", vehicle_data.get('time_range', 'N/A')),
        ]
        
        for i, (label, value) in enumerate(details):
            ctk.CTkLabel(
                container,
                text=label,
                font=("Arial", 10, "bold"),
                text_color="#888888"
            ).grid(row=i, column=0, sticky="e", padx=(0, 5), pady=2)
            
            ctk.CTkLabel(
                container,
                text=value,
                font=("Arial", 10),
                text_color="white"
            ).grid(row=i, column=1, sticky="w", pady=2)
    
    def _load_image(self):
        """Carga una imagen desde el sistema de archivos."""
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
                self._display_image(self.current_image)
                self.status_label.configure(text="Imagen cargada. Click 'Procesar'")
                
                # Limpiar lista y stats
                self._clear_vehicle_list()
                self._clear_stats()
                
            except Exception as e:
                error_msg = traceback.format_exc()
                print(f"[APP-ERROR] Error al cargar imagen:\n{error_msg}")
                messagebox.showerror("Error", f"Error al cargar imagen: {str(e)}")
    
    def _load_video(self):
        """Carga y procesa un video desde el sistema de archivos."""
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
            self.detections_per_frame = []
            self.selected_vehicle_id = None
            self._clear_vehicle_list()
            self.btn_replay.configure(state="disabled")
            
            # Reset pipeline antes de procesar nuevo video
            if self.pipeline:
                self.pipeline.reset()
                self.pipeline.mode = 'video'
                self.pipeline.redetection_interval = getattr(config, 'REDETECTION_INTERVAL_VIDEO', 5)
                print(f"[APP-VIDEO] Modo video activado")
            
            self._clear_stats()
            
            print(f"[APP-VIDEO] Iniciando procesamiento de video: {file_path}")
            threading.Thread(
                target=self._process_video,
                args=(file_path,),
                daemon=True
            ).start()
    
    def _process_video(self, video_path):
        """Procesa un video frame por frame."""
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
            self.video_fps = fps
            
            annotated_frames = []
            self.video_stats_history = []
            self.video_vehicles_summary = {}
            self.detections_per_frame = []
            frame_idx = 0
            self.progress.set(0)
            self.progress_label.configure(text="0%")

            print("[APP-VIDEO] Iniciando procesamiento frame por frame...\n")
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_idx += 1
                
                try:
                    if self.pipeline:
                        result = self.pipeline.process_video_frame(frame)
                        annotated = result['annotated_image']
                        detections = result['detections']
                        
                        # Guardar detecciones de este frame para highlight
                        self.detections_per_frame.append(detections)
                        
                        # Acumular informacion de vehiculos unicos
                        self._accumulate_vehicle_info(detections, frame_idx, fps)
                        
                        # Guardar stats de este frame
                        current_stats = self.pipeline.get_video_stats().copy()
                        self.video_stats_history.append(current_stats)
                    else:
                        annotated = frame
                        self.detections_per_frame.append([])
                        self.video_stats_history.append({
                            'inside': 0, 'entries': 0, 'exits': 0, 
                            'last_entry': None, 'last_exit': None
                        })
                    
                    annotated_frames.append(annotated)
                    
                except Exception as e:
                    print(f"[APP-ERROR] Error procesando frame {frame_idx}: {str(e)}")
                    annotated_frames.append(frame.copy())
                    self.detections_per_frame.append([])
                    self.video_stats_history.append({
                        'inside': 0, 'entries': 0, 'exits': 0,
                        'last_entry': None, 'last_exit': None
                    })

                # Actualizar progreso
                if total_frames:
                    progress = frame_idx / total_frames
                    self.progress.set(progress)
                    self.progress_label.configure(text=f"{progress*100:5.1f}%")

                time.sleep(0.001)
            
            cap.release()
            
            print(f"\n[APP-VIDEO] Procesamiento completado - {frame_idx} frames")
            print(f"[APP-VIDEO] Vehiculos unicos: {len(self.video_vehicles_summary)}")
            
            # Guardar frames procesados
            self.processed_frames = annotated_frames
            
            # Habilitar replay
            self.btn_replay.configure(state="normal")
            
            self.progress.set(1)
            self.progress_label.configure(text="100%")
            self.status_label.configure(text="Video procesado. Seleccione vehiculo o Reproduzca.")
            
            # Poblar lista de vehiculos
            self._populate_vehicle_list()

            # Reproducir automaticamente
            print("[APP-VIDEO] Iniciando reproduccion...\n")
            self._play_frames(0, len(annotated_frames) - 1)
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"[APP-ERROR] Error critico:\n{error_msg}")
            self.status_label.configure(text=f"Error: {str(e)}")
    
    def _accumulate_vehicle_info(self, detections, frame_idx, fps):
        """Acumula informacion de vehiculos unicos durante el video."""
        for det in detections:
            track_id = det['id']
            
            if track_id not in self.video_vehicles_summary:
                # Nuevo vehiculo
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
                
                # Actualizar placa si se detecto una mejor
                current_plate = self.video_vehicles_summary[track_id]['plate']
                new_plate = det.get('Numero-Placa', '------')
                
                if current_plate == '------' and new_plate != '------':
                    self.video_vehicles_summary[track_id]['plate'] = new_plate
    
    def _frames_to_time(self, frame, fps):
        """Convierte numero de frame a formato MM:SS."""
        if fps <= 0:
            fps = 30.0
        seconds = frame / fps
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _populate_vehicle_list(self):
        """Puebla la lista de vehiculos detectados."""
        self._clear_vehicle_list()
        
        if not self.video_vehicles_summary:
            return
        
        # Actualizar titulo
        count = len(self.video_vehicles_summary)
        self.list_title.configure(text=f"VEHICULOS DETECTADOS ({count})")
        
        # Ordenar por ID
        sorted_vehicles = sorted(self.video_vehicles_summary.items(), key=lambda x: x[0])
        
        for track_id, vehicle in sorted_vehicles:
            # Calcular tiempo
            fps = vehicle.get('fps', 30.0)
            time_start = self._frames_to_time(vehicle['first_frame'], fps)
            time_end = self._frames_to_time(vehicle['last_frame'], fps)
            
            vehicle_data = {
                **vehicle,
                'time_range': f"{time_start}-{time_end}"
            }
            
            # Crear fila
            row = VehicleListRow(
                self.vehicle_list_frame,
                vehicle_data,
                self._on_vehicle_click,
                is_selected=(track_id == self.selected_vehicle_id)
            )
            row.pack(fill="x", pady=2, padx=2)
            
            self.vehicle_rows[track_id] = row
    
    def _clear_vehicle_list(self):
        """Limpia la lista de vehiculos."""
        for widget in self.vehicle_list_frame.winfo_children():
            widget.destroy()
        
        self.vehicle_rows = {}
        self.list_title.configure(text="VEHICULOS DETECTADOS")
        self._update_detail_panel(None)
    
    def _on_vehicle_click(self, vehicle_data):
        """Maneja click en un vehiculo de la lista."""
        track_id = vehicle_data['id']
        
        print(f"[APP-UI] Click en vehiculo #{track_id}")
        
        # Actualizar seleccion visual
        if self.selected_vehicle_id is not None and self.selected_vehicle_id in self.vehicle_rows:
            self.vehicle_rows[self.selected_vehicle_id].set_selected(False)
        
        self.selected_vehicle_id = track_id
        
        if track_id in self.vehicle_rows:
            self.vehicle_rows[track_id].set_selected(True)
        
        # Actualizar panel de detalle
        self._update_detail_panel(vehicle_data)
        
        # Reproducir segmento del vehiculo
        if self.processed_frames:
            first_frame = vehicle_data.get('first_frame', 1) - 1  # Ajustar a indice 0
            last_frame = vehicle_data.get('last_frame', len(self.processed_frames)) - 1
            
            # Asegurar limites validos
            first_frame = max(0, first_frame)
            last_frame = min(len(self.processed_frames) - 1, last_frame)
            
            print(f"[APP-UI] Reproduciendo segmento: frames {first_frame} a {last_frame}")
            self.status_label.configure(text=f"Reproduciendo vehiculo #{track_id}")
            
            self._play_frames(first_frame, last_frame, highlight_id=track_id)
    
    def _play_frames(self, start_frame, end_frame, highlight_id=None):
        """
        Reproduce un rango de frames con highlight opcional.
        
        Args:
            start_frame: Indice del primer frame
            end_frame: Indice del ultimo frame
            highlight_id: ID del vehiculo a resaltar en amarillo
        """
        if not self.processed_frames:
            return
        
        # Detener reproduccion anterior si existe
        self.playback_stop_requested = True
        time.sleep(0.05)  # Dar tiempo a que se detenga
        
        self.playback_active = True
        self.playback_stop_requested = False
        self.btn_stop.configure(state="normal")
        
        delay_ms = int(1000 / self.video_fps) if self.video_fps > 0 else 33
        
        def show_frame(i):
            if self.playback_stop_requested or i > end_frame:
                self.playback_active = False
                self.btn_stop.configure(state="disabled")
                if not self.playback_stop_requested:
                    self.status_label.configure(text="Reproduccion finalizada")
                return
            
            try:
                frame = self.processed_frames[i].copy()
                
                # Aplicar highlight si se especifico
                if highlight_id is not None:
                    frame = self._apply_highlight(frame, i, highlight_id)
                
                self._display_image(frame)
                
                # Actualizar stats
                if i < len(self.video_stats_history):
                    self._update_stats_from_dict(self.video_stats_history[i])
                
            except Exception as e:
                print(f"[APP-WARNING] Error en frame {i}: {str(e)}")
            
            self.root.after(delay_ms, lambda: show_frame(i + 1))
        
        show_frame(start_frame)
    
    def _apply_highlight(self, frame, frame_idx, highlight_id):
        """
        Aplica highlight amarillo al bbox del vehiculo seleccionado.
        
        Args:
            frame: Frame a modificar
            frame_idx: Indice del frame actual (0-indexed)
            highlight_id: ID del vehiculo a resaltar
            
        Returns:
            Frame con highlight aplicado
        """
        output = frame.copy()
        
        # Buscar detecciones de este frame
        if frame_idx >= len(self.detections_per_frame):
            return output
        
        detections = self.detections_per_frame[frame_idx]
        
        # Buscar el vehiculo por ID
        target_detection = None
        for det in detections:
            if det.get('id') == highlight_id:
                target_detection = det
                break
        
        if not target_detection:
            # Vehiculo no visible en este frame, mostrar indicador
            cv2.putText(output, f"Vehiculo #{highlight_id} (fuera de cuadro)", 
                       (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            return output
        
        # Obtener bbox
        bbox = target_detection.get('bbox')
        if not bbox or len(bbox) != 4:
            return output
        
        x1, y1, x2, y2 = [int(c) for c in bbox]
        
        # Dibujar bbox amarillo grueso (encima del verde existente)
        cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 255), 4)
        
        # Etiqueta amarilla
        label = f"#{highlight_id}"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        
        # Fondo para el texto
        cv2.rectangle(output, 
                     (x1, y1 - label_size[1] - 10),
                     (x1 + label_size[0] + 10, y1),
                     (0, 255, 255), -1)
        
        # Texto negro sobre fondo amarillo
        cv2.putText(output, label, (x1 + 5, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        return output
    
    def _stop_playback(self):
        """Detiene la reproduccion actual."""
        print("[APP-UI] Deteniendo reproduccion")
        self.playback_stop_requested = True
        self.status_label.configure(text="Reproduccion detenida")
    
    def _replay_video(self):
        """Reproduce todo el video desde el inicio."""
        if not self.processed_frames:
            messagebox.showinfo("Info", "No hay video procesado")
            return
        
        print(f"\n[APP-REPLAY] Reproduciendo video completo ({len(self.processed_frames)} frames)")
        
        # Deseleccionar vehiculo
        if self.selected_vehicle_id is not None and self.selected_vehicle_id in self.vehicle_rows:
            self.vehicle_rows[self.selected_vehicle_id].set_selected(False)
        self.selected_vehicle_id = None
        self._update_detail_panel(None)
        
        self.status_label.configure(text="Reproduciendo video completo...")
        self._play_frames(0, len(self.processed_frames) - 1)
    
    def _toggle_camera(self):
        """Activa o desactiva la camara."""
        if not self.camera_active:
            print("\n[APP-CAMERA] Activando camara...")
            
            self.current_mode = 'camera'
            self._update_stats_mode_label()
            
            if self.pipeline:
                self.pipeline.reset()
                self.pipeline.mode = 'camera'
                self.pipeline.redetection_interval = getattr(config, 'REDETECTION_INTERVAL_CAMERA', 30)
            
            self.camera_active = True
            self.btn_camera.configure(text="Detener Camara", fg_color="red")
            self._clear_vehicle_list()
            
            threading.Thread(target=self._camera_loop, daemon=True).start()
        else:
            print("[APP-CAMERA] Deteniendo camara...")
            self.camera_active = False
            self.btn_camera.configure(text="Activar Camara", fg_color="#1f6aa5")
            if self.video_capture:
                self.video_capture.release()
    
    def _camera_loop(self):
        """Loop principal de captura de camara."""
        try:
            self.video_capture = cv2.VideoCapture(0)
            
            if not self.video_capture.isOpened():
                print("[APP-ERROR] No se pudo abrir la camara")
                self.status_label.configure(text="No se pudo abrir la camara")
                self.camera_active = False
                return
            
            print("[APP-CAMERA] Camara abierta\n")
            
            while self.camera_active:
                ret, frame = self.video_capture.read()
                if not ret:
                    break
                
                try:
                    if self.pipeline:
                        result = self.pipeline.process_video_frame(frame)
                        self._display_image(result['annotated_image'])
                        
                        self.frame_counter += 1
                        if self.frame_counter >= self.stats_update_interval:
                            self._update_stats()
                            self.frame_counter = 0
                    else:
                        self._display_image(frame)
                except Exception as e:
                    print(f"[APP-ERROR] Error en frame: {str(e)}")
                
                time.sleep(0.03)
            
            self.video_capture.release()
            print("[APP-CAMERA] Camara detenida\n")
            self.status_label.configure(text="Camara detenida")
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"[APP-ERROR] Error en camara:\n{error_msg}")
            self.camera_active = False
    
    def _process_current(self):
        """Procesa la imagen actual cargada."""
        if self.current_image is None:
            messagebox.showinfo("Info", "Cargue una imagen primero")
            return
        
        if not self.pipeline:
            messagebox.showinfo("Info", "Modelos aun cargando...")
            return
        
        print("\n[APP-PROCESS] Procesando imagen...")
        threading.Thread(target=self._process_image_thread, daemon=True).start()
    
    def _process_image_thread(self):
        """Procesa la imagen en un thread separado."""
        try:
            self.status_label.configure(text="Procesando...")
            
            result = self.pipeline.process_image(self.current_image)
            
            self._display_image(result['annotated_image'])
            
            num_detections = len(result['detections'])
            print(f"[APP-PROCESS] {num_detections} vehiculos detectados\n")
            
            self.status_label.configure(
                text=f"Procesado: {num_detections} vehiculos"
            )
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"[APP-ERROR] Error:\n{error_msg}")
            self.status_label.configure(text=f"Error: {str(e)}")
    
    def _display_image(self, image):
        """Muestra una imagen en el canvas."""
        try:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 800
                canvas_height = 600
            
            h, w = image_rgb.shape[:2]
            
            scale = min(canvas_width/w, canvas_height/h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            image_resized = cv2.resize(image_rgb, (new_w, new_h))
            
            pil_image = Image.fromarray(image_resized)
            self.photo_image = ImageTk.PhotoImage(pil_image)
            
            self.canvas.delete("all")
            
            x = (canvas_width - new_w) // 2
            y = (canvas_height - new_h) // 2
            
            self.canvas.create_image(x, y, anchor="nw", image=self.photo_image)
            
        except Exception as e:
            print(f"[APP-WARNING] Error mostrando imagen: {str(e)}")
    
    def _update_stats_mode_label(self):
        """Actualiza el label que indica el modo."""
        if self.current_mode == 'video':
            self.stats_mode_label.configure(text="(Video - Temporal)")
        elif self.current_mode == 'camera':
            self.stats_mode_label.configure(text="(Camara - BD)")
        else:
            self.stats_mode_label.configure(text="")
    
    def _clear_stats(self):
        """Limpia las estadisticas."""
        self.stats_labels['inside'].configure(text="DENTRO: 0")
        self.stats_labels['entries'].configure(text="ENTRADAS: 0")
        self.stats_labels['exits'].configure(text="SALIDAS: 0")
    
    def _update_stats_from_dict(self, stats):
        """Actualiza stats desde un diccionario."""
        try:
            self.stats_labels['inside'].configure(text=f"DENTRO: {stats.get('inside', 0)}")
            self.stats_labels['entries'].configure(text=f"ENTRADAS: {stats.get('entries', 0)}")
            self.stats_labels['exits'].configure(text=f"SALIDAS: {stats.get('exits', 0)}")
        except Exception as e:
            print(f"[APP-WARNING] Error actualizando stats: {str(e)}")
    
    def _update_stats(self):
        """Actualiza estadisticas segun el modo."""
        try:
            if not self.pipeline:
                self._clear_stats()
                return
            
            if self.current_mode == 'video':
                stats = self.pipeline.get_video_stats()
                self._update_stats_from_dict(stats)
            
            elif self.current_mode == 'camera':
                if self.pipeline.enable_database and self.pipeline.db:
                    stats = self.pipeline.db.get_today_stats()
                    self.stats_labels['inside'].configure(text=f"DENTRO: {stats['inside']}")
                    self.stats_labels['entries'].configure(text=f"ENTRADAS: {stats['entries_today']}")
                    self.stats_labels['exits'].configure(text=f"SALIDAS: {stats['exits_today']}")
            else:
                self._clear_stats()
                
        except Exception as e:
            print(f"[APP-WARNING] Error actualizando stats: {str(e)}")
    
    def run(self):
        """Inicia la aplicacion."""
        print("\n[APP-RUN] Iniciando loop principal\n")
        self.root.mainloop()


def main():
    app = VehicleDetectorApp()
    app.run()


if __name__ == "__main__":
    main()