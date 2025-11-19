import cv2
from .car_detector import CarDetector
from .plate_recognizer import PlateRecognizer
from .classifier import VehicleClassifier


class VehicleDetectionPipeline:
    def __init__(self):
        """
        Inicializa el pipeline completo de deteccion de vehiculos.
        Orquesta todos los modelos: detector, OCR y clasificador.
        """
        self.car_detector = CarDetector()
        self.plate_recognizer = PlateRecognizer()
        self.vehicle_classifier = VehicleClassifier()
    
    def process_image(self, image):
        """
        Procesa una imagen completa detectando vehiculos y extrayendo informacion.
        
        Args:
            image: Imagen en formato numpy array (BGR)
            
        Returns:
            dict: {
                'annotated_image': numpy.ndarray,  # Imagen con anotaciones
                'detections': list  # Lista de vehiculos detectados con su info
            }
        """
        # 1. Detectar vehiculos
        vehicle_detections = self.car_detector.detect_vehicles(image)
        
        results = []
        
        # 2. Procesar cada vehiculo detectado
        for idx, detection in enumerate(vehicle_detections):
            x1, y1, x2, y2 = detection['bbox']
            
            # Recortar vehiculo de la imagen original
            vehicle_crop = image[y1:y2, x1:x2]
            
            # 3. Reconocer placa (retorna dict con texto y bbox)
            plate_result = self.plate_recognizer.recognize_plate(vehicle_crop)
            
            # 4. Clasificar marca y color
            classification = self.vehicle_classifier.classify(vehicle_crop)
            
            # Determinar estado de la placa
            plate_text = plate_result['text']
            has_plate = plate_text not in ["SIN PLACA", "NO DETECTADA"]
            
            # Guardar resultados con nombres específicos solicitados
            vehicle_info = {
                'id': idx + 1,
                'bbox': detection['bbox'],
                'confidence': detection['confidence'],
                'class': detection['class'],
                'Placa': 'SI' if has_plate else 'NO',  # "SI" o "NO"
                'Numero-Placa': plate_text if has_plate else '------',  # Número o "------"
                'plate_bbox': plate_result['bbox'],  # Para dibujar
                'brand': classification['brand'],
                'color': classification['color']
            }
            
            results.append(vehicle_info)
        
        # 5. Dibujar resultados en la imagen
        annotated_image = self._draw_results(image, results)
        
        return {
            'annotated_image': annotated_image,
            'detections': results
        }
    
    def _draw_results(self, image, detections):
        """
        Dibuja los resultados de deteccion en la imagen.
        
        Args:
            image: Imagen original
            detections: Lista de detecciones con informacion completa
            
        Returns:
            numpy.ndarray: Imagen anotada
        """
        output = image.copy()
        
        for det in detections:
            vx1, vy1, vx2, vy2 = det['bbox']
            
            # Rectangulo del vehiculo (verde)
            cv2.rectangle(output, (vx1, vy1), (vx2, vy2), (0, 255, 0), 2)
            
            # Dibujar cuadro de la placa si fue detectada (amarillo)
            if det['plate_bbox'] is not None and det['Placa'] == 'SI':
                px1, py1, px2, py2 = det['plate_bbox']
                # Convertir coordenadas relativas a absolutas
                abs_px1 = vx1 + px1
                abs_py1 = vy1 + py1
                abs_px2 = vx1 + px2
                abs_py2 = vy1 + py2
                
                cv2.rectangle(output, (abs_px1, abs_py1), (abs_px2, abs_py2), 
                            (0, 255, 255), 2)  # Amarillo para placa
            
            # Preparar texto de informacion
            info_lines = [
                f"ID: {det['id']}",
                f"Tipo: {det['class']}",
            ]
            
            # Agregar informacion de placa
            if det['Placa'] == 'SI':
                info_lines.append(f"Placa: {det['Numero-Placa']}")
            else:
                info_lines.append("Placa: NO DETECTADA")
            
            # Agregar color y marca
            info_lines.extend([
                f"Color: {det['color']}",
                f"Marca: {det['brand']}"
            ])
            
            # Dibujar fondo para el texto
            text_y = vy1 - 10
            for line in reversed(info_lines):
                text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                
                # Fondo negro semi-transparente
                cv2.rectangle(output, 
                            (vx1, text_y - text_size[1] - 5),
                            (vx1 + text_size[0] + 5, text_y),
                            (0, 0, 0), -1)
                
                # Texto blanco
                cv2.putText(output, line, (vx1 + 2, text_y - 2),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                text_y -= (text_size[1] + 8)
        
        return output
    
    def process_video_frame(self, frame):
        """
        Procesa un frame de video (simplemente llama a process_image).
        
        Args:
            frame: Frame de video (numpy array BGR)
            
        Returns:
            dict: Mismo formato que process_image
        """
        return self.process_image(frame)