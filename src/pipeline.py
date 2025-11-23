import cv2
import config
from datetime import datetime
from .car_detector import CarDetector
from .plate_recognizer import PlateRecognizer
from .classifier import VehicleClassifier
from .tracker import VehicleTracker
from .database import DatabaseManager
from .event_detector import EventDetector


class VehicleDetectionPipeline:
    def __init__(self, car_min_confidence=0.4, enable_database=True, enable_events=True):
        """
        Inicializa el pipeline completo de deteccion de vehiculos.
        Orquesta todos los modelos: detector, OCR, clasificador, tracker, DB y eventos.
        
        Args:
            car_min_confidence (float): Confianza minima para deteccion de vehiculos (0.0-1.0)
            enable_database (bool): Activar sistema de base de datos
            enable_events (bool): Activar detector de eventos
        """
        print("\n" + "="*80)
        print("[PIPELINE-INIT] Inicializando VehicleDetectionPipeline")
        print("="*80)
        
        # Modulos principales (FASE 1)
        print("\n[PIPELINE-INIT] Cargando modulos principales...")
        self.car_detector = CarDetector(min_confidence=car_min_confidence)
        self.plate_recognizer = PlateRecognizer()
        self.vehicle_classifier = VehicleClassifier()
        
        # Tracker (FASE 2A)
        print("\n[PIPELINE-INIT] Inicializando sistema de tracking...")
        self.tracker = VehicleTracker(
            max_age=getattr(config, "TRACKING_MAX_AGE", 30),
            min_hits=getattr(config, "TRACKING_MIN_HITS", 3),
            iou_threshold=getattr(config, "TRACKING_IOU_THRESHOLD", 0.3),
        )
        
        # Base de datos (FASE 2B) - OPCIONAL
        self.enable_database = enable_database
        if enable_database:
            print("\n[PIPELINE-INIT] Inicializando sistema de base de datos...")
            try:
                db_path = getattr(config, 'DB_PATH', 'database/estacionamiento.db')
                self.db = DatabaseManager(db_path)
                print("[PIPELINE-INIT] Base de datos inicializada exitosamente")
            except Exception as e:
                print(f"[PIPELINE-ERROR] Error al inicializar base de datos: {str(e)}")
                print("[PIPELINE-WARNING] Continuando sin base de datos")
                self.enable_database = False
                self.db = None
        else:
            print("[PIPELINE-INIT] Base de datos desactivada")
            self.db = None
        
        # Detector de eventos (FASE 2B) - OPCIONAL
        self.enable_events = enable_events
        if enable_events:
            print("\n[PIPELINE-INIT] Inicializando detector de eventos...")
            try:
                line_pos = getattr(config, 'EVENT_LINE_POSITION', 400)
                entry_dir = getattr(config, 'EVENT_ENTRY_DIRECTION', 'down')
                self.event_detector = EventDetector(line_position=line_pos, entry_direction=entry_dir)
                print("[PIPELINE-INIT] Detector de eventos inicializado exitosamente")
            except Exception as e:
                print(f"[PIPELINE-ERROR] Error al inicializar detector de eventos: {str(e)}")
                print("[PIPELINE-WARNING] Continuando sin detector de eventos")
                self.enable_events = False
                self.event_detector = None
        else:
            print("[PIPELINE-INIT] Detector de eventos desactivado")
            self.event_detector = None
        
        # Estado
        self.frame_count = 0
        self.known_vehicles = {}  # track_id -> vehicle_info (cache)
        
        print("\n" + "="*80)
        print("[PIPELINE-INIT] Pipeline inicializado correctamente")
        print(f"[PIPELINE-INIT] - Base de datos: {'ACTIVADA' if self.enable_database else 'DESACTIVADA'}")
        print(f"[PIPELINE-INIT] - Eventos: {'ACTIVADOS' if self.enable_events else 'DESACTIVADOS'}")
        print("="*80 + "\n")
    
    def reset(self):
        """
        Resetea el estado del pipeline para procesar un nuevo video.
        Limpia tracker, cache de vehiculos conocidos y eventos.
        """
        print("\n[PIPELINE-RESET] Reseteando pipeline para nuevo video...")
        
        # Reset tracker
        self.tracker = VehicleTracker(
            max_age=getattr(config, "TRACKING_MAX_AGE", 30),
            min_hits=getattr(config, "TRACKING_MIN_HITS", 3),
            iou_threshold=getattr(config, "TRACKING_IOU_THRESHOLD", 0.3),
        )
        
        # Reset estado
        self.frame_count = 0
        self.known_vehicles = {}
        
        # Reset detector de eventos si existe
        if self.enable_events and self.event_detector:
            self.event_detector.reset_history()
        
        print("[PIPELINE-RESET] Pipeline reseteado - IDs comenzaran desde 1\n")
    
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
        print(f"\n[PIPELINE-IMAGE] Procesando imagen...")
        
        try:
            # 1. Detectar vehiculos
            print("[PIPELINE-IMAGE] Paso 1: Detectando vehiculos...")
            vehicle_detections = self.car_detector.detect_vehicles(image)
            print(f"[PIPELINE-IMAGE] Detectados {len(vehicle_detections)} vehiculos")
            
            # 2. Actualizar tracker para mantener IDs persistentes
            print("[PIPELINE-IMAGE] Paso 2: Actualizando tracker...")
            track_outputs = self.tracker.update(vehicle_detections)
            print(f"[PIPELINE-IMAGE] Tracker retorno {len(track_outputs)} tracks activos")

            results = []
            
            # 3. Procesar cada vehiculo detectado
            print(f"[PIPELINE-IMAGE] Paso 3: Procesando {len(vehicle_detections)} detecciones...")
            for idx, detection in enumerate(vehicle_detections):
                try:
                    x1, y1, x2, y2 = detection['bbox']
                    
                    # Recortar vehiculo de la imagen original
                    vehicle_crop = image[y1:y2, x1:x2]
                    
                    # 4. Reconocer placa (retorna dict con texto y bbox)
                    print(f"[PIPELINE-IMAGE] Vehiculo {idx+1}: Reconociendo placa...")
                    plate_result = self.plate_recognizer.recognize_plate(vehicle_crop)
                    
                    # 5. Clasificar marca y color
                    print(f"[PIPELINE-IMAGE] Vehiculo {idx+1}: Clasificando marca y color...")
                    classification = self.vehicle_classifier.classify(vehicle_crop)
                    
                    # Determinar estado de la placa
                    plate_text = plate_result['text']
                    has_plate = plate_text not in ["SIN PLACA", "NO DETECTADA"]

                    # Obtener ID persistente del tracker usando IoU
                    assigned_id = self._assign_track_id(detection, track_outputs)
                    detection_id = assigned_id if assigned_id is not None else idx + 1
                    
                    print(f"[PIPELINE-IMAGE] Vehiculo {idx+1}: ID asignado: {detection_id}, Placa: {plate_text}")
                    
                    # Guardar resultados
                    vehicle_info = {
                        'id': detection_id,
                        'bbox': detection['bbox'],
                        'confidence': detection['confidence'],
                        'class': detection['class'],
                        'Placa': 'SI' if has_plate else 'NO',
                        'Numero-Placa': plate_text if has_plate else '------',
                        'plate_bbox': plate_result['bbox'],
                        'brand': classification['brand'],
                        'brand_bbox': classification['brand_bbox'],
                        'color': classification['color']
                    }
                    
                    results.append(vehicle_info)
                    
                except Exception as e:
                    print(f"[PIPELINE-ERROR] Error procesando vehiculo {idx+1}: {str(e)}")
                    continue
            
            # 5. Dibujar resultados en la imagen
            print("[PIPELINE-IMAGE] Paso 4: Dibujando resultados...")
            annotated_image = self._draw_results(image, results)
            
            print(f"[PIPELINE-IMAGE] Procesamiento completado exitosamente")
            
            return {
                'annotated_image': annotated_image,
                'detections': results
            }
            
        except Exception as e:
            print(f"[PIPELINE-ERROR] Error critico en process_image: {str(e)}")
            # Retornar imagen original en caso de error
            return {
                'annotated_image': image.copy(),
                'detections': []
            }
    
    def process_video_frame(self, frame):
        """
        Procesa un frame de video con tracking, BD y eventos.
        
        Args:
            frame: Frame de video (numpy array BGR)
            
        Returns:
            dict: {
                'annotated_image': numpy.ndarray,
                'detections': list,
                'tracks': list,
                'events': list
            }
        """
        self.frame_count += 1
        
        # Logging condicional basado en config
        verbose = getattr(config, 'DEBUG_VERBOSE', False)
        log_interval = getattr(config, 'DEBUG_LOG_INTERVAL', 30)
        
        if self.frame_count % log_interval == 0 or verbose:
            print(f"\n[PIPELINE-VIDEO] Procesando frame {self.frame_count}...")
        
        try:
            # 1. Detectar vehiculos
            vehicle_detections = self.car_detector.detect_vehicles(frame)
            
            # 2. Tracking - asignar IDs
            tracks = self.tracker.update(vehicle_detections)
            
            # 3. Para cada track, clasificar si es nuevo
            for track in tracks:
                track_id = track['id']
                
                try:
                    if track_id not in self.known_vehicles:
                        # Vehiculo nuevo, clasificar
                        # CRITICAL: Convert bbox coords to int
                        x1, y1, x2, y2 = track['bbox']
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        vehicle_crop = frame[y1:y2, x1:x2]
                        
                        print(f"[PIPELINE-VIDEO] Nuevo vehiculo detectado - Track ID: {track_id}")
                        
                        plate_info = self.plate_recognizer.recognize_plate(vehicle_crop)
                        classification = self.vehicle_classifier.classify(vehicle_crop)
                        
                        # Generar placa final (con ID temporal si no tiene placa)
                        plate_text = plate_info['text']
                        if plate_text in ["SIN PLACA", "NO DETECTADA"]:
                            # Generar ID temporal
                            temp_prefix = getattr(config, 'TEMP_PLATE_PREFIX', 'TEMP_')
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            plate_text = f"{temp_prefix}{timestamp}_{track_id}"
                            print(f"[PIPELINE-VIDEO] Placa no legible, usando ID temporal: {plate_text}")
                        
                        vehicle_data = {
                            'plate': plate_text,
                            'brand': classification['brand'],
                            'color': classification['color']
                        }
                        
                        self.known_vehicles[track_id] = vehicle_data
                
                except Exception as e:
                    print(f"[PIPELINE-ERROR] Error procesando track {track_id}: {str(e)}")
                    continue
            
            # 4. Detectar eventos si esta habilitado
            events = []
            if self.enable_events and self.event_detector:
                try:
                    events = self.event_detector.detect_events(tracks)
                    
                    # 5. Procesar eventos con NUEVA LOGICA BD
                    for event in events:
                        track_id = event['track_id']
                        vehicle_data = self.known_vehicles.get(track_id)
                        
                        if not vehicle_data:
                            print(f"[PIPELINE-WARNING] Evento para track {track_id} sin datos de vehiculo")
                            continue
                        
                        plate = vehicle_data['plate']
                        brand = vehicle_data['brand']
                        color = vehicle_data['color']
                        
                        if self.enable_database and self.db:
                            try:
                                if event['event'] == 'entry':
                                    # ENTRADA: Buscar en active_vehicles
                                    existing = self.db.find_active_by_plate(plate)
                                    
                                    if existing:
                                        # Ya esta dentro, actualizar track_id
                                        print(f"[PARKING] {plate} ya registrado dentro, actualizando track_id")
                                        self.db.update_active_track_id(plate, track_id)
                                    else:
                                        # Registrar nueva entrada
                                        self.db.register_entry(
                                            plate=plate,
                                            track_id=track_id,
                                            brand=brand,
                                            color=color
                                        )
                                        print(f"[PARKING] {plate} ENTRO al estacionamiento")
                                
                                elif event['event'] == 'exit':
                                    # SALIDA: Mover de active_vehicles a parking_history
                                    session = self.db.register_exit(plate)
                                    
                                    if session:
                                        print(f"[PARKING] {plate} SALIO - Duracion: {session['duration_minutes']} min")
                                    else:
                                        print(f"[PARKING-WARNING] {plate} salio sin entrada registrada")
                                
                            except Exception as e:
                                print(f"[PIPELINE-ERROR] Error procesando evento {event['event']} para {plate}: {str(e)}")
                
                except Exception as e:
                    print(f"[PIPELINE-ERROR] Error en detector de eventos: {str(e)}")
            
            # 6. Preparar detecciones para visualizacion
            detections = []
            for track in tracks:
                track_id = track['id']
                vehicle_data = self.known_vehicles.get(track_id, {})
                
                plate_text = vehicle_data.get('plate', 'DESCONOCIDA')
                
                # Determinar si tiene placa legible (no temporal)
                temp_prefix = getattr(config, 'TEMP_PLATE_PREFIX', 'TEMP_')
                has_plate = not plate_text.startswith(temp_prefix) and plate_text not in ["DESCONOCIDA", "SIN PLACA"]
                
                # CRITICAL: Ensure bbox coords are integers
                bbox = track['bbox']
                bbox_int = [int(coord) for coord in bbox]
                
                detection_info = {
                    'id': track_id,
                    'bbox': bbox_int,
                    'confidence': 0.9,
                    'class': 'car',
                    'Placa': 'SI' if has_plate else 'NO',
                    'Numero-Placa': plate_text if has_plate else '------',
                    'plate_bbox': None,
                    'brand': vehicle_data.get('brand', 'DESCONOCIDA'),
                    'brand_bbox': None,
                    'color': vehicle_data.get('color', 'DESCONOCIDO')
                }
                
                detections.append(detection_info)
            
            # 7. Dibujar resultados
            annotated = self._draw_results(frame, detections)
            
            # Dibujar linea virtual si eventos estan habilitados
            if self.enable_events and self.event_detector:
                try:
                    annotated = self.event_detector.draw_line(annotated)
                except Exception as e:
                    print(f"[PIPELINE-WARNING] Error dibujando linea: {str(e)}")
            
            return {
                'annotated_image': annotated,
                'detections': detections,
                'tracks': tracks,
                'events': events
            }
            
        except Exception as e:
            print(f"[PIPELINE-ERROR] Error critico en process_video_frame: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Retornar frame original en caso de error
            return {
                'annotated_image': frame.copy(),
                'detections': [],
                'tracks': [],
                'events': []
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
            try:
                # Validate and convert bbox coords to int
                bbox = det['bbox']
                if not bbox or len(bbox) != 4:
                    print(f"[DRAW-WARNING] Invalid bbox for vehicle {det['id']}: {bbox}")
                    continue
                
                vx1, vy1, vx2, vy2 = bbox
                
                # Ensure all coords are integers
                vx1, vy1, vx2, vy2 = int(vx1), int(vy1), int(vx2), int(vy2)
                
                # Validate bbox is within image bounds
                h, w = image.shape[:2]
                vx1 = max(0, min(vx1, w))
                vy1 = max(0, min(vy1, h))
                vx2 = max(0, min(vx2, w))
                vy2 = max(0, min(vy2, h))
                
                # Skip if bbox is invalid
                if vx2 <= vx1 or vy2 <= vy1:
                    print(f"[DRAW-WARNING] Invalid bbox dimensions for vehicle {det['id']}")
                    continue
                
                # Rectangulo del vehiculo (verde)
                cv2.rectangle(output, (vx1, vy1), (vx2, vy2), (0, 255, 0), 2)
            
                # Dibujar cuadro de la placa si fue detectada (amarillo)
                if det['plate_bbox'] is not None and det['Placa'] == 'SI':
                    px1, py1, px2, py2 = det['plate_bbox']
                    abs_px1 = int(vx1 + px1)
                    abs_py1 = int(vy1 + py1)
                    abs_px2 = int(vx1 + px2)
                    abs_py2 = int(vy1 + py2)
                    
                    cv2.rectangle(output, (abs_px1, abs_py1), (abs_px2, abs_py2), 
                                (0, 255, 255), 2)
                
                # Dibujar cuadro del logo de marca si fue detectado (azul)
                if det['brand_bbox'] is not None and det['brand'] != 'DESCONOCIDA':
                    bx1, by1, bx2, by2 = det['brand_bbox']
                    abs_bx1 = int(vx1 + bx1)
                    abs_by1 = int(vy1 + by1)
                    abs_bx2 = int(vx1 + bx2)
                    abs_by2 = int(vy1 + by2)
                    
                    cv2.rectangle(output, (abs_bx1, abs_by1), (abs_bx2, abs_by2), 
                                (255, 0, 0), 2)
                
                # Dibujar ID del vehiculo
                info_lines = [
                    f"ID: {det['id']}",
                ]
                
                # Dibujar fondo para el texto
                text_y = vy1 - 10
                for line in reversed(info_lines):
                    text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                    
                    cv2.rectangle(output, 
                                (vx1, text_y - text_size[1] - 5),
                                (vx1 + text_size[0] + 5, text_y),
                                (0, 0, 0), -1)
                    
                    cv2.putText(output, line, (vx1 + 2, text_y - 2),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    text_y -= (text_size[1] + 8)
                    
            except Exception as e:
                print(f"[DRAW-ERROR] Error dibujando vehiculo {det.get('id', 'unknown')}: {str(e)}")
                continue
        
        return output

    def _assign_track_id(self, detection, tracks):
        """
        Asigna el ID de track a una deteccion actual usando IoU.
        Retorna None si no hay match sobre el umbral.
        """
        best_iou = 0.0
        best_id = None
        for track in tracks:
            iou = self.tracker._iou(detection['bbox'], track['bbox'])
            if iou > best_iou:
                best_iou = iou
                best_id = track['id']

        if best_id is not None and best_iou >= self.tracker.iou_threshold:
            return best_id
        return None