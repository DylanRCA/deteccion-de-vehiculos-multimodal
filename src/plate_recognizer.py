import easyocr
import cv2
import numpy as np
import os
from ultralytics import YOLO


class PlateRecognizer:
    def __init__(self, plate_detector_path=None):
        """
        Inicializa el reconocedor de placas.
        Usa YOLO para detectar la placa y EasyOCR para leer el texto.
        
        Args:
            plate_detector_path (str): Ruta al modelo YOLO de deteccion de placas
        """
        # Cargar modelo YOLO de deteccion de placas
        if plate_detector_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            plate_detector_path = os.path.join(project_root, 'models', 'plate_detector.pt')
        
        print(f"[DEBUG] Buscando modelo YOLO de placas: {plate_detector_path}")
        
        if not os.path.exists(plate_detector_path):
            raise FileNotFoundError(
                f"Modelo no encontrado: {plate_detector_path}\n"
                f"Descarga el modelo desde Google Drive y colocalo en /models/plate_detector.pt"
            )
        
        print(f"[DEBUG] Modelo encontrado. Tamano: {os.path.getsize(plate_detector_path) / (1024*1024):.2f} MB")
        print(f"[DEBUG] Cargando modelo YOLO de placas: {plate_detector_path}")
        self.plate_detector = YOLO(plate_detector_path)
        print("[DEBUG] Modelo YOLO de placas cargado")
        
        # Inicializar EasyOCR
        print("[DEBUG] Inicializando EasyOCR (puede tardar en primera ejecucion)...")
        self.reader = easyocr.Reader(['es', 'en'], gpu=False)
        print("[DEBUG] EasyOCR inicializado correctamente")
        
        # Configuracion de validacion (umbrales mas permisivos)
        self.min_confidence = 0.2  # Confianza minima del OCR (reducido)
        self.min_plate_length = 4  # Longitud minima de caracteres (reducido)
        self.max_plate_length = 12  # Longitud maxima de caracteres (aumentado)
    
    def detect_plate_region_yolo_with_bbox(self, vehicle_image):
        """
        Detecta la region de la placa usando YOLO y retorna bbox.
        
        Args:
            vehicle_image: Imagen del vehiculo (numpy array BGR)
            
        Returns:
            tuple: (plate_image, bbox) donde bbox es [x1, y1, x2, y2] o None
        """
        # Detectar placas con YOLO
        results = self.plate_detector(vehicle_image, verbose=False)
        
        for result in results:
            boxes = result.boxes
            if len(boxes) == 0:
                continue
            
            # Tomar la placa con mayor confianza
            best_box = None
            best_conf = 0
            
            for box in boxes:
                conf = float(box.conf[0])
                if conf > best_conf:
                    best_conf = conf
                    best_box = box
            
            # Umbral de confianza mas permisivo
            if best_box is not None and best_conf > 0.25:
                x1, y1, x2, y2 = best_box.xyxy[0].cpu().numpy().astype(int)
                
                # Asegurar que las coordenadas estan dentro de la imagen
                h, w = vehicle_image.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                # Validar dimensiones minimas
                plate_w = x2 - x1
                plate_h = y2 - y1
                
                if plate_w < 40 or plate_h < 15:
                    print(f"[DEBUG] Placa YOLO muy pequena: {plate_w}x{plate_h}")
                    return None, None
                
                # Validar aspect ratio
                aspect_ratio = plate_w / float(plate_h)
                if not (1.8 <= aspect_ratio <= 5.0):
                    print(f"[DEBUG] Aspect ratio invalido: {aspect_ratio:.2f}")
                    return None, None
                
                # Recortar placa
                plate_image = vehicle_image[y1:y2, x1:x2]
                bbox = [x1, y1, x2, y2]
                print(f"[DEBUG] Placa detectada con YOLO (conf: {best_conf:.2f})")
                return plate_image, bbox
        
        return None, None
    
    def validate_plate_text(self, text, confidence):
        """
        Valida si el texto reconocido es una placa valida.
        Validacion permisiva para maximizar deteccion.
        
        Args:
            text (str): Texto reconocido
            confidence (float): Confianza del OCR
            
        Returns:
            bool: True si es valido, False si no
        """
        # Limpiar texto
        text = text.strip()
        
        # Validacion 1: Longitud
        if len(text) < self.min_plate_length or len(text) > self.max_plate_length:
            return False
        
        # Validacion 2: Confianza minima (muy baja para ser permisivo)
        if confidence < self.min_confidence:
            return False
        
        # Validacion 3: Debe contener al menos UN numero O una letra
        has_digit = any(c.isdigit() for c in text)
        has_letter = any(c.isalpha() for c in text)
        
        if not (has_digit or has_letter):
            return False
        
        # Validacion 4: Al menos 50% alfanumerico
        alnum_count = sum(c.isalnum() for c in text)
        if alnum_count < len(text) * 0.5:
            return False
        
        return True
    
    def recognize_plate(self, vehicle_image):
        """
        Reconoce el texto de la placa en la imagen del vehiculo.
        
        Args:
            vehicle_image: Imagen del vehiculo recortada (numpy array BGR)
            
        Returns:
            dict: {
                'text': str,  # Texto de la placa
                'bbox': [x1, y1, x2, y2] or None  # Coordenadas relativas a vehicle_image
            }
        """
        # Detectar placa con YOLO
        plate_image, plate_bbox = self.detect_plate_region_yolo_with_bbox(vehicle_image)
        
        # Si no se detecto ninguna region valida, retornar sin placa
        if plate_image is None or plate_image.size == 0:
            print("[DEBUG] No se detecto region de placa")
            return {'text': "SIN PLACA", 'bbox': None}
        
        # Redimensionar placa si es muy pequena (mejora OCR)
        h, w = plate_image.shape[:2]
        if h < 50 or w < 150:
            scale = max(50/h, 150/w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            plate_image = cv2.resize(plate_image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Convertir a escala de grises
        plate_gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar filtro de nitidez
        kernel_sharpening = np.array([[-1,-1,-1],
                                       [-1, 9,-1],
                                       [-1,-1,-1]])
        plate_sharp = cv2.filter2D(plate_gray, -1, kernel_sharpening)
        
        # Aumentar contraste con CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        plate_enhanced = clahe.apply(plate_sharp)
        
        # Intentar multiples tecnicas de binarizacion
        techniques = []
        
        # Tecnica 1: Otsu
        _, otsu = cv2.threshold(plate_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        techniques.append(('otsu', otsu))
        
        # Tecnica 2: Threshold adaptativo
        adaptive = cv2.adaptiveThreshold(
            plate_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        techniques.append(('adaptive', adaptive))
        
        # Tecnica 3: Threshold adaptativo inverso
        adaptive_inv = cv2.adaptiveThreshold(
            plate_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        techniques.append(('adaptive_inv', adaptive_inv))
        
        # Tecnica 4: Imagen mejorada directamente
        techniques.append(('enhanced', plate_enhanced))
        
        # Probar OCR con cada tecnica
        all_results = []
        
        for technique_name, processed_img in techniques:
            try:
                results = self.reader.readtext(processed_img, detail=1)
                for result in results:
                    bbox_ocr, text, conf = result
                    
                    # Limpiar texto
                    text = ''.join(c for c in text if c.isalnum() or c == ' ')
                    text = text.upper().strip().replace(' ', '')
                    
                    if text:  # Solo agregar si hay texto
                        all_results.append({
                            'text': text,
                            'confidence': conf,
                            'technique': technique_name
                        })
            except Exception as e:
                print(f"[DEBUG] Error en tecnica {technique_name}: {str(e)}")
                continue
        
        # Si no hay resultados del OCR
        if not all_results:
            print("[DEBUG] OCR no encontro texto")
            return {'text': "SIN PLACA", 'bbox': plate_bbox}
        
        # Filtrar resultados validos
        valid_results = [
            r for r in all_results 
            if self.validate_plate_text(r['text'], r['confidence'])
        ]
        
        # Si no hay resultados validos
        if not valid_results:
            print(f"[DEBUG] Ningun resultado paso validacion. Mejor intento: {all_results[0]['text']} (conf: {all_results[0]['confidence']:.2f})")
            return {'text': "SIN PLACA", 'bbox': plate_bbox}
        
        # Ordenar por confianza y tomar el mejor
        best_result = max(valid_results, key=lambda x: x['confidence'])
        text = best_result['text']
        
        print(f"[DEBUG] Placa reconocida: {text} (conf: {best_result['confidence']:.2f}, tecnica: {best_result['technique']})")
        
        return {'text': text, 'bbox': plate_bbox}