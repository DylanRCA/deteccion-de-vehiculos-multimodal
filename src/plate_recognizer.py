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
            plate_detector_path (str): Ruta al modelo YOLO de detección de placas
        """
        # Cargar modelo YOLO de detección de placas
        if plate_detector_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            plate_detector_path = os.path.join(project_root, 'models', 'plate_detector.pt')
        
        if os.path.exists(plate_detector_path):
            print(f"[DEBUG] Cargando modelo YOLO de placas: {plate_detector_path}")
            self.plate_detector = YOLO(plate_detector_path)
            print("[DEBUG] Modelo YOLO de placas cargado")
        else:
            print("[DEBUG] Modelo YOLO de placas no encontrado, usando heurística")
            self.plate_detector = None
        
        # Inicializar EasyOCR
        print("[DEBUG] Inicializando EasyOCR (puede tardar en primera ejecución)...")
        self.reader = easyocr.Reader(['es', 'en'], gpu=False)
        print("[DEBUG] EasyOCR inicializado correctamente")
        
        # Configuración de validación
        self.min_confidence = 0.4  # Confianza mínima del OCR
        self.min_plate_length = 5  # Longitud mínima de caracteres
        self.max_plate_length = 10  # Longitud máxima de caracteres
    
    def detect_plate_region_yolo_with_bbox(self, vehicle_image):
        """
        Detecta la región de la placa usando YOLO y retorna bbox.
        
        Args:
            vehicle_image: Imagen del vehículo (numpy array BGR)
            
        Returns:
            tuple: (plate_image, bbox) donde bbox es [x1, y1, x2, y2] o None
        """
        if self.plate_detector is None:
            return None, None
        
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
            
            # Umbral de confianza más estricto
            if best_box is not None and best_conf > 0.35:
                x1, y1, x2, y2 = best_box.xyxy[0].cpu().numpy().astype(int)
                
                # Asegurar que las coordenadas están dentro de la imagen
                h, w = vehicle_image.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                # Validar dimensiones mínimas
                plate_w = x2 - x1
                plate_h = y2 - y1
                
                if plate_w < 40 or plate_h < 15:
                    print(f"[DEBUG] Placa YOLO muy pequeña: {plate_w}x{plate_h}")
                    return None, None
                
                # Validar aspect ratio
                aspect_ratio = plate_w / float(plate_h)
                if not (1.8 <= aspect_ratio <= 5.0):
                    print(f"[DEBUG] Aspect ratio inválido: {aspect_ratio:.2f}")
                    return None, None
                
                # Recortar placa
                plate_image = vehicle_image[y1:y2, x1:x2]
                bbox = [x1, y1, x2, y2]
                print(f"[DEBUG] Placa detectada con YOLO (conf: {best_conf:.2f})")
                return plate_image, bbox
        
        return None, None
    
    def detect_plate_region_heuristic_with_bbox(self, vehicle_image):
        """
        Intenta localizar la región de la placa usando heurísticas.
        Retorna la imagen y las coordenadas.
        
        Args:
            vehicle_image: Imagen del vehículo recortada (numpy array BGR)
            
        Returns:
            tuple: (plate_image, bbox) donde bbox es [x1, y1, x2, y2] o None
        """
        # Convertir a escala de grises
        gray = cv2.cvtColor(vehicle_image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar filtro bilateral para reducir ruido manteniendo bordes
        bilateral = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Detectar bordes
        edged = cv2.Canny(bilateral, 30, 200)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:15]
        
        plate_candidates = []
        
        # Buscar contornos rectangulares que cumplan criterios de placa
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * perimeter, True)
            
            # Las placas suelen ser rectangulares (4 vértices)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)
                area = cv2.contourArea(contour)
                
                # Validaciones más estrictas
                # 1. Aspect ratio típico de placas
                if not (2.0 <= aspect_ratio <= 4.5):
                    continue
                
                # 2. Tamaño mínimo
                if w < 50 or h < 15:
                    continue
                
                # 3. Área mínima
                if area < 750:
                    continue
                
                # 4. Posición: placas generalmente están en la mitad inferior
                img_height = vehicle_image.shape[0]
                if y < img_height * 0.3:
                    continue
                
                plate_candidates.append({
                    'contour': approx,
                    'bbox': (x, y, w, h),
                    'aspect_ratio': aspect_ratio,
                    'area': area
                })
        
        # Si hay candidatos, tomar el que mejor cumpla criterios
        if plate_candidates:
            # Ordenar por área (placas suelen ser prominentes)
            plate_candidates.sort(key=lambda x: x['area'], reverse=True)
            best = plate_candidates[0]
            
            x, y, w, h = best['bbox']
            plate_image = vehicle_image[y:y+h, x:x+w]
            bbox = [x, y, x+w, y+h]
            print(f"[DEBUG] Placa detectada con heurística (aspect: {best['aspect_ratio']:.2f}, area: {best['area']:.0f})")
            return plate_image, bbox
        
        print("[DEBUG] No se encontró región válida de placa")
        return None, None
    
    def validate_plate_text(self, text, confidence):
        """
        Valida si el texto reconocido es una placa válida.
        
        Args:
            text (str): Texto reconocido
            confidence (float): Confianza del OCR
            
        Returns:
            bool: True si es válido, False si no
        """
        # Limpiar texto
        text = text.strip()
        
        # Validación 1: Longitud
        if len(text) < self.min_plate_length or len(text) > self.max_plate_length:
            return False
        
        # Validación 2: Confianza mínima
        if confidence < self.min_confidence:
            return False
        
        # Validación 3: Debe contener al menos algunos números
        digit_count = sum(c.isdigit() for c in text)
        if digit_count < 2:
            return False
        
        # Validación 4: Debe contener al menos algunas letras
        letter_count = sum(c.isalpha() for c in text)
        if letter_count < 2:
            return False
        
        # Validación 5: No debe tener muchos espacios o caracteres especiales
        alnum_count = sum(c.isalnum() for c in text)
        if alnum_count < len(text) * 0.7:
            return False
        
        return True
    
    def recognize_plate(self, vehicle_image):
        """
        Reconoce el texto de la placa en la imagen del vehículo.
        
        Args:
            vehicle_image: Imagen del vehículo recortada (numpy array BGR)
            
        Returns:
            dict: {
                'text': str,  # Texto de la placa
                'bbox': [x1, y1, x2, y2] or None  # Coordenadas relativas a vehicle_image
            }
        """
        # Intentar detectar placa con YOLO primero
        plate_image = None
        plate_bbox = None
        
        if self.plate_detector is not None:
            plate_image, plate_bbox = self.detect_plate_region_yolo_with_bbox(vehicle_image)
        
        # Si YOLO no funcionó, usar heurística
        if plate_image is None or plate_image.size == 0:
            plate_image, plate_bbox = self.detect_plate_region_heuristic_with_bbox(vehicle_image)
        
        # Si no se detectó ninguna región válida, retornar sin placa
        if plate_image is None or plate_image.size == 0:
            print("[DEBUG] No se detectó región de placa")
            return {'text': "SIN PLACA", 'bbox': None}
        
        # Redimensionar placa si es muy pequeña (mejora OCR)
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
        
        # Intentar múltiples técnicas de binarización
        techniques = []
        
        # Técnica 1: Otsu
        _, otsu = cv2.threshold(plate_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        techniques.append(('otsu', otsu))
        
        # Técnica 2: Threshold adaptativo
        adaptive = cv2.adaptiveThreshold(
            plate_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        techniques.append(('adaptive', adaptive))
        
        # Técnica 3: Threshold adaptativo inverso
        adaptive_inv = cv2.adaptiveThreshold(
            plate_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        techniques.append(('adaptive_inv', adaptive_inv))
        
        # Técnica 4: Imagen mejorada directamente
        techniques.append(('enhanced', plate_enhanced))
        
        # Probar OCR con cada técnica
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
                print(f"[DEBUG] Error en técnica {technique_name}: {str(e)}")
                continue
        
        # Si no hay resultados del OCR
        if not all_results:
            print("[DEBUG] OCR no encontró texto")
            return {'text': "SIN PLACA", 'bbox': plate_bbox}
        
        # Filtrar resultados válidos
        valid_results = [
            r for r in all_results 
            if self.validate_plate_text(r['text'], r['confidence'])
        ]
        
        # Si no hay resultados válidos
        if not valid_results:
            print(f"[DEBUG] Ningún resultado pasó validación. Mejor intento: {all_results[0]['text']} (conf: {all_results[0]['confidence']:.2f})")
            return {'text': "SIN PLACA", 'bbox': plate_bbox}
        
        # Ordenar por confianza y tomar el mejor
        best_result = max(valid_results, key=lambda x: x['confidence'])
        text = best_result['text']
        
        print(f"[DEBUG] Placa reconocida: {text} (conf: {best_result['confidence']:.2f}, técnica: {best_result['technique']})")
        
        return {'text': text, 'bbox': plate_bbox}