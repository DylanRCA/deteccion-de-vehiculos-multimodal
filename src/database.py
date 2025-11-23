import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager


class DatabaseManager:
    def __init__(self, db_path='database/estacionamiento.db'):
        """
        Inicializa el gestor de base de datos para estacionamiento.
        
        Esquema:
        - active_vehicles: Vehiculos dentro del estacionamiento AHORA
        - parking_history: Sesiones completadas (historico)
        - vehicle_registry: Catalogo de vehiculos conocidos
        
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
            
            # Tabla 1: Vehiculos actualmente dentro del estacionamiento
            print("[DB-INIT] Creando tabla 'active_vehicles'...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS active_vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL,
                    track_id INTEGER,
                    brand TEXT,
                    color TEXT,
                    entry_time TIMESTAMP NOT NULL,
                    parking_duration_minutes INTEGER DEFAULT 0
                )
            ''')
            
            # Tabla 2: Historial de sesiones de estacionamiento
            print("[DB-INIT] Creando tabla 'parking_history'...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parking_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL,
                    brand TEXT,
                    color TEXT,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP NOT NULL,
                    duration_minutes INTEGER,
                    source TEXT DEFAULT 'live_camera'
                )
            ''')
            
            # Tabla 3: Registro de vehiculos conocidos
            print("[DB-INIT] Creando tabla 'vehicle_registry'...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vehicle_registry (
                    plate TEXT PRIMARY KEY,
                    brand TEXT,
                    color TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    total_visits INTEGER DEFAULT 0,
                    avg_duration_minutes INTEGER DEFAULT 0
                )
            ''')
            
            # Indices para queries rapidas
            print("[DB-INIT] Creando indices...")
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_active_plate ON active_vehicles(plate)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_plate ON parking_history(plate)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_times ON parking_history(entry_time, exit_time)')
            
        print("[DB-INIT] Esquema creado exitosamente")
    
    # ==================== OPERACIONAL (active_vehicles) ====================
    
    def register_entry(self, plate, track_id, brand, color):
        """
        Registra la entrada de un vehiculo al estacionamiento.
        
        Args:
            plate (str): Numero de placa o ID temporal
            track_id (int): ID del tracker
            brand (str): Marca del vehiculo
            color (str): Color del vehiculo
            
        Returns:
            int: ID del registro en active_vehicles, o None si ya existe
        """
        print(f"[DB-ENTRY] Registrando entrada - Placa: {plate}, Track: {track_id}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar si ya esta dentro
                cursor.execute('SELECT id FROM active_vehicles WHERE plate = ?', (plate,))
                existing = cursor.fetchone()
                
                if existing:
                    import config
                    if getattr(config, 'PARKING_WARN_DUPLICATE_ENTRY', True):
                        print(f"[DB-WARNING] Vehiculo {plate} ya esta dentro (posible oclusion larga)")
                    
                    # Actualizar track_id
                    cursor.execute('''
                        UPDATE active_vehicles 
                        SET track_id = ?
                        WHERE plate = ?
                    ''', (track_id, plate))
                    
                    return existing['id']
                
                # Registrar nueva entrada
                entry_time = datetime.now()
                cursor.execute('''
                    INSERT INTO active_vehicles (plate, track_id, brand, color, entry_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (plate, track_id, brand, color, entry_time))
                
                active_id = cursor.lastrowid
                
                # Actualizar registro de vehiculo
                self._update_vehicle_registry(plate, brand, color, entry_time)
                
                print(f"[DB-ENTRY] Entrada registrada - ID: {active_id}")
                return active_id
                
        except Exception as e:
            print(f"[DB-ERROR] Error al registrar entrada: {str(e)}")
            return None
    
    def register_exit(self, plate):
        """
        Registra la salida de un vehiculo del estacionamiento.
        Mueve el registro de active_vehicles a parking_history.
        
        Args:
            plate (str): Numero de placa
            
        Returns:
            dict: Informacion de la sesion completada, o None si no estaba dentro
        """
        print(f"[DB-EXIT] Registrando salida - Placa: {plate}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Buscar en active_vehicles
                cursor.execute('SELECT * FROM active_vehicles WHERE plate = ?', (plate,))
                active = cursor.fetchone()
                
                if not active:
                    import config
                    if getattr(config, 'PARKING_WARN_NO_EXIT_ENTRY', True):
                        print(f"[DB-WARNING] Salida sin entrada registrada: {plate}")
                    return None
                
                # Calcular duracion
                exit_time = datetime.now()
                entry_time = datetime.fromisoformat(active['entry_time'])
                duration = exit_time - entry_time
                duration_minutes = int(duration.total_seconds() / 60)
                
                # Insertar en historial
                cursor.execute('''
                    INSERT INTO parking_history (plate, brand, color, entry_time, exit_time, duration_minutes, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    active['plate'],
                    active['brand'],
                    active['color'],
                    active['entry_time'],
                    exit_time,
                    duration_minutes,
                    'live_camera'
                ))
                
                history_id = cursor.lastrowid
                
                # Eliminar de active_vehicles
                cursor.execute('DELETE FROM active_vehicles WHERE plate = ?', (plate,))
                
                # Actualizar registro
                self._update_vehicle_registry_on_exit(plate, exit_time, duration_minutes)
                
                session = {
                    'id': history_id,
                    'plate': active['plate'],
                    'brand': active['brand'],
                    'color': active['color'],
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'duration_minutes': duration_minutes
                }
                
                print(f"[DB-EXIT] Salida registrada - Duracion: {duration_minutes} min")
                return session
                
        except Exception as e:
            print(f"[DB-ERROR] Error al registrar salida: {str(e)}")
            return None
    
    def get_active_vehicles(self):
        """
        Obtiene lista de vehiculos actualmente dentro del estacionamiento.
        
        Returns:
            list: Lista de vehiculos activos
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM active_vehicles ORDER BY entry_time DESC')
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[DB-ERROR] Error consultando vehiculos activos: {str(e)}")
            return []
    
    def find_active_by_plate(self, plate):
        """
        Busca un vehiculo en active_vehicles por placa.
        
        Args:
            plate (str): Numero de placa
            
        Returns:
            dict: Informacion del vehiculo o None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM active_vehicles WHERE plate = ?', (plate,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[DB-ERROR] Error buscando vehiculo activo: {str(e)}")
            return None
    
    def update_active_track_id(self, plate, new_track_id):
        """
        Actualiza el track_id de un vehiculo activo.
        Util cuando el tracker reinicia y asigna nuevo ID al mismo vehiculo.
        
        Args:
            plate (str): Numero de placa
            new_track_id (int): Nuevo ID del tracker
        """
        print(f"[DB-UPDATE] Actualizando track_id de {plate} a {new_track_id}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE active_vehicles 
                    SET track_id = ?
                    WHERE plate = ?
                ''', (new_track_id, plate))
                
                print(f"[DB-UPDATE] Track ID actualizado")
        except Exception as e:
            print(f"[DB-ERROR] Error actualizando track_id: {str(e)}")
    
    # ==================== HISTORICO (parking_history) ====================
    
    def get_history_by_date(self, date):
        """
        Obtiene sesiones de estacionamiento de una fecha especifica.
        
        Args:
            date (datetime.date): Fecha a consultar
            
        Returns:
            list: Lista de sesiones
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                date_str = date.strftime('%Y-%m-%d')
                
                cursor.execute('''
                    SELECT * FROM parking_history 
                    WHERE DATE(entry_time) = ?
                    ORDER BY entry_time DESC
                ''', (date_str,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[DB-ERROR] Error consultando historial: {str(e)}")
            return []
    
    def get_history_by_plate(self, plate):
        """
        Obtiene historial de sesiones de un vehiculo especifico.
        
        Args:
            plate (str): Numero de placa
            
        Returns:
            list: Lista de sesiones del vehiculo
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM parking_history 
                    WHERE plate = ?
                    ORDER BY entry_time DESC
                ''', (plate,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[DB-ERROR] Error consultando historial de placa: {str(e)}")
            return []
    
    # ==================== REGISTRO (vehicle_registry) ====================
    
    def _update_vehicle_registry(self, plate, brand, color, timestamp):
        """
        Actualiza o crea entrada en vehicle_registry al detectar entrada.
        
        Args:
            plate (str): Numero de placa
            brand (str): Marca
            color (str): Color
            timestamp (datetime): Timestamp de la entrada
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Buscar si existe
                cursor.execute('SELECT * FROM vehicle_registry WHERE plate = ?', (plate,))
                existing = cursor.fetchone()
                
                if existing:
                    # Actualizar
                    cursor.execute('''
                        UPDATE vehicle_registry
                        SET last_seen = ?,
                            total_visits = total_visits + 1
                        WHERE plate = ?
                    ''', (timestamp, plate))
                else:
                    # Crear nuevo
                    cursor.execute('''
                        INSERT INTO vehicle_registry (plate, brand, color, first_seen, last_seen, total_visits)
                        VALUES (?, ?, ?, ?, ?, 1)
                    ''', (plate, brand, color, timestamp, timestamp))
                
        except Exception as e:
            print(f"[DB-ERROR] Error actualizando registro: {str(e)}")
    
    def _update_vehicle_registry_on_exit(self, plate, timestamp, duration_minutes):
        """
        Actualiza vehicle_registry al registrar salida (actualiza promedio de duracion).
        
        Args:
            plate (str): Numero de placa
            timestamp (datetime): Timestamp de salida
            duration_minutes (int): Duracion de esta sesion
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT total_visits, avg_duration_minutes FROM vehicle_registry WHERE plate = ?', (plate,))
                registry = cursor.fetchone()
                
                if registry:
                    # Calcular nuevo promedio
                    total_visits = registry['total_visits']
                    old_avg = registry['avg_duration_minutes'] or 0
                    
                    new_avg = ((old_avg * (total_visits - 1)) + duration_minutes) / total_visits
                    new_avg = int(new_avg)
                    
                    cursor.execute('''
                        UPDATE vehicle_registry
                        SET last_seen = ?,
                            avg_duration_minutes = ?
                        WHERE plate = ?
                    ''', (timestamp, new_avg, plate))
                
        except Exception as e:
            print(f"[DB-ERROR] Error actualizando registro en salida: {str(e)}")
    
    def get_vehicle_stats(self, plate):
        """
        Obtiene estadisticas de un vehiculo del registro.
        
        Args:
            plate (str): Numero de placa
            
        Returns:
            dict: Estadisticas del vehiculo o None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM vehicle_registry WHERE plate = ?', (plate,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[DB-ERROR] Error consultando estadisticas: {str(e)}")
            return None
    
    def get_frequent_visitors(self, limit=10):
        """
        Obtiene vehiculos mas frecuentes (top visitantes).
        
        Args:
            limit (int): Numero de resultados
            
        Returns:
            list: Lista de vehiculos ordenados por total_visits
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM vehicle_registry 
                    ORDER BY total_visits DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[DB-ERROR] Error consultando visitantes frecuentes: {str(e)}")
            return []
    
    def get_today_stats(self):
        """
        Obtiene estadisticas del dia actual.
        
        Returns:
            dict: {
                'inside': int,              # Vehiculos dentro ahora
                'entries_today': int,       # Entradas del dia
                'exits_today': int,         # Salidas del dia
                'avg_duration': int,        # Duracion promedio (minutos)
                'last_entry': dict or None  # Ultima entrada
            }
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Vehiculos dentro ahora
                cursor.execute('SELECT COUNT(*) FROM active_vehicles')
                inside = cursor.fetchone()[0]
                
                # Entradas del dia (desde parking_history)
                cursor.execute('''
                    SELECT COUNT(*) FROM parking_history
                    WHERE DATE(entry_time) = DATE('now')
                ''')
                entries_today = cursor.fetchone()[0]
                
                # Salidas del dia
                cursor.execute('''
                    SELECT COUNT(*) FROM parking_history
                    WHERE DATE(exit_time) = DATE('now')
                ''')
                exits_today = cursor.fetchone()[0]
                
                # Duracion promedio del dia
                cursor.execute('''
                    SELECT AVG(duration_minutes) FROM parking_history
                    WHERE DATE(entry_time) = DATE('now')
                ''')
                avg_duration = cursor.fetchone()[0]
                avg_duration = int(avg_duration) if avg_duration else 0
                
                # Ultima entrada (de active_vehicles)
                cursor.execute('''
                    SELECT * FROM active_vehicles
                    ORDER BY entry_time DESC
                    LIMIT 1
                ''')
                last_entry_row = cursor.fetchone()
                last_entry = dict(last_entry_row) if last_entry_row else None
                
                return {
                    'inside': inside,
                    'entries_today': entries_today,
                    'exits_today': exits_today,
                    'avg_duration': avg_duration,
                    'last_entry': last_entry
                }
                
        except Exception as e:
            print(f"[DB-ERROR] Error consultando estadisticas del dia: {str(e)}")
            return {
                'inside': 0,
                'entries_today': 0,
                'exits_today': 0,
                'avg_duration': 0,
                'last_entry': None
            }