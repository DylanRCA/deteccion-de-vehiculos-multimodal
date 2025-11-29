# Detector de Vehiculos Multimodal - Documentacion del Proyecto

## Descripcion General
Sistema completo de deteccion y gestion de vehiculos con tracking multi-vehiculo, base de datos, deteccion de eventos entrada/salida, reconocimiento de placas y panel de estadisticas en tiempo real.

## Estado Actual del Proyecto

### Fase 1 - Deteccion Basica - COMPLETADA
- Deteccion de vehiculos (YOLOv8)
- Reconocimiento de placas (YOLO + OCR)
- Clasificacion de marca (YOLO logos)
- Clasificacion de color (heuristica HSV)
- Interfaz grafica CustomTkinter

### Fase 2A - Sistema de Tracking - COMPLETADA
- Implementacion ByteTrack desde cero
- IDs persistentes entre frames
- Manejo de oclusiones (hasta 45 frames)
- Reset automatico entre videos
- Optimizacion de performance (10x mas rapido)

### Fase 2B - Persistencia y Eventos - COMPLETADA
- Base de datos SQLite con 3 tablas
- Detector de eventos entrada/salida
- Sistema de linea virtual configurable
- Logging comprensivo en todos los modulos
- Manejo robusto de errores
- Re-identificacion por placa
- IDs temporales para vehiculos sin placa

### Fase 3 - UI y Estadisticas - COMPLETADA
- Panel de estadisticas en tiempo real (lado derecho UI)
- Estadisticas separadas para video (temporal) y camara (BD)
- Ultima entrada y ultima salida
- Reproduccion de video con estadisticas en tiempo real
- Boton "Reproducir Video" para re-ver videos procesados
- Consultas optimizadas de BD

## Tecnologias Utilizadas

### Modelos de IA
- **YOLOv8** (Ultralytics) - Deteccion de vehiculos, placas y logos
- **EasyOCR** - Lectura de texto en placas
- **ByteTrack** - Tracking multi-objeto (implementacion propia)

### Procesamiento
- **OpenCV** - Procesamiento de imagenes y video
- **NumPy** - Operaciones numericas
- **Filterpy** - Filtro de Kalman para tracking
- **LAP** - Algoritmo hungaro para asociacion

### Persistencia
- **SQLite3** - Base de datos local
- **Python sqlite3** - Interfaz de BD

### Interfaz
- **CustomTkinter** - UI moderna
- **PIL/Pillow** - Manejo de imagenes

## Arquitectura del Sistema

### Flujo Principal

```
1. Usuario carga imagen/video/camara
   |
2. Pipeline resetea (si es nuevo video)
   |
3. DETECCION -> CarDetector (YOLO)
   |
4. TRACKING -> VehicleTracker (ByteTrack)
   |
5. CLASIFICACION (solo vehiculos nuevos)
   |- PlateRecognizer (YOLO + OCR)
   |- VehicleClassifier (Logo YOLO + Color HSV)
   +- Cache en known_vehicles
   |
6. EVENTOS (cada frame)
   |- EventDetector.detect_events()
   |- Detectar cruces de linea virtual
   +- Clasificar entry/exit
   |
7. ESTADISTICAS
   |- Video: _video_stats (memoria)
   +- Camara: BD (get_today_stats)
   |
8. VISUALIZACION
   |- Dibujar bounding boxes
   |- Mostrar IDs de tracking
   |- Dibujar linea virtual
   +- Renderizar en UI
   |
9. PANEL ESTADISTICAS
   |- Dentro/Entradas/Salidas
   |- Ultima entrada/salida
   +- Duracion promedio (solo camara)
```

### Estructura de Directorios

```
detector_vehiculos/
+-- data/                    # Videos e imagenes de prueba
+-- models/                  # Modelos YOLO (.pt)
|   +-- car_detector.pt         # Deteccion vehiculos
|   +-- plate_detector.pt       # Deteccion placas
|   +-- brand_detector.pt       # Deteccion logos (14 marcas)
+-- database/                # Base de datos SQLite
|   +-- estacionamiento.db      # BD principal
+-- src/                     # Codigo fuente
|   +-- __init__.py
|   +-- car_detector.py         # Detector YOLO vehiculos
|   +-- plate_recognizer.py     # Detector placas + OCR
|   +-- classifier.py           # Clasificador marca/color
|   +-- tracker.py              # Sistema ByteTrack
|   +-- database.py             # Gestor SQLite
|   +-- event_detector.py       # Detector entrada/salida
|   +-- pipeline.py             # Orquestador principal
|   +-- DOCUMENTATION.md        # Doc del directorio src/
+-- main.py                  # Aplicacion GUI
+-- config.py                # Configuracion centralizada
+-- requirements.txt         # Dependencias
+-- DOCUMENTATION.md         # Este archivo
+-- PLANNING.md              # Plan de desarrollo
+-- README.md                # Readme del proyecto
```

## Componentes Principales

### 1. VehicleDetectionPipeline (pipeline.py)
Orquestador principal del sistema.

**Modos de operacion:**
- `video`: Estadisticas temporales en memoria, no persiste en BD
- `camera`: Estadisticas en BD, persiste eventos

**Metodos principales:**
```python
__init__(car_min_confidence, enable_database, enable_events, mode)
reset()                    # Reset para nuevo video
process_image(image)       # Procesar imagen unica
process_video_frame(frame) # Procesar frame de video
get_video_stats()          # Obtener stats temporales (modo video)
```

**Estadisticas de video (_video_stats):**
```python
{
    'inside': int,       # Vehiculos dentro (contador)
    'entries': int,      # Total entradas
    'exits': int,        # Total salidas
    'last_entry': dict,  # {plate, timestamp}
    'last_exit': dict    # {plate, timestamp}
}
```

### 2. DatabaseManager (database.py)
Gestor de base de datos SQLite.

**Esquema (3 tablas):**
```sql
-- Vehiculos dentro AHORA
active_vehicles (id, plate, track_id, brand, color, entry_time)

-- Sesiones completadas
parking_history (id, plate, brand, color, entry_time, exit_time, duration_minutes, source)

-- Catalogo de vehiculos
vehicle_registry (plate PK, brand, color, first_seen, last_seen, total_visits, avg_duration_minutes)
```

**Metodo get_today_stats():**
```python
{
    'inside': int,           # COUNT(active_vehicles)
    'entries_today': int,    # active_vehicles(hoy) + parking_history(hoy)
    'exits_today': int,      # parking_history(hoy)
    'avg_duration': int,     # AVG(duration) del dia
    'last_entry': dict,      # Ultimo en active_vehicles
    'last_exit': dict        # Ultimo en parking_history(hoy)
}
```

### 3. EventDetector (event_detector.py)
Detecta eventos de entrada/salida.

**Algoritmo:**
1. Calcular centroide Y de cada track
2. Mantener historial de posiciones por track_id
3. Detectar cruces de linea virtual
4. Clasificar direccion (entry/exit)
5. Evitar duplicados

**Configuracion:**
- `line_position`: Posicion Y de la linea
- `entry_direction`: 'down' o 'up'

### 4. VehicleTracker (tracker.py)
Sistema ByteTrack para tracking multi-vehiculo.

**Parametros (config.py):**
- `TRACKING_MAX_AGE = 45`: Frames sin deteccion antes de eliminar
- `TRACKING_MIN_HITS = 5`: Detecciones para confirmar track
- `TRACKING_IOU_THRESHOLD = 0.25`: Umbral de matching

### 5. VehicleDetectorApp (main.py)
Interfaz grafica de usuario.

**Layout (3 columnas):**
```
+----------+------------+-------------+
| Controles|   Video    | Estadisticas|
|  250px   | Expandible |    200px    |
+----------+------------+-------------+
```

**Funcionalidades:**
- Subir imagen/video
- Activar camara
- Reproducir video procesado
- Panel estadisticas en tiempo real
- Boton actualizar manual

**Reproduccion de video:**
- Guarda frames procesados en `processed_frames`
- Guarda stats por frame en `video_stats_history`
- Reproduce con estadisticas sincronizadas
- Boton "Reproducir Video" para re-ver

## Configuracion (config.py)

### Tracking
```python
TRACKING_MAX_AGE = 45
TRACKING_MIN_HITS = 5
TRACKING_IOU_THRESHOLD = 0.25
```

### Deteccion
```python
CAR_MIN_CONFIDENCE = 0.5
```

### Eventos
```python
EVENT_LINE_POSITION = 230
EVENT_ENTRY_DIRECTION = 'down'
EVENT_MIN_CONFIDENCE = 0.6
EVENT_LINE_TOLERANCE = 15
```

### Base de Datos
```python
DB_PATH = 'database/estacionamiento.db'
TEMP_PLATE_PREFIX = 'TEMP_'
```

### Performance
```python
REDETECTION_INTERVAL_CAMERA = 30
REDETECTION_INTERVAL_VIDEO = 5
MAX_FRAMES_WITHOUT_DETECTION = 3
```

## Diferencias Video vs Camara

| Aspecto | Video | Camara |
|---------|-------|--------|
| Estadisticas | Memoria (_video_stats) | BD (get_today_stats) |
| Persistencia | No | Si |
| Entradas | Contador simple | active + history |
| Duracion prom | N/A | Calculado de BD |
| Reproduccion | Si (replay) | No |

## Dependencias

```
opencv-python-headless
customtkinter
ultralytics
easyocr
torch
torchvision
Pillow
lap>=0.4.0
filterpy>=1.4.5
scipy>=1.7.0
```

## Uso

### Iniciar Aplicacion
```bash
python main.py
```

### Procesar Video
1. Click "Subir Video"
2. Esperar procesamiento (barra de progreso)
3. Video se reproduce con estadisticas
4. Click "Reproducir Video" para re-ver

### Usar Camara
1. Click "Activar Camara"
2. Estadisticas se actualizan cada 30 frames
3. Datos persisten en BD
4. Click "Detener Camara" para parar

## Limitaciones

- Placas: Detecta placas genericas, no optimizado para formato especifico
- Marcas: 14 marcas soportadas
- Colores: 7 colores basicos
- Tracking: Puede perder en oclusiones >1.5seg
- Stats video: No incluye duracion promedio