# src/ - Código Fuente del Sistema

## Módulos Principales

### `car_detector.py`
Detector de vehículos usando YOLOv8.
- **Filtro**: confianza >= 0.4
- **Clases COCO**: car, motorcycle, bus, truck
- **Retorna**: lista de vehículos con bbox y confianza

### `plate_recognizer.py`
Reconocimiento de placas (detección + OCR).
- **Detección**: YOLO (si existe modelo) o heurística de contornos
- **OCR**: EasyOCR con 4 técnicas de preprocesamiento
- **Validación**: longitud 4-12 chars, confianza >= 0.2
- **Retorna**: texto de placa y bbox

### `classifier.py`
Clasificación de marca y color.
- **Marca**: YOLO para detectar logos (14 marcas), retorna bbox
- **Color**: Heurística HSV (7 colores básicos)
- **Sin ML para color**: Decisión de performance
- **Retorna**: marca, brand_bbox, color

### `pipeline.py`
Orquestador principal que une todos los módulos.
- **Flujo**: Detecta vehículo → Recorta → Clasifica → Dibuja
- **Cuadros**: Verde (vehículo), Azul (logo), Amarillo (placa)
- **Formato salida**: Placa SI/NO, Numero-Placa XXXXX/------

## Dependencias entre Módulos
```
pipeline.py
├── car_detector.py (detecta vehículos)
├── plate_recognizer.py (detecta + lee placas)
└── classifier.py (detecta logos + clasifica color)
```

## Umbrales Configurables

| Módulo | Parámetro | Valor | Ubicación |
|--------|-----------|-------|-----------|
| car_detector | min_confidence | 0.4 | línea 7 |
| plate_recognizer | min_confidence | 0.2 | línea 23 |
| plate_recognizer | YOLO threshold | 0.25 | línea 66 |
| classifier | logo threshold | 0.3 | línea 126 |

## Flujo de Datos
```
Imagen BGR
  ↓
car_detector.detect_vehicles()
  ↓
Para cada vehículo:
  vehicle_crop = image[y1:y2, x1:x2]
  ↓
  ├─ plate_recognizer.recognize_plate(vehicle_crop)
  │    → {text: str, bbox: [x,y,x,y]}
  │
  ├─ classifier.classify(vehicle_crop)
  │    → {brand: str, brand_bbox: [x,y,x,y], color: str}
  │
  └─ Merge en vehicle_info dict
  ↓
pipeline._draw_results()
  ↓
Imagen anotada + lista de detecciones
```

## Coordenadas
- **Absolutas**: Respecto a imagen completa
- **Relativas**: Respecto a crop del vehículo
- **Conversión**: `abs_x = vehicle_x + relative_x`

## Modificaciones Comunes

### Cambiar umbral de vehículos
```python
# car_detector.py línea 7
def __init__(self, model_path=None, min_confidence=0.5):  # Cambiar 0.4 → 0.5
```

### Cambiar umbral de placas
```python
# plate_recognizer.py línea 23
self.min_confidence = 0.3  # Cambiar 0.2 → 0.3
```

### Agregar nuevo color
```python
# classifier.py línea 49
self.colors = {
    'NARANJA': ([10, 100, 100], [20, 255, 255]),  # Agregar
    # ... resto de colores
}
```
