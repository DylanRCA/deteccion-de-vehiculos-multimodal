# Detector de Vehiculos Multimodal - Documentacion del Proyecto

## Descripcion General
Sistema completo de deteccion y gestion de vehiculos con tracking multi-vehiculo, base de datos, deteccion de eventos entrada/salida, reconocimiento de placas para Peru y panel de estadisticas en tiempo real.

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
- ✅ Base de datos SQLite con 3 tablas (NUEVO ESQUEMA)
- ✅ Detector de eventos entrada/salida
- ✅ Sistema de linea virtual configurable
- ✅ Logging comprensivo en todos los modulos
- ✅ Manejo robusto de errores
- ✅ Re-identificacion por placa
- ✅ IDs temporales para vehiculos sin placa

### Fase 2C - Optimizaciones ✅ COMPLETADA
- ✅ Reduccion de logging BD (90% menos writes)
- ✅ Parametros de tracking optimizados
- ✅ Configuracion centralizada (config.py)
- ✅ Validaciones de bbox robustas
- ✅ Sistema de reset entre videos

### Fase 3 - UI y Estadisticas ✅ PARCIALMENTE COMPLETADA
- ✅ Panel de estadisticas en tiempo real (lado derecho UI)
- ✅ Consultas optimizadas de BD
- ✅ Actualizacion automatica cada 30 frames
- ⏳ Visor de historial (pendiente)
- ⏳ Graficos de ocupacion (pendiente)
- ⏳ Configuracion interactiva (pendiente)
- ⏳ Reportes exportables (pendiente)

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
6. EVENTOS (cada frame)
   ├─ EventDetector.detect_events()
   ├─ Detectar cruces de linea virtual
   └─ Clasificar entry/exit
   ↓
7. BASE DE DATOS (eventos entry/exit)
   ├─ ENTRY → INSERT active_vehicles + UPDATE vehicle_registry
   ├─ EXIT → INSERT parking_history + DELETE active_vehicles
   └─ Re-identificacion por placa
   ↓
8. VISUALIZACION
   ├─ Dibujar bounding boxes
   ├─ Mostrar IDs de tracking
   ├─ Dibujar linea virtual
   └─ Renderizar en UI
   ↓
9. ESTADISTICAS (cada 30 frames)
   ├─ Consultar BD (get_today_stats)
   ├─ Actualizar panel UI
   └─ Mostrar dentro/entradas/salidas/duracion
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
│   └── estacionamiento.db      # BD principal (NUEVO ESQUEMA)
├── snapshots/               # Capturas de vehiculos (futuro)
├── src/                     # Codigo fuente
│   ├── __init__.py
│   ├── car_detector.py         # Detector YOLO vehiculos
│   ├── plate_recognizer.py     # Detector placas + OCR
│   ├── classifier.py           # Clasificador marca/color
│   ├── tracker.py              # Sistema ByteTrack
│   ├── database.py             # Gestor SQLite (NUEVO ESQUEMA)
│   ├── event_detector.py       # Detector entrada/salida
│   ├── pipeline.py             # Orquestador principal
│   └── DOCUMENTATION.md        # Doc del directorio src/
├── main.py                  # Aplicacion GUI (CON PANEL STATS)
├── config.py                # Configuracion centralizada
├── diagnostico_bd.py        # Script de diagnostico
├── requirements.txt         # Dependencias
├── DOCUMENTATION.md         # Este archivo
├── PLANNING.md              # Plan de desarrollo
├── MIGRACION.md             # Guia de migracion esquema BD
├── TROUBLESHOOTING.md       # Guia de problemas comunes
├── PANEL_ESTADISTICAS.md    # Doc del panel de stats
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

### 5. DatabaseManager (database.py) - NUEVO ESQUEMA
**Proposito**: Persistir vehiculos, sesiones y estadisticas

**Tecnologia**: SQLite3 con WAL mode

**Esquema** (3 tablas):
```sql
-- 1. OPERACIONAL: Vehiculos dentro AHORA
active_vehicles (
    id, plate, track_id, brand, color,
    entry_time, parking_duration_minutes
)

-- 2. HISTORICO: Sesiones completadas
parking_history (
    id, plate, brand, color,
    entry_time, exit_time, duration_minutes,
    source  -- 'live_camera' o 'video_analysis'
)

-- 3. REGISTRO: Catalogo de vehiculos conocidos
vehicle_registry (
    plate PRIMARY KEY, brand, color,
    first_seen, last_seen,
    total_visits, avg_duration_minutes
)
```

**API Principal**:
```python
# OPERACIONAL
register_entry(plate, track_id, brand, color) -> int
register_exit(plate) -> dict  # Retorna sesion completada
get_active_vehicles() -> list
find_active_by_plate(plate) -> dict or None
update_active_track_id(plate, new_track_id)

# HISTORICO
get_history_by_date(date) -> list
get_history_by_plate(plate) -> list

# REGISTRO
get_vehicle_stats(plate) -> dict
get_frequent_visitors(limit=10) -> list

# ESTADISTICAS
get_today_stats() -> dict  # NUEVO - Para panel UI
```

**Caracteristicas**:
- Re-identificacion por placa (evita duplicados)
- IDs temporales para vehiculos sin placa
- Calculo automatico de duracion
- Estadisticas acumulativas
- WAL mode para concurrencia

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

### 7. VehicleDetectionPipeline (pipeline.py)
**Proposito**: Orquestar todos los componentes

**Caracteristicas**:
- Inicializacion con flags de activacion
- Cache de vehiculos conocidos
- Logging condicional basado en config
- Reset automatico entre videos
- Manejo de errores robusto
- Generacion de IDs temporales

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
   - Si sin placa → Generar ID temporal
4. Detectar eventos (cruces de linea)
5. Procesar eventos entry/exit:
   - ENTRY: Buscar en active_vehicles → Registrar si nuevo
   - EXIT: Mover de active_vehicles a parking_history
6. Dibujar resultados
7. Retornar imagen anotada

### 8. VehicleDetectorApp (main.py) - CON PANEL DE ESTADISTICAS
**Proposito**: Interfaz grafica de usuario

**Layout** (3 columnas):
```
┌──────────┬────────────┬─────────────┐
│ Controles│   Video    │ Estadisticas│
│  250px   │ Expandible │    200px    │
└──────────┴────────────┴─────────────┘
```

**Panel de Estadisticas** (Columna Derecha):
- **DENTRO: X** - Vehiculos actualmente en estacionamiento
- **ENTRADAS: X** - Total entradas del dia
- **SALIDAS: X** - Total salidas del dia
- **ULTIMA ENTRADA** - Placa + tiempo relativo ("hace 2 min")
- **DURACION PROM: X min** - Promedio de estadia del dia
- **Boton "Actualizar"** - Refrescar stats manualmente

**Actualizacion de Stats**:
- Automatica: Cada 30 frames en camara
- Manual: Boton "Actualizar"
- Post-video: Al finalizar procesamiento

**Metodos Nuevos**:
```python
_update_stats() -> None  # Consulta BD y actualiza UI
```

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
DB_SOURCE_LIVE = 'live_camera'
DB_SOURCE_VIDEO = 'video_analysis'
TEMP_PLATE_PREFIX = 'TEMP_'
PARKING_WARN_NO_EXIT_ENTRY = True
PARKING_WARN_DUPLICATE_ENTRY = True
```

### Eventos
```python
EVENT_LINE_POSITION = 400
EVENT_ENTRY_DIRECTION = 'down'
EVENT_MIN_CONFIDENCE = 0.6
EVENT_LINE_TOLERANCE = 15
```

### UI
```python
UI_STATS_UPDATE_INTERVAL = 30  # Frames entre actualizaciones de stats
```

### Debug
```python
DEBUG_VERBOSE = False
DEBUG_LOG_INTERVAL = 30
DEBUG_SHOW_TRACK_IDS = True
DEBUG_SHOW_EVENT_LINE = True
```

## Performance

### Metricas (Video 400 frames, 8 vehiculos)

**Con Tracking + BD + Eventos + Stats**:
- Tiempo: ~30-50ms/frame (20-30 FPS)
- Total: ~15-20 segundos
- Track IDs: 1-12 (optimizados)
- BD writes: Minimos (solo en eventos)
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
| Eventos | ~2ms | Por frame |
| BD writes | <1ms | Solo en eventos |
| Stats query | ~5ms | Cada 30 frames |
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
    'Numero-Placa': 'ABC1234',        # Texto o ID temporal
    'plate_bbox': [10, 50, 80, 70],   # Relativo a vehiculo
    'brand': 'Toyota',
    'brand_bbox': [20, 20, 60, 50],   # Relativo a vehiculo
    'color': 'BLANCO'
}
```

### Evento
```python
{
    'track_id': 1,
    'event': 'entry',                  # 'entry' o 'exit'
    'timestamp': datetime(2024, 11, 23, 10, 30, 0)
}
```

### Registro BD (active_vehicles)
```sql
{
    id: 1,
    plate: 'ABC1234',                  -- O 'TEMP_20241123_103000_5'
    track_id: 1,
    brand: 'Toyota',
    color: 'BLANCO',
    entry_time: '2024-11-23 10:30:00',
    parking_duration_minutes: 0
}
```

### Estadisticas (get_today_stats)
```python
{
    'inside': 3,                       # Vehiculos dentro ahora
    'entries_today': 12,               # Entradas del dia
    'exits_today': 9,                  # Salidas del dia
    'avg_duration': 15,                # Duracion promedio (min)
    'last_entry': {                    # Ultima entrada o None
        'plate': 'TEMP_...',
        'entry_time': '2024-11-23 10:35:00',
        ...
    }
}
```

## Casos de Uso

### 1. Monitoreo en Tiempo Real (Camara)
```python
1. Click "Activar Camara"
   → Pipeline resetea
   → IDs empiezan en 1
2. Sistema procesa en vivo
   → ~20-30 FPS
   → BD acumula eventos entry/exit
   → Panel stats se actualiza cada 30 frames
3. Click "Detener Camara"
   → BD mantiene historial
```

### 2. Analisis de Video Historico
```python
1. Click "Subir Video"
   → Pipeline resetea
2. Video procesa automaticamente
   → Deteccion + Tracking + Clasificacion
   → Eventos detectados (NO persisten en BD)
   → Linea virtual visible
3. Video se reproduce con anotaciones
```

### 3. Procesar Imagen Unica
```python
1. Click "Subir Imagen"
2. Click "Procesar"
   → Deteccion + Clasificacion (sin tracking)
3. Ver resultados en panel derecho
```

### 4. Consultar Estadisticas
```python
1. Mientras camara activa:
   → Stats se actualizan automaticamente
2. O click "Actualizar" manualmente
3. Ver:
   - Vehiculos dentro
   - Entradas/salidas del dia
   - Ultima entrada con tiempo relativo
   - Duracion promedio
```

## Problemas Resueltos

### Problema 1: Bbox Float vs Int ✅
**Solucion**: Conversion explicita a int en pipeline.py

### Problema 2: Demasiados Track IDs ✅
**Solucion**: Parametros optimizados (MIN_HITS=5, IOU=0.25)

### Problema 3: IDs Acumulan Entre Videos ✅
**Solucion**: Metodo pipeline.reset() automatico

### Problema 4: Logging Excesivo ✅
**Solucion**: Logging condicional (DEBUG_VERBOSE, LOG_INTERVAL)

### Problema 5: Duplicados en BD ✅
**Solucion**: Re-identificacion por placa

### Problema 6: Vehiculos Sin Placa ✅
**Solucion**: IDs temporales (TEMP_YYYYMMDD_HHMMSS_trackid)

### Problema 7: Flechas Unicode "???" ✅
**Solucion**: Texto descriptivo en event_detector.py

### Problema 8: Stats No Visibles ✅
**Solucion**: Panel dedicado en UI con actualizacion automatica

## Limitaciones Conocidas

### Tecnicas
1. **Placas**: Optimizado para formato peruano
2. **Marcas**: Solo 14 marcas soportadas
3. **Colores**: 7 colores basicos (heuristica)
4. **Tracking**: Puede perder vehiculos en oclusiones >1.5seg
5. **Eventos**: Requiere linea virtual correctamente posicionada
6. **Stats**: Solo dia actual (no historico multi-dia en UI)

### Performance
1. **OCR**: ~250ms por vehiculo (primera vez)
2. **BD**: SQLite single-threaded
3. **UI**: Single-threaded, puede congelar en videos largos
4. **Stats**: Query cada 30 frames agrega ~5ms

### Funcionales
1. **Re-identificacion**: Solo por placa (no apariencia visual)
2. **UI Stats**: Sin graficos (solo numeros)
3. **Historial UI**: No hay visor de sesiones pasadas
4. **Exportacion**: No hay reportes PDF/CSV
5. **Configuracion UI**: No hay interfaz para ajustar linea virtual

## Troubleshooting

### Error: "slice indices must be integers"
**Causa**: Bbox con floats
**Solucion**: Ya resuelto en pipeline.py actual

### Demasiados Track IDs
**Solucion**: Ajustar en config.py:
```python
TRACKING_MIN_HITS = 7
CAR_MIN_CONFIDENCE = 0.6
```

### Sin Registros en BD
**Solucion**: 
1. Verificar `enable_database=True` en main.py
2. Verificar eventos detectados (cruzan linea virtual)
3. Ejecutar `python diagnostico_bd.py`

### Panel Stats Vacio
**Solucion**:
1. Activar camara y generar eventos
2. Click "Actualizar" manualmente
3. Verificar BD con `sqlite3 database/estacionamiento.db`

### "???" en Linea Virtual
**Solucion**: Reemplazar `src/event_detector.py` con version corregida

## Scripts de Utilidad

### diagnostico_bd.py
Verifica estado de BD y configuracion:
```bash
python diagnostico_bd.py
```

Muestra:
- Tablas existentes
- Cantidad de registros
- Parametros de configuracion
- Recomendaciones para ajustes

### Consultas BD Manuales
```bash
sqlite3 database/estacionamiento.db
```

```sql
-- Vehiculos dentro ahora
SELECT * FROM active_vehicles;

-- Sesiones del dia
SELECT * FROM parking_history 
WHERE DATE(entry_time) = DATE('now');

-- Stats rapidas
SELECT COUNT(*) FROM active_vehicles;
SELECT COUNT(*) FROM parking_history 
WHERE DATE(entry_time) = DATE('now');
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

### v3.0 (Fase 3 - Panel Stats) - ACTUAL
- ✅ Panel de estadisticas en UI
- ✅ Actualizacion automatica cada 30 frames
- ✅ Metodo get_today_stats() en BD
- ✅ Vista de tiempo relativo ("hace X min")

### v2.1 (Fase 2C) - Optimizaciones
- ✅ Reduccion logging BD (90%)
- ✅ Configuracion centralizada
- ✅ Validaciones bbox robustas
- ✅ Sistema de reset

### v2.0 (Fase 2B) - BD y Eventos
- ✅ Nuevo esquema BD (3 tablas)
- ✅ Re-identificacion por placa
- ✅ IDs temporales
- ✅ Detector de eventos
- ✅ Logging comprensivo

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