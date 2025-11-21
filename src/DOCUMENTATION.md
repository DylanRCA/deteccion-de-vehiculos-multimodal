# src/ - Codigo Fuente del Sistema

## Modulos Principales

### `car_detector.py`
Detector de vehiculos usando YOLOv8.

**API**:
```python
detect_vehicles(image) -> [{'bbox': [x1,y1,x2,y2], 'confidence': float, 'class': str}]
```

**Configuracion**:
- Umbral: `min_confidence=0.4` (linea 7)
- Clases: car, motorcycle, bus, truck

---

### `plate_recognizer.py`
Reconocimiento de placas (deteccion + OCR).

**API**:
```python
recognize_plate(vehicle_image) -> {'text': str, 'bbox': [x1,y1,x2,y2]|None}
```

**Estrategia**:
1. YOLO (si disponible)
2. Heuristica de contornos (fallback)
3. OCR con 4 tecnicas

**Configuracion**:
- Umbral OCR: `min_confidence=0.2` (linea 23)
- Umbral YOLO: `0.25` (linea 66)
- Longitud: 4-12 caracteres

---

### `classifier.py`
Clasificacion de marca y color.

**API**:
```python
classify(vehicle_image) -> {'brand': str, 'brand_bbox': [...]|None, 'color': str}
```

**Marca**: YOLO para logos (14 marcas), umbral 0.3
**Color**: Heuristica HSV (7 colores)

**Configuracion**:
- Umbral logo: `0.3` (linea 126)

---

### `tracker.py`
Sistema de tracking ByteTrack.

**API**:
```python
update(detections) -> [{'id': int, 'bbox': [...], 'hits': int, 'age': int, ...}]
```

**Algoritmo**:
1. Calcular matriz IoU
2. Asociar con algoritmo hungaro
3. Actualizar tracks matched
4. Crear nuevos tracks
5. Eliminar antiguos (age > max_age)

**Configuracion**:
- `max_age = 30` - Frames sin deteccion
- `min_hits = 3` - Detecciones para confirmar
- `iou_threshold = 0.3` - Umbral matching

---

### `pipeline.py`
Orquestador principal.

**Flujo**:
```python
1. car_detector.detect_vehicles()
2. tracker.update(detections)
3. Para cada track nuevo:
   - plate_recognizer.recognize_plate()
   - classifier.classify()
   - Guardar en cache
4. Dibujar resultados
```

**Optimizacion**: Cache de vehiculos conocidos (`known_vehicles`) evita re-clasificacion.

**Colores**:
- Verde: Vehiculo
- Amarillo: Placa
- Azul: Logo

---

## Dependencias entre Modulos

```
pipeline.py
├── car_detector.py
├── tracker.py
├── plate_recognizer.py
└── classifier.py
```

---

## Umbrales Configurables

| Modulo | Parametro | Valor | Ubicacion |
|--------|-----------|-------|-----------|
| car_detector | min_confidence | 0.4 | linea 7 |
| plate_recognizer | min_confidence | 0.2 | linea 23 |
| classifier | logo threshold | 0.3 | linea 126 |
| tracker | max_age | 30 | config.py |
| tracker | min_hits | 3 | config.py |
| tracker | iou_threshold | 0.3 | config.py |

---

## Coordenadas

- **Absolutas**: Respecto a imagen completa
- **Relativas**: Respecto a crop del vehiculo

**Conversion**:
```python
abs_x = vehicle_x1 + relative_x
abs_y = vehicle_y1 + relative_y
```

---

## Performance por Modulo

| Modulo | Tiempo |
|--------|--------|
| car_detector | ~100ms |
| tracker | ~15ms |
| plate_recognizer | ~300ms |
| classifier | ~60ms |
| **Total sin tracking** | ~500ms/frame |
| **Total con tracking** | ~50ms/frame |

---

## Modificaciones Comunes

### Cambiar umbral vehiculos
```python
# car_detector.py linea 7
def __init__(self, model_path=None, min_confidence=0.5):
```

### Cambiar umbral placas
```python
# plate_recognizer.py linea 23
self.min_confidence = 0.3
```

### Ajustar tracking
```python
# config.py
TRACKING_IOU_THRESHOLD = 0.25  # Mas permisivo
TRACKING_MAX_AGE = 45          # Mayor tolerancia
```

### Agregar color
```python
# classifier.py linea 49
self.colors = {
    'NARANJA': ([10, 100, 100], [20, 255, 255]),
    # ...
}
```