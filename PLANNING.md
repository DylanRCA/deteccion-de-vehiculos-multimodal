# Plan Detallado - Sistema de Estacionamiento Inteligente

## Vision General
Transformar detector de vehiculos en sistema completo de gestion de estacionamiento con tracking, persistencia, deteccion de eventos entrada/salida, re-identificacion y panel de estadisticas.

**Estado Actual**: Fase 3 parcialmente completada (Panel de Estadisticas)
**Fecha**: Noviembre 2024
*Planeacion sujeta a cambios segun necesidades*

---

## ESTADO ACTUAL DEL PROYECTO

### Fases Completadas: 1, 2A, 2B, 2C, 3 (parcial) ✅
### Fase Actual: Panel de Estadisticas Funcional ✅
### Siguiente Fase: 3 (Expansiones adicionales) ⏳

---

## FASE 1: DETECCION BASICA ✅ COMPLETADA

### Objetivo
Sistema basico de deteccion de vehiculos con reconocimiento de placas y clasificacion.

### Componentes Implementados
- ✅ **CarDetector** (`car_detector.py`)
- ✅ **PlateRecognizer** (`plate_recognizer.py`)
- ✅ **VehicleClassifier** (`classifier.py`)
- ✅ **VehicleDetectionPipeline** (`pipeline.py`)
- ✅ **Interfaz GUI** (`main.py`)

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
- ✅ **Configuracion** (`config.py`)

### Modificaciones
- ✅ Pipeline integrado con tracker
- ✅ Cache de vehiculos conocidos
- ✅ Clasificacion solo en primera deteccion

### Resultados
- **Performance**: ~20ms/frame (20 FPS)
- **Mejora**: 10x mas rapido
- **Track IDs**: Estables y consistentes

---

## FASE 2B: BASE DE DATOS Y EVENTOS ✅ COMPLETADA

### 1. Base de Datos ✅

**Archivo**: `src/database.py`

**Esquema Implementado** (3 tablas):

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

**API Implementada**:
- ✅ `register_entry(plate, track_id, brand, color)`
- ✅ `register_exit(plate)`
- ✅ `get_active_vehicles()`
- ✅ `find_active_by_plate(plate)`
- ✅ `update_active_track_id(plate, new_track_id)`
- ✅ `get_history_by_date(date)`
- ✅ `get_history_by_plate(plate)`
- ✅ `get_vehicle_stats(plate)`
- ✅ `get_frequent_visitors(limit)`

**Caracteristicas**:
- ✅ Re-identificacion por placa
- ✅ IDs temporales para vehiculos sin placa
- ✅ Calculo automatico de duracion
- ✅ WAL mode para concurrencia

---

### 2. Detector de Eventos ✅

**Archivo**: `src/event_detector.py`

**Funcionalidad**:
- ✅ Linea virtual configurable
- ✅ Deteccion de cruces por centroide
- ✅ Determinacion de direccion
- ✅ Clasificacion entry/exit
- ✅ Prevencion de duplicados
- ✅ Visualizacion de linea (sin Unicode)

**Estados de Vehiculo**:
- `approaching_line`
- `crossed_entry`
- `crossed_exit`
- `inside`
- `outside`

---

### 3. Integracion en Pipeline ✅

**Modificaciones en `pipeline.py`**:
- ✅ Flags de activacion (enable_database, enable_events)
- ✅ Metodo reset() para nuevos videos
- ✅ Generacion de IDs temporales
- ✅ Procesamiento de eventos entry/exit
- ✅ Re-identificacion por placa

**Flujo Completo**:
```
1. Detectar vehiculos
2. Actualizar tracking
3. Clasificar vehiculos nuevos
   → Si sin placa: Generar TEMP_YYYYMMDD_HHMMSS_trackid
4. Detectar eventos
5. Procesar eventos:
   → ENTRY: Buscar en active_vehicles → Registrar
   → EXIT: Mover a parking_history
6. Dibujar resultados + linea virtual
```

---

## FASE 2C: OPTIMIZACIONES ✅ COMPLETADA

### Problemas Identificados y Resueltos

**1. Error Bbox Float vs Int** ✅
- **Solucion**: Conversion explicita a int en pipeline.py

**2. Demasiados Track IDs** ✅
- **Solucion**: 
  ```python
  TRACKING_MIN_HITS = 5
  TRACKING_IOU_THRESHOLD = 0.25
  CAR_MIN_CONFIDENCE = 0.5
  ```

**3. IDs Acumulan Entre Videos** ✅
- **Solucion**: `pipeline.reset()` automatico

**4. Logging Excesivo** ✅
- **Solucion**: Logging condicional, 90% reduccion

**5. Duplicados en BD** ✅
- **Solucion**: Re-identificacion por placa

**6. Vehiculos Sin Placa** ✅
- **Solucion**: IDs temporales

**7. Flechas Unicode "???"** ✅
- **Solucion**: Texto descriptivo en event_detector.py

---

## FASE 3: UI Y ESTADISTICAS ✅ PARCIALMENTE COMPLETADA

### 3.1 Panel de Estadisticas en UI ✅ COMPLETADA

**Archivos Modificados**:
- `main.py` - Layout 3 columnas, panel derecho
- `src/database.py` - Metodo `get_today_stats()`

**Implementacion**:

#### Layout de UI
```
┌──────────┬────────────┬─────────────┐
│ Controles│   Video    │ Estadisticas│
│  250px   │ Expandible │    200px    │
└──────────┴────────────┴─────────────┘
```

#### Estadisticas Mostradas
```
ESTADISTICAS
────────────
DENTRO: 3         ← Vehiculos actualmente dentro
ENTRADAS: 12      ← Total entradas del dia
SALIDAS: 9        ← Total salidas del dia
────────────
ULTIMA ENTRADA:
TEMP_..._5        ← Placa mas reciente
hace 2 min        ← Tiempo relativo
────────────
DURACION PROM:
15 min            ← Promedio de estadia del dia

[Actualizar]      ← Boton refrescar manual
```

#### Actualizacion
- ✅ Automatica: Cada 30 frames en camara (~1 segundo)
- ✅ Manual: Boton "Actualizar"
- ✅ Post-video: Al finalizar procesamiento

#### Metodo BD
```python
def get_today_stats(self):
    """
    Returns: {
        'inside': int,
        'entries_today': int,
        'exits_today': int,
        'avg_duration': int,
        'last_entry': dict or None
    }
    """
```

**Tiempo estimado**: 3-4 dias
**Resultado**: ✅ COMPLETADO

---

### 3.2 Visor de Historial ⏳ PENDIENTE

**Objetivo**: Ventana adicional para consultar historial de sesiones

**Diseño Propuesto**:
```
┌────────────────────────────────────┐
│ HISTORIAL DE SESIONES             │
├────────────────────────────────────┤
│ Fecha: [Selector] [Hoy] [Ayer]    │
├────────────────────────────────────┤
│ Placa     | Entrada  | Salida  |  │
│ ABC123    | 10:30    | 12:45   |  │
│ TEMP_...  | 11:00    | 11:15   |  │
│ DEF456    | 12:00    | En est. |  │
├────────────────────────────────────┤
│ [Exportar CSV] [Cerrar]            │
└────────────────────────────────────┘
```

**Funcionalidades**:
- Tabla con todas las sesiones
- Filtros por fecha/placa
- Orden por columnas
- Exportacion CSV

**Archivos a crear**:
- `src/history_viewer.py` - Ventana Tkinter
- Metodo en `main.py` para abrir ventana

**Tiempo estimado**: 4-5 dias
**Prioridad**: Media

---

### 3.3 Graficos de Ocupacion ⏳ PENDIENTE

**Objetivo**: Visualizar ocupacion del estacionamiento en el tiempo

**Diseño Propuesto**:
```
┌────────────────────────────────────┐
│ OCUPACION DEL DIA                  │
├────────────────────────────────────┤
│ Vehiculos                          │
│ 10 ┤     ╭──╮                      │
│  8 ┤   ╭─╯  ╰─╮                    │
│  6 ┤ ╭─╯      ╰──╮                 │
│  4 ┤─╯           ╰─               │
│  2 ┤                               │
│  0 └──┬──┬──┬──┬──┬──┬──          │
│     8  10 12 14 16 18 20  Hora    │
└────────────────────────────────────┘
```

**Tecnologia**: matplotlib integrado en Tkinter

**Funcionalidades**:
- Grafico de linea por hora
- Selector de fecha
- Exportacion PNG

**Archivos a modificar**:
- `main.py` - Agregar tab o ventana
- `requirements.txt` - Agregar matplotlib

**Tiempo estimado**: 3-4 dias
**Prioridad**: Baja

---

### 3.4 Configuracion Interactiva ⏳ PENDIENTE

**Objetivo**: UI para configurar linea virtual

**Diseño Propuesto**:
```
┌────────────────────────────────────┐
│ CONFIGURACION LINEA VIRTUAL        │
├────────────────────────────────────┤
│ [Vista de camara]                  │
│                                    │
│ Haz click en la imagen para        │
│ posicionar la linea                │
│                                    │
├────────────────────────────────────┤
│ Posicion Y: [400] px               │
│ Direccion entrada:                 │
│ ( ) Arriba  (•) Abajo              │
│                                    │
│ [Guardar] [Cancelar]               │
└────────────────────────────────────┘
```

**Funcionalidades**:
- Click en imagen para posicionar linea
- Vista previa en tiempo real
- Guardado en config.py

**Archivos a crear**:
- Ventana de configuracion en `main.py`

**Tiempo estimado**: 2-3 dias
**Prioridad**: Alta (mejora UX)

---

### 3.5 Reportes Exportables ⏳ PENDIENTE

**Objetivo**: Generar reportes PDF/Excel

**Formatos**:
- PDF con graficos y tablas
- Excel con hojas multiples
- CSV simple

**Libreria**: reportlab (PDF), openpyxl (Excel)

**Funcionalidades**:
- Reporte diario automatico
- Reporte mensual
- Reporte por vehiculo

**Tiempo estimado**: 5-7 dias
**Prioridad**: Media

---

### 3.6 Snapshots Automaticos ⏳ PENDIENTE

**Objetivo**: Guardar imagen en eventos

**Funcionalidades**:
- Captura automatica en entry/exit
- Organizacion por fecha
- Limpieza automatica (retention)

**Directorio**:
```
snapshots/
├── 2024-11-23/
│   ├── entry_103000_ABC123.jpg
│   ├── exit_124500_ABC123.jpg
│   └── entry_110000_TEMP_5.jpg
└── 2024-11-24/
```

**Archivos a modificar**:
- `pipeline.py` - Guardar snapshot en eventos
- `config.py` - Configuracion retention

**Tiempo estimado**: 2-3 dias
**Prioridad**: Baja

---

## METRICAS DE PERFORMANCE

### Fase 3 (Con Panel Stats) - ACTUAL
```
Tiempo por frame: ~30-50ms (vehiculos conocidos)
                  ~320ms (vehiculos nuevos, 1 vez)
FPS: 20-30 (promedio)
Track IDs: 10-12 para 8 vehiculos (ratio 1.3:1)
BD writes: Minimos (solo en eventos)
Stats query: ~5ms cada 30 frames
UI: Responsiva, sin bloqueos
```

### Breakdown de Tiempo (Por Frame)

**Frame Normal**:
```
Deteccion YOLO:      ~10ms
Tracking:            ~5ms
Clasificacion:       ~0ms   (cache)
Eventos:             ~2ms
Stats query:         ~5ms   (cada 30 frames)
Dibujo:              ~3ms
TOTAL:               ~20ms  (50 FPS teórico)
```

**Frame con Vehiculo NUEVO**:
```
Deteccion YOLO:      ~10ms
Tracking:            ~5ms
Clasificacion:       ~300ms (primera vez)
  - Placa OCR:       ~250ms
  - Marca YOLO:      ~30ms
  - Color HSV:       ~20ms
Eventos:             ~2ms
BD write:            ~1ms
Dibujo:              ~3ms
TOTAL:               ~320ms
```

---

## ORDEN DE IMPLEMENTACION RECOMENDADO (Fase 3 Restante)

### Sprint Actual: ✅ Completado
Panel de Estadisticas funcional

### Sprint Proximo: Configuracion Interactiva (3.4)
**Tiempo estimado**: 2-3 dias
**Impacto**: Alto (mejora UX significativa)
1. Ventana de configuracion de linea
2. Click en imagen para posicionar
3. Vista previa en tiempo real
4. Guardado en config.py

### Sprint Siguiente: Visor de Historial (3.2)
**Tiempo estimado**: 4-5 dias
**Impacto**: Alto (funcionalidad core)
1. Ventana de historial
2. Tabla de sesiones
3. Filtros y busqueda
4. Exportacion CSV

### Sprint Opcional: Graficos (3.3)
**Tiempo estimado**: 3-4 dias
**Impacto**: Medio (visual)
1. Integrar matplotlib
2. Grafico de ocupacion
3. Selector de fecha

### Sprint Opcional 2: Reportes (3.5)
**Tiempo estimado**: 5-7 dias
**Impacto**: Medio (exportacion)
1. Implementar reportlab
2. Generacion PDF
3. Exportacion Excel/CSV

---

## ESTRUCTURA DE ARCHIVOS ACTUALIZADA

```
detector_vehiculos/
├── data/                    # Videos e imagenes
├── models/                  # Modelos YOLO
├── database/                # Base de datos
│   └── estacionamiento.db      # SQLite (NUEVO ESQUEMA)
├── snapshots/               # Capturas (futuro)
├── src/
│   ├── __init__.py
│   ├── car_detector.py         # Fase 1 ✅
│   ├── plate_recognizer.py     # Fase 1 ✅
│   ├── classifier.py           # Fase 1 ✅
│   ├── tracker.py              # Fase 2A ✅
│   ├── database.py             # Fase 2B/3 ✅ (con get_today_stats)
│   ├── event_detector.py       # Fase 2B ✅
│   ├── pipeline.py             # Fase 2C ✅
│   └── DOCUMENTATION.md        # Doc tecnica ✅
├── main.py                  # Fase 3 ✅ (con panel stats)
├── config.py                # Fase 2A-2C ✅
├── diagnostico_bd.py        # Utilidad ✅
├── requirements.txt         # Dependencias ✅
├── DOCUMENTATION.md         # Doc principal ✅
├── PLANNING.md              # Este archivo ✅
├── MIGRACION.md             # Guia migracion BD ✅
├── TROUBLESHOOTING.md       # Problemas comunes ✅
├── PANEL_ESTADISTICAS.md    # Doc panel stats ✅
└── README.md                # Readme proyecto ✅
```

---

## CRITERIOS DE EXITO

### Fase 1 ✅
- ✅ Vehiculos detectados correctamente
- ✅ Placas reconocidas
- ✅ UI funcional

### Fase 2A ✅
- ✅ IDs consistentes entre frames
- ✅ Performance >10 FPS
- ✅ Tests pasando

### Fase 2B ✅
- ✅ BD registra vehiculos
- ✅ Eventos detectan entrada/salida
- ✅ Re-identificacion funcional
- ✅ Sistema estable >1 hora

### Fase 2C ✅
- ✅ IDs optimizados
- ✅ Logging reducido 90%
- ✅ Reset funciona
- ✅ Sin crashes

### Fase 3 (Parcial) ✅
- ✅ Panel stats visible y actualizado
- ✅ Estadisticas correctas de BD
- ✅ UI responsiva
- ⏳ Historial consultable (pendiente)
- ⏳ Configuracion interactiva (pendiente)
- ⏳ Reportes exportables (pendiente)

---

## CONFIGURACION RECOMENDADA

### Para Estacionamiento Real
```python
# config.py
TRACKING_MAX_AGE = 45
TRACKING_MIN_HITS = 5
TRACKING_IOU_THRESHOLD = 0.25
CAR_MIN_CONFIDENCE = 0.5
EVENT_LINE_POSITION = 400  # Ajustar segun camara
EVENT_ENTRY_DIRECTION = 'down'
UI_STATS_UPDATE_INTERVAL = 30
```

### Para Testing con Carro de Juguete
```python
TRACKING_MIN_HITS = 2          # Mas permisivo
CAR_MIN_CONFIDENCE = 0.3       # Detecta objetos pequeños
EVENT_LINE_POSITION = 300      # Ajustar segun setup
```

---

## LIMITACIONES CONOCIDAS

### Tecnicas
1. **Placas**: Optimizado para formato peruano
2. **Marcas**: 14 marcas soportadas
3. **Colores**: 7 colores basicos
4. **Oclusiones**: Max 1.5 segundos
5. **Re-ID**: Por placa, no apariencia
6. **Stats UI**: Solo dia actual

### Performance
1. **OCR**: Lento (~250ms) pero solo 1 vez
2. **BD**: SQLite single-threaded
3. **UI**: Puede congelar en videos largos
4. **Stats**: Query agrega ~5ms cada 30 frames

### Funcionales
1. **Historial UI**: No implementado
2. **Graficos**: No implementados
3. **Exportacion**: No implementada
4. **Configuracion UI**: No implementada

---

## NOTAS IMPORTANTES

### Mantenimiento
- Limpiar BD periodicamente si crece mucho
- Backup antes de cambios mayores
- Verificar modelos YOLO presentes

### Testing
- Probar con videos diversos
- Validar precision de eventos
- Verificar estabilidad de IDs

### Expansion
- Fase 3 es modular
- Priorizar segun necesidades
- Configuracion interactiva es high-priority

---

**Ultima actualizacion**: Fase 3 (Panel Stats) completada
**Proximo objetivo**: Configuracion interactiva de linea o Visor de historial (a definir)