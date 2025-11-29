# src/ - Codigo Fuente del Sistema

## Modulos

### car_detector.py
Detector de vehiculos usando YOLOv8.

**API**:
```python
detect_vehicles(image) -> [{'bbox': [x1,y1,x2,y2], 'confidence': float, 'class': str}]
```

**Configuracion**: `CAR_MIN_CONFIDENCE = 0.5`

---

### plate_recognizer.py
Reconocimiento de placas (deteccion + OCR).

**API**:
```python
recognize_plate(vehicle_image) -> {'text': str, 'bbox': [x1,y1,x2,y2]|None}
```

**Estrategia**:
1. YOLO para detectar region de placa
2. OCR con 4 tecnicas de binarizacion
3. Validacion de formato

---

### classifier.py
Clasificacion de marca y color.

**API**:
```python
classify(vehicle_image) -> {'brand': str, 'brand_bbox': [...]|None, 'color': str}
```

**Marca**: YOLO para logos (14 marcas)
**Color**: Heuristica HSV (7 colores)

---

### tracker.py
Sistema de tracking ByteTrack.

**API**:
```python
update(detections) -> [{'id': int, 'bbox': [...], 'hits': int, 'age': int, ...}]
```

**Parametros**:
- `max_age = 45` - Frames sin deteccion
- `min_hits = 5` - Detecciones para confirmar
- `iou_threshold = 0.25` - Umbral matching

---

### database.py
Gestor de base de datos SQLite.

**Tablas**:
- `active_vehicles` - Vehiculos dentro ahora
- `parking_history` - Sesiones completadas
- `vehicle_registry` - Catalogo de vehiculos

**API Principal**:
```python
register_entry(plate, track_id, brand, color) -> int
register_exit(plate) -> dict
get_active_vehicles() -> list
get_today_stats() -> dict  # inside, entries, exits, last_entry, last_exit
```

---

### event_detector.py
Detector de eventos entrada/salida.

**API**:
```python
configure_line(y_position, entry_direction)
detect_events(tracks) -> [{'track_id': int, 'event': str, 'timestamp': datetime}]
draw_line(image) -> image
reset_history()
```

**Algoritmo**: Detecta cruces de linea virtual usando historial de centroides.

---

### pipeline.py
Orquestador principal.

**Modos**:
- `video`: Stats temporales en memoria
- `camera`: Stats en BD

**API**:
```python
__init__(car_min_confidence, enable_database, enable_events, mode)
reset()
process_image(image) -> dict
process_video_frame(frame) -> dict
get_video_stats() -> dict  # inside, entries, exits, last_entry, last_exit
```

**Stats de video (_video_stats)**:
```python
{
    'inside': int,       # Contador (no set)
    'entries': int,
    'exits': int,
    'last_entry': dict,  # {plate, timestamp}
    'last_exit': dict    # {plate, timestamp}
}
```

---

## Flujo de Datos

```
CarDetector.detect_vehicles()
    |
VehicleTracker.update()
    |
PlateRecognizer + VehicleClassifier (solo nuevos)
    |
EventDetector.detect_events()
    |
Pipeline._update_video_stats() o DatabaseManager
    |
Pipeline._draw_results()
```

---

## Configuracion (config.py)

| Parametro | Valor | Descripcion |
|-----------|-------|-------------|
| TRACKING_MAX_AGE | 45 | Frames sin deteccion |
| TRACKING_MIN_HITS | 5 | Detecciones para confirmar |
| TRACKING_IOU_THRESHOLD | 0.25 | Umbral matching |
| CAR_MIN_CONFIDENCE | 0.5 | Confianza minima |
| EVENT_LINE_POSITION | 230 | Posicion Y linea |
| EVENT_ENTRY_DIRECTION | 'down' | Direccion entrada |