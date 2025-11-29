import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
from PIL import Image
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
        control_frame = ctk.CTkFrame(main_frame, width=250)
        control_frame.pack(side="left", fill="y", padx=(0, 10))
        control_frame.pack_propagate(False)
        
        # Titulo
        title_label = ctk.CTkLabel(
            control_frame,
            text="Detector de Vehiculos",
            font=("Arial", 20, "bold")
        )
        title_label.pack(pady=20)
        
        # Botones de control
        self.btn_image = ctk.CTkButton(
            control_frame,
            text="Subir Imagen",
            command=self._load_image,
            height=40
        )
        self.btn_image.pack(pady=10, padx=20, fill="x")
        
        self.btn_video = ctk.CTkButton(
            control_frame,
            text="Subir Video",
            command=self._load_video,
            height=40
        )
        self.btn_video.pack(pady=10, padx=20, fill="x")
        
        self.btn_camera = ctk.CTkButton(
            control_frame,
            text="Activar Camara",
            command=self._toggle_camera,
            height=40
        )
        self.btn_camera.pack(pady=10, padx=20, fill="x")
        
        self.btn_process = ctk.CTkButton(
            control_frame,
            text="Procesar",
            command=self._process_current,
            height=40,
            fg_color="green"
        )
        self.btn_process.pack(pady=10, padx=20, fill="x")
        
        # Boton para reproducir video procesado nuevamente
        self.btn_replay = ctk.CTkButton(
            control_frame,
            text="Reproducir Video",
            command=self._replay_video,
            height=40,
            fg_color="#FF9800",
            state="disabled"
        )
        self.btn_replay.pack(pady=10, padx=20, fill="x")
        
        # Separador
        separator = ctk.CTkFrame(control_frame, height=2)
        separator.pack(pady=20, padx=20, fill="x")
        
        # Area de informacion de detecciones
        info_label = ctk.CTkLabel(
            control_frame,
            text="Informacion de Detecciones",
            font=("Arial", 14, "bold")
        )
        info_label.pack(pady=10)
        
        self.info_text = ctk.CTkTextbox(
            control_frame,
            width=230,
            height=250
        )
        self.info_text.pack(pady=10, padx=20)

        # Barra de progreso para procesamiento de video
        self.progress = ctk.CTkProgressBar(control_frame, width=200)
        self.progress.set(0)
        self.progress.pack(pady=5, padx=20)
        self.progress_label = ctk.CTkLabel(control_frame, text="")
        self.progress_label.pack(pady=(0, 10))
        
        # Estado
        self.status_label = ctk.CTkLabel(
            control_frame,
            text="Inicializando...",
            font=("Arial", 10)
        )
        self.status_label.pack(side="bottom", pady=10)
        
        # === COLUMNA CENTRO: Visualizacion ===
        display_frame = ctk.CTkFrame(main_frame)
        display_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Canvas para mostrar imagen/video
        self.canvas = ctk.CTkLabel(
            display_frame,
            text="Cargue una imagen, video o active la camara",
            font=("Arial", 16)
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === COLUMNA DERECHA: Estadisticas ===
        stats_frame = ctk.CTkFrame(main_frame, width=200)
        stats_frame.pack(side="right", fill="y")
        stats_frame.pack_propagate(False)
        
        # Titulo con indicador de modo
        self.stats_title = ctk.CTkLabel(
            stats_frame,
            text="ESTADISTICAS",
            font=("Arial", 18, "bold")
        )
        self.stats_title.pack(pady=20)
        
        # Indicador de modo
        self.stats_mode_label = ctk.CTkLabel(
            stats_frame,
            text="",
            font=("Arial", 10),
            text_color="gray"
        )
        self.stats_mode_label.pack(pady=(0, 10))
        
        # Separador
        ctk.CTkFrame(stats_frame, height=2, fg_color="gray").pack(fill="x", padx=20, pady=10)
        
        # Stats labels
        self.stats_labels = {}
        
        # DENTRO
        self.stats_labels['inside'] = ctk.CTkLabel(
            stats_frame,
            text="DENTRO: 0",
            font=("Arial", 16, "bold"),
            text_color="#4CAF50"
        )
        self.stats_labels['inside'].pack(pady=10, padx=20, anchor="w")
        
        # ENTRADAS
        self.stats_labels['entries'] = ctk.CTkLabel(
            stats_frame,
            text="ENTRADAS: 0",
            font=("Arial", 14)
        )
        self.stats_labels['entries'].pack(pady=5, padx=20, anchor="w")
        
        # SALIDAS
        self.stats_labels['exits'] = ctk.CTkLabel(
            stats_frame,
            text="SALIDAS: 0",
            font=("Arial", 14)
        )
        self.stats_labels['exits'].pack(pady=5, padx=20, anchor="w")
        
        # Separador
        ctk.CTkFrame(stats_frame, height=2, fg_color="gray").pack(fill="x", padx=20, pady=15)
        
        # ULTIMA ENTRADA
        ctk.CTkLabel(
            stats_frame,
            text="ULTIMA ENTRADA:",
            font=("Arial", 12, "bold")
        ).pack(pady=(10, 5), padx=20, anchor="w")
        
        self.stats_labels['last_entry_plate'] = ctk.CTkLabel(
            stats_frame,
            text="---",
            font=("Arial", 11)
        )
        self.stats_labels['last_entry_plate'].pack(pady=2, padx=20, anchor="w")
        
        self.stats_labels['last_entry_time'] = ctk.CTkLabel(
            stats_frame,
            text="",
            font=("Arial", 10),
            text_color="gray"
        )
        self.stats_labels['last_entry_time'].pack(pady=2, padx=20, anchor="w")
        
        # ULTIMA SALIDA
        ctk.CTkLabel(
            stats_frame,
            text="ULTIMA SALIDA:",
            font=("Arial", 12, "bold")
        ).pack(pady=(10, 5), padx=20, anchor="w")
        
        self.stats_labels['last_exit_plate'] = ctk.CTkLabel(
            stats_frame,
            text="---",
            font=("Arial", 11)
        )
        self.stats_labels['last_exit_plate'].pack(pady=2, padx=20, anchor="w")
        
        self.stats_labels['last_exit_time'] = ctk.CTkLabel(
            stats_frame,
            text="",
            font=("Arial", 10),
            text_color="gray"
        )
        self.stats_labels['last_exit_time'].pack(pady=2, padx=20, anchor="w")
        
        # Separador
        ctk.CTkFrame(stats_frame, height=2, fg_color="gray").pack(fill="x", padx=20, pady=15)
        
        # DURACION PROMEDIO (solo en modo camara/BD)
        ctk.CTkLabel(
            stats_frame,
            text="DURACION PROM:",
            font=("Arial", 12, "bold")
        ).pack(pady=(10, 5), padx=20, anchor="w")
        
        self.stats_labels['avg_duration'] = ctk.CTkLabel(
            stats_frame,
            text="---",
            font=("Arial", 14)
        )
        self.stats_labels['avg_duration'].pack(pady=2, padx=20, anchor="w")
        
        # Boton de refrescar stats manualmente
        self.btn_refresh_stats = ctk.CTkButton(
            stats_frame,
            text="Actualizar",
            command=self._update_stats,
            height=30,
            width=160
        )
        self.btn_refresh_stats.pack(pady=20, padx=20)
        
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
                self._display_image(self.current_image)
                self.info_text.delete("1.0", "end")
                self.info_text.insert("1.0", "Imagen cargada. Presione 'Procesar'.")
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
            self.btn_replay.configure(state="disabled")
            
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
            self.video_stats_history = []  # Reset historial de stats
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

                # Actualizar info cada 5 frames
                if frame_idx % 5 == 0 and self.pipeline:
                    try:
                        self._update_info_text(detections)
                    except Exception as e:
                        print(f"[APP-WARNING] Error actualizando UI: {str(e)}")

                # Pausa minima
                time.sleep(0.001)
            
            cap.release()
            
            print(f"\n[APP-VIDEO] Procesamiento completado - {frame_idx} frames procesados")
            print(f"[APP-VIDEO] Stats history: {len(self.video_stats_history)} registros")
            
            # Guardar frames procesados para replay
            self.processed_frames = annotated_frames
            self.video_fps = fps
            
            # Habilitar boton de replay
            self.btn_replay.configure(state="normal")
            
            self.progress.set(1)
            self.progress_label.configure(text="100%")
            self.status_label.configure(text="Video procesado, reproduciendo...")

            print("[APP-VIDEO] Iniciando reproduccion con stats en tiempo real...\n")
            self._play_processed_frames(annotated_frames, fps)
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"[APP-ERROR] Error critico en procesamiento de video:\n{error_msg}")
            self.status_label.configure(text=f"Error en video: {str(e)}")
    
    def _toggle_camera(self):
        """
        Activa o desactiva la camara.
        """
        if not self.camera_active:
            print("\n[APP-CAMERA] Activando camara...")
            
            # Cambiar modo a camara
            self.current_mode = 'camera'
            self._update_stats_mode_label()
            
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
                        self._display_image(result['annotated_image'])
                        self._update_info_text(result['detections'])
                        
                        # Actualizar stats cada 30 frames
                        self.frame_counter += 1
                        if self.frame_counter >= self.stats_update_interval:
                            self._update_stats()
                            self.frame_counter = 0
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
            
            self._display_image(result['annotated_image'])
            self._update_info_text(result['detections'])
            
            num_detections = len(result['detections'])
            print(f"[APP-PROCESS] Procesamiento completado - {num_detections} vehiculos detectados\n")
            
            self.status_label.configure(
                text=f"Procesado: {num_detections} vehiculos detectados"
            )
            
        except Exception as e:
            error_msg = traceback.format_exc()
            print(f"[APP-ERROR] Error en procesamiento:\n{error_msg}")
            self.status_label.configure(text=f"Error: {str(e)}")
    
    def _display_image(self, image):
        """
        Muestra una imagen en el canvas.
        """
        try:
            # Convertir BGR a RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Redimensionar manteniendo aspect ratio
            max_width = 900
            max_height = 700
            h, w = image_rgb.shape[:2]
            
            scale = min(max_width/w, max_height/h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            image_resized = cv2.resize(image_rgb, (new_w, new_h))
            
            # Convertir a formato PIL
            pil_image = Image.fromarray(image_resized)
            
            # Usar CTkImage
            ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, 
                                      size=(new_w, new_h))
            
            # Actualizar canvas
            self.canvas.configure(image=ctk_image, text="")
            self.canvas.image = ctk_image
            
        except Exception as e:
            print(f"[APP-WARNING] Error mostrando imagen: {str(e)}")
    
    def _update_info_text(self, detections):
        """
        Actualiza el area de texto con informacion de detecciones.
        """
        try:
            self.info_text.delete("1.0", "end")
            
            if not detections:
                self.info_text.insert("1.0", "No se detectaron vehiculos")
                return
            
            # Contar vehiculos con placas legibles
            vehicles_with_plates = sum(1 for det in detections if det['Placa'] == 'SI')
            
            info = f"Vehiculos detectados: {len(detections)}\n"
            info += f"Placas legibles: {vehicles_with_plates}\n\n"
            
            for det in detections:
                info += f"{'='*25}\n"
                info += f"VEHICULO #{det['id']}\n"
                info += f"{'='*25}\n"
                info += f"Tipo: {det['class']}\n"
                info += f"Confianza: {det['confidence']:.2f}\n\n"
                
                info += f"Placa: {det['Placa']}\n"
                info += f"Numero-Placa: {det['Numero-Placa']}\n\n"
                
                info += f"Color: {det['color']}\n"
                info += f"Marca: {det['brand']}\n\n"
            
            self.info_text.insert("1.0", info)
            
        except Exception as e:
            print(f"[APP-WARNING] Error actualizando info text: {str(e)}")
    
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
        self.stats_labels['avg_duration'].configure(text="---")
    
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
                    # Calcular "hace X min"
                    now = datetime.now()
                    diff = now - entry_time
                    minutes_ago = int(diff.total_seconds() / 60)
                    
                    if minutes_ago < 1:
                        time_str = "hace menos de 1 min"
                    elif minutes_ago < 60:
                        time_str = f"hace {minutes_ago} min"
                    else:
                        hours = minutes_ago // 60
                        time_str = f"hace {hours}h {minutes_ago % 60}min"
                else:
                    time_str = ""
                
                # Truncar placa si es muy larga
                if len(plate) > 20:
                    plate = plate[:17] + "..."
                
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
                    # Calcular "hace X min"
                    now = datetime.now()
                    diff = now - exit_time
                    minutes_ago = int(diff.total_seconds() / 60)
                    
                    if minutes_ago < 1:
                        time_str = "hace menos de 1 min"
                    elif minutes_ago < 60:
                        time_str = f"hace {minutes_ago} min"
                    else:
                        hours = minutes_ago // 60
                        time_str = f"hace {hours}h {minutes_ago % 60}min"
                else:
                    time_str = ""
                
                # Truncar placa si es muy larga
                if len(plate) > 20:
                    plate = plate[:17] + "..."
                
                self.stats_labels['last_exit_plate'].configure(text=plate)
                self.stats_labels['last_exit_time'].configure(text=time_str)
            else:
                self.stats_labels['last_exit_plate'].configure(text="---")
                self.stats_labels['last_exit_time'].configure(text="")
            
            # Duracion promedio no disponible en modo video
            self.stats_labels['avg_duration'].configure(text="N/A")
            
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
                    
                    # Calcular "hace X min"
                    now = datetime.now()
                    diff = now - entry_time
                    minutes_ago = int(diff.total_seconds() / 60)
                    
                    if minutes_ago < 1:
                        time_str = "hace menos de 1 min"
                    elif minutes_ago < 60:
                        time_str = f"hace {minutes_ago} min"
                    else:
                        hours = minutes_ago // 60
                        time_str = f"hace {hours}h {minutes_ago % 60}min"
                    
                    # Truncar placa si es muy larga
                    if len(plate) > 20:
                        plate = plate[:17] + "..."
                    
                    self.stats_labels['last_entry_plate'].configure(text=plate)
                    self.stats_labels['last_entry_time'].configure(text=time_str)
                else:
                    self.stats_labels['last_entry_plate'].configure(text="---")
                    self.stats_labels['last_entry_time'].configure(text="")
                
                # Ultima salida
                if stats.get('last_exit'):
                    plate = stats['last_exit']['plate']
                    exit_time = datetime.fromisoformat(stats['last_exit']['exit_time'])
                    
                    # Calcular "hace X min"
                    now = datetime.now()
                    diff = now - exit_time
                    minutes_ago = int(diff.total_seconds() / 60)
                    
                    if minutes_ago < 1:
                        time_str = "hace menos de 1 min"
                    elif minutes_ago < 60:
                        time_str = f"hace {minutes_ago} min"
                    else:
                        hours = minutes_ago // 60
                        time_str = f"hace {hours}h {minutes_ago % 60}min"
                    
                    # Truncar placa si es muy larga
                    if len(plate) > 20:
                        plate = plate[:17] + "..."
                    
                    self.stats_labels['last_exit_plate'].configure(text=plate)
                    self.stats_labels['last_exit_time'].configure(text=time_str)
                else:
                    self.stats_labels['last_exit_plate'].configure(text="---")
                    self.stats_labels['last_exit_time'].configure(text="")
                
                # Duracion promedio
                self.stats_labels['avg_duration'].configure(text=f"{stats['avg_duration']} min")
            
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