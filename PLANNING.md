# Plan Detallado - FASE 2A: Fundamentos para Sistema de Estacionamiento

## Visión General
Transformar el detector de vehículos actual en un sistema con capacidad de tracking, persistencia de datos y detección de eventos de entrada/salida.

*Esta planeacion esta sujeto a cambios de ser necesario*
---

## 1. SISTEMA DE TRACKING

### 1.1 Implementación ByteTrack
**Objetivo**: Asignar IDs únicos y persistentes a vehículos entre frames

**Archivos a crear**:
```
src/tracker.py          # Clase VehicleTracker
```

**Funcionalidades**:
- Mantener ID consistente del vehículo mientras esté visible
- Asociar detecciones entre frames consecutivos
- Manejar oclusiones temporales (vehículo oculto brevemente)
- Re-identificación cuando vehículo reaparece

**Dependencias nuevas**:
```
# requirements.txt (agregar)
lap>=0.4.0              # Para algoritmo de asignación húngara
filterpy>=1.4.5         # Para filtro de Kalman
```

**API propuesta**:
```python
class VehicleTracker:
    def update(self, detections: list) -> list
        """
        Args:
            detections: Lista de detecciones del frame actual
        Returns:
            Lista de tracks con IDs persistentes
        """
```

---

## 2. BASE DE DATOS

### 2.1 Modelo de Datos
**Objetivo**: Persistir eventos y detecciones para análisis histórico

**Archivo a crear**:
```
src/database.py         # Clase DatabaseManager
```

**Esquema de tablas**:

```sql
-- Tabla de vehículos registrados
CREATE TABLE vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER UNIQUE,          -- ID del tracker
    plate_number TEXT,                -- Placa (puede ser NULL)
    brand TEXT,
    color TEXT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    status TEXT                       -- 'inside', 'outside'
);

-- Tabla de eventos
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER,
    event_type TEXT,                  -- 'entry', 'exit', 'detection'
    timestamp TIMESTAMP,
    camera_id TEXT,                   -- Para futuro multi-cámara
    confidence REAL,
    plate_confidence REAL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

-- Tabla de detecciones (snapshot de cada detección)
CREATE TABLE detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER,
    timestamp TIMESTAMP,
    bbox_x1 INTEGER,
    bbox_y1 INTEGER,
    bbox_x2 INTEGER,
    bbox_y2 INTEGER,
    frame_number INTEGER,
    image_path TEXT,                  -- Path a snapshot guardado
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

-- Índices para consultas rápidas
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_vehicle ON events(vehicle_id);
CREATE INDEX idx_vehicles_status ON vehicles(status);
```

**API propuesta**:
```python
class DatabaseManager:
    def register_vehicle(self, track_id, plate, brand, color) -> int
    def log_event(self, vehicle_id, event_type, timestamp, camera_id)
    def log_detection(self, vehicle_id, bbox, frame_num, image_path=None)
    def update_vehicle_status(self, vehicle_id, status)
    def get_vehicle_by_track_id(self, track_id) -> dict
    def get_vehicles_inside(self) -> list
    def get_events_by_date(self, date) -> list
```

---

## 3. SISTEMA DE EVENTOS (ENTRADA/SALIDA)

### 3.1 Detector de Eventos
**Objetivo**: Determinar si un vehículo está entrando o saliendo

**Archivo a crear**:
```
src/event_detector.py   # Clase EventDetector
```

**Enfoque - Línea Virtual**:
```
    ENTRADA ←               → SALIDA
         ↑                      ↑
    =================================== Línea virtual
         ↓                      ↓
    Camera View
```

**Lógica**:
1. Configurar línea virtual en la imagen (ej: Y=400)
2. Detectar cruces de línea usando tracking
3. Determinar dirección por movimiento previo del centroide

**Estados de vehículo**:
- `approaching_line`: Acercándose a la línea
- `crossed_entry`: Cruzó hacia entrada
- `crossed_exit`: Cruzó hacia salida
- `inside`: Dentro del estacionamiento
- `outside`: Fuera del estacionamiento

**API propuesta**:
```python
class EventDetector:
    def __init__(self, line_position, entry_direction='down')
    def configure_line(self, y_position: int, entry_direction: str)
    def detect_events(self, tracks: list) -> list
        """
        Returns: [
            {'track_id': 5, 'event': 'entry', 'timestamp': ...},
            {'track_id': 8, 'event': 'exit', 'timestamp': ...}
        ]
        """
```

---

## 4. INTEGRACIÓN EN PIPELINE

### 4.1 Modificar `pipeline.py`
**Cambios necesarios**:

```python
class VehicleDetectionPipeline:
    def __init__(self, ...):
        # Existentes
        self.car_detector = CarDetector()
        self.plate_recognizer = PlateRecognizer()
        self.vehicle_classifier = VehicleClassifier()
        
        # NUEVOS
        self.tracker = VehicleTracker()
        self.db = DatabaseManager('estacionamiento.db')
        self.event_detector = EventDetector(line_position=400)
        
        # Estado
        self.frame_count = 0
        self.known_vehicles = {}  # track_id -> vehicle_info
    
    def process_video_frame(self, frame):
        """
        Flujo modificado:
        1. Detectar vehículos (existente)
        2. [NUEVO] Tracking - asignar IDs
        3. Clasificar placas/color/marca (existente)
        4. [NUEVO] Detectar eventos (entrada/salida)
        5. [NUEVO] Actualizar base de datos
        6. Dibujar resultados (modificado)
        """
```

**Flujo detallado**:
```python
def process_video_frame(self, frame):
    self.frame_count += 1
    
    # 1. Detectar vehículos (sin cambios)
    detections = self.car_detector.detect_vehicles(frame)
    
    # 2. NUEVO: Tracking
    tracks = self.tracker.update(detections)
    
    # 3. Para cada track, clasificar si es nuevo
    for track in tracks:
        if track['id'] not in self.known_vehicles:
            # Vehículo nuevo, clasificar
            vehicle_crop = frame[track['bbox']]
            plate_info = self.plate_recognizer.recognize_plate(vehicle_crop)
            classification = self.vehicle_classifier.classify(vehicle_crop)
            
            # Registrar en DB
            vehicle_id = self.db.register_vehicle(
                track_id=track['id'],
                plate=plate_info['text'],
                brand=classification['brand'],
                color=classification['color']
            )
            
            self.known_vehicles[track['id']] = {
                'db_id': vehicle_id,
                'plate': plate_info['text'],
                'brand': classification['brand'],
                'color': classification['color']
            }
        
        # Log detección
        self.db.log_detection(
            vehicle_id=self.known_vehicles[track['id']]['db_id'],
            bbox=track['bbox'],
            frame_num=self.frame_count
        )
    
    # 4. NUEVO: Detectar eventos
    events = self.event_detector.detect_events(tracks)
    
    # 5. NUEVO: Procesar eventos
    for event in events:
        vehicle_info = self.known_vehicles.get(event['track_id'])
        if vehicle_info:
            self.db.log_event(
                vehicle_id=vehicle_info['db_id'],
                event_type=event['event'],
                timestamp=event['timestamp'],
                camera_id='cam_01'
            )
            
            # Actualizar estado
            new_status = 'inside' if event['event'] == 'entry' else 'outside'
            self.db.update_vehicle_status(vehicle_info['db_id'], new_status)
    
    # 6. Dibujar (modificado para mostrar IDs de tracking)
    annotated = self._draw_results_with_tracking(frame, tracks, events)
    
    return {
        'annotated_image': annotated,
        'tracks': tracks,
        'events': events
    }
```

---

## 5. MODIFICACIONES EN UI (main.py)

### 5.1 Panel de Estadísticas en Tiempo Real
**Agregar**:
```python
# En _create_widgets():
stats_frame = ctk.CTkFrame(control_frame)
stats_frame.pack(pady=10, padx=20, fill="x")

self.stats_labels = {
    'inside': ctk.CTkLabel(stats_frame, text="Dentro: 0"),
    'total_entries': ctk.CTkLabel(stats_frame, text="Entradas hoy: 0"),
    'total_exits': ctk.CTkLabel(stats_frame, text="Salidas hoy: 0")
}
```

### 5.2 Configuración de Línea Virtual
**Nueva ventana de configuración**:
```python
def _configure_line(self):
    """
    Ventana para configurar línea de detección de entrada/salida
    Usuario hace clic en la imagen para posicionar la línea
    """
```

### 5.3 Visor de Historial
**Nuevo botón**:
```python
self.btn_history = ctk.CTkButton(
    control_frame,
    text="Ver Historial",
    command=self._show_history
)
```

---

## 6. ESTRUCTURA DE ARCHIVOS ACTUALIZADA

```
detector_vehiculos/
├── data/
├── models/
├── database/                    # NUEVO
│   └── estacionamiento.db      # Base de datos SQLite
├── snapshots/                   # NUEVO - capturas de vehículos
│   └── YYYY-MM-DD/
│       └── vehicle_X_timestamp.jpg
├── src/
│   ├── __init__.py
│   ├── car_detector.py
│   ├── plate_recognizer.py
│   ├── classifier.py
│   ├── tracker.py              # NUEVO
│   ├── database.py             # NUEVO
│   ├── event_detector.py       # NUEVO
│   └── pipeline.py             # MODIFICADO
├── main.py                      # MODIFICADO
├── config.py                    # NUEVO - configuraciones
└── requirements.txt             # ACTUALIZADO
```

---

## 7. ORDEN DE IMPLEMENTACIÓN (DO)

### Sprint 1: Tracking (3-4 días)
1. Investigar e instalar dependencias (lap, filterpy)
2. Implementar `VehicleTracker` con ByteTrack
3. Integrar en `pipeline.py` (solo tracking, sin eventos)
4. Probar estabilidad de IDs en videos

### Sprint 2: Base de Datos (2-3 días)
1. Crear esquema SQL
2. Implementar `DatabaseManager`
3. Escribir tests básicos de DB
4. Integrar registro de vehículos en pipeline

### Sprint 3: Eventos (3-4 días)
1. Implementar `EventDetector`
2. Crear UI para configurar línea virtual
3. Integrar detección de eventos en pipeline
4. Testing de entrada/salida

### Sprint 4: UI y Pulido (2-3 días)
1. Panel de estadísticas en tiempo real
2. Visor de historial
3. Guardado de snapshots
4. Documentación

**Total estimado: 10-14 días de desarrollo**

---

## 8. CONSIDERACIONES TÉCNICAS

### Performance
- Tracking agrega ~10-15ms por frame
- Base de datos: usar WAL mode para escrituras concurrentes
- Snapshots: guardar solo en eventos, no cada frame

### Robustez
- Manejar pérdida temporal de tracking (oclusiones)
- Validar placas antes de registrar eventos
- Sistema de confianza para eventos (no registrar si confianza < 0.5)

### Configuración
Crear `config.py`:
```python
# Tracking
TRACKING_MAX_AGE = 30           # Frames sin detección antes de eliminar track
TRACKING_MIN_HITS = 3           # Detecciones necesarias para confirmar track

# Eventos
EVENT_LINE_POSITION = 400       # Posición Y de línea virtual
EVENT_MIN_CONFIDENCE = 0.5      # Confianza mínima para registrar evento

# Database
DB_PATH = 'database/estacionamiento.db'
SNAPSHOT_DIR = 'snapshots/'

# Camera
CAMERA_ID = 'cam_entrance'
```

---

## 9. CRITERIOS DE ÉXITO

La Fase 2A estará completa cuando:

✅ Vehículos mantengan IDs consistentes entre frames
✅ Sistema detecte entradas y salidas correctamente
✅ Base de datos registre todos los eventos
✅ UI muestre estadísticas en tiempo real
✅ Se puedan consultar eventos históricos
✅ Sistema funcione de manera estable por >1 hora continua

