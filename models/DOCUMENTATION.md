# models/ - Modelos de Machine Learning

## Modelos Requeridos

### `car_detector.pt` (Obligatorio)
- **Tipo**: YOLOv8 PyTorch
- **Función**: Detectar vehículos en imagen
- **Clases**: Cualquier clase de vehículo (car, truck, bus, etc.)
- **Fallback**: Si no existe, descarga `yolov8n.pt` automáticamente
- **Umbral**: Confianza >= 0.4 para procesar

### `plate_detector.pt` (Opcional)
- **Tipo**: YOLOv8 PyTorch
- **Función**: Detectar región de placa en vehículo
- **Clases**: 1 clase (plate/placa)
- **Fallback**: Heurística de contornos si no existe
- **Umbral**: Confianza >= 0.25

### `brand_detector.pt` (Opcional)
- **Tipo**: YOLOv8 PyTorch
- **Función**: Detectar logos de marcas
- **Clases**: 14 marcas
  ```
  0: Audi, 1: BMW, 2: Chevrolet, 3: Ford
  4: Honda, 5: Hyundai, 6: KIA, 7: Mazda
  8: Mercedes, 9: Mitsubishi, 10: Nissan
  11: Suzuki, 12: Toyota, 13: Volkswagen
  ```
- **Fallback**: Retorna "DESCONOCIDA" si no existe
- **Umbral**: Confianza >= 0.3

## NO Incluido

### ❌ `color_model.h5`
**Decisión**: NO se usa modelo de clasificación de color.
**Razón**: Performance. Se mantiene heurística HSV.
**Alternativa actual**: `classifier._detect_dominant_color()` con rangos HSV

## Descarga de Modelos

Los modelos están en `.gitignore` por ser archivos grandes.

**Enlaces de descarga**:
- Detector de autos: [Google Drive](https://drive.google.com/file/d/1L6cJo8qc3bneezpsXarUuLzs-hMHTFkV/view?usp=drive_link)
- Detector de placas: [Google Drive](https://drive.google.com/file/d/1nagx_2bYU8iuFM-pGYkdgVaP7eZdOX-8/view?usp=drive_link)
- Detector de marcas: [Google Drive](https://drive.google.com/file/d/1JcKxU9Bz80XMNu2hd7oeYr7MdeeysyGg/view?usp=drive_link)

## Formato de Modelos

Todos los modelos deben ser:
- **Formato**: `.pt` (PyTorch - Ultralytics YOLO)
- **Framework**: Ultralytics YOLOv8
- **NO usar**: `.h5`, `.onnx`, `.pth` (otros formatos)

## Verificar Modelos

```python
from ultralytics import YOLO

# Cargar y verificar
model = YOLO('models/car_detector.pt')
print(model.names)  # Ver clases
```

## Entrenar Modelos Personalizados

Para entrenar tus propios modelos:

```python
from ultralytics import YOLO

# 1. Cargar modelo base
model = YOLO('yolov8n.pt')

# 2. Entrenar
model.train(
    data='dataset.yaml',
    epochs=100,
    imgsz=640
)

# 3. Guardar
model.save('models/custom_detector.pt')
```

## Tamaños Típicos

- `car_detector.pt`: ~6-50 MB (depende de modelo base)
- `plate_detector.pt`: ~6-20 MB
- `brand_detector.pt`: ~6-20 MB

## Troubleshooting

### Modelo no carga
```
Error: No such file or directory
```
**Solución**: Verificar que el archivo `.pt` está en `models/` y no está corrupto.

### Clases incorrectas
```python
# Verificar clases del modelo
model = YOLO('models/brand_detector.pt')
print(model.names)  # Debe coincidir con brand_names en classifier.py
```

### Performance lento
- Usar modelos más pequeños (yolov8n vs yolov8x)
- Reducir resolución de entrada
- Verificar uso de GPU vs CPU
