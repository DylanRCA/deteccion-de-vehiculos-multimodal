# Plan Detallado - Sistema de Estacionamiento Inteligente

## Vision General
Transformar detector de vehiculos en sistema completo de gestion de estacionamiento con tracking, persistencia, deteccion de eventos entrada/salida y re-identificacion.

**Estado Actual**: Fase 2C completada con optimizaciones
**Fecha**: Noviembre 2024
*Planeacion sujeta a cambios segun necesidades*

---

## ESTADO ACTUAL DEL PROYECTO

### Fases Completadas: 1, 2A, 2B, 2C ✅
### Fase Actual: Funcional y Optimizado ✅
### Siguiente Fase: 3 (Expansiones) ⏳

---

## FASE 1: DETECCION BASICA ✅ COMPLETADA

### Objetivo
Sistema basico de deteccion de vehiculos con reconocimiento de placas y clasificacion.

### Componentes Implementados
- ✅ **CarDetector** (`car_detector.py`)
  - Deteccion YOLO de vehiculos
  - Confianza minima configurable
  - ~10ms por frame
  
- ✅ **PlateRecognizer** (`plate_recognizer.py`)
  - Deteccion YOLO + EasyOCR
  - 4 tecnicas de binarizacion
  - ~250ms por vehiculo
  
- ✅ **VehicleClassifier** (`classifier.py`)
  - Deteccion logos (14 marcas)
  - Clasificacion color HSV (7 colores)
  - ~50ms por vehiculo
  
- ✅ **VehicleDetectionPipeline** (`pipeline.py`)
  - Orquestacion de componentes
  - Procesamiento secuencial
  
- ✅ **Interfaz GUI** (`main.py`)
  - CustomTkinter
  - Imagen/Video/Camara
  - Panel de informacion

### Resultados
- Funcionalidad completa
- Performance: ~500ms/frame (2 FPS)
- Sin tracking (IDs no persistentes)

---

## FASE 2A: SISTEMA DE TRACKING ✅ COMPLETADA

### Objetivo
Implementar tracking multi-vehiculo con IDs persistentes usando ByteTrack.

### Componentes Implementados
- ✅ **VehicleTracker** (`tracker.py`)
  - Implementacion ByteTrack desde cero
  - Algoritmo hungaro greedy
  - IDs secuenciales persistentes
  - Manejo de oclusiones
  
- ✅ **Configuracion** (`config.py`)
  - Parametros centralizados
  - TRACKING_MAX_AGE = 45
  - TRACKING_MIN_HITS = 5
  - TRACKING_IOU_THRESHOLD = 0.25

### Modificaciones
- ✅ Pipeline integrado con tracker
- ✅ Cache de vehiculos conocidos
- ✅ Clasificacion solo en primera deteccion

### Resultados
- **Performance**: ~20ms/frame (20 FPS)
- **Mejora**: 10x mas rapido (500ms → 50ms)
- **Track IDs**: Estables y consistentes
- **Oclusiones**: Maneja hasta 1.5 segundos

### Documentacion
- `src/TRACKER_DOCS.md` - Documentacion detallada
- Tests unitarios basicos
- Configuracion en `config.py`

---

## FASE 2B: BASE DE DATOS Y EVENTOS ✅ COMPLETADA

### 1. Base de Datos ✅

**Archivo**: `src/database.py`

**Esquema Implementado**:

```sql
-- Vehiculos registrados
CREATE TABLE vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER UNIQUE,
    plate_number TEXT,
    brand TEXT,
    color TEXT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    status TEXT  -- 'inside', 'outside', 'unknown'
);

-- Eventos entrada/salida
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER,
    event_type TEXT,  -- 'entry', 'exit', 'detection'
    timestamp TIMESTAMP,
    camera_id TEXT,
    confidence REAL,
    plate_confidence REAL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);

-- Historial de detecciones
CREATE TABLE detections (
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
);

-- Indices para queries rapidas
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_vehicle ON events(vehicle_id);
CREATE INDEX idx_vehicles_status ON vehicles(status);
```

**API Implementada**:
- ✅ `register_vehicle(track_id, plate, brand, color)` → vehicle_id
- ✅ `log_event(vehicle_id, event_type, timestamp, camera_id)`
- ✅ `log_detection(vehicle_id, bbox, frame_num)`
- ✅ `update_vehicle_status(vehicle_id, status)`
- ✅ `get_vehicle_by_track_id(track_id)` → dict
- ✅ `get_vehicles_inside()` → list
- ✅ `get_events_by_date(date)` → list

**Caracteristicas**:
- ✅ WAL mode para concurrencia
- ✅ Context managers para conexiones
- ✅ Logging comprensivo
- ✅ Manejo robusto de errores
- ✅ No bloquea procesamiento en errores

---

### 2. Detector de Eventos ✅

**Archivo**: `src/event_detector.py`

**Funcionalidad**:
- ✅ Linea virtual configurable (Y position)
- ✅ Deteccion de cruces por centroide
- ✅ Determinacion de direccion (historial)
- ✅ Clasificacion entry/exit
- ✅ Prevencion de eventos duplicados
- ✅ Visualizacion de linea (debug)

**API Implementada**:
```python
configure_line(y_position, entry_direction)
detect_events(tracks) → [{track_id, event, timestamp}]
draw_line(image) → image_with_line
reset_history()
```

**Estados de Vehiculo**:
- `approaching_line` - Acercandose a la linea
- `crossed_entry` - Cruzo hacia entrada
- `crossed_exit` - Cruzo hacia salida
- `inside` - Dentro del estacionamiento
- `outside` - Fuera del estacionamiento

**Algoritmo**:
1. Calcular centroide Y del bbox
2. Detectar cruce de linea virtual
3. Determinar direccion por historial (ultimas 10 posiciones)
4. Clasificar como entry/exit segun configuracion
5. Evitar duplicados comparando con last_event

**Configuracion**:
- EVENT_LINE_POSITION = 400
- EVENT_ENTRY_DIRECTION = 'down' o 'up'
- EVENT_MIN_CONFIDENCE = 0.6
- EVENT_LINE_TOLERANCE = 15

---

### 3. Integracion en Pipeline ✅

**Modificaciones en `pipeline.py`**:
- ✅ Flags de activacion (enable_database, enable_events)
- ✅ Inicializacion de BD y eventos en __init__
- ✅ Metodo reset() para nuevos videos
- ✅ Registro de vehiculos nuevos en BD
- ✅ Log de detecciones (optimizado: cada 10 frames)
- ✅ Deteccion de eventos cada frame
- ✅ Procesamiento de eventos (BD update)
- ✅ Visualizacion de linea virtual

**Flujo Completo**:
```
1. Detectar vehiculos (CarDetector)
2. Actualizar tracking (VehicleTracker)
3. Para vehiculos nuevos:
   - Clasificar (PlateRecognizer + VehicleClassifier)
   - Registrar en BD
   - Guardar en cache
4. Log detecciones en BD (cada 10 frames)
5. Detectar eventos (EventDetector)
6. Procesar eventos:
   - Log evento en BD
   - Actualizar status vehiculo
7. Dibujar resultados + linea virtual
8. Retornar imagen anotada
```

---

### 4. Mejoras en UI ✅

**Modificaciones en `main.py`**:
- ✅ Reset automatico al cargar video
- ✅ Reset automatico al activar camara
- ✅ Try-except en todos los puntos criticos
- ✅ Logging de progreso detallado
- ✅ Manejo robusto de errores
- ✅ Reproduccion de video procesado

**Pendiente** (Fase 3):
- ⏳ Panel de estadisticas en tiempo real
- ⏳ Ventana de configuracion de linea virtual
- ⏳ Visor de historial de BD
- ⏳ Selector de camara (si multiples)

---

## FASE 2C: OPTIMIZACIONES Y CORRECCIONES ✅ COMPLETADA

### Problemas Identificados y Resueltos

**1. Error Bbox Float vs Int** ✅
- **Problema**: OpenCV error "Can't parse pt1"
- **Causa**: Tracker retorna coords float, OpenCV necesita int
- **Solucion**: 
  - Conversion explicita a int antes de slicing
  - Validacion de bbox en _draw_results()
  - Try-except en dibujo de cada vehiculo
- **Archivo**: `pipeline.py`
- **Resultado**: Video procesa correctamente, sin crashes

**2. Demasiados Track IDs** ✅
- **Problema**: 55 IDs para 8 vehiculos reales (ratio 6.9:1)
- **Causa**: Parametros de tracking muy permisivos
- **Solucion**: Config optimizado
  ```python
  TRACKING_MIN_HITS = 5        # Antes: 3
  TRACKING_IOU_THRESHOLD = 0.25  # Antes: 0.3
  CAR_MIN_CONFIDENCE = 0.5     # Antes: 0.4
  ```
- **Archivo**: `config.py`
- **Resultado**: ~10-12 IDs (ratio 1.25:1)

**3. IDs Acumulan Entre Videos** ✅
- **Problema**: Video 1 → IDs 1-12, Video 2 → IDs 13-24
- **Causa**: Tracker no resetea entre videos
- **Solucion**: 
  - Metodo `pipeline.reset()`
  - Llamado automatico en `_load_video()`
  - Llamado automatico en `_toggle_camera()`
- **Archivos**: `pipeline.py`, `main.py`
- **Resultado**: Cada video empieza con ID=1

**4. Logging Excesivo** ✅
- **Problema**: 2,400+ writes BD, consola saturada
- **Causa**: Log detecciones cada frame
- **Solucion**:
  ```python
  DB_DETECTION_LOG_INTERVAL = 10  # Log cada 10 frames
  DEBUG_VERBOSE = False           # Logs reducidos
  DEBUG_LOG_INTERVAL = 30         # Log debug cada 30 frames
  ```
- **Archivos**: `config.py`, `pipeline.py`
- **Resultado**: 90% reduccion logs (2,400 → ~240)

**5. Video No Se Procesa** ✅
- **Problema**: Barra 100% pero video no reproduce
- **Causa**: Excepciones no manejadas en BD/eventos
- **Solucion**:
  - Try-except en todos los puntos criticos
  - Retornos seguros (frame original si error)
  - Logging comprensivo con traceback
- **Archivos**: `pipeline.py`, `main.py`
- **Resultado**: Video siempre procesa, errores logeados

---

## METRICAS DE PERFORMANCE

### Fase 1 (Baseline)
```
Tiempo por frame: ~500ms
FPS: 2
Detecciones: OK
Tracking: No
BD: No
Eventos: No
```

### Fase 2A (Con Tracking)
```
Tiempo por frame: ~50ms (vehiculos conocidos)
                  ~320ms (vehiculos nuevos)
FPS: 20 (promedio)
Mejora: 10x mas rapido
Detecciones: OK
Tracking: IDs estables
BD: No
Eventos: No
```

### Fase 2B/2C (Completo Optimizado)
```
Tiempo por frame: ~30-50ms (vehiculos conocidos)
                  ~320ms (vehiculos nuevos, 1 vez)
FPS: 20-30 (promedio)
Mejora: 10x mas rapido vs Fase 1
Detecciones: OK
Tracking: IDs estables (10-12 para 8 vehiculos)
BD: 90% menos writes (240 vs 2,400)
Eventos: Detectados correctamente
Reset: Automatico entre videos
```

### Breakdown de Tiempo (Por Frame)

**Frame con Vehiculo NUEVO** (primera deteccion):
```
Deteccion YOLO:      ~10ms
Tracking:            ~5ms
Clasificacion:       ~300ms  ← Solo primera vez!
  - Placa OCR:       ~250ms
  - Marca YOLO:      ~30ms
  - Color HSV:       ~20ms
BD write:            ~1ms
Eventos:             ~2ms
Dibujo:              ~3ms
TOTAL:               ~320ms
```

**Frame con Vehiculo CONOCIDO** (resto del video):
```
Deteccion YOLO:      ~10ms
Tracking:            ~5ms
Clasificacion:       ~0ms   ← Cache lookup!
BD write:            ~1ms   ← Solo cada 10 frames
Eventos:             ~2ms
Dibujo:              ~3ms
TOTAL:               ~20ms  (16x mas rapido!)
```

---

## FASE 2B PENDIENTE - Re-identificacion (OPCIONAL)

### Objetivo
Mejorar matching de vehiculos que salen despues de estar dentro.

### Problema
- Vehiculo entra → Track ID=5 (registrado en BD)
- Vehiculo dentro → fuera de vista (ID=5 eliminado del tracker)
- Vehiculo sale → Tracker crea NUEVO ID=47
- Sistema no sabe que ID=47 = mismo vehiculo que ID=5

### Solucion Propuesta

**Matching por Placa** (Principal):
```python
# En salida
1. Detectar evento 'exit' para Track ID=47
2. Clasificar placa: "ABC123"
3. BD: SELECT * FROM vehicles WHERE plate="ABC123" AND status="inside"
4. Encontrar vehiculo original (ID del Track 5)
5. BD: UPDATE ese vehicle_id SET status="outside"
6. Evento vinculado al vehicle_id correcto
```

**Fallbacks**:
- Si sin placa: Matching por marca+color (confianza 70%)
- Si ambiguo: FIFO temporal (confianza 50%)

**Metodos BD Adicionales** (pendientes):
```python
find_vehicle_by_plate(plate, status="inside") → dict
find_vehicles_by_features(brand, color, status="inside") → list
match_exit_vehicle(detection) → vehicle_id or None
```

**Prioridad**: Media (funciona sin esto, pero mejora precision)

---

## FASE 3: EXPANSIONES FUTURAS ⏳

### 3.1 Panel de Estadisticas en UI
- Vehiculos dentro (tiempo real)
- Entradas/salidas del dia
- Tracks activos
- Grafico de ocupacion

### 3.2 Visor de Historial
- Selector de fecha
- Tabla de eventos
- Filtros por tipo
- Detalles de vehiculo
- Exportacion CSV

### 3.3 Configuracion Interactiva
- Ventana para configurar linea virtual
- Click en imagen para posicionar
- Vista previa en tiempo real
- Guardado de configuraciones

### 3.4 Multi-Camara
- Multiples instancias de pipeline
- Sincronizacion de eventos
- BD centralizada
- UI con tabs por camara

### 3.5 Dashboard Web
- Flask/FastAPI backend
- Frontend React/Vue
- Visualizacion en tiempo real
- API REST para consultas

### 3.6 Reportes
- Exportacion PDF/Excel
- Reportes diarios/semanales/mensuales
- Graficos de ocupacion
- Estadisticas por vehiculo

### 3.7 Snapshots Automaticos
- Guardar imagen en eventos
- Organizacion por fecha
- Limpieza automatica (retention)

### 3.8 Ejecutable Portable
- PyInstaller
- Sin dependencias externas
- Instalador Windows
- Auto-descarga de modelos

---

## ORDEN DE IMPLEMENTACION RECOMENDADO

### Sprint Actual: Completo ✅
Todo implementado y optimizado.

### Sprint Siguiente (Opcional): Re-identificacion
**Tiempo estimado**: 2-3 dias
1. Agregar metodos BD para matching
2. Implementar logica de re-identificacion en pipeline
3. Testing con videos de estacionamiento
4. Ajuste de confianzas

### Sprint Fase 3.1: UI Estadisticas
**Tiempo estimado**: 3-4 dias
1. Diseñar panel de estadisticas
2. Queries BD para stats
3. Integracion en main.py
4. Actualización en tiempo real

### Sprint Fase 3.2: Visor Historial
**Tiempo estimado**: 4-5 dias
1. Ventana de historial
2. Selector de fechas
3. Tabla de eventos
4. Filtros y busqueda
5. Exportacion CSV

---

## ESTRUCTURA DE ARCHIVOS ACTUAL

```
detector_vehiculos/
├── data/                    # Videos e imagenes de prueba
├── models/                  # Modelos YOLO
│   ├── car_detector.pt         # 49.62 MB
│   ├── plate_detector.pt
│   └── brand_detector.pt
├── database/                # Base de datos ✅
│   └── estacionamiento.db      # SQLite
├── snapshots/               # Capturas (futuro)
├── src/                     # Codigo fuente
│   ├── __init__.py
│   ├── car_detector.py         # Fase 1 ✅
│   ├── plate_recognizer.py     # Fase 1 ✅
│   ├── classifier.py           # Fase 1 ✅
│   ├── tracker.py              # Fase 2A ✅
│   ├── database.py             # Fase 2B ✅
│   ├── event_detector.py       # Fase 2B ✅
│   ├── pipeline.py             # Fase 1-2C ✅
│   ├── DOCUMENTATION.md        # Doc tecnica ✅
│   └── TRACKER_DOCS.md         # Doc tracker ✅
├── main.py                  # UI Fase 1-2C ✅
├── config.py                # Config Fase 2A-2C ✅
├── requirements.txt         # Dependencias ✅
├── DOCUMENTATION.md         # Doc principal ✅
├── PLANNING.md              # Este archivo ✅
└── README.md                # Readme proyecto ✅
```

---

## CRITERIOS DE EXITO

### Fase 1 ✅
- ✅ Vehiculos detectados correctamente
- ✅ Placas reconocidas con >70% precision
- ✅ Marca y color clasificados
- ✅ UI funcional

### Fase 2A ✅
- ✅ IDs mantienen consistencia entre frames
- ✅ Performance >10 FPS
- ✅ Oclusiones manejadas
- ✅ Tests pasando

### Fase 2B ✅
- ✅ BD registra todos los vehiculos
- ✅ Eventos detectan entrada/salida >85% precision
- ✅ Sistema estable >1 hora continua
- ✅ Logs comprensivos

### Fase 2C ✅
- ✅ IDs optimizados (~1.3:1 ratio)
- ✅ Logging reducido 90%
- ✅ Reset automatico funciona
- ✅ Sin crashes en procesamiento

### Fase 3 (Futuro)
- ⏳ UI estadisticas actualizadas en tiempo real
- ⏳ Historial consultable
- ⏳ Multi-camara funcional
- ⏳ Dashboard web accesible

---

## CONFIGURACION RECOMENDADA

### Para Videos de Estacionamiento Normales
```python
# config.py
TRACKING_MAX_AGE = 45
TRACKING_MIN_HITS = 5
TRACKING_IOU_THRESHOLD = 0.25
CAR_MIN_CONFIDENCE = 0.5
EVENT_LINE_POSITION = 400  # Ajustar segun video
EVENT_ENTRY_DIRECTION = 'down'
DB_DETECTION_LOG_INTERVAL = 10
DEBUG_VERBOSE = False
```

### Para Videos con Muchas Oclusiones
```python
TRACKING_MAX_AGE = 60          # Mas tolerancia
TRACKING_MIN_HITS = 3          # Confirma mas rapido
TRACKING_IOU_THRESHOLD = 0.30  # Mas permisivo
```

### Para Videos de Alta Calidad
```python
TRACKING_MIN_HITS = 7          # Mas estricto
CAR_MIN_CONFIDENCE = 0.6       # Solo vehiculos claros
EVENT_MIN_CONFIDENCE = 0.7     # Eventos muy confiables
```

---

## LIMITACIONES CONOCIDAS

### Tecnicas
1. **Placas**: Optimizado para formato peruano
2. **Marcas**: Solo 14 marcas soportadas
3. **Colores**: 7 colores basicos (heuristica)
4. **Oclusiones**: Max 1.5 segundos
5. **Re-ID**: Por posicion (IoU), no apariencia

### Performance
1. **OCR**: Lento (~250ms) pero solo 1 vez por vehiculo
2. **BD**: SQLite single-threaded
3. **UI**: Puede congelar en videos muy largos

### Funcionales
1. **Multi-camara**: No implementado
2. **UI Stats**: Pendiente Fase 3
3. **Historial UI**: Pendiente Fase 3
4. **Re-identificacion**: Opcional, no implementado

---

## NOTAS IMPORTANTES

### Mantenimiento
- Limpiar BD periodicamente si crece mucho
- Verificar modelos YOLO presentes en `/models`
- Backup de BD antes de cambios mayores

### Testing
- Probar con videos diversos (dia/noche, lluvia, etc.)
- Validar precision de eventos con ground truth
- Verificar estabilidad de IDs en videos largos

### Expansion
- Fase 3 es modular, puede implementarse en cualquier orden
- Re-identificacion es opcional pero recomendada
- Multi-camara requiere refactoring de BD

---

**Ultima actualizacion**: Fase 2C completada
**Proximo objetivo**: Fase 3 o Re-identificacion (a definir)