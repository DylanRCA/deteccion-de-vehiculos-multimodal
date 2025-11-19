# Detector de Vehiculos Multimodal

Sistema de deteccion automatica de vehiculos con reconocimiento de placas, marca y color.

## Caracteristicas

- Deteccion de vehiculos usando YOLOv8
- Reconocimiento de placas peruanas (OCR)
- Clasificacion de color del vehiculo
- Soporte para imagenes, videos y camara en tiempo real
- Interfaz grafica intuitiva

## Estructura del Proyecto

```
detector_vehiculos/
├── data/                 # Imagenes y videos de prueba
├── models/              # Modelos de IA
│   ├── car_detector.pt       # Modelo YOLO de detección de autos
│   └── plate_detector.pt     # Modelo YOLO de detección de placas
├── notebooks/           # Notebooks de entrenamiento 
├── src/                 # Codigo fuente
│   ├── __init__.py
│   ├── pipeline.py      # Orquestador principal
│   ├── car_detector.py  # Detector YOLO de autos
│   ├── plate_recognizer.py  # Detector YOLO + OCR de placas
│   └── classifier.py    # Clasificador marca/color
├── main.py              # Aplicacion principal
└── requirements.txt     # Dependencias
```

## Instalacion

### Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

#### Colocar los modelos en la carpeta /models
| Modelo | Descarga |
| --- | --- |
| Detector de marcas | https://drive.google.com/file/d/1JcKxU9Bz80XMNu2hd7oeYr7MdeeysyGg/view?usp=drive_link |
| Detector de autos | https://drive.google.com/file/d/1L6cJo8qc3bneezpsXarUuLzs-hMHTFkV/view?usp=drive_link |
| Detector de placas(sin lectura) | https://drive.google.com/file/d/1nagx_2bYU8iuFM-pGYkdgVaP7eZdOX-8/view?usp=drive_link |


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

**Nota**: La primera vez que ejecutes la aplicacion, YOLO y EasyOCR descargaran automaticamente los modelos necesarios (puede tardar varios minutos dependiendo de tu conexion).

## Uso

### Iniciar la Aplicacion

```bash
python main.py
```

### Funcionalidades

1. **Subir Imagen**: Carga una imagen desde tu computadora para procesarla
2. **Subir Video**: Procesa un video frame por frame
3. **Activar Camara**: Usa la camara web para deteccion en tiempo real
4. **Procesar**: Ejecuta la deteccion en la imagen cargada

### Resultados

La aplicacion muestra:
- Rectangulos verdes alrededor de vehiculos detectados
- Informacion de cada vehiculo:
  - Tipo de vehiculo
  - Numero de placa
  - Color estimado
  - Marca (placeholder en Fase 1)

## Estado Actual (Fase 1)

✅ Detector de vehiculos (YOLOv8)
✅ Reconocimiento de placas:
   - Detección con YOLO personalizado (si existe `models/plate_detector.pt`)
   - Lectura con EasyOCR (múltiples técnicas de preprocesamiento)
   - Fallback a heurística si no hay modelo
✅ Clasificacion de color (heuristica HSV)
✅ Clasificacion de marca:
   - Detección de logos con YOLO (si existe `models/brand_detector.pt`)
   - 14 marcas soportadas
   - Fallback a "DESCONOCIDA" si no hay modelo

## Modelos Personalizados

### Colocar tus Modelos

Coloca tus modelos entrenados en la carpeta `models/`:

```
models/
├── car_detector.pt      # Tu modelo YOLO de detección de autos
├── plate_detector.pt    # Tu modelo YOLO de detección de placas
└── brand_detector.pt    # Tu modelo YOLO de detección de logos de marcas
```

### Comportamiento

- **car_detector.pt**: Si existe, se usa. Si no, descarga `yolov8n.pt` automáticamente
- **plate_detector.pt**: Si existe, se usa para detectar placas. Si no, usa heurística de contornos
- **brand_detector.pt**: Si existe, se usa para detectar logos. Si no, retorna "DESCONOCIDA"

### Requisitos de los Modelos

- **Formato**: `.pt` (PyTorch/Ultralytics YOLO)
- **car_detector.pt**: Debe detectar clase de autos (cualquier índice de clase)
- **plate_detector.pt**: Debe detectar placas (cualquier índice de clase)
- **brand_detector.pt**: Debe detectar logos con clases:
  ```
  0: Audi, 1: BMW, 2: Chevrolet, 3: Ford, 4: Honda,
  5: Hyundai, 6: KIA, 7: Mazda, 8: Mercedes, 9: Mitsubishi,
  10: Nissan, 11: Suzuki, 12: Toyota, 13: Volkswagen
  ```

## Proximos Pasos (Fase 2)

- Entrenar modelo personalizado para clasificacion de marca
- Mejorar deteccion de placas con modelo YOLO especializado
- Crear datasets de entrenamiento
- Fine-tuning de modelos

## Fase 3: Ejecutable Portable

Una vez completadas las fases anteriores, se creara un archivo .exe portable usando PyInstaller para distribucion sin necesidad de instalar Python.

## Notas Tecnicas

### Formato de Placas 

El sistema esta optimizado para reconocer placas con formato:
- Alfanumericas
- Aspect ratio aproximado 2:1 a 4:1
- Ubicacion tipica en parte inferior del vehiculo

### Rendimiento

- Imagenes: Procesamiento bajo demanda
- Video/Camara: ~30 FPS (depende del hardware)
- Primera carga: Puede tardar debido a descarga de modelos

## Problemas Comunes

### La aplicacion no inicia
- Verifica que el entorno virtual este activado
- Asegurate de que todas las dependencias esten instaladas

### No detecta vehiculos
- Verifica que la imagen tenga buena calidad y resolucion
- Asegurate de que los vehiculos sean visibles claramente

### No reconoce placas
- Las placas deben estar visibles y no muy pixeladas
- El sistema funciona mejor con placas limpias y bien iluminadas

## Licencia

Proyecto educativo - Instituto Superior
