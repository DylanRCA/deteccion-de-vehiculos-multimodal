# Detector de Vehiculos Multimodal + Tracking

Sistema de deteccion automatica de vehiculos con reconocimiento de placas, marca, color y **tracking multi-vehiculo con IDs persistentes**.

## Caracteristicas

- ✅ Deteccion de vehiculos usando YOLOv8
- ✅ Reconocimiento de placas peruanas (OCR)
- ✅ Clasificacion de color y marca del vehiculo
- ✅ **NUEVO: Tracking multi-vehiculo (ByteTrack)**
- ✅ **NUEVO: IDs persistentes entre frames**
- ✅ Soporte para imagenes, videos y camara en tiempo real
- ✅ Interfaz grafica intuitiva

## Novedades - Fase 2A (Tracking)

### Sistema de Tracking Implementado

El sistema ahora mantiene IDs consistentes de vehiculos a traves de frames:

```python
Frame 1: Vehiculo ID=1 detectado
Frame 2: Vehiculo ID=1 en movimiento
Frame 3: Vehiculo ID=1 continua (mismo vehiculo!)
...
Frame 50: Vehiculo ID=1 sale del frame
```

**Ventajas**:
- Reconoce el mismo vehiculo en diferentes posiciones
- Mantiene informacion (placa, marca, color) sin re-procesamiento
- Maneja oclusiones temporales
- ~85% mas rapido en videos (clasifica solo una vez por vehiculo)

### Algoritmo: ByteTrack

Implementacion desde cero usando:
- **Filtro de Kalman**: Prediccion de movimiento
- **Algoritmo Hungaro**: Asociacion optima de detecciones
- **Sin modelos preentrenados**: Solo matematicas

**Performance**: ~10-15ms por frame adicionales

## Estructura del Proyecto

```
detector_vehiculos/
├── data/                 # Imagenes y videos de prueba
├── models/              # Modelos de IA
│   ├── car_detector.pt       # Modelo YOLO de deteccion de autos
│   ├── plate_detector.pt     # Modelo YOLO de deteccion de placas
│   └── brand_detector.pt     # Modelo YOLO de logos de marcas
├── notebooks/           # Notebooks de entrenamiento 
├── src/                 # Codigo fuente
│   ├── __init__.py
│   ├── pipeline.py      # Orquestador principal (CON TRACKING)
│   ├── car_detector.py  # Detector YOLO de autos
│   ├── plate_recognizer.py  # Detector YOLO + OCR de placas
│   ├── classifier.py    # Clasificador marca/color
│   ├── tracker.py       # NUEVO: Sistema de tracking ByteTrack
│   ├── TRACKER_DOCS.md  # NUEVO: Documentacion del tracker
│   └── DOCUMENTATION.md
├── main.py              # Aplicacion principal
├── config.py            # NUEVO: Configuraciones del sistema
├── test_tracker.py      # NUEVO: Tests del tracker
├── test_pipeline_integration.py  # NUEVO: Tests de integracion
├── requirements.txt     # Dependencias (actualizadas)
├── INTEGRACION_TRACKER.md  # NUEVO: Guia de integracion
└── README.md            # Este archivo
```

## Instalacion

### Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Modelos

Colocar los modelos en la carpeta `/models`:

| Modelo | Descarga |
| --- | --- |
| Detector de marcas | [Google Drive](https://drive.google.com/file/d/1JcKxU9Bz80XMNu2hd7oeYr7MdeeysyGg/view?usp=drive_link) |
| Detector de autos | [Google Drive](https://drive.google.com/file/d/1L6cJo8qc3bneezpsXarUuLzs-hMHTFkV/view?usp=drive_link) |
| Detector de placas | [Google Drive](https://drive.google.com/file/d/1nagx_2bYU8iuFM-pGYkdgVaP7eZdOX-8/view?usp=drive_link) |

### Pasos de Instalacion

1. Clonar o copiar la carpeta del proyecto:
```bash
cd detector_vehiculos
```

2. Crear entorno virtual (recomendado):
```bash
python -m venv venv
```

3. Activar entorno virtual:
   - Windows:
   ```bash
   venv\Scripts\activate
   ```
   - Linux/Mac:
   ```bash
   source venv/bin/activate
   ```

4. Instalar dependencias:
```bash
pip install -r requirements.txt
```

**Dependencias nuevas** (Fase 2A):
- `lap>=0.4.0` - Algoritmo hungaro
- `filterpy>=1.4.5` - Filtros de Kalman
- `scipy>=1.7.0` - Optimizacion

## Uso

### Iniciar la Aplicacion

```bash
python main.py
```

### Funcionalidades

1. **Subir Imagen**: Carga una imagen desde tu computadora para procesarla
2. **Subir Video**: Procesa un video frame por frame **CON TRACKING**
3. **Activar Camara**: Usa la camara web para deteccion en tiempo real **CON TRACKING**
4. **Procesar**: Ejecuta la deteccion en la imagen cargada

### Resultados

La aplicacion muestra:
- Rectangulos verdes alrededor de vehiculos detectados
- **Track ID persistente** (mantiene mismo numero en video)
- Informacion de cada vehiculo:
  - **Track ID** (nuevo)
  - Tipo de vehiculo
  - Numero de placa
  - Color estimado
  - Marca detectada
  - **Age**: Cuantos frames lleva el vehiculo

## Testing

### Test del Tracker

```bash
python test_tracker.py
```

Ejecuta 4 tests:
1. Calculo de IoU
2. Tracking basico
3. Manejo de oclusiones
4. Multiples vehiculos

### Test de Integracion

```bash
python test_pipeline_integration.py
```

Simula video completo con oclusiones y mide performance.

## Estado Actual

### Fase 1 ✅
- ✅ Detector de vehiculos (YOLOv8)
- ✅ Reconocimiento de placas (YOLO + OCR)
- ✅ Clasificacion de marca (YOLO de logos)
- ✅ Clasificacion de color (heuristica HSV)

### Fase 2A ✅ (COMPLETADA)
- ✅ Sistema de tracking ByteTrack implementado
- ✅ IDs persistentes funcionando
- ✅ Manejo de oclusiones
- ✅ Optimizacion de performance (85% mas rapido)
- ✅ Tests unitarios y de integracion

### Fase 2B (Siguiente)
- ⏳ Base de datos SQLite
- ⏳ Deteccion de eventos (entrada/salida)
- ⏳ Persistencia de tracks
- ⏳ UI mejorada con estadisticas

### Fase 3 (Futuro)
- ⏳ Multi-camara
- ⏳ Dashboard web
- ⏳ Ejecutable portable

## Configuracion

El archivo `config.py` contiene parametros ajustables:

```python
# Tracking
TRACKING_MAX_AGE = 30           # Frames sin deteccion antes de eliminar
TRACKING_MIN_HITS = 3           # Detecciones para confirmar track
TRACKING_IOU_THRESHOLD = 0.3    # Umbral de IoU para matching

# Deteccion
CAR_MIN_CONFIDENCE = 0.4        # Confianza minima para vehiculos

# (mas configuraciones en config.py)
```

## Performance

### Sin Tracking (Fase 1)
- Imagenes: ~500ms por imagen
- Video: ~500ms por frame (1-2 FPS)

### Con Tracking (Fase 2A)
- Primer frame de vehiculo: ~500ms (clasificacion completa)
- Frames posteriores: ~15ms (solo tracking)
- **Video promedio: ~50ms por frame (20 FPS)**

**Mejora: 10x mas rapido en videos**

## Algoritmo ByteTrack

### Como Funciona

1. **Deteccion**: YOLO detecta vehiculos en el frame
2. **Prediccion**: Kalman predice donde estara cada vehiculo
3. **Asociacion**: Algoritmo hungaro asocia detecciones con predicciones
4. **Actualizacion**: Tracks matched actualizan su posicion
5. **Gestion**: Crear nuevos tracks, eliminar tracks perdidos

### Ventajas

- ✅ Sin modelos preentrenados (solo matematicas)
- ✅ Rapido (~10-15ms por frame)
- ✅ Maneja oclusiones (hasta 30 frames)
- ✅ Multiples vehiculos simultaneos
- ✅ Codigo transparente y academicamente valido

## Documentacion Tecnica

- `src/TRACKER_DOCS.md` - Documentacion del tracker
- `INTEGRACION_TRACKER.md` - Guia de integracion con pipeline
- `SPRINT1_RESUMEN.md` - Resumen del desarrollo

## Notas Tecnicas

### Formato de Placas 

El sistema esta optimizado para reconocer placas con formato:
- Alfanumericas
- Aspect ratio aproximado 2:1 a 4:1
- Ubicacion tipica en parte inferior del vehiculo

### Tracking

- IDs comienzan en 1 y aumentan secuencialmente
- Mismo vehiculo mantiene mismo ID entre frames
- Oclusiones manejadas hasta 30 frames sin deteccion
- Re-identificacion basada en IoU (posicion y tamaño)

## Problemas Comunes

### La aplicacion no inicia
- Verifica que el entorno virtual este activado
- Asegurate de que todas las dependencias esten instaladas

### IDs cambian constantemente en video
- Ajustar `TRACKING_IOU_THRESHOLD` en `config.py`
- Aumentar `TRACKING_MIN_HITS` para mayor estabilidad

### Vehiculos no se re-identifican despues de oclusion
- Aumentar `TRACKING_MAX_AGE` en `config.py`

## Licencia

Proyecto educativo - Instituto Superior

## Creditos

**Tracking**: Basado en paper "ByteTrack: Multi-Object Tracking by Associating Every Detection Box"
**Implementacion**: Desarrollada desde cero sin dependencias de modelos preentrenados