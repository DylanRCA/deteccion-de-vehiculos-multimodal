# Configuracion del Sistema de Deteccion de Vehiculos

# ==================== TRACKING ====================
# Parametros del sistema de tracking ByteTrack

# Frames maximos sin deteccion antes de eliminar un track
TRACKING_MAX_AGE = 30

# Detecciones minimas consecutivas para confirmar un track
TRACKING_MIN_HITS = 3

# Umbral de IoU para considerar un match valido
TRACKING_IOU_THRESHOLD = 0.3


# ==================== DETECCION ====================
# Parametros de deteccion de vehiculos

# Confianza minima para aceptar deteccion de vehiculo (0.0-1.0)
CAR_MIN_CONFIDENCE = 0.4


# ==================== BASE DE DATOS ====================
# Rutas y configuraciones de persistencia

# Ruta a la base de datos SQLite
DB_PATH = 'database/estacionamiento.db'

# Directorio para guardar snapshots de vehiculos
SNAPSHOT_DIR = 'snapshots/'

# Guardar snapshot solo en eventos (True) o en cada deteccion (False)
SNAPSHOT_ONLY_ON_EVENTS = True


# ==================== EVENTOS ====================
# Configuracion de deteccion de entrada/salida

# Posicion Y de la linea virtual (pixeles desde arriba)
EVENT_LINE_POSITION = 400

# Direccion de entrada: 'down' (hacia abajo) o 'up' (hacia arriba)
EVENT_ENTRY_DIRECTION = 'down'

# Confianza minima para registrar un evento
EVENT_MIN_CONFIDENCE = 0.5

# Tolerancia para considerar que un vehiculo cruzo la linea (pixeles)
EVENT_LINE_TOLERANCE = 10


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
DEBUG_VERBOSE = True

# Mostrar IDs de tracking en imagen
DEBUG_SHOW_TRACK_IDS = True

# Mostrar linea virtual en imagen
DEBUG_SHOW_EVENT_LINE = True