from deepface import DeepFace
import cv2

def detect_emotion(frame):
    try:
        # Convert to RGB (DeepFace expects RGB)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        result = DeepFace.analyze(
            rgb,
            actions=['emotion'],
            enforce_detection=False
        )

        # Sometimes result is list
        if isinstance(result, list):
            result = result[0]

        emotions = result.get('emotion', {})
        dominant = result.get('dominant_emotion', 'neutral')

        # ✅ SAFE confidence (fix NaN issue)
        confidence = float(emotions.get(dominant, 0) or 0)

        return dominant, confidence

    except Exception as e:
        print("Emotion Error:", e)   # helpful debug
        return "Detecting...", 0
