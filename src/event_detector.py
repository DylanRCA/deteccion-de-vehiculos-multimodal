from datetime import datetime


class EventDetector:
    def __init__(self, line_position=400, entry_direction='down'):
        """
        Inicializa el detector de eventos de entrada/salida.
        
        Args:
            line_position (int): Posicion Y de la linea virtual (pixeles desde arriba)
            entry_direction (str): Direccion de entrada ('down' o 'up')
        """
        print(f"[EVENT-INIT] Inicializando EventDetector - Linea Y: {line_position}, Direccion: {entry_direction}")
        
        self.line_position = line_position
        self.entry_direction = entry_direction
        self.tolerance = 10  # Pixeles de tolerancia
        
        # Historial de posiciones para cada track
        self.track_history = {}  # track_id -> {'positions': [...], 'last_event': None}
        
        print(f"[EVENT-INIT] EventDetector inicializado correctamente")
    
    def configure_line(self, y_position, entry_direction='down'):
        """
        Configura la posicion de la linea virtual.
        
        Args:
            y_position (int): Nueva posicion Y
            entry_direction (str): Nueva direccion de entrada
        """
        print(f"[EVENT-CONFIG] Configurando linea - Y: {y_position}, Direccion: {entry_direction}")
        
        self.line_position = y_position
        self.entry_direction = entry_direction
        
        print(f"[EVENT-CONFIG] Configuracion actualizada")
    
    def _get_centroid_y(self, bbox):
        """
        Calcula la coordenada Y del centroide de un bounding box.
        
        Args:
            bbox (list): [x1, y1, x2, y2]
            
        Returns:
            float: Coordenada Y del centroide
        """
        y1, y2 = bbox[1], bbox[3]
        return (y1 + y2) / 2.0
    
    def _determine_direction(self, track_id, current_y):
        """
        Determina la direccion de movimiento de un vehiculo.
        
        Args:
            track_id (int): ID del track
            current_y (float): Posicion Y actual
            
        Returns:
            str: 'down', 'up', o 'stationary'
        """
        if track_id not in self.track_history:
            return 'stationary'
        
        positions = self.track_history[track_id]['positions']
        
        if len(positions) < 2:
            return 'stationary'
        
        # Comparar con posicion anterior
        prev_y = positions[-1]
        
        if current_y > prev_y + self.tolerance:
            return 'down'
        elif current_y < prev_y - self.tolerance:
            return 'up'
        else:
            return 'stationary'
    
    def _is_crossing_line(self, track_id, current_y):
        """
        Detecta si un vehiculo esta cruzando la linea virtual.
        
        Args:
            track_id (int): ID del track
            current_y (float): Posicion Y actual
            
        Returns:
            bool: True si esta cruzando la linea
        """
        if track_id not in self.track_history:
            return False
        
        positions = self.track_history[track_id]['positions']
        
        if len(positions) < 1:
            return False
        
        prev_y = positions[-1]
        
        # Verificar si cruzo la linea entre frames
        crossed = (prev_y < self.line_position <= current_y) or \
                  (prev_y > self.line_position >= current_y)
        
        return crossed
    
    def detect_events(self, tracks):
        """
        Detecta eventos de entrada/salida basados en cruces de linea.
        
        Args:
            tracks (list): Lista de tracks del frame actual
                          [{'id': int, 'bbox': [x1,y1,x2,y2], ...}]
        
        Returns:
            list: Lista de eventos detectados
                  [{'track_id': int, 'event': str, 'timestamp': datetime}, ...]
        """
        print(f"[EVENT-DETECT] Procesando {len(tracks)} tracks para deteccion de eventos")
        
        events = []
        current_track_ids = set()
        
        for track in tracks:
            track_id = track['id']
            current_track_ids.add(track_id)
            
            # Calcular centroide
            centroid_y = self._get_centroid_y(track['bbox'])
            
            # Inicializar historial si es nuevo
            if track_id not in self.track_history:
                print(f"[EVENT-DETECT] Nuevo track detectado: {track_id}")
                self.track_history[track_id] = {
                    'positions': [],
                    'last_event': None
                }
            
            # Detectar cruce de linea
            is_crossing = self._is_crossing_line(track_id, centroid_y)
            
            if is_crossing:
                # Determinar direccion de movimiento
                direction = self._determine_direction(track_id, centroid_y)
                
                print(f"[EVENT-DETECT] Track {track_id} cruzando linea - Direccion: {direction}, Y actual: {centroid_y:.1f}, Linea: {self.line_position}")
                
                # Determinar tipo de evento
                event_type = None
                
                if self.entry_direction == 'down':
                    if direction == 'down':
                        event_type = 'entry'
                    elif direction == 'up':
                        event_type = 'exit'
                else:  # entry_direction == 'up'
                    if direction == 'up':
                        event_type = 'entry'
                    elif direction == 'down':
                        event_type = 'exit'
                
                # Evitar eventos duplicados
                last_event = self.track_history[track_id]['last_event']
                
                if event_type and event_type != last_event:
                    event = {
                        'track_id': track_id,
                        'event': event_type,
                        'timestamp': datetime.now()
                    }
                    events.append(event)
                    
                    # Actualizar ultimo evento
                    self.track_history[track_id]['last_event'] = event_type
                    
                    print(f"[EVENT-DETECTED] Evento '{event_type}' registrado para track {track_id}")
                elif event_type == last_event:
                    print(f"[EVENT-SKIP] Evento duplicado '{event_type}' para track {track_id}, ignorando")
            
            # Actualizar historial de posiciones (mantener ultimas 10 posiciones)
            self.track_history[track_id]['positions'].append(centroid_y)
            if len(self.track_history[track_id]['positions']) > 10:
                self.track_history[track_id]['positions'].pop(0)
        
        # Limpiar tracks que ya no estan activos (llevan mas de 100 frames sin aparecer)
        # Para evitar que el historial crezca indefinidamente
        tracks_to_remove = []
        for track_id in self.track_history:
            if track_id not in current_track_ids:
                # Podriamos implementar un contador de frames inactivos
                # Por ahora, mantener todos para no perder informacion
                pass
        
        print(f"[EVENT-DETECT] Total de eventos detectados: {len(events)}")
        
        return events
    
    def draw_line(self, image):
        """
        Dibuja la linea virtual en la imagen (para debug/visualizacion).
        
        Args:
            image: Imagen numpy array (BGR)
            
        Returns:
            numpy.ndarray: Imagen con linea dibujada
        """
        import cv2
        
        output = image.copy()
        
        # Obtener dimensiones
        height, width = image.shape[:2]
        
        # Dibujar linea horizontal
        color = (0, 255, 255)  # Amarillo
        thickness = 2
        
        cv2.line(output, (0, self.line_position), (width, self.line_position), color, thickness)
        
        # Dibujar texto indicando direccion
        if self.entry_direction == 'down':
            text_entry = "ENTRADA (ABAJO)"
            text_exit = "SALIDA (ARRIBA)"
        else:
            text_entry = "ENTRADA (ARRIBA)"
            text_exit = "SALIDA (ABAJO)"
        
        # Posicionar texto
        y_entry = self.line_position + 30
        y_exit = self.line_position - 10
        
        cv2.putText(output, text_entry, (10, y_entry),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(output, text_exit, (10, y_exit),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return output
    
    def reset_history(self):
        """Limpia el historial de tracks (util para debugging)."""
        print(f"[EVENT-RESET] Limpiando historial de tracks")
        self.track_history = {}
        print(f"[EVENT-RESET] Historial limpiado")