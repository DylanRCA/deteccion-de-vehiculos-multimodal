from __future__ import annotations
from typing import List, Dict, Any
import numpy as np

try:
    import config

    DEFAULT_MAX_AGE = getattr(config, "TRACKING_MAX_AGE", 30)
    DEFAULT_MIN_HITS = getattr(config, "TRACKING_MIN_HITS", 3)
    DEFAULT_IOU_THRESHOLD = getattr(config, "TRACKING_IOU_THRESHOLD", 0.3)
except Exception:
    DEFAULT_MAX_AGE, DEFAULT_MIN_HITS, DEFAULT_IOU_THRESHOLD = 30, 3, 0.3


class _Track:
    def __init__(self, bbox: List[float], track_id: int):
        self.id = track_id
        self.bbox = bbox
        self.hits = 1
        self.hit_streak = 1
        self.age = 0
        self.time_since_update = 0

    def update(self, bbox: List[float]) -> None:
        self.bbox = bbox
        self.hits += 1
        self.hit_streak += 1
        self.time_since_update = 0

    def mark_missed(self) -> None:
        # No incrementamos contadores aquí porque ya se hace en VehicleTracker.update
        self.hit_streak = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "bbox": [float(v) for v in self.bbox],
            "hits": self.hits,
            "hit_streak": self.hit_streak,
            "age": self.age,
            "time_since_update": self.time_since_update,
        }


class VehicleTracker:
    def __init__(
        self,
        max_age: int = DEFAULT_MAX_AGE,
        min_hits: int = DEFAULT_MIN_HITS,
        iou_threshold: float = DEFAULT_IOU_THRESHOLD,
    ):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks: List[_Track] = []
        self.next_id = 1
        self.frame_count = 0

    def _iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])

        inter_w = max(0.0, x2 - x1)
        inter_h = max(0.0, y2 - y1)
        inter_area = inter_w * inter_h

        area1 = max(0.0, (bbox1[2] - bbox1[0])) * max(0.0, (bbox1[3] - bbox1[1]))
        area2 = max(0.0, (bbox2[2] - bbox2[0])) * max(0.0, (bbox2[3] - bbox2[1]))

        denom = area1 + area2 - inter_area
        if denom <= 0.0:
            return 0.0
        return inter_area / denom

    def _associate(
        self, detections: List[Dict[str, Any]]
    ) -> (List[tuple], List[int], List[int]):
        if not self.tracks or not detections:
            return [], list(range(len(self.tracks))), list(range(len(detections)))

        iou_matrix = np.zeros((len(self.tracks), len(detections)), dtype=np.float32)
        for t_idx, track in enumerate(self.tracks):
            for d_idx, det in enumerate(detections):
                iou_matrix[t_idx, d_idx] = self._iou(track.bbox, det["bbox"])

        matches = []
        matched_tracks = set()
        matched_dets = set()

        while True:
            t_idx, d_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
            max_iou = iou_matrix[t_idx, d_idx]
            if max_iou < self.iou_threshold:
                break

            if t_idx in matched_tracks or d_idx in matched_dets:
                iou_matrix[t_idx, d_idx] = -1
                continue

            matches.append((t_idx, d_idx))
            matched_tracks.add(t_idx)
            matched_dets.add(d_idx)
            iou_matrix[t_idx, :] = -1
            iou_matrix[:, d_idx] = -1

        unmatched_tracks = [i for i in range(len(self.tracks)) if i not in matched_tracks]
        unmatched_dets = [i for i in range(len(detections)) if i not in matched_dets]
        return matches, unmatched_tracks, unmatched_dets

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.frame_count += 1
        detections = detections or []

        # Envejecer todos los tracks antes de asociar
        for track in self.tracks:
            track.age += 1
            track.time_since_update += 1

        matches, unmatched_tracks, unmatched_dets = self._associate(detections)

        # Actualizar tracks con detecciones asignadas
        for t_idx, d_idx in matches:
            self.tracks[t_idx].update(detections[d_idx]["bbox"])

        # Marcar tracks sin detección
        for t_idx in unmatched_tracks:
            self.tracks[t_idx].mark_missed()

        # Crear tracks nuevos para detecciones no asignadas
        for d_idx in unmatched_dets:
            new_track = _Track(detections[d_idx]["bbox"], self.next_id)
            self.next_id += 1
            self.tracks.append(new_track)

        # Eliminar tracks demasiado antiguos
        self.tracks = [
            track for track in self.tracks if track.time_since_update <= self.max_age
        ]

        # Devolver solo tracks confirmados (min_hits) o recién actualizados en arranque
        output = []
        for track in self.tracks:
            if track.hits >= self.min_hits or (
                track.time_since_update == 0 and self.frame_count <= self.min_hits
            ):
                output.append(track.to_dict())
        return output
