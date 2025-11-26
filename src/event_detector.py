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
        self.tolerance = 5  # Reducido para detectar mejor
        
        # Historial de posiciones para cada track
        self.track_history = {}  # track_id -> {'positions': [...], 'last_event': None, 'crossed': False}
        
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
        
        # Comparar con posiciones anteriores (promedio para estabilidad)
        if len(positions) >= 3:
            avg_prev = sum(positions[-3:]) / 3
        else:
            avg_prev = positions[-1]
        
        diff = current_y - avg_prev
        
        if diff > self.tolerance:
            return 'down'
        elif diff < -self.tolerance:
            return 'up'
        else:
            return 'stationary'
    
    def _check_line_crossing(self, track_id, current_y):
        """
        Verifica si el vehiculo cruzo la linea entre el frame anterior y el actual.
        
        Args:
            track_id (int): ID del track
            current_y (float): Posicion Y actual
            
        Returns:
            str or None: 'down_cross', 'up_cross', o None
        """
        if track_id not in self.track_history:
            return None
        
        positions = self.track_history[track_id]['positions']
        
        if len(positions) < 1:
            return None
        
        prev_y = positions[-1]
        line = self.line_position
        
        # Cruce de arriba hacia abajo
        if prev_y < line and current_y >= line:
            return 'down_cross'
        
        # Cruce de abajo hacia arriba
        if prev_y > line and current_y <= line:
            return 'up_cross'
        
        return None
    
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
        events = []
        current_track_ids = set()
        
        for track in tracks:
            track_id = track['id']
            current_track_ids.add(track_id)
            
            # Calcular centroide
            centroid_y = self._get_centroid_y(track['bbox'])
            
            # Inicializar historial si es nuevo
            if track_id not in self.track_history:
                self.track_history[track_id] = {
                    'positions': [centroid_y],  # Iniciar con posicion actual
                    'last_event': None,
                    'crossed': False
                }
                continue  # Necesitamos al menos 2 frames para detectar cruce
            
            # Verificar cruce de linea
            crossing = self._check_line_crossing(track_id, centroid_y)
            
            if crossing:
                # Determinar tipo de evento segun direccion configurada
                event_type = None
                
                if self.entry_direction == 'down':
                    # Entrada = cruzar hacia abajo, Salida = cruzar hacia arriba
                    if crossing == 'down_cross':
                        event_type = 'entry'
                    elif crossing == 'up_cross':
                        event_type = 'exit'
                else:  # entry_direction == 'up'
                    # Entrada = cruzar hacia arriba, Salida = cruzar hacia abajo
                    if crossing == 'up_cross':
                        event_type = 'entry'
                    elif crossing == 'down_cross':
                        event_type = 'exit'
                
                # Evitar eventos duplicados para el mismo track
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
                    self.track_history[track_id]['crossed'] = True
                    
                    print(f"[EVENT] Track {track_id} -> {event_type.upper()} (Y: {centroid_y:.0f}, Linea: {self.line_position})")
            
            # Actualizar historial de posiciones (mantener ultimas 10 posiciones)
            self.track_history[track_id]['positions'].append(centroid_y)
            if len(self.track_history[track_id]['positions']) > 10:
                self.track_history[track_id]['positions'].pop(0)
        
        # Limpiar tracks muy antiguos (no vistos en 50+ frames)
        # Esto se maneja implicitamente ya que los tracks eliminados del tracker
        # simplemente no aparecen en la lista
        
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
        y_entry = self.line_position + 25
        y_exit = self.line_position - 10
        
        cv2.putText(output, text_exit, (10, y_exit),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(output, text_entry, (10, y_entry),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return output
    
    def reset_history(self):
        """Limpia el historial de tracks (util para nuevo video)."""
        print(f"[EVENT-RESET] Limpiando historial de tracks")
        self.track_history = {}
        print(f"[EVENT-RESET] Historial limpiado")
    
    def get_debug_info(self):
        """Retorna info de debug sobre el estado actual."""
        info = {
            'line_position': self.line_position,
            'entry_direction': self.entry_direction,
            'tracked_vehicles': len(self.track_history),
            'vehicles_with_events': sum(1 for v in self.track_history.values() if v['last_event'])
        }
        return info