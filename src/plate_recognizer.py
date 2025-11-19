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
    
    def detect_plate_region_yolo(self, vehicle_image):
        """
        Detecta la región de la placa usando YOLO.
        
        Args:
            vehicle_image: Imagen del vehículo (numpy array BGR)
            
        Returns:
            numpy.ndarray or None: Imagen de la placa recortada, o None si no se encuentra
        """
        if self.plate_detector is None:
            return None
        
        # Detectar placas con YOLO
        results = self.plate_detector(vehicle_image, verbose=False)
        
        for result in results:
            boxes = result.boxes
            if len(boxes) == 0:
                continue
            
            # Tomar la primera placa detectada (o la de mayor confianza)
            best_box = None
            best_conf = 0
            
            for box in boxes:
                conf = float(box.conf[0])
                if conf > best_conf:
                    best_conf = conf
                    best_box = box
            
            if best_box is not None and best_conf > 0.25:  # Umbral de confianza
                x1, y1, x2, y2 = best_box.xyxy[0].cpu().numpy().astype(int)
                
                # Asegurar que las coordenadas están dentro de la imagen
                h, w = vehicle_image.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                # Recortar placa
                plate_image = vehicle_image[y1:y2, x1:x2]
                return plate_image
        
        return None
        
    def detect_plate_region_heuristic(self, vehicle_image):
        """
        Intenta localizar la región de la placa usando heurísticas.
        Fallback si no hay modelo YOLO.
        
        Args:
            vehicle_image: Imagen del vehículo recortada (numpy array BGR)
            
        Returns:
            numpy.ndarray or None: Imagen de la placa recortada, o None si no se encuentra
        """
        # Convertir a escala de grises
        gray = cv2.cvtColor(vehicle_image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar filtro bilateral para reducir ruido manteniendo bordes
        bilateral = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Detectar bordes
        edged = cv2.Canny(bilateral, 30, 200)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        
        plate_contour = None
        
        # Buscar contorno rectangular (placa)
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * perimeter, True)
            
            # Las placas suelen ser rectangulares (4 vértices)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)
                
                # Placas peruanas tienen aspect ratio entre 2:1 y 4:1
                if 2.0 <= aspect_ratio <= 4.5:
                    plate_contour = approx
                    break
        
        if plate_contour is not None:
            x, y, w, h = cv2.boundingRect(plate_contour)
            plate_image = vehicle_image[y:y+h, x:x+w]
            return plate_image
        
        # Si no se encuentra placa por contornos, usar región inferior central
        height, width = vehicle_image.shape[:2]
        plate_region = vehicle_image[int(height*0.6):int(height*0.9), 
                                     int(width*0.2):int(width*0.8)]
        return plate_region
    
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
        
        if plate_image is None or plate_image.size == 0:
            return {'text': "NO DETECTADA", 'bbox': None}
        
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
        techniques.append(otsu)
        
        # Técnica 2: Threshold adaptativo
        adaptive = cv2.adaptiveThreshold(
            plate_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        techniques.append(adaptive)
        
        # Técnica 3: Threshold adaptativo inverso (para placas con fondo oscuro)
        adaptive_inv = cv2.adaptiveThreshold(
            plate_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        techniques.append(adaptive_inv)
        
        # Técnica 4: Imagen mejorada directamente
        techniques.append(plate_enhanced)
        
        # Probar OCR con cada técnica y tomar el mejor resultado
        all_results = []
        
        for idx, processed_img in enumerate(techniques):
            try:
                results = self.reader.readtext(processed_img, detail=1)
                for result in results:
                    bbox, text, conf = result
                    all_results.append({
                        'text': text,
                        'confidence': conf,
                        'technique': idx
                    })
            except:
                continue
        
        # Si no hay resultados, retornar NO DETECTADA
        if not all_results:
            return {'text': "NO DETECTADA", 'bbox': plate_bbox}
        
        # Ordenar por confianza y tomar el mejor
        best_result = max(all_results, key=lambda x: x['confidence'])
        text = best_result['text']
        
        # Limpiar texto: solo alfanuméricos y espacios
        text = ''.join(c for c in text if c.isalnum() or c == ' ')
        text = text.upper().strip()
        
        # Si el texto es muy corto o muy largo, probablemente sea error
        if len(text) < 4 or len(text) > 12:
            # Intentar con el segundo mejor
            sorted_results = sorted(all_results, key=lambda x: x['confidence'], reverse=True)
            if len(sorted_results) > 1:
                text = sorted_results[1]['text']
                text = ''.join(c for c in text if c.isalnum() or c == ' ')
                text = text.upper().strip()
        
        return {'text': text if text else "NO DETECTADA", 'bbox': plate_bbox}
    
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
            
            # Tomar la primera placa detectada (o la de mayor confianza)
            best_box = None
            best_conf = 0
            
            for box in boxes:
                conf = float(box.conf[0])
                if conf > best_conf:
                    best_conf = conf
                    best_box = box
            
            if best_box is not None and best_conf > 0.25:  # Umbral de confianza
                x1, y1, x2, y2 = best_box.xyxy[0].cpu().numpy().astype(int)
                
                # Asegurar que las coordenadas están dentro de la imagen
                h, w = vehicle_image.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                # Recortar placa
                plate_image = vehicle_image[y1:y2, x1:x2]
                bbox = [x1, y1, x2, y2]
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
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        
        plate_contour = None
        
        # Buscar contorno rectangular (placa)
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * perimeter, True)
            
            # Las placas suelen ser rectangulares (4 vértices)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)
                
                # Placas peruanas tienen aspect ratio entre 2:1 y 4:1
                if 2.0 <= aspect_ratio <= 4.5:
                    plate_contour = approx
                    break
        
        if plate_contour is not None:
            x, y, w, h = cv2.boundingRect(plate_contour)
            plate_image = vehicle_image[y:y+h, x:x+w]
            bbox = [x, y, x+w, y+h]
            return plate_image, bbox
        
        # Si no se encuentra placa por contornos, usar región inferior central
        height, width = vehicle_image.shape[:2]
        x1, y1 = int(width*0.2), int(height*0.6)
        x2, y2 = int(width*0.8), int(height*0.9)
        plate_region = vehicle_image[y1:y2, x1:x2]
        bbox = [x1, y1, x2, y2]
        return plate_region, bbox