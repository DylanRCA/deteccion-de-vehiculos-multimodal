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
        
        print(f"[DEBUG] Buscando modelo YOLO de logos: {model_path}")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Modelo no encontrado: {model_path}\n"
                f"Descarga el modelo desde Google Drive y colocalo en /models/brand_detector.pt"
            )
        
        print(f"[DEBUG] Modelo encontrado. Tamano: {os.path.getsize(model_path) / (1024*1024):.2f} MB")
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
        
        # Paleta de colores expandida (12 colores comunes en vehiculos)
        # Rangos HSV para metodo fallback (si K-Means falla)
        self.colors = {
            'BLANCO': ([0, 0, 200], [180, 30, 255]),
            'NEGRO': ([0, 0, 0], [180, 255, 50]),
            'GRIS': ([0, 0, 50], [180, 50, 200]),
            'PLATA': ([0, 0, 150], [180, 30, 200]),
            'ROJO': ([0, 100, 100], [10, 255, 255]),
            'ROJO_OSCURO': ([170, 100, 50], [180, 255, 150]),
            'AZUL': ([100, 100, 100], [130, 255, 255]),
            'AZUL_OSCURO': ([100, 100, 50], [130, 255, 150]),
            'VERDE': ([40, 100, 100], [80, 255, 255]),
            'AMARILLO': ([20, 100, 100], [30, 255, 255]),
            'NARANJA': ([10, 100, 100], [20, 255, 255]),
            'CAFE': ([10, 100, 20], [20, 255, 100]),
        }
    
    def _detect_dominant_color(self, vehicle_image):
        """
        Detecta el color dominante usando ROI + K-Means optimizado.
        OPCION 2: Balance entre precision y rendimiento.
        
        Args:
            vehicle_image: Imagen del vehiculo en BGR
            
        Returns:
            str: Nombre del color detectado
        """
        h, w = vehicle_image.shape[:2]
        
        # ROI: zona central (30-70% vertical, 20-80% horizontal)
        # Esto evita neumaticos, ventanas, sombras y elementos no representativos
        roi = vehicle_image[int(h*0.3):int(h*0.7), int(w*0.2):int(w*0.8)]
        
        # Validar ROI
        if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 10:
            print("[DEBUG-COLOR] ROI invalido, usando metodo fallback")
            return self._detect_color_fallback(vehicle_image)
        
        # Downsampling agresivo para rendimiento (60x60)
        roi_small = cv2.resize(roi, (60, 60))
        
        try:
            # K-Means con K=3 (rapido)
            pixels = roi_small.reshape((-1, 3)).astype(np.float32)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(pixels, 3, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
            
            # Cluster dominante (el que tiene mas pixeles)
            unique, counts = np.unique(labels, return_counts=True)
            dominant_cluster = unique[np.argmax(counts)]
            dominant_bgr = centers[dominant_cluster].astype(int)
            
            # Mapear BGR a nombre de color
            color_name = self._bgr_to_color_name(dominant_bgr)
            
            return color_name
            
        except Exception as e:
            print(f"[DEBUG-COLOR] Error en K-Means: {str(e)}, usando fallback")
            return self._detect_color_fallback(vehicle_image)
    
    def _bgr_to_color_name(self, bgr):
        """
        Mapea BGR a nombre de color usando clasificacion mejorada.
        Soporta 12 colores comunes en vehiculos.
        
        Args:
            bgr: Array numpy [B, G, R]
            
        Returns:
            str: Nombre del color
        """
        # Convertir BGR a HSV para clasificacion
        hsv_pixel = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = hsv_pixel
        
        # Clasificacion por brillo y saturacion primero
        if v < 40:
            return 'NEGRO'
        elif s < 20:
            # Colores acromaticos (blanco/gris/plata)
            if v > 200:
                return 'BLANCO'
            elif v > 140:
                return 'PLATA'
            else:
                return 'GRIS'
        
        # Clasificacion por tono (H) para colores saturados
        # Rojo (wrap around en HSV: 0-10 y 170-180)
        if 0 <= h <= 10 or 170 <= h <= 180:
            return 'ROJO' if v > 100 else 'ROJO_OSCURO'
        
        # Naranja/Cafe
        elif 10 < h <= 20:
            return 'NARANJA' if s > 100 else 'CAFE'
        
        # Amarillo
        elif 20 < h <= 35:
            return 'AMARILLO'
        
        # Verde
        elif 35 < h <= 85:
            return 'VERDE'
        
        # Azul
        elif 85 < h <= 135:
            return 'AZUL' if v > 100 else 'AZUL_OSCURO'
        
        # Si no cae en ninguna categoria
        return 'DESCONOCIDO'
    
    def _detect_color_fallback(self, vehicle_image):
        """
        Metodo fallback usando heuristica HSV tradicional.
        Usado si K-Means falla o ROI es invalido.
        
        Args:
            vehicle_image: Imagen del vehiculo en BGR
            
        Returns:
            str: Nombre del color detectado
        """
        # Convertir a HSV
        hsv = cv2.cvtColor(vehicle_image, cv2.COLOR_BGR2HSV)
        
        # Redimensionar para acelerar procesamiento
        hsv_small = cv2.resize(hsv, (100, 100))
        
        color_percentages = {}
        
        for color_name, (lower, upper) in self.colors.items():
            lower_bound = np.array(lower, dtype=np.uint8)
            upper_bound = np.array(upper, dtype=np.uint8)
            
            mask = cv2.inRange(hsv_small, lower_bound, upper_bound)
            
            # Usar porcentaje en lugar de conteo absoluto
            percentage = (cv2.countNonZero(mask) / mask.size) * 100
            color_percentages[color_name] = percentage
        
        # Si ningun color supera 15%, retornar DESCONOCIDO
        if not color_percentages or max(color_percentages.values()) < 15:
            return 'DESCONOCIDO'
        
        dominant_color = max(color_percentages, key=color_percentages.get)
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
        Usa K-Means optimizado con ROI.
        
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
                'brand_bbox': list|None,
                'color': str
            }
        """
        brand_result = self.classify_brand(vehicle_image)
        color = self.classify_color(vehicle_image)
        
        return {
            'brand': brand_result['brand'],
            'brand_bbox': brand_result['brand_bbox'],
            'color': color
        }