# Configuracion del Sistema de Deteccion de Vehiculos

# ==================== TRACKING ====================
# Parametros del sistema de tracking ByteTrack

# Frames maximos sin deteccion antes de eliminar un track
# AUMENTADO: Permite que vehiculos desaparezcan temporalmente (oclusiones)
TRACKING_MAX_AGE = 45  # Antes: 30, Ahora: 45 (1.5 segundos a 30fps)

# Detecciones minimas consecutivas para confirmar un track
# AUMENTADO: Reduce falsos positivos y creacion de IDs espurios
TRACKING_MIN_HITS = 5  # Antes: 3, Ahora: 5

# Umbral de IoU para considerar un match valido
# AUMENTADO: Mas estricto para evitar matches incorrectos
TRACKING_IOU_THRESHOLD = 0.25  # Antes: 0.3, Ahora: 0.25 (mas estricto)


# ==================== DETECCION ====================
# Parametros de deteccion de vehiculos

# Confianza minima para aceptar deteccion de vehiculo (0.0-1.0)
CAR_MIN_CONFIDENCE = 0.5  # Antes: 0.4, Ahora: 0.5 (reducir detecciones espurias)


# ==================== BASE DE DATOS ====================
# Rutas y configuraciones de persistencia

# Ruta a la base de datos SQLite
DB_PATH = 'database/estacionamiento.db'

# Directorio para guardar snapshots de vehiculos
SNAPSHOT_DIR = 'snapshots/'

# Guardar snapshot solo en eventos (True) o en cada deteccion (False)
SNAPSHOT_ONLY_ON_EVENTS = True

# Frecuencia de logging de detecciones en BD (cada N frames)
# NUEVO: Reducir escrituras a BD para mejor performance
DB_DETECTION_LOG_INTERVAL = 10  # Log cada 10 frames en lugar de cada frame


# ==================== EVENTOS ====================
# Configuracion de deteccion de entrada/salida

# Posicion Y de la linea virtual (pixeles desde arriba)
EVENT_LINE_POSITION = 400

# Direccion de entrada: 'down' (hacia abajo) o 'up' (hacia arriba)
EVENT_ENTRY_DIRECTION = 'down'

# Confianza minima para registrar un evento
EVENT_MIN_CONFIDENCE = 0.6  # Antes: 0.5, Ahora: 0.6

# Tolerancia para considerar que un vehiculo cruzo la linea (pixeles)
EVENT_LINE_TOLERANCE = 15  # Antes: 10, Ahora: 15


# ==================== CAMARA ====================
# Identificacion de camaras

# ID de camara por defecto (para futura expansion multi-camara)
CAMERA_ID = 'cam_entrance'


# ==================== UI ====================
# Configuraciones de interfaz

# Actualizar estadisticas cada N frames
UI_STATS_UPDATE_INTERVAL = 30

# Tamano maximo de imagen en UI (pixeles)
UI_MAX_IMAGE_WIDTH = 900
UI_MAX_IMAGE_HEIGHT = 700


# ==================== DEBUG ====================
# Opciones de debugging

# Imprimir mensajes de debug detallados
DEBUG_VERBOSE = False  # Cambiar a True para ver todos los logs

# Mostrar IDs de tracking en imagen
DEBUG_SHOW_TRACK_IDS = True

# Mostrar linea virtual en imagen
DEBUG_SHOW_EVENT_LINE = True

# Intervalo de logging de debug (cada N frames)
DEBUG_LOG_INTERVAL = 30


# ==================== PERFORMANCE ====================
# Optimizaciones de rendimiento

# Reducir logs de deteccion en BD (solo cada N frames)
# Esto evita saturar la consola y la BD
REDUCE_DB_LOGGING = True