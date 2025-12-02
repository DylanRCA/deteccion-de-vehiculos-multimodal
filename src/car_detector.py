import os
from ultralytics import YOLO
import cv2

try:
    import config
except ImportError:
    config = None


class CarDetector:
    def __init__(self, model_path=None, min_confidence=0.4):
        """
        Inicializa el detector de vehiculos usando YOLOv8.
        
        Args:
            model_path (str): Ruta al modelo YOLO. Si es None, usa car_detector.pt de /models
            min_confidence (float): Confianza minima para aceptar detecciones (0.0-1.0)
        """
        if model_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(project_root, 'models', 'car_detector.pt')
        
        print(f"[DEBUG] Buscando modelo YOLO en: {model_path}")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Modelo no encontrado: {model_path}\n"
                f"Descarga el modelo desde Google Drive y colocalo en /models/car_detector.pt"
            )
        
        print(f"[DEBUG] Modelo encontrado. Tamano: {os.path.getsize(model_path) / (1024*1024):.2f} MB")
        print(f"[DEBUG] Cargando modelo YOLO: {model_path}")
        self.model = YOLO(model_path)
        print(f"[DEBUG] Modelo YOLO cargado. Clases: {self.model.names}")
        
        # Configuracion
        self.min_confidence = min_confidence
        print(f"[DEBUG] Confianza minima para deteccion de vehiculos: {self.min_confidence}")
        
        # Clases de vehiculos en COCO dataset
        self.vehicle_classes = [2, 3, 5, 7]  # car, motorcycle, bus, truck
        
        # Filtros de tamano (porcentaje del frame) - desde config o defaults
        self.max_bbox_ratio = getattr(config, 'CAR_MAX_BBOX_RATIO', 0.70)
        self.min_bbox_ratio = getattr(config, 'CAR_MIN_BBOX_RATIO', 0.001)
        print(f"[DEBUG] Filtro de tamano: min={self.min_bbox_ratio:.1%}, max={self.max_bbox_ratio:.0%} del frame")
        
    def detect_vehicles(self, image):
        """
        Detecta vehiculos en una imagen.
        Solo retorna vehiculos con confianza >= min_confidence.
        Filtra detecciones con tamano anormal (muy grandes o muy pequenas).
        
        Args:
            image: Imagen en formato numpy array (BGR)
            
        Returns:
            list: Lista de diccionarios con informacion de cada vehiculo detectado
                  {'bbox': [x1, y1, x2, y2], 'confidence': float, 'class': str}
        """
        results = self.model(image, verbose=False)
        detections = []
        
        # Obtener dimensiones de la imagen para calcular ratios
        img_height, img_width = image.shape[:2]
        img_area = img_height * img_width
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                # Filtrar por confianza minima
                if confidence < self.min_confidence:
                    print(f"[DEBUG] Vehiculo rechazado por baja confianza: {confidence:.2f} < {self.min_confidence}")
                    continue
                
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Calcular area del bbox
                bbox_width = x2 - x1
                bbox_height = y2 - y1
                bbox_area = bbox_width * bbox_height
                
                # Calcular ratio respecto al frame
                bbox_ratio = bbox_area / img_area if img_area > 0 else 0
                
                # Filtrar por tamano maximo (evitar falsos positivos gigantes)
                if bbox_ratio > self.max_bbox_ratio:
                    print(f"[DEBUG] Vehiculo rechazado por tamano excesivo: {bbox_ratio:.1%} del frame (max: {self.max_bbox_ratio:.0%})")
                    continue
                
                # Filtrar por tamano minimo (evitar ruido)
                if bbox_ratio < self.min_bbox_ratio:
                    print(f"[DEBUG] Vehiculo rechazado por tamano muy pequeno: {bbox_ratio:.3%} del frame")
                    continue
                
                # Filtrar por aspect ratio anomalo (muy ancho o muy alto)
                aspect_ratio = bbox_width / bbox_height if bbox_height > 0 else 0
                if aspect_ratio > 6.0 or aspect_ratio < 0.2:
                    print(f"[DEBUG] Vehiculo rechazado por aspect ratio anomalo: {aspect_ratio:.2f}")
                    continue
                
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'confidence': confidence,
                    'class': result.names[class_id]
                })
                
                print(f"[DEBUG] Vehiculo detectado: {result.names[class_id]} con confianza {confidence:.2f} ({bbox_ratio:.1%} del frame)")
        
        return detections
    
    def draw_detections(self, image, detections):
        """
        Dibuja las detecciones en la imagen.
        
        Args:
            image: Imagen en formato numpy array (BGR)
            detections: Lista de detecciones del metodo detect_vehicles
            
        Returns:
            numpy.ndarray: Imagen con las detecciones dibujadas
        """
        output_image = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']
            class_name = det['class']
            
            # Dibujar rectangulo
            cv2.rectangle(output_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Texto con clase y confianza
            label = f"{class_name}: {conf:.2f}"
            cv2.putText(output_image, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return output_image