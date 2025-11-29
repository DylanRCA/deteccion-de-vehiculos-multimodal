# Detector de Vehiculos Multimodal + Tracking

Sistema de deteccion automatica de vehiculos con reconocimiento de placas, marca, color, tracking multi-vehiculo y panel de estadisticas en tiempo real.

## Caracteristicas

- Deteccion de vehiculos usando YOLOv8
- Reconocimiento de placas peruanas (OCR)
- Clasificacion de color y marca del vehiculo
- Tracking multi-vehiculo (ByteTrack) con IDs persistentes
- Deteccion de eventos entrada/salida
- Base de datos SQLite para persistencia
- Panel de estadisticas en tiempo real
- Reproduccion de video con estadisticas sincronizadas
- Soporte para imagenes, videos y camara en tiempo real
- Interfaz grafica intuitiva

## Estructura del Proyecto

```
detector_vehiculos/
+-- data/                    # Imagenes y videos de prueba
+-- models/                  # Modelos de IA
|   +-- car_detector.pt
|   +-- plate_detector.pt
|   +-- brand_detector.pt
+-- database/                # Base de datos SQLite
+-- src/                     # Codigo fuente
|   +-- car_detector.py
|   +-- plate_recognizer.py
|   +-- classifier.py
|   +-- tracker.py
|   +-- database.py
|   +-- event_detector.py
|   +-- pipeline.py
+-- main.py                  # Aplicacion principal
+-- config.py                # Configuraciones
+-- requirements.txt         # Dependencias
```

## Instalacion

### Requisitos Previos
- Python 3.8 o superior
- pip

### Modelos
Colocar los modelos en la carpeta `/models`:

| Modelo | Descarga |
| --- | --- |
| Detector de marcas | [Google Drive](https://drive.google.com/file/d/1JcKxU9Bz80XMNu2hd7oeYr7MdeeysyGg/view?usp=drive_link) |
| Detector de autos | [Google Drive](https://drive.google.com/file/d/1L6cJo8qc3bneezpsXarUuLzs-hMHTFkV/view?usp=drive_link) |
| Detector de placas | [Google Drive](https://drive.google.com/file/d/1nagx_2bYU8iuFM-pGYkdgVaP7eZdOX-8/view?usp=drive_link) |

### Pasos de Instalacion

1. Clonar o copiar el proyecto
2. Crear entorno virtual:
```bash
python -m venv venv
```

3. Activar entorno:
```bash
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

4. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Uso

### Iniciar la Aplicacion
```bash
python main.py
```

### Funcionalidades

**Subir Imagen**: Procesa una imagen estatica

**Subir Video**: 
- Procesa el video frame por frame
- Muestra estadisticas en tiempo real durante reproduccion
- Boton "Reproducir Video" para volver a ver

**Activar Camara**:
- Deteccion en tiempo real
- Estadisticas se guardan en base de datos
- Persiste entre sesiones

### Panel de Estadisticas

Muestra en tiempo real:
- **DENTRO**: Vehiculos actualmente en estacionamiento
- **ENTRADAS**: Total de entradas del dia
- **SALIDAS**: Total de salidas del dia
- **ULTIMA ENTRADA**: Placa y tiempo
- **ULTIMA SALIDA**: Placa y tiempo
- **DURACION PROM**: Solo en modo camara

## Configuracion

Editar `config.py` para ajustar:

```python
# Posicion de linea virtual
EVENT_LINE_POSITION = 230

# Direccion de entrada
EVENT_ENTRY_DIRECTION = 'down'

# Parametros de tracking
TRACKING_MAX_AGE = 45
TRACKING_MIN_HITS = 5
```

## Diferencias Video vs Camara

| Aspecto | Video | Camara |
|---------|-------|--------|
| Estadisticas | Temporales | Persistentes |
| Base de datos | No usa | Si usa |
| Replay | Si | No |
| Duracion prom | N/A | Calculado |

## Dependencias

- opencv-python-headless
- customtkinter
- ultralytics
- easyocr
- torch, torchvision
- Pillow
- lap, filterpy, scipy

## Creditos

- **YOLOv8**: Ultralytics
- **EasyOCR**: JaidedAI
- **ByteTrack**: Paper "Multi-Object Tracking by Associating Every Detection Box"
- **CustomTkinter**: TomSchimansky