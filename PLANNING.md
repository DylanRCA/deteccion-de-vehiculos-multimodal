# Plan de Desarrollo - Sistema de Estacionamiento Inteligente

## Vision General
Sistema completo de deteccion y gestion de vehiculos con tracking, persistencia, deteccion de eventos entrada/salida y panel de estadisticas en tiempo real.

**Estado**: Fase 3 completada
**Fecha**: Noviembre 2024

---

## FASES COMPLETADAS

### Fase 1: Deteccion Basica - COMPLETADA
- Detector de vehiculos (YOLOv8)
- Reconocimiento de placas (YOLO + OCR)
- Clasificacion de marca (YOLO logos)
- Clasificacion de color (heuristica HSV)
- Interfaz GUI basica

### Fase 2A: Sistema de Tracking - COMPLETADA
- Implementacion ByteTrack
- IDs persistentes entre frames
- Manejo de oclusiones
- Optimizacion performance

### Fase 2B: Base de Datos y Eventos - COMPLETADA
- SQLite con 3 tablas (active_vehicles, parking_history, vehicle_registry)
- Detector de eventos entrada/salida
- Linea virtual configurable
- Re-identificacion por placa
- IDs temporales para vehiculos sin placa

### Fase 3: UI y Estadisticas - COMPLETADA
- Panel estadisticas en tiempo real
- Estadisticas separadas video/camara
- Ultima entrada y ultima salida
- Reproduccion video con stats sincronizadas
- Boton "Reproducir Video" para replay
- Conteo correcto de entradas (active + history)

---

## ESTRUCTURA DE ARCHIVOS

```
detector_vehiculos/
+-- data/                    # Videos e imagenes
+-- models/                  # Modelos YOLO
|   +-- car_detector.pt
|   +-- plate_detector.pt
|   +-- brand_detector.pt
+-- database/
|   +-- estacionamiento.db
+-- src/
|   +-- __init__.py
|   +-- car_detector.py
|   +-- plate_recognizer.py
|   +-- classifier.py
|   +-- tracker.py
|   +-- database.py
|   +-- event_detector.py
|   +-- pipeline.py
|   +-- DOCUMENTATION.md
+-- main.py
+-- config.py
+-- requirements.txt
+-- DOCUMENTATION.md
+-- PLANNING.md
+-- README.md
```

---

## CONFIGURACION ACTUAL

### config.py
```python
# Tracking
TRACKING_MAX_AGE = 45
TRACKING_MIN_HITS = 5
TRACKING_IOU_THRESHOLD = 0.25

# Deteccion
CAR_MIN_CONFIDENCE = 0.5

# Eventos
EVENT_LINE_POSITION = 230
EVENT_ENTRY_DIRECTION = 'down'

# Performance
REDETECTION_INTERVAL_CAMERA = 30
REDETECTION_INTERVAL_VIDEO = 5
```

---

## POSIBLES MEJORAS FUTURAS

### Prioridad Alta
- Configuracion interactiva de linea virtual (click en imagen)
- Visor de historial de sesiones
- Limpiar BD automaticamente

### Prioridad Media
- Graficos de ocupacion
- Reportes exportables (PDF/CSV)
- Snapshots automaticos en eventos

### Prioridad Baja
- Multi-camara
- Dashboard web
- Ejecutable portable

---

## NOTAS TECNICAS

### Estadisticas Video vs Camara
- **Video**: Usa `_video_stats` en memoria, no persiste
- **Camara**: Usa BD, persiste en `active_vehicles` y `parking_history`

### Conteo de Entradas
- Entradas = vehiculos en `active_vehicles`(hoy) + vehiculos en `parking_history`(hoy)
- Esto asegura que las entradas se cuenten inmediatamente, no solo al salir

### Reproduccion de Video
- Frames guardados en `processed_frames`
- Stats por frame en `video_stats_history`
- Permite replay con estadisticas sincronizadas