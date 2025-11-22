# Detector de Vehiculos Multimodal - Documentacion del Proyecto

## Descripcion General
Sistema completo de deteccion y gestion de vehiculos con tracking multi-vehiculo, base de datos, deteccion de eventos entrada/salida y reconocimiento de placas para Peru.

## Estado Actual del Proyecto

### Fase 1 - Deteccion Basica ✅ COMPLETADA
- ✅ Deteccion de vehiculos (YOLOv8)
- ✅ Reconocimiento de placas (YOLO + OCR)
- ✅ Clasificacion de marca (YOLO logos)
- ✅ Clasificacion de color (heuristica HSV)
- ✅ Interfaz grafica CustomTkinter

### Fase 2A - Sistema de Tracking ✅ COMPLETADA
- ✅ Implementacion ByteTrack desde cero
- ✅ IDs persistentes entre frames
- ✅ Manejo de oclusiones (hasta 45 frames)
- ✅ Reset automatico entre videos
- ✅ Optimizacion de performance (10x mas rapido)

### Fase 2B - Persistencia y Eventos ✅ COMPLETADA
- ✅ Base de datos SQLite con 3 tablas
- ✅ Detector de eventos entrada/salida
- ✅ Sistema de linea virtual configurable
- ✅ Logging comprensivo en todos los modulos
- ✅ Manejo robusto de errores

### Fase 2C - Optimizaciones ✅ COMPLETADA
- ✅ Reduccion de logging BD (90% menos writes)
- ✅ Parametros de tracking optimizados
- ✅ Configuracion centralizada (config.py)
- ✅ Validaciones de bbox robustas
- ✅ Sistema de reset entre videos

### Fase 3 - Futuro ⏳
- ⏳ Multi-camara
- ⏳ Dashboard web
- ⏳ Panel de estadisticas en UI
- ⏳ Visor de historial
- ⏳ Reportes exportables

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
   ↓
2. Pipeline resetea (si es nuevo video)
   ↓
3. DETECCION → CarDetector (YOLO)
   ↓
4. TRACKING → VehicleTracker (ByteTrack)
   ↓
5. CLASIFICACION (solo vehiculos nuevos)
   ├─ PlateRecognizer (YOLO + OCR)
   ├─ VehicleClassifier (Logo YOLO + Color HSV)
   └─ Cache en known_vehicles
   ↓
6. BASE DE DATOS (cada 10 frames)
   ├─ Registrar vehiculo nuevo
   └─ Log deteccion
   ↓
7. EVENTOS (cada frame)
   ├─ EventDetector.detect_events()
   ├─ Log evento en BD
   └─ Actualizar estado vehiculo
   ↓
8. VISUALIZACION
   ├─ Dibujar bounding boxes
   ├─ Mostrar IDs de tracking
   ├─ Dibujar linea virtual
   └─ Renderizar en UI
```

### Estructura de Directorios

```
detector_vehiculos/
├── data/                    # Videos e imagenes de prueba
├── models/                  # Modelos YOLO (.pt)
│   ├── car_detector.pt         # Deteccion vehiculos
│   ├── plate_detector.pt       # Deteccion placas
│   └── brand_detector.pt       # Deteccion logos (14 marcas)
├── database/                # Base de datos SQLite
│   └── estacionamiento.db      # BD principal
├── snapshots/               # Capturas de vehiculos (futuro)
├── src/                     # Codigo fuente
│   ├── __init__.py
│   ├── car_detector.py         # Detector YOLO vehiculos
│   ├── plate_recognizer.py     # Detector placas + OCR
│   ├── classifier.py           # Clasificador marca/color
│   ├── tracker.py              # Sistema ByteTrack
│   ├── database.py             # Gestor SQLite
│   ├── event_detector.py       # Detector entrada/salida
│   ├── pipeline.py             # Orquestador principal
│   ├── DOCUMENTATION.md        # Doc del directorio src/
│   └── TRACKER_DOCS.md         # Doc especifica del tracker
├── main.py                  # Aplicacion GUI
├── config.py                # Configuracion centralizada
├── requirements.txt         # Dependencias
├── DOCUMENTATION.md         # Este archivo
├── PLANNING.md              # Plan de desarrollo
└── README.md                # Readme del proyecto
```

## Componentes Principales

### 1. CarDetector (car_detector.py)
**Proposito**: Detectar vehiculos en imagen/video

**Tecnologia**: YOLOv8n custom-trained

**API**:
```python
detect_vehicles(image) -> List[dict]
# Retorna: [{'bbox': [x1,y1,x2,y2], 'confidence': float, 'class': str}]
```

**Configuracion**:
- `CAR_MIN_CONFIDENCE = 0.5` (config.py)
- Clases: car, motorcycle, bus, truck

### 2. PlateRecognizer (plate_recognizer.py)
**Proposito**: Detectar y leer placas vehiculares

**Tecnologia**: YOLO (deteccion) + EasyOCR (lectura)

**API**:
```python
recognize_plate(vehicle_image) -> dict
# Retorna: {'text': str, 'bbox': [x1,y1,x2,y2] or None}
```

**Estrategia**:
1. Detectar region con YOLO (si disponible)
2. Fallback a heuristica de contornos
3. OCR con 4 tecnicas (Otsu, Adaptive, etc.)
4. Validacion de formato

**Configuracion**:
- `min_confidence = 0.2` (OCR)
- `min_plate_length = 4`
- `max_plate_length = 12`

### 3. VehicleClassifier (classifier.py)
**Proposito**: Clasificar marca y color del vehiculo

**Tecnologia**: 
- Marca: YOLO de logos (14 marcas)
- Color: Heuristica HSV

**API**:
```python
classify(vehicle_image) -> dict
# Retorna: {
#   'brand': str,
#   'brand_bbox': [x1,y1,x2,y2] or None,
#   'color': str
# }
```

**Marcas soportadas** (14):
Audi, BMW, Chevrolet, Ford, Honda, Hyundai, KIA, Mazda, Mercedes, Mitsubishi, Nissan, Suzuki, Toyota, Volkswagen

**Colores soportados** (7):
BLANCO, NEGRO, GRIS, ROJO, AZUL, VERDE, AMARILLO

### 4. VehicleTracker (tracker.py)
**Proposito**: Mantener IDs persistentes entre frames

**Tecnologia**: ByteTrack (implementacion propia)

**Algoritmo**:
1. Predecir posicion siguiente (Kalman - implementado simple)
2. Calcular matriz IoU entre detecciones y tracks
3. Asociar con algoritmo hungaro (greedy)
4. Actualizar tracks matched
5. Crear nuevos tracks
6. Eliminar tracks antiguos (age > max_age)

**API**:
```python
update(detections) -> List[dict]
# Retorna: [{
#   'id': int,
#   'bbox': [x1,y1,x2,y2],
#   'hits': int,
#   'age': int,
#   'time_since_update': int
# }]
```

**Configuracion**:
- `TRACKING_MAX_AGE = 45` - Frames sin deteccion antes de eliminar
- `TRACKING_MIN_HITS = 5` - Detecciones para confirmar track
- `TRACKING_IOU_THRESHOLD = 0.25` - Umbral de matching

**Caracteristicas**:
- IDs empiezan en 1
- Reset automatico entre videos
- Maneja oclusiones hasta 1.5 segundos
- Sin modelos preentrenados (solo matematicas)

### 5. DatabaseManager (database.py)
**Proposito**: Persistir vehiculos, eventos y detecciones

**Tecnologia**: SQLite3 con WAL mode

**Esquema**:
- `vehicles` - Vehiculos registrados
- `events` - Eventos entrada/salida
- `detections` - Historial de detecciones

**API**:
```python
register_vehicle(track_id, plate, brand, color) -> int
log_event(vehicle_id, event_type, timestamp, camera_id)
log_detection(vehicle_id, bbox, frame_num)
update_vehicle_status(vehicle_id, status)
get_vehicle_by_track_id(track_id) -> dict
get_vehicles_inside() -> List[dict]
get_events_by_date(date) -> List[dict]
```

**Caracteristicas**:
- Logging comprensivo
- Manejo de errores robusto
- WAL mode para concurrencia
- Indices optimizados

### 6. EventDetector (event_detector.py)
**Proposito**: Detectar eventos de entrada/salida

**Tecnologia**: Linea virtual + analisis de centroide

**Algoritmo**:
1. Calcular centroide Y de cada track
2. Detectar cruces de linea virtual
3. Determinar direccion por historial
4. Clasificar como entry/exit
5. Evitar eventos duplicados

**API**:
```python
configure_line(y_position, entry_direction)
detect_events(tracks) -> List[dict]
# Retorna: [{
#   'track_id': int,
#   'event': 'entry' or 'exit',
#   'timestamp': datetime
# }]

draw_line(image) -> image  # Para visualizacion
reset_history()  # Limpiar historial
```

**Configuracion**:
- `EVENT_LINE_POSITION = 400` - Posicion Y de linea
- `EVENT_ENTRY_DIRECTION = 'down'` - Direccion de entrada
- `EVENT_MIN_CONFIDENCE = 0.6` - Confianza minima
- `EVENT_LINE_TOLERANCE = 15` - Tolerancia en pixeles

**Estados de vehiculo**:
- `approaching_line` - Acercandose
- `crossed_entry` - Cruzo hacia entrada
- `crossed_exit` - Cruzo hacia salida
- `inside` - Dentro del estacionamiento
- `outside` - Fuera del estacionamiento

### 7. VehicleDetectionPipeline (pipeline.py)
**Proposito**: Orquestar todos los componentes

**Caracteristicas**:
- Inicializacion con flags de activacion
- Cache de vehiculos conocidos
- Logging condicional basado en config
- Reset automatico entre videos
- Manejo de errores robusto

**API**:
```python
__init__(car_min_confidence, enable_database, enable_events)
reset()  # Reset para nuevo video
process_image(image) -> dict
process_video_frame(frame) -> dict
```

**Flujo process_video_frame()**:
1. Detectar vehiculos
2. Actualizar tracker
3. Clasificar vehiculos nuevos (cache)
4. Log detecciones BD (cada 10 frames)
5. Detectar eventos
6. Procesar eventos (BD)
7. Dibujar resultados
8. Retornar imagen anotada

**Optimizaciones**:
- Clasifica solo vehiculos nuevos
- Logging BD cada 10 frames (no cada frame)
- Logging debug condicional (config)
- Validacion bbox robusta
- Try-except en puntos criticos

## Configuracion (config.py)

### Tracking
```python
TRACKING_MAX_AGE = 45          # Frames sin deteccion
TRACKING_MIN_HITS = 5          # Detecciones para confirmar
TRACKING_IOU_THRESHOLD = 0.25  # Umbral matching
```

### Deteccion
```python
CAR_MIN_CONFIDENCE = 0.5       # Confianza minima vehiculo
```

### Base de Datos
```python
DB_PATH = 'database/estacionamiento.db'
SNAPSHOT_DIR = 'snapshots/'
DB_DETECTION_LOG_INTERVAL = 10  # Log cada N frames
```

### Eventos
```python
EVENT_LINE_POSITION = 400
EVENT_ENTRY_DIRECTION = 'down'
EVENT_MIN_CONFIDENCE = 0.6
EVENT_LINE_TOLERANCE = 15
```

### Debug
```python
DEBUG_VERBOSE = False          # Logging detallado
DEBUG_LOG_INTERVAL = 30        # Log cada N frames
DEBUG_SHOW_TRACK_IDS = True
DEBUG_SHOW_EVENT_LINE = True
```

## Performance

### Metricas (Video 400 frames, 8 vehiculos)

**Antes (Fase 1)**:
- Tiempo: ~500ms/frame (2 FPS)
- Total: ~200 segundos
- Track IDs: N/A (sin tracking)

**Despues (Fase 2A - Tracking)**:
- Tiempo: ~50ms/frame (20 FPS)
- Total: ~20 segundos
- Mejora: 10x mas rapido
- Track IDs: 1-12 (estables)

**Despues (Fase 2B - BD + Eventos)**:
- Tiempo: ~30-50ms/frame (20-30 FPS)
- Total: ~15-20 segundos
- BD writes: ~240 (vs 2,400 sin optimizacion)
- Track IDs: 1-12 (optimizados)
- Consola: Limpia

### Breakdown de Tiempo (Por Frame)

| Componente | Tiempo | Notas |
|------------|--------|-------|
| Deteccion YOLO | ~10ms | Constante |
| Tracking | ~5ms | Por frame |
| Clasificacion | ~300ms | **Solo vehiculos nuevos** |
| - Placa OCR | ~250ms | Parte lenta |
| - Marca YOLO | ~30ms | |
| - Color HSV | ~20ms | |
| BD writes | <1ms | Cada 10 frames |
| Eventos | ~2ms | Por frame |
| Dibujo | ~3ms | Por frame |
| **Total (nuevo vehiculo)** | ~320ms | Ocurre 1 vez |
| **Total (tracking)** | ~20ms | Resto del video |

## Formato de Datos

### Deteccion Individual
```python
{
    'id': 1,                          # Track ID
    'bbox': [100, 200, 300, 400],     # [x1, y1, x2, y2]
    'confidence': 0.85,
    'class': 'car',
    'Placa': 'SI',                    # 'SI' o 'NO'
    'Numero-Placa': 'ABC1234',        # Texto o '------'
    'plate_bbox': [10, 50, 80, 70],   # Relativo a vehiculo
    'brand': 'Toyota',
    'brand_bbox': [20, 20, 60, 50],   # Relativo a vehiculo
    'color': 'BLANCO'
}
```

### Track (Tracker)
```python
{
    'id': 1,
    'bbox': [100.0, 200.0, 300.0, 400.0],  # Floats
    'hits': 15,                             # Total detecciones
    'hit_streak': 15,                       # Detecciones consecutivas
    'age': 15,                              # Frames desde creacion
    'time_since_update': 0                  # Frames sin deteccion
}
```

### Evento
```python
{
    'track_id': 1,
    'event': 'entry',                  # 'entry' o 'exit'
    'timestamp': datetime(2024, 1, 15, 10, 30, 0)
}
```

### Registro BD (vehicles)
```sql
{
    id: 1,                             -- Auto-increment
    track_id: 1,                       -- Del tracker
    plate_number: 'ABC1234',           -- Puede ser NULL
    brand: 'Toyota',
    color: 'BLANCO',
    first_seen: '2024-01-15 10:30:00',
    last_seen: '2024-01-15 10:35:00',
    status: 'inside'                   -- 'inside', 'outside', 'unknown'
}
```

## Casos de Uso

### 1. Procesar Video de Estacionamiento
```python
# UI
1. Abrir main.py
2. Click "Subir Video"
3. Seleccionar archivo
   → Pipeline resetea automaticamente
   → IDs empiezan en 1
4. Video procesa automaticamente
   → Deteccion + Tracking + Clasificacion
   → BD registra vehiculos y eventos
   → Eventos detectan entrada/salida
5. Video se reproduce con anotaciones
   → Bounding boxes verdes
   → IDs de tracking
   → Linea virtual amarilla
```

### 2. Monitoreo en Tiempo Real (Camara)
```python
1. Click "Activar Camara"
   → Pipeline resetea
   → IDs empiezan en 1
2. Sistema procesa en vivo
   → ~20-30 FPS
   → BD acumula historial
   → Eventos detectados
3. Click "Detener Camara"
   → BD mantiene historial
```

### 3. Procesar Imagen Unica
```python
1. Click "Subir Imagen"
2. Seleccionar archivo
3. Click "Procesar"
   → Deteccion + Clasificacion (sin tracking)
4. Ver resultados en panel derecho
```

## Problemas Resueltos y Soluciones

### Problema 1: Bbox Float vs Int ✅
**Sintoma**: Error OpenCV "Can't parse pt1"

**Causa**: Tracker retorna floats, OpenCV necesita ints

**Solucion**: 
- Conversion explicita a int antes de slicing
- Validacion de bbox en _draw_results()
- Try-except robusto

**Archivo**: pipeline.py

### Problema 2: Demasiados Track IDs ✅
**Sintoma**: 55 IDs para 8 vehiculos (ratio 6.9:1)

**Causa**: Parametros muy permisivos

**Solucion**:
- TRACKING_MIN_HITS = 5 (mas estricto)
- TRACKING_IOU_THRESHOLD = 0.25 (mas selectivo)
- CAR_MIN_CONFIDENCE = 0.5 (reduce false positives)

**Resultado**: ~10-12 IDs (ratio 1.25:1)

### Problema 3: IDs Acumulan Entre Videos ✅
**Sintoma**: Video 1 → IDs 1-12, Video 2 → IDs 13-24

**Causa**: Tracker no resetea entre videos

**Solucion**:
- Metodo pipeline.reset()
- Llamado automatico en load_video()
- Llamado automatico en toggle_camera()

**Resultado**: Cada video empieza en ID=1

### Problema 4: Video No Se Procesa ✅
**Sintoma**: Barra 100% pero video no reproduce

**Causa**: Excepciones no manejadas en BD/eventos

**Solucion**:
- Try-except en todos los puntos criticos
- Retornos seguros (frame original si error)
- Logging comprensivo

**Resultado**: Video siempre procesa, errores logeados

### Problema 5: Logging Excesivo ✅
**Sintoma**: 2,400+ writes BD, consola saturada

**Causa**: Log cada frame

**Solucion**:
- DB_DETECTION_LOG_INTERVAL = 10
- DEBUG_VERBOSE = False
- Logging condicional

**Resultado**: 90% reduccion, consola limpia

## Limitaciones Conocidas

### Tecnicas
1. **Placas**: Optimizado para formato peruano alfanumerico
2. **Marcas**: Solo 14 marcas soportadas (expandible)
3. **Colores**: 7 colores basicos, deteccion heuristica
4. **Tracking**: Puede perder vehiculos en oclusiones >1.5seg
5. **Eventos**: Requiere linea virtual correctamente posicionada

### Performance
1. **OCR**: ~250ms por vehiculo (primera vez)
2. **BD**: SQLite single-threaded
3. **UI**: Single-threaded, puede congelar en videos largos

### Funcionales
1. **Multi-camara**: No implementado aun
2. **Re-identificacion**: Solo por posicion (IoU), no por apariencia
3. **UI Stats**: Panel de estadisticas pendiente
4. **Historial**: Visor de BD pendiente
5. **Exportacion**: Reportes pendientes

## Troubleshooting

### Error: "slice indices must be integers"
**Causa**: Bbox con floats

**Solucion**: Ya resuelto en pipeline.py actual

### Error: "database is locked"
**Causa**: Multiples writes simultaneos

**Solucion**: Ya manejado con try-except, no bloquea

### Demasiados Track IDs
**Solucion**: Ajustar en config.py:
```python
TRACKING_MIN_HITS = 7
CAR_MIN_CONFIDENCE = 0.6
```

### Pierde Vehiculos Reales
**Solucion**: Ajustar en config.py:
```python
TRACKING_IOU_THRESHOLD = 0.3
TRACKING_MIN_HITS = 3
```

### Video Muy Lento
**Solucion**: 
- Desactivar BD: `enable_database=False` en main.py
- Desactivar eventos: `enable_events=False`

### IDs No Resetean
**Solucion**: Verificar que main.py llame `pipeline.reset()`

## Testing

### Unit Tests (Pendiente)
```bash
# Futuros tests
python -m pytest tests/test_tracker.py
python -m pytest tests/test_database.py
python -m pytest tests/test_events.py
```

### Manual Testing
```bash
python main.py
# 1. Probar imagen
# 2. Probar video
# 3. Probar camara
# 4. Verificar BD
```

### Verificar BD
```bash
sqlite3 database/estacionamiento.db
sqlite> SELECT COUNT(*) FROM vehicles;
sqlite> SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;
sqlite> .exit
```

## Dependencias

### Core
- opencv-python-headless
- ultralytics (YOLOv8)
- easyocr
- torch / torchvision

### UI
- customtkinter
- Pillow

### Tracking
- lap (algoritmo hungaro)
- filterpy (Kalman)
- scipy

### BD
- sqlite3 (built-in)

### Completo
Ver `requirements.txt`

## Changelog

### v2.1 (Fase 2C) - Optimizaciones
- ✅ Reduccion logging BD (90%)
- ✅ Configuracion centralizada
- ✅ Validaciones bbox robustas
- ✅ Sistema de reset

### v2.0 (Fase 2B) - BD y Eventos
- ✅ Base de datos SQLite
- ✅ Detector de eventos
- ✅ Logging comprensivo
- ✅ Manejo de errores

### v1.5 (Fase 2A) - Tracking
- ✅ ByteTrack implementado
- ✅ IDs persistentes
- ✅ Performance 10x

### v1.0 (Fase 1) - Baseline
- ✅ Deteccion vehiculos
- ✅ Reconocimiento placas
- ✅ Clasificacion marca/color
- ✅ UI basica

## Creditos

- **YOLOv8**: Ultralytics
- **EasyOCR**: JaidedAI
- **ByteTrack**: Paper "Multi-Object Tracking by Associating Every Detection Box"
- **CustomTkinter**: TomSchimansky

Proyecto educativo - Instituto Superior