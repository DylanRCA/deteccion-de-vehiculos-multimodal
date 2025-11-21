# Detector de Vehiculos Multimodal - Contexto del Proyecto

## Descripcion General
Sistema de deteccion automatica de vehiculos con reconocimiento de placas, marca, color y tracking multi-vehiculo con IDs persistentes para Peru.

## Estado Actual

### Fase 1 - Deteccion Basica ✅
- Deteccion de vehiculos (YOLOv8)
- Reconocimiento de placas (YOLO + OCR)
- Clasificacion de marca y color
- Interfaz grafica CustomTkinter

### Fase 2A - Sistema de Tracking ✅
- Implementacion ByteTrack
- IDs persistentes entre frames
- Manejo de oclusiones
- 10x mas rapido en videos

### Fase 2B - Persistencia y Eventos ⏳
- Base de datos SQLite
- Deteccion entrada/salida
- Panel de estadisticas
- Visor de historial

## Tecnologias Principales

- **YOLOv8**: Deteccion de vehiculos, placas y logos
- **EasyOCR**: Lectura de texto en placas
- **OpenCV**: Procesamiento de imagenes
- **CustomTkinter**: Interfaz grafica
- **ByteTrack**: Sistema de tracking
- **SQLite**: Base de datos (Fase 2B)

## Estructura del Sistema

```
1. Deteccion vehiculos (YOLO) → confianza >= 0.4
2. Tracking → IDs persistentes
3. Clasificacion (solo primera vez por vehiculo):
   ├─ Placa (YOLO + OCR)
   ├─ Logo (YOLO)
   └─ Color (HSV)
4. Visualizacion con IDs
```

## Modelos Requeridos

Colocar en carpeta `models/`:
- `car_detector.pt` - Deteccion vehiculos
- `plate_detector.pt` - Deteccion placas
- `brand_detector.pt` - Deteccion logos (14 marcas)

## Configuracion Principal

Ver `config.py`:

```python
# Tracking
TRACKING_MAX_AGE = 30
TRACKING_MIN_HITS = 3
TRACKING_IOU_THRESHOLD = 0.3

# Deteccion
CAR_MIN_CONFIDENCE = 0.4

# Eventos (Fase 2B)
EVENT_LINE_POSITION = 400
EVENT_ENTRY_DIRECTION = 'down'
```

## Formato de Salida

```
VEHICULO #1
Tipo: car
Confianza: 0.85

Placa: SI
Numero-Placa: ABC1234

Color: BLANCO
Marca: Toyota
```

## Performance

- Imagen: ~500ms
- Video sin tracking: ~500ms/frame (2 FPS)
- Video con tracking: ~50ms/frame (20 FPS)
- Mejora: 10x mas rapido

## Arquitectura

```
detector_vehiculos/
├── data/                    # Videos e imagenes
├── models/                  # Modelos YOLO
├── database/                # SQLite (Fase 2B)
├── snapshots/               # Capturas (Fase 2B)
├── src/
│   ├── car_detector.py     # Detector vehiculos
│   ├── plate_recognizer.py # Detector placas + OCR
│   ├── classifier.py       # Marca y color
│   ├── tracker.py          # Sistema tracking
│   ├── database.py         # Gestor BD (Fase 2B)
│   ├── event_detector.py   # Eventos (Fase 2B)
│   └── pipeline.py         # Orquestador
├── main.py                  # Aplicacion GUI
├── config.py                # Configuraciones
└── requirements.txt         # Dependencias
```

## Ejecutar

```bash
pip install -r requirements.txt
python main.py
```

## Notas Tecnicas

### Placas
- Formato alfanumerico
- Aspect ratio: 2:1 a 4:1
- OCR con 4 tecnicas

### Tracking
- IDs comienzan en 1
- Mismo vehiculo mantiene ID
- Oclusiones hasta 30 frames
- Re-identificacion por IoU

### Colores
BLANCO, NEGRO, GRIS, ROJO, AZUL, VERDE, AMARILLO, DESCONOCIDO

### Marcas (14)
Audi, BMW, Chevrolet, Ford, Honda, Hyundai, KIA, Mazda, Mercedes, Mitsubishi, Nissan, Suzuki, Toyota, Volkswagen

## Creditos

- YOLOv8: Ultralytics
- EasyOCR: JaidedAI
- ByteTrack: Paper "Multi-Object Tracking by Associating Every Detection Box"
- Proyecto educativo - Instituto Superior