# Plan - Sistema de Estacionamiento

## Vision General
Transformar detector de vehiculos en sistema de gestion de estacionamiento con tracking, persistencia y deteccion de eventos entrada/salida.

**Estado**: Fase 2A completada, Fase 2B en progreso
*Planeacion sujeta a cambios*

---

## FASE 1: DETECCION BASICA ✅

- ✅ Detector vehiculos (YOLOv8)
- ✅ Reconocimiento placas (YOLO + OCR)
- ✅ Clasificador marca/color
- ✅ Pipeline integracion
- ✅ Interfaz GUI

---

## FASE 2A: TRACKING ✅

### Implementado
- ✅ ByteTrack (`src/tracker.py`)
- ✅ IDs persistentes
- ✅ Manejo oclusiones (30 frames)
- ✅ Integracion pipeline
- ✅ Tests unitarios
- ✅ Configuracion global (`config.py`)

### Resultados
- Performance: ~50ms/frame (20 FPS)
- Mejora: 10x mas rapido vs Fase 1
- Cache de clasificaciones

---

## FASE 2B: BASE DE DATOS Y EVENTOS ⏳

### 1. Base de Datos

**Archivo**: `src/database.py`

**Tablas**:
- `vehicles` - Vehiculos registrados
- `events` - Eventos entrada/salida
- `detections` - Historial detecciones

**Metodos**:
- `register_vehicle()` - Registrar nuevo
- `log_event()` - Guardar evento
- `log_detection()` - Guardar deteccion
- `update_vehicle_status()` - Actualizar estado
- `get_vehicles_inside()` - Consultar dentro
- `get_events_by_date()` - Historial por fecha
- `find_vehicle_by_plate()` - Buscar por placa y estado
- `find_vehicles_by_features()` - Buscar por marca/color
- `match_exit_vehicle()` - Re-identificacion completa

---

### 2. Detector de Eventos

**Archivo**: `src/event_detector.py`

**Funcionalidad**:
- Linea virtual configurable
- Deteccion cruces de linea
- Determinar direccion (entrada/salida)
- Estados: `approaching`, `crossed_entry`, `crossed_exit`, `inside`, `outside`

**Metodos**:
- `detect_events(tracks)` - Detectar entrada/salida
- `configure_line()` - Configurar posicion
- `draw_line()` - Dibujar linea (debug)

---

### 3. Re-identificacion por Placa

**Problema**:
- Vehiculo entra → Track ID=5, se guarda en BD
- Vehiculo dentro del estacionamiento → fuera de vista de camara
- Tracker pierde ID=5 (elimina despues de 30 frames)
- Vehiculo sale → Tracker crea NUEVO ID=47
- Sistema necesita saber que ID=47 es el mismo vehiculo que ID=5

**Solucion - Matching por Placa**:

**En Entrada**:
- Track ID=5 cruza linea hacia inside
- Clasificar: Placa="ABC123", Marca="Toyota", Color="Blanco"
- BD: INSERT vehicle (track_id=5, plate="ABC123", status="inside")
- Evento: "entry"

**En Salida**:
- NUEVO Track ID=47 cruza linea hacia outside
- Clasificar: Placa="ABC123"
- BD: SELECT * WHERE plate="ABC123" AND status="inside"
- Encuentra el registro original (vehicle_id del track_id=5)
- BD: UPDATE ese vehicle_id SET status="outside"
- Evento: "exit" vinculado al vehicle_id correcto

**Prioridades de Matching**:
1. **Placa exacta** (confianza 95%) - metodo principal
2. **Marca + Color** (confianza 70%) - fallback si no hay placa
3. **FIFO temporal** (confianza 50%) - ultimo recurso

**Casos Edge**:
- Sin placa detectada en salida → usar marca+color
- Multiples matches ambiguos → marcar evento "match_confidence=low"
- Salida sin entrada previa → evento "exit_without_entry"

**Metodos BD adicionales**:
- `find_vehicle_by_plate(plate, status)` - buscar por placa
- `find_vehicles_by_features(brand, color, status)` - buscar por caracteristicas
- `match_exit_vehicle(detection)` - logica completa de matching

---

### 4. Modificaciones Pipeline

**Integracion**:
- Inicializar `DatabaseManager`
- Inicializar `EventDetector`
- Registrar vehiculos nuevos en BD
- Detectar eventos cada frame
- **Aplicar re-identificacion en eventos de salida**
- Guardar eventos en BD
- Actualizar estados
- Snapshots en eventos (opcional)

---

### 5. Mejoras UI

**Panel Estadisticas**:
- Vehiculos dentro
- Entradas/salidas del dia
- Tracks activos

**Configuracion Linea**:
- Ventana configuracion
- Posicion Y ajustable
- Direccion entrada/salida
- Vista previa (opcional)

**Visor Historial**:
- Selector de fecha
- Tabla de eventos
- Filtros por tipo
- Detalles vehiculo

---

### 6. Estructura Actualizada

```
detector_vehiculos/
├── database/
│   └── estacionamiento.db      # SQLite
├── snapshots/                   # Capturas eventos
│   └── YYYY-MM-DD/
├── src/
│   ├── tracker.py              # ✅ Fase 2A
│   ├── database.py             # ⏳ Fase 2B
│   ├── event_detector.py       # ⏳ Fase 2B
│   └── pipeline.py             # ⏳ Modificar
├── main.py                      # ⏳ Modificar UI
└── config.py                    # ⏳ Agregar configs
```

---

## ORDEN DE IMPLEMENTACION - FASE 2B

### Sprint 1: Base de Datos (3-4 dias)
**Tareas**:
1. Crear esquema SQL
2. Implementar `DatabaseManager`
3. Implementar metodos re-identificacion
4. Tests unitarios BD y matching
5. Integrar en pipeline
6. Probar con datos

**Criterios**:
- BD se crea automaticamente
- Vehiculos se registran
- Consultas funcionan
- Re-identificacion por placa >90%
- Sin errores concurrencia

---

### Sprint 2: Detector Eventos + Re-identificacion (3-4 dias)
**Tareas**:
1. Implementar `EventDetector`
2. Logica linea virtual
3. Integrar re-identificacion en eventos salida
4. Integrar en pipeline
5. Tests eventos y matching
6. Probar con videos

**Criterios**:
- Eventos detectados correctamente
- Direccion determinada bien
- Re-identificacion funciona entrada/salida
- Falsos positivos < 5%
- Estados actualizados

---

### Sprint 3: UI y Estadisticas (2-3 dias)
**Tareas**:
1. Panel estadisticas
2. Ventana configuracion linea
3. Visor historial
4. Indicador visual linea
5. Pruebas usuario

**Criterios**:
- Estadisticas actualizadas
- Linea configurable
- Historial funcional
- UI responsive

---

### Sprint 4: Pulido (2 dias)
**Tareas**:
1. Snapshots eventos
2. Optimizar consultas BD
3. Testing integral
4. Documentacion
5. Correccion bugs

**Criterios**:
- Sistema estable >1 hora
- Performance < 100ms/frame
- Tests 100% pass
- Docs actualizadas

**Total Fase 2B: 10-13 dias**

---

## CONSIDERACIONES TECNICAS

### Performance
- Tracking: ~15ms ✅
- BD writes: WAL mode
- Snapshots: solo eventos
- Eventos: ~5ms

### Robustez
- Oclusiones manejadas ✅
- Re-identificacion por placa >90%
- Fallback marca+color si sin placa
- Validar placas pre-eventos
- Confianza minima 0.5
- Reintentos BD

### Configuracion
```python
# Tracking (ajustado)
TRACKING_MAX_AGE = 30
TRACKING_MIN_HITS = 3
TRACKING_IOU_THRESHOLD = 0.3

# Eventos (nuevo)
EVENT_LINE_POSITION = 400
EVENT_ENTRY_DIRECTION = 'down'
EVENT_MIN_CONFIDENCE = 0.5

# Database (nuevo)
DB_PATH = 'database/estacionamiento.db'
SNAPSHOT_DIR = 'snapshots/'
```

---

## CRITERIOS EXITO - FASE 2B

✅ Base de datos funcional
✅ Eventos detectados >90% precision
✅ Re-identificacion entrada/salida por placa funcional
✅ Correlacion correcta mismo vehiculo
✅ UI con estadisticas tiempo real
✅ Sistema estable >1 hora
✅ Performance < 100ms/frame

---

## FASE 3 - FUTURO

- Multi-camara
- Dashboard web
- API REST
- Ejecutable portable
- Reportes exportables

---

**Estimado Fase 2B**: 10-13 dias
**Estimado Total Fase 2**: 20-27 dias