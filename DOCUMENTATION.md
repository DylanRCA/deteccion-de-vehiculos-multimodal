# Detector de Vehículos Multimodal - Contexto del Proyecto

## Descripción General
Sistema de detección automática de vehículos con reconocimiento de placas, marca y color para Perú.

## Tecnologías Principales
- **YOLOv8**: Detección de vehículos, placas y logos
- **EasyOCR**: Lectura de texto en placas
- **OpenCV**: Procesamiento de imágenes
- **CustomTkinter**: Interfaz gráfica moderna

## Estructura del Sistema
```
1. Detección de vehículos (YOLO) → Filtro confianza >= 0.4
2. Para cada vehículo:
   ├─ Detección de placa (YOLO + OCR)
   ├─ Detección de logo (YOLO)
   └─ Clasificación de color (heurística HSV)
3. Visualización con cuadros de colores
```

## Modelos Requeridos
Colocar en carpeta `models/`:
- `car_detector.pt` - YOLO para vehículos
- `plate_detector.pt` - YOLO para placas
- `brand_detector.pt` - YOLO para logos (14 marcas)

## Estado Actual
- ✅ Detección de vehículos con umbral 0.4
- ✅ Reconocimiento de placas (YOLO + OCR)
- ✅ Detección de logos con bbox
- ✅ Color por heurística HSV (sin ML)
- ✅ Visualización: verde (vehículo), azul (logo), amarillo (placa)

## Formato de Salida
```
Placa: SI/NO
Numero-Placa: ABC1234 o ------
Color: BLANCO, NEGRO, etc.
Marca: Toyota, Honda, DESCONOCIDA, etc.
```

## Decisiones de Diseño
1. **Color sin ML**: Se mantiene heurística HSV para performance
2. **Fallbacks**: Si falta modelo, usa alternativas (YOLO predeterminado, heurísticas)
3. **Umbrales permisivos**: Maximizar detecciones reales, minimizar falsos positivos

## Ejecutar
```bash
python main.py
```
