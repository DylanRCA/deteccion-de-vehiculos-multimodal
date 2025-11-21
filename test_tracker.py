"""
Script de prueba basico para VehicleTracker.
Simula detecciones y verifica que los IDs se mantienen consistentes.
"""

import sys
import os

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tracker import VehicleTracker
import numpy as np


def test_basic_tracking():
    """
    Test 1: Tracking basico - vehiculo moviendose horizontalmente.
    """
    print("\n" + "="*50)
    print("TEST 1: Tracking Basico")
    print("="*50)
    
    tracker = VehicleTracker(max_age=30, min_hits=3, iou_threshold=0.3)
    
    # Simular vehiculo moviendose de izquierda a derecha
    # Frame 1-10: vehiculo detectado
    for frame in range(1, 11):
        x1 = 100 + frame * 10  # Movimiento horizontal
        y1 = 200
        x2 = x1 + 100
        y2 = y1 + 80
        
        detections = [{
            'bbox': [x1, y1, x2, y2],
            'confidence': 0.9,
            'class': 'car'
        }]
        
        tracks = tracker.update(detections)
        
        if len(tracks) > 0:
            print(f"Frame {frame}: Track ID={tracks[0]['id']}, "
                  f"bbox={tracks[0]['bbox']}, hits={tracks[0]['hit_streak']}")
        else:
            print(f"Frame {frame}: No tracks confirmados aun")
    
    print("\nResultado: ID debe mantenerse consistente despues de frame 3")


def test_occlusion_handling():
    """
    Test 2: Manejo de oclusiones - vehiculo desaparece temporalmente.
    """
    print("\n" + "="*50)
    print("TEST 2: Manejo de Oclusiones")
    print("="*50)
    
    tracker = VehicleTracker(max_age=30, min_hits=3, iou_threshold=0.3)
    
    # Establecer vehiculo
    for frame in range(1, 6):
        detections = [{
            'bbox': [100, 200, 200, 280],
            'confidence': 0.9,
            'class': 'car'
        }]
        tracks = tracker.update(detections)
        if len(tracks) > 0:
            print(f"Frame {frame}: Track ID={tracks[0]['id']}")
    
    # Oclusion: vehiculo no detectado por 5 frames
    print("\nOclusion: vehiculo no detectado...")
    original_id = tracks[0]['id'] if len(tracks) > 0 else None
    
    for frame in range(6, 11):
        detections = []  # Sin detecciones
        tracks = tracker.update(detections)
        print(f"Frame {frame}: {len(tracks)} tracks activos")
    
    # Vehiculo reaparece
    print("\nVehiculo reaparece...")
    for frame in range(11, 14):
        detections = [{
            'bbox': [105, 205, 205, 285],  # Ligeramente movido
            'confidence': 0.9,
            'class': 'car'
        }]
        tracks = tracker.update(detections)
        if len(tracks) > 0:
            print(f"Frame {frame}: Track ID={tracks[0]['id']}")
            if tracks[0]['id'] == original_id:
                print("  ✓ ID mantenido despues de oclusion!")
            else:
                print(f"  ✗ ID cambio (original={original_id}, nuevo={tracks[0]['id']})")


def test_multiple_vehicles():
    """
    Test 3: Multiples vehiculos simultaneos.
    """
    print("\n" + "="*50)
    print("TEST 3: Multiples Vehiculos")
    print("="*50)
    
    tracker = VehicleTracker(max_age=30, min_hits=3, iou_threshold=0.3)
    
    # Dos vehiculos en diferentes posiciones
    for frame in range(1, 8):
        detections = [
            {
                'bbox': [100, 200, 200, 280],
                'confidence': 0.9,
                'class': 'car'
            },
            {
                'bbox': [400, 200, 500, 280],
                'confidence': 0.85,
                'class': 'car'
            }
        ]
        
        tracks = tracker.update(detections)
        
        if len(tracks) > 0:
            print(f"Frame {frame}: {len(tracks)} tracks")
            for track in tracks:
                print(f"  ID={track['id']}, bbox={track['bbox']}, age={track['age']}")


def test_iou_calculation():
    """
    Test 4: Verificar calculo de IoU.
    """
    print("\n" + "="*50)
    print("TEST 4: Calculo de IoU")
    print("="*50)
    
    tracker = VehicleTracker()
    
    # Mismo bbox
    bbox1 = [100, 100, 200, 200]
    bbox2 = [100, 100, 200, 200]
    iou = tracker._iou(bbox1, bbox2)
    print(f"IoU (mismo bbox): {iou:.4f} (esperado: 1.0)")
    
    # Sin overlap
    bbox1 = [100, 100, 200, 200]
    bbox2 = [300, 300, 400, 400]
    iou = tracker._iou(bbox1, bbox2)
    print(f"IoU (sin overlap): {iou:.4f} (esperado: 0.0)")
    
    # Overlap parcial
    bbox1 = [100, 100, 200, 200]
    bbox2 = [150, 150, 250, 250]
    iou = tracker._iou(bbox1, bbox2)
    print(f"IoU (overlap parcial): {iou:.4f} (esperado: ~0.14)")


def main():
    print("\n" + "="*60)
    print(" TESTS DE VehicleTracker - ByteTrack Implementation")
    print("="*60)
    
    try:
        test_iou_calculation()
        test_basic_tracking()
        test_occlusion_handling()
        test_multiple_vehicles()
        
        print("\n" + "="*60)
        print("✓ Todos los tests completados")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error en tests: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()