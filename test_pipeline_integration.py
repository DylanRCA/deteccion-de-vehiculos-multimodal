"""
Test de integracion: Pipeline + Tracker
Simula frames de video para verificar que el tracking funciona correctamente.
"""

import sys
import os
import numpy as np
import cv2

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tracker import VehicleTracker


def create_synthetic_frame(frame_num, vehicles):
    """
    Crea un frame sintetico con vehiculos.
    
    Args:
        frame_num: Numero de frame
        vehicles: Lista de vehiculos [(x, y, w, h), ...]
        
    Returns:
        Frame BGR (numpy array)
    """
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (50, 50, 50)  # Fondo gris oscuro
    
    for i, (x, y, w, h) in enumerate(vehicles):
        # Dibujar vehiculo como rectangulo
        color = (0, 255, 0) if i == 0 else (0, 100, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, -1)
        
        # Dibujar "ventanas"
        cv2.rectangle(frame, (x+10, y+10), (x+w-10, y+20), (200, 200, 200), -1)
    
    # Agregar numero de frame
    cv2.putText(frame, f"Frame {frame_num}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    return frame


def test_pipeline_integration():
    """
    Test de integracion: simula video con vehiculos moviendose.
    """
    print("\n" + "="*60)
    print("TEST INTEGRACION: Pipeline + Tracker")
    print("="*60)
    
    tracker = VehicleTracker(max_age=30, min_hits=3, iou_threshold=0.3)
    
    # Escenario: 2 vehiculos moviendose
    # Vehiculo 1: Entra desde izquierda
    # Vehiculo 2: Estatico a la derecha
    
    scenarios = []
    
    # Frames 1-5: Vehiculo 1 entra desde izquierda
    for i in range(5):
        x1 = 50 + i * 30
        scenarios.append([
            (x1, 200, 100, 80),      # Vehiculo 1 moviendose
            (450, 150, 100, 80)      # Vehiculo 2 estatico
        ])
    
    # Frames 6-8: Vehiculo 1 desaparece (oclusion)
    for i in range(3):
        scenarios.append([
            (450, 150, 100, 80)      # Solo vehiculo 2
        ])
    
    # Frames 9-12: Vehiculo 1 reaparece
    for i in range(4):
        x1 = 230 + i * 20
        scenarios.append([
            (x1, 200, 100, 80),      # Vehiculo 1 reaparece
            (450, 150, 100, 80)      # Vehiculo 2 estatico
        ])
    
    # Ejecutar simulacion
    print("\nSimulando video...")
    track_history = {}
    
    for frame_num, vehicles in enumerate(scenarios, start=1):
        # Crear frame sintetico
        frame = create_synthetic_frame(frame_num, vehicles)
        
        # Simular detecciones
        detections = []
        for x, y, w, h in vehicles:
            detections.append({
                'bbox': [x, y, x+w, y+h],
                'confidence': 0.9,
                'class': 'car'
            })
        
        # Actualizar tracker
        tracks = tracker.update(detections)
        
        # Guardar historial
        for track in tracks:
            track_id = track['id']
            if track_id not in track_history:
                track_history[track_id] = []
            track_history[track_id].append(frame_num)
        
        # Mostrar estado
        if len(tracks) > 0:
            print(f"Frame {frame_num:2d}: {len(tracks)} tracks - ", end="")
            for track in tracks:
                print(f"ID={track['id']} (age={track['age']}, hits={track['hit_streak']}) ", end="")
            print()
        else:
            print(f"Frame {frame_num:2d}: No tracks confirmados")
    
    # Analizar resultados
    print("\n" + "-"*60)
    print("ANALISIS DE TRACKING:")
    print("-"*60)
    
    for track_id, frames in track_history.items():
        print(f"\nTrack ID {track_id}:")
        print(f"  Frames activo: {frames}")
        print(f"  Total frames: {len(frames)}")
        print(f"  Primer frame: {frames[0]}")
        print(f"  Ultimo frame: {frames[-1]}")
        
        # Detectar gaps (oclusiones)
        gaps = []
        for i in range(len(frames)-1):
            gap = frames[i+1] - frames[i] - 1
            if gap > 0:
                gaps.append((frames[i], frames[i+1], gap))
        
        if gaps:
            print(f"  Oclusiones detectadas: {len(gaps)}")
            for start, end, duration in gaps:
                print(f"    - Frames {start}-{end} (gap de {duration} frames)")
    
    # Verificaciones
    print("\n" + "-"*60)
    print("VERIFICACIONES:")
    print("-"*60)
    
    if len(track_history) == 2:
        print("✓ Correcto: 2 vehiculos trackeados (esperado: 2)")
    else:
        print(f"✗ Error: {len(track_history)} vehiculos (esperado: 2)")
    
    # Verificar que vehiculo 1 mantuvo ID despues de oclusion
    # El vehiculo 1 deberia estar en frames 1-5 y 9-12
    vehiculo1_found = False
    for track_id, frames in track_history.items():
        if 1 in frames and 12 in frames:
            vehiculo1_found = True
            print(f"✓ Vehiculo 1 (ID={track_id}) mantuvo ID despues de oclusion")
            break
    
    if not vehiculo1_found:
        print("✗ Vehiculo 1 no mantuvo ID despues de oclusion")
    
    print("\n" + "="*60)


def test_performance():
    """
    Test de performance: medir velocidad de tracking.
    """
    print("\n" + "="*60)
    print("TEST PERFORMANCE: Velocidad de Tracking")
    print("="*60)
    
    import time
    
    tracker = VehicleTracker(max_age=30, min_hits=3, iou_threshold=0.3)
    
    # Simular 100 frames con 10 vehiculos
    num_frames = 100
    num_vehicles = 10
    
    times = []
    
    print(f"\nProcesando {num_frames} frames con {num_vehicles} vehiculos...")
    
    for frame_num in range(num_frames):
        # Generar detecciones aleatorias
        detections = []
        for i in range(num_vehicles):
            x = np.random.randint(50, 500)
            y = np.random.randint(50, 400)
            w = np.random.randint(80, 120)
            h = np.random.randint(60, 100)
            
            detections.append({
                'bbox': [x, y, x+w, y+h],
                'confidence': 0.8 + np.random.random() * 0.2,
                'class': 'car'
            })
        
        # Medir tiempo
        start = time.time()
        tracks = tracker.update(detections)
        end = time.time()
        
        times.append((end - start) * 1000)  # En ms
    
    # Estadisticas
    avg_time = np.mean(times)
    min_time = np.min(times)
    max_time = np.max(times)
    std_time = np.std(times)
    
    print(f"\nResultados:")
    print(f"  Tiempo promedio: {avg_time:.2f} ms/frame")
    print(f"  Tiempo minimo:   {min_time:.2f} ms")
    print(f"  Tiempo maximo:   {max_time:.2f} ms")
    print(f"  Desv. estandar:  {std_time:.2f} ms")
    print(f"  FPS estimado:    {1000/avg_time:.1f} fps")
    
    if avg_time < 20:
        print("\n✓ Performance excelente (<20ms por frame)")
    elif avg_time < 50:
        print("\n✓ Performance buena (<50ms por frame)")
    else:
        print("\n⚠ Performance podria mejorar (>50ms por frame)")
    
    print("="*60)


def main():
    try:
        test_pipeline_integration()
        test_performance()
        
        print("\n✓ Tests de integracion completados\n")
        
    except Exception as e:
        print(f"\n✗ Error en tests: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()