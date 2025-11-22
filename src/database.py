import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager


class DatabaseManager:
    def __init__(self, db_path='database/estacionamiento.db'):
        """
        Inicializa el gestor de base de datos con logging detallado.
        
        Args:
            db_path (str): Ruta a la base de datos SQLite
        """
        print(f"[DB-INIT] Inicializando DatabaseManager con path: {db_path}")
        
        self.db_path = db_path
        
        # Crear directorio si no existe
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            print(f"[DB-INIT] Creando directorio: {db_dir}")
            os.makedirs(db_dir)
        
        # Inicializar base de datos
        try:
            self._init_database()
            print(f"[DB-INIT] Base de datos inicializada correctamente")
        except Exception as e:
            print(f"[DB-ERROR] Error al inicializar base de datos: {str(e)}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones a la base de datos."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            # Habilitar WAL mode para mejor concurrencia
            conn.execute('PRAGMA journal_mode=WAL')
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[DB-ERROR] Error en conexion: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """Crea las tablas si no existen."""
        print("[DB-INIT] Creando esquema de base de datos...")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de vehiculos
            print("[DB-INIT] Creando tabla 'vehicles'...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id INTEGER UNIQUE,
                    plate_number TEXT,
                    brand TEXT,
                    color TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    status TEXT
                )
            ''')
            
            # Tabla de eventos
            print("[DB-INIT] Creando tabla 'events'...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER,
                    event_type TEXT,
                    timestamp TIMESTAMP,
                    camera_id TEXT,
                    confidence REAL,
                    plate_confidence REAL,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                )
            ''')
            
            # Tabla de detecciones
            print("[DB-INIT] Creando tabla 'detections'...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER,
                    timestamp TIMESTAMP,
                    bbox_x1 INTEGER,
                    bbox_y1 INTEGER,
                    bbox_x2 INTEGER,
                    bbox_y2 INTEGER,
                    frame_number INTEGER,
                    image_path TEXT,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                )
            ''')
            
            # Indices
            print("[DB-INIT] Creando indices...")
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_vehicle ON events(vehicle_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status)')
            
        print("[DB-INIT] Esquema creado exitosamente")
    
    def register_vehicle(self, track_id, plate, brand, color):
        """
        Registra un nuevo vehiculo en la base de datos.
        
        Args:
            track_id (int): ID del tracker
            plate (str): Numero de placa
            brand (str): Marca del vehiculo
            color (str): Color del vehiculo
            
        Returns:
            int: ID del vehiculo en la base de datos
        """
        print(f"[DB-REGISTER] Registrando vehiculo - Track ID: {track_id}, Placa: {plate}, Marca: {brand}, Color: {color}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar si ya existe
                cursor.execute('SELECT id FROM vehicles WHERE track_id = ?', (track_id,))
                existing = cursor.fetchone()
                
                if existing:
                    vehicle_id = existing['id']
                    print(f"[DB-REGISTER] Vehiculo ya existe con ID: {vehicle_id}")
                    return vehicle_id
                
                # Insertar nuevo vehiculo
                now = datetime.now()
                cursor.execute('''
                    INSERT INTO vehicles (track_id, plate_number, brand, color, first_seen, last_seen, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (track_id, plate, brand, color, now, now, 'unknown'))
                
                vehicle_id = cursor.lastrowid
                print(f"[DB-REGISTER] Vehiculo registrado exitosamente con ID: {vehicle_id}")
                return vehicle_id
                
        except Exception as e:
            print(f"[DB-ERROR] Error al registrar vehiculo: {str(e)}")
            raise
    
    def log_event(self, vehicle_id, event_type, timestamp=None, camera_id='cam_01', confidence=1.0, plate_confidence=None):
        """
        Registra un evento (entrada/salida).
        
        Args:
            vehicle_id (int): ID del vehiculo en BD
            event_type (str): Tipo de evento ('entry', 'exit', 'detection')
            timestamp: Timestamp del evento
            camera_id (str): ID de la camara
            confidence (float): Confianza del evento
            plate_confidence (float): Confianza de la placa
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        print(f"[DB-EVENT] Registrando evento - Vehicle ID: {vehicle_id}, Tipo: {event_type}, Timestamp: {timestamp}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO events (vehicle_id, event_type, timestamp, camera_id, confidence, plate_confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (vehicle_id, event_type, timestamp, camera_id, confidence, plate_confidence))
                
                event_id = cursor.lastrowid
                print(f"[DB-EVENT] Evento registrado con ID: {event_id}")
                
        except Exception as e:
            print(f"[DB-ERROR] Error al registrar evento: {str(e)}")
            raise
    
    def log_detection(self, vehicle_id, bbox, frame_num, timestamp=None, image_path=None):
        """
        Registra una deteccion de vehiculo.
        
        Args:
            vehicle_id (int): ID del vehiculo en BD
            bbox (list): Bounding box [x1, y1, x2, y2]
            frame_num (int): Numero de frame
            timestamp: Timestamp de la deteccion
            image_path (str): Ruta a snapshot (opcional)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        print(f"[DB-DETECT] Registrando deteccion - Vehicle ID: {vehicle_id}, Frame: {frame_num}, BBox: {bbox}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO detections (vehicle_id, timestamp, bbox_x1, bbox_y1, bbox_x2, bbox_y2, frame_number, image_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (vehicle_id, timestamp, bbox[0], bbox[1], bbox[2], bbox[3], frame_num, image_path))
                
                detection_id = cursor.lastrowid
                print(f"[DB-DETECT] Deteccion registrada con ID: {detection_id}")
                
        except Exception as e:
            print(f"[DB-ERROR] Error al registrar deteccion: {str(e)}")
            # No lanzar excepcion para no detener el procesamiento
            pass
    
    def update_vehicle_status(self, vehicle_id, status):
        """
        Actualiza el estado de un vehiculo.
        
        Args:
            vehicle_id (int): ID del vehiculo en BD
            status (str): Nuevo estado ('inside', 'outside', etc.)
        """
        print(f"[DB-UPDATE] Actualizando estado - Vehicle ID: {vehicle_id}, Status: {status}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE vehicles 
                    SET status = ?, last_seen = ?
                    WHERE id = ?
                ''', (status, datetime.now(), vehicle_id))
                
                print(f"[DB-UPDATE] Estado actualizado exitosamente")
                
        except Exception as e:
            print(f"[DB-ERROR] Error al actualizar estado: {str(e)}")
            raise
    
    def get_vehicle_by_track_id(self, track_id):
        """
        Obtiene informacion de un vehiculo por su track ID.
        
        Args:
            track_id (int): ID del tracker
            
        Returns:
            dict: Informacion del vehiculo o None
        """
        print(f"[DB-QUERY] Buscando vehiculo por track_id: {track_id}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM vehicles WHERE track_id = ?', (track_id,))
                row = cursor.fetchone()
                
                if row:
                    result = dict(row)
                    print(f"[DB-QUERY] Vehiculo encontrado: ID={result['id']}")
                    return result
                else:
                    print(f"[DB-QUERY] No se encontro vehiculo con track_id: {track_id}")
                    return None
                    
        except Exception as e:
            print(f"[DB-ERROR] Error en consulta: {str(e)}")
            return None
    
    def get_vehicles_inside(self):
        """
        Obtiene lista de vehiculos actualmente dentro del estacionamiento.
        
        Returns:
            list: Lista de vehiculos con status='inside'
        """
        print(f"[DB-QUERY] Consultando vehiculos dentro del estacionamiento")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM vehicles WHERE status = ?', ('inside',))
                rows = cursor.fetchall()
                
                results = [dict(row) for row in rows]
                print(f"[DB-QUERY] Encontrados {len(results)} vehiculos dentro")
                return results
                
        except Exception as e:
            print(f"[DB-ERROR] Error en consulta: {str(e)}")
            return []
    
    def get_events_by_date(self, date):
        """
        Obtiene eventos de una fecha especifica.
        
        Args:
            date (datetime.date): Fecha a consultar
            
        Returns:
            list: Lista de eventos
        """
        print(f"[DB-QUERY] Consultando eventos para fecha: {date}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Convertir fecha a string para comparacion
                date_str = date.strftime('%Y-%m-%d')
                
                cursor.execute('''
                    SELECT e.*, v.plate_number, v.brand, v.color
                    FROM events e
                    JOIN vehicles v ON e.vehicle_id = v.id
                    WHERE DATE(e.timestamp) = ?
                    ORDER BY e.timestamp DESC
                ''', (date_str,))
                
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
                
                print(f"[DB-QUERY] Encontrados {len(results)} eventos")
                return results
                
        except Exception as e:
            print(f"[DB-ERROR] Error en consulta: {str(e)}")
            return []