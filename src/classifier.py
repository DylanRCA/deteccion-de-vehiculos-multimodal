import cv2
import numpy as np
import os
from ultralytics import YOLO


class VehicleClassifier:
    def __init__(self, model_path=None):
        """
        Inicializa el clasificador de marca y color.
        Usa YOLO para detectar logos de marcas.
        
        Args:
            model_path (str): Ruta al modelo YOLO de deteccion de logos
        """
        # Cargar modelo YOLO de logos
        if model_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(project_root, 'models', 'brand_detector.pt')
        
        if os.path.exists(model_path):
            print(f"[DEBUG] Cargando modelo YOLO de logos: {model_path}")
            self.brand_detector = YOLO(model_path)
            print("[DEBUG] Modelo de logos cargado exitosamente")
            
            # Nombres de marcas (deben coincidir con el orden del modelo)
            self.brand_names = {
                0: 'Audi',
                1: 'BMW',
                2: 'Chevrolet',
                3: 'Ford',
                4: 'Honda',
                5: 'Hyundai',
                6: 'KIA',
                7: 'Mazda',
                8: 'Mercedes',
                9: 'Mitsubishi',
                10: 'Nissan',
                11: 'Suzuki',
                12: 'Toyota',
                13: 'Volkswagen'
            }
        else:
            print("[DEBUG] Modelo de logos no encontrado, usando placeholder")
            self.brand_detector = None
            self.brand_names = {}
        
        # Colores detectables por heuristica HSV
        self.colors = {
            'BLANCO': ([0, 0, 200], [180, 30, 255]),
            'NEGRO': ([0, 0, 0], [180, 255, 50]),
            'GRIS': ([0, 0, 50], [180, 50, 200]),
            'ROJO': ([0, 100, 100], [10, 255, 255]),
            'AZUL': ([100, 100, 100], [130, 255, 255]),
            'VERDE': ([40, 100, 100], [80, 255, 255]),
            'AMARILLO': ([20, 100, 100], [30, 255, 255]),
        }
    
    def _detect_dominant_color(self, vehicle_image):
        """
        Detecta el color dominante usando heuristica HSV.
        
        Args:
            vehicle_image: Imagen del vehiculo en BGR
            
        Returns:
            str: Nombre del color detectado
        """
        # Convertir a HSV para mejor deteccion de color
        hsv = cv2.cvtColor(vehicle_image, cv2.COLOR_BGR2HSV)
        
        # Redimensionar para acelerar procesamiento
        hsv_small = cv2.resize(hsv, (100, 100))
        
        color_counts = {}
        
        for color_name, (lower, upper) in self.colors.items():
            lower_bound = np.array(lower, dtype=np.uint8)
            upper_bound = np.array(upper, dtype=np.uint8)
            
            mask = cv2.inRange(hsv_small, lower_bound, upper_bound)
            count = cv2.countNonZero(mask)
            color_counts[color_name] = count
        
        if not color_counts or max(color_counts.values()) < 100:
            return 'DESCONOCIDO'
        
        dominant_color = max(color_counts, key=color_counts.get)
        return dominant_color
    
    def classify_brand(self, vehicle_image):
        """
        Detecta la marca del vehiculo usando YOLO.
        Retorna la marca y el bbox del logo detectado.
        
        Args:
            vehicle_image: Imagen del vehiculo recortada (numpy array BGR)
            
        Returns:
            dict: {
                'brand': str,           # Nombre de la marca
                'brand_bbox': list|None # [x1, y1, x2, y2] o None
            }
        """
        if self.brand_detector is None:
            return {
                'brand': "DESCONOCIDA",
                'brand_bbox': None
            }
        
        try:
            # Detectar logos con YOLO
            results = self.brand_detector(vehicle_image, verbose=False)
            
            # Buscar el logo con mayor confianza
            best_detection = None
            best_conf = 0.0
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    conf = float(box.conf[0])
                    if conf > best_conf:
                        best_conf = conf
                        best_detection = box
            
            # Si hay deteccion con confianza razonable
            if best_detection is not None and best_conf > 0.3:
                class_id = int(best_detection.cls[0])
                
                if class_id in self.brand_names:
                    brand = self.brand_names[class_id]
                    
                    # Extraer bbox
                    x1, y1, x2, y2 = best_detection.xyxy[0].cpu().numpy().astype(int)
                    
                    # Asegurar que las coordenadas esten dentro de la imagen
                    h, w = vehicle_image.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    
                    bbox = [x1, y1, x2, y2]
                    
                    print(f"[DEBUG] Logo detectado: {brand} (confianza: {best_conf:.2f})")
                    return {
                        'brand': brand,
                        'brand_bbox': bbox
                    }
            
            return {
                'brand': "DESCONOCIDA",
                'brand_bbox': None
            }
            
        except Exception as e:
            print(f"[ERROR] Error al detectar logo: {str(e)}")
            return {
                'brand': "DESCONOCIDA",
                'brand_bbox': None
            }
    
    def classify_color(self, vehicle_image):
        """
        Clasifica el color del vehiculo.
        Usa heuristica HSV basica.
        
        Args:
            vehicle_image: Imagen del vehiculo recortada (numpy array BGR)
            
        Returns:
            str: Color del vehiculo
        """
        return self._detect_dominant_color(vehicle_image)
    
    def classify(self, vehicle_image):
        """
        Clasifica marca y color del vehiculo.
        
        Args:
            vehicle_image: Imagen del vehiculo recortada (numpy array BGR)
            
        Returns:
            dict: {
                'brand': str, 
                'brand_bbox': list|None,  # NUEVO: bbox del logo
                'color': str
            }
        """
        brand_result = self.classify_brand(vehicle_image)
        color = self.classify_color(vehicle_image)
        
        return {
            'brand': brand_result['brand'],
            'brand_bbox': brand_result['brand_bbox'],  # NUEVO
            'color': color
        }