from flask import Flask, render_template, Response, request, redirect, session, jsonify
import cv2
import sqlite3
import time
import os
from emotion import detect_emotion

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- CAMERA ----------
camera = cv2.VideoCapture(0)
time.sleep(2)

if not camera.isOpened():
    print("❌ Camera not working")
else:
    print("✅ Camera started")

# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS emotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            emotion TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- GLOBAL ----------
frame_count = 0
current_emotion = "Detecting..."
last_saved_time = 0
emotion_history = []

# ---------- VIDEO STREAM ----------
def generate_frames():
    global frame_count, current_emotion, last_saved_time, emotion_history

    while True:
        success, frame = camera.read()

        if not success or frame is None or frame.size == 0:
            continue

        frame = cv2.flip(frame, 1)
        frame_count += 1

        # ---------- EMOTION DETECTION ----------
        if frame_count % 15 == 0:   # faster detection
            try:
                emotion, confidence = detect_emotion(frame)

                # store history (reduced size for faster response)
                emotion_history.append(emotion)

                if len(emotion_history) > 5:
                    emotion_history.pop(0)

                # majority vote
                current_emotion = max(set(emotion_history), key=emotion_history.count)

            except:
                current_emotion = "Detecting..."

        # ---------- SAVE TO DB (FASTER) ----------
        if time.time() - last_saved_time > 1:
            try:
                conn = get_db()
                conn.execute(
                    "INSERT INTO emotions (username, emotion, timestamp) VALUES (?, ?, ?)",
                    (session.get("user", "guest"), current_emotion, time.strftime("%H:%M:%S"))
                )
                conn.commit()
                conn.close()

                last_saved_time = time.time()

                print("Saving:", current_emotion)

            except:
                pass

        # ---------- DRAW ----------
        cv2.rectangle(frame, (20, 20), (400, 80), (0, 0, 0), -1)
        cv2.putText(frame, current_emotion.upper(), (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# ---------- ROUTES ----------
@app.route('/')
def index():
    if "user" in session:
        return render_template("index.html")
    return redirect("/login")

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session["user"] = request.form.get("username")
        return redirect("/")
    return render_template("login.html")

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

# ---------- API (REAL-TIME FIXED) ----------
@app.route('/api/live_emotions')
def live_emotions():
    conn = get_db()

    data = conn.execute("""
        SELECT emotion, COUNT(*) 
        FROM (
            SELECT emotion FROM emotions 
            WHERE emotion NOT IN ('Detecting...', 'No Face')
            ORDER BY id DESC LIMIT 5
        ) 
        GROUP BY emotion
    """).fetchall()

    conn.close()

    return jsonify([{"emotion": r[0], "count": r[1]} for r in data])

# ---------- CURRENT EMOTION (INSTANT) ----------
@app.route('/api/current_emotion')
def current():
    return jsonify({"emotion": current_emotion})

@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect("/login")

# ---------- CLEANUP ----------
import atexit
def release_camera():
    camera.release()
atexit.register(release_camera)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, threaded=True)
