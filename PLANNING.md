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

### 3. Modificaciones Pipeline

**Integracion**:
- Inicializar `DatabaseManager`
- Inicializar `EventDetector`
- Registrar vehiculos nuevos en BD
- Detectar eventos cada frame
- Guardar eventos en BD
- Actualizar estados
- Snapshots en eventos (opcional)

---

### 4. Mejoras UI

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

### 5. Estructura Actualizada

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
3. Tests unitarios BD
4. Integrar en pipeline
5. Probar con datos

**Criterios**:
- BD se crea automaticamente
- Vehiculos se registran
- Consultas funcionan
- Sin errores concurrencia

---

### Sprint 2: Detector Eventos (2-3 dias)
**Tareas**:
1. Implementar `EventDetector`
2. Logica linea virtual
3. Integrar en pipeline
4. Tests eventos
5. Probar con videos

**Criterios**:
- Eventos detectados correctamente
- Direccion determinada bien
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

**Total Fase 2B: 9-12 dias**

---

## CONSIDERACIONES TECNICAS

### Performance
- Tracking: ~15ms ✅
- BD writes: WAL mode
- Snapshots: solo eventos
- Eventos: ~5ms

### Robustez
- Oclusiones manejadas ✅
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

**Estimado Fase 2B**: 9-12 dias
**Estimado Total Fase 2**: 19-26 dias