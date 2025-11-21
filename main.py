import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
from PIL import Image
import threading
import os
import sys
import time

# Agregar src al path para importar modulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.pipeline import VehicleDetectionPipeline


class VehicleDetectorApp:
    def __init__(self):
        """
        Inicializa la aplicacion de deteccion de vehiculos.
        """
        self.root = ctk.CTk()
        self.root.title("Detector de Vehiculos - Peru")
        self.root.geometry("1200x800")
        
        # Configurar tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Inicializar pipeline
        self.pipeline = None
        self.current_image = None
        self.camera_active = False
        self.video_capture = None
        
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
            print("[DEBUG] Iniciando carga del pipeline...")
            self.pipeline = VehicleDetectionPipeline()
            print("[DEBUG] Pipeline cargado exitosamente")
            self.status_label.configure(text="✓ Modelos cargados. Listo para usar.")
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            print(f"[ERROR] Error completo al cargar modelos:\n{error_msg}")
            self.status_label.configure(text=f"✗ Error: Ver consola para detalles")
            messagebox.showerror("Error de Carga", 
                               f"Error al cargar modelos:\n{str(e)}\n\nRevisa la consola para mas detalles.")
    
    def _create_widgets(self):
        """
        Crea los widgets de la interfaz grafica.
        """
        # Frame principal
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame izquierdo: controles
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
            height=300
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
        
        # Frame derecho: visualizacion
        display_frame = ctk.CTkFrame(main_frame)
        display_frame.pack(side="right", fill="both", expand=True)
        
        # Canvas para mostrar imagen/video
        self.canvas = ctk.CTkLabel(
            display_frame,
            text="Cargue una imagen, video o active la camara",
            font=("Arial", 16)
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _load_image(self):
        """
        Carga una imagen desde el sistema de archivos.
        """
        file_path = filedialog.askopenfilename(
            title="Seleccionar Imagen",
            filetypes=[
                ("Imagenes", "*.jpg *.jpeg *.png *.bmp"),
                ("Todos", "*.*")
            ]
        )
        
        if file_path:
            try:
                self.current_image = cv2.imread(file_path)
                if self.current_image is None:
                    messagebox.showerror("Error", "No se pudo cargar la imagen")
                    return
                
                self._display_image(self.current_image)
                self.info_text.delete("1.0", "end")
                self.info_text.insert("1.0", "Imagen cargada. Presione 'Procesar'.")
                self.status_label.configure(text="Imagen cargada")
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar imagen: {str(e)}")
    
    def _load_video(self):
        """
        Carga y procesa un video desde el sistema de archivos.
        """
        file_path = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[
                ("Videos", "*.mp4 *.avi *.mov *.mkv"),
                ("Todos", "*.*")
            ]
        )
        
        if file_path:
            threading.Thread(
                target=self._process_video,
                args=(file_path,),
                daemon=True
            ).start()
    
    def _process_video(self, video_path):
        """
        Procesa un video frame por frame.
        """
        try:
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                self.status_label.configure(text="Error al abrir video")
                return
            
            self.status_label.configure(text="Procesando video...")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or None
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            annotated_frames = []
            frame_idx = 0
            self.progress.set(0)
            self.progress_label.configure(text="0%")

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                if self.pipeline:
                    result = self.pipeline.process_video_frame(frame)
                    annotated = result['annotated_image']
                    detections = result['detections']
                else:
                    annotated = frame
                    detections = []

                annotated_frames.append(annotated)
                frame_idx += 1

                if total_frames:
                    progress = frame_idx / total_frames
                    self.progress.set(progress)
                    self.progress_label.configure(text=f"{progress*100:5.1f}%")

                # Actualiza info de vez en cuando sin bloquear
                if frame_idx % 5 == 0 and self.pipeline:
                    self._update_info_text(detections)

                # Pausa minima para no saturar CPU (sin HighGUI)
                time.sleep(0.001)
            
            cap.release()
            self.progress.set(1)
            self.progress_label.configure(text="100%")
            self.status_label.configure(text="Video procesado, reproduciendo...")

            self._play_processed_frames(annotated_frames, fps)
            
        except Exception as e:
            self.status_label.configure(text=f"Error en video: {str(e)}")
    
    def _toggle_camera(self):
        """
        Activa o desactiva la camara.
        """
        if not self.camera_active:
            self.camera_active = True
            self.btn_camera.configure(text="Detener Camara", fg_color="red")
            threading.Thread(target=self._camera_loop, daemon=True).start()
        else:
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
                self.status_label.configure(text="No se pudo abrir la camara")
                self.camera_active = False
                return
            
            while self.camera_active:
                ret, frame = self.video_capture.read()
                if not ret:
                    break
                
                if self.pipeline:
                    result = self.pipeline.process_video_frame(frame)
                    self._display_image(result['annotated_image'])
                    self._update_info_text(result['detections'])
                else:
                    self._display_image(frame)
                
                time.sleep(0.03)
            
            self.video_capture.release()
            self.status_label.configure(text="Camara detenida")
            
        except Exception as e:
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
            
            self.status_label.configure(
                text=f"Procesado: {len(result['detections'])} vehiculos detectados"
            )
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
    
    def _display_image(self, image):
        """
        Muestra una imagen en el canvas.
        """
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
        
        # Usar CTkImage para evitar warning
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, 
                                  size=(new_w, new_h))
        
        # Actualizar canvas
        self.canvas.configure(image=ctk_image, text="")
        self.canvas.image = ctk_image  # Mantener referencia
    
    def _update_info_text(self, detections):
        """
        Actualiza el area de texto con informacion de detecciones.
        Formato: Placa: SI/NO, Numero-Placa: XXXXX/------
        """
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
            
            # Formato exacto solicitado
            info += f"Placa: {det['Placa']}\n"
            info += f"Numero-Placa: {det['Numero-Placa']}\n\n"
            
            # Caracteristicas del vehiculo
            info += f"Color: {det['color']}\n"
            info += f"Marca: {det['brand']}\n\n"
        
        self.info_text.insert("1.0", info)

    def _play_processed_frames(self, frames, fps):
        """
        Reproduce en la UI la lista de frames procesados respetando el FPS.
        """
        if not frames:
            self.status_label.configure(text="Sin frames para reproducir")
            return

        delay_ms = int(1000 / fps) if fps and fps > 0 else 33

        def show_frame(i):
            if i >= len(frames):
                self.status_label.configure(text="Reproduccion finalizada")
                return
            self._display_image(frames[i])
            self.root.after(delay_ms, lambda: show_frame(i + 1))

        show_frame(0)
    
    def run(self):
        """
        Inicia la aplicacion.
        """
        self.root.mainloop()


def main():
    app = VehicleDetectorApp()
    app.run()


if __name__ == "__main__":
    main()
