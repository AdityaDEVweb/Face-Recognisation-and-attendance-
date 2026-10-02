import base64
import binascii
import os
import threading


class InvalidFaceImage(ValueError):
    pass


_analyzer = None
_analyzer_lock = threading.Lock()


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        with _analyzer_lock:
            if _analyzer is None:
                from insightface.app import FaceAnalysis

                _analyzer = FaceAnalysis(
                    name=os.environ.get("INSIGHTFACE_MODEL", "buffalo_l"),
                    providers=["CPUExecutionProvider"],
                )
                _analyzer.prepare(ctx_id=-1, det_size=(640, 640))
    return _analyzer


def extract_face_embedding(image_data: str) -> list[float]:
    import cv2
    import numpy as np

    encoded = image_data.partition(",")[2] if image_data.startswith("data:") else image_data
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise InvalidFaceImage("The camera image is not valid base64 data.") from error

    if not image_bytes or len(image_bytes) > 10_000_000:
        raise InvalidFaceImage("The camera image must be smaller than 10 MB.")

    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise InvalidFaceImage("The camera image could not be decoded.")

    faces = _get_analyzer().get(image)
    if not faces:
        raise InvalidFaceImage("No face detected. Center one face in the camera and try again.")
    if len(faces) != 1:
        raise InvalidFaceImage("More than one face detected. Only one person should be in frame.")

    embedding = np.asarray(faces[0].normed_embedding, dtype=np.float32)
    if embedding.size == 0 or not np.isfinite(embedding).all():
        raise InvalidFaceImage("A usable face could not be detected. Try another image.")
    return embedding.tolist()


def best_match(embedding: list[float], known_faces: list[dict]):
    best = None
    best_score = -1.0
    for person in known_faces:
        candidate = person["embedding"]
        if len(candidate) != len(embedding):
            continue
        score = sum(left * right for left, right in zip(embedding, candidate))
        if score > best_score:
            best = person
            best_score = score
    return (best, best_score) if best is not None else (None, None)