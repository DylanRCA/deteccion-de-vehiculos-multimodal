# data/ - Datos de Prueba

## Propósito
Contiene imágenes y videos de prueba para validar el sistema.

## Estructura Recomendada
```
data/
├── images/
│   ├── test_car_1.jpg
│   ├── test_car_2.jpg
│   └── test_parking.jpg
├── videos/
│   ├── traffic_sample.mp4
│   └── parking_lot.mp4
└── results/
    └── (salidas opcionales)
```

## Archivos Ignorados
Los archivos grandes están en `.gitignore`:
- `*.mp4`, `*.avi`, `*.mov` (videos)
- `*.zip` (comprimidos)

## Tipos de Prueba Recomendados

### Imágenes de Prueba
1. **Vehículo frontal con placa visible**
   - Para validar detección completa
   - Logo y placa deben estar claros

2. **Vehículo de perfil**
   - Para probar fallback cuando no hay placa/logo

3. **Múltiples vehículos**
   - Para validar detección en estacionamientos

4. **Condiciones difíciles**
   - Baja iluminación
   - Placa sucia o parcialmente oculta
   - Vehículos lejanos

### Videos de Prueba
1. **Tráfico urbano** (30-60 seg)
2. **Estacionamiento** (cámara fija)
3. **Cámara vehicular** (dashcam)

## Formato Recomendado

**Imágenes**:
- Formato: JPG, PNG
- Resolución: 1280x720 o superior
- Peso: < 5 MB por imagen

**Videos**:
- Formato: MP4 (codec H.264)
- Resolución: 1280x720 o 1920x1080
- FPS: 25-30
- Duración: < 2 min para pruebas rápidas

## Obtener Datos de Prueba

### Imágenes
- Google Images: "autos peru placa"
- Tomar fotos propias en estacionamientos
- Datasets públicos: Stanford Cars, BIT-Vehicle

### Videos
- YouTube: "traffic peru", "estacionamiento lima"
- Dashcam footage
- CCTV samples

## Métricas de Evaluación

Al probar, validar:
- **Tasa de detección**: % vehículos detectados
- **Falsos positivos**: Objetos no-vehículos detectados
- **Lectura de placas**: % placas leídas correctamente
- **Detección de logos**: % logos identificados
- **Precisión de color**: % colores clasificados correctamente

## Ejemplo de Validación

```python
# Script de prueba simple
import cv2
from src.pipeline import VehicleDetectionPipeline

pipeline = VehicleDetectionPipeline()
image = cv2.imread('data/images/test_car_1.jpg')
result = pipeline.process_image(image)

print(f"Vehículos: {len(result['detections'])}")
for det in result['detections']:
    print(f"  - Placa: {det['Numero-Placa']}")
    print(f"  - Marca: {det['brand']}")
    print(f"  - Color: {det['color']}")
```

## NO Incluir en Git
- Videos largos (> 10 MB)
- Datasets completos
- Imágenes con información sensible (placas reales identificables)

## Privacidad
Si usas imágenes reales:
- Difuminar placas antes de compartir
- No incluir rostros visibles
- Cumplir normativas de protección de datos
