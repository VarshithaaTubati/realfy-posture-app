from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import mediapipe as mp
import numpy as np
import base64
import tempfile

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mp_pose = mp.solutions.pose

class WebcamFrame(BaseModel):
    image: str  # base64 image

# -------------------------------------------
# Posture check logic (improved)
# -------------------------------------------
def check_posture_landmarks(landmarks, image_width, image_height):
    feedback = []

    def get_point(idx):
        return (
            int(landmarks[idx].x * image_width),
            int(landmarks[idx].y * image_height)
        )

    try:
        left_knee = get_point(25)
        left_ankle = get_point(27)
        left_hip = get_point(23)
        left_shoulder = get_point(11)
        left_ear = get_point(7)

        # 🛌 Lying posture check
        if abs(left_shoulder[1] - left_hip[1]) < 30:
            return ["🛌 Person is lying down — skipping posture analysis."]

        # ✅ Lower body visibility
        if landmarks[25].visibility < 0.3 or landmarks[27].visibility < 0.3:
            feedback.append("⚠️ Lower body not visible — skipping leg checks.")
        else:
            # ⚠️ Knee over ankle (squat form)
            if abs(left_knee[1] - left_ankle[1]) < 15:
                feedback.append("⚠️ Knee too low (over ankle) — possible squat form issue.")



        left_knee = get_point(25)
        left_ankle = get_point(27)
        left_hip = get_point(23)
        left_toe = get_point(31)  # Add this

        # ✅ Knee goes beyond toe check (x-axis)
        if abs(left_knee[0] - left_toe[0]) > 20:  # Customize this threshold
            feedback.append("⚠️ Knee goes beyond toe — possible squat risk")


        



        # 🔍 Hunched back detection (more accurate)
        if abs(left_shoulder[1] - left_hip[1]) > 40:
            back_vector = np.array(left_shoulder) - np.array(left_hip)
            vertical = np.array([0, -1])
            back_angle = np.degrees(np.arccos(np.dot(back_vector, vertical) / (np.linalg.norm(back_vector) + 1e-6)))

            if back_angle < 150:
                feedback.append("⚠️ Hunched back detected")

        # 💻 Neck bend detection
        neck_vector = np.array(left_ear) - np.array(left_shoulder)
        vertical = np.array([0, -1])
        neck_angle = np.degrees(np.arccos(np.dot(neck_vector, vertical) / (np.linalg.norm(neck_vector) + 1e-6)))
        if neck_angle > 30:
            feedback.append("⚠️ Neck bending > 30° detected")

    except Exception as e:
        feedback.append(f"⚠️ Landmark processing failed: {str(e)}")

    return feedback if feedback else ["✅ Posture looks good"]

# -------------------------------------------
# Video Upload Analysis
# -------------------------------------------
@app.post("/analyze")
async def analyze_video(file: UploadFile = File(...)):
    print(f"📥 Received video: {file.filename}")

    temp_video = tempfile.NamedTemporaryFile(delete=False)
    temp_video.write(await file.read())
    temp_video.close()

    cap = cv2.VideoCapture(temp_video.name)
    pose = mp_pose.Pose()

    total_frames = 0
    bad_frames = 0
    lying_frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        total_frames += 1
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(frame_rgb)

        if result.pose_landmarks:
            height, width, _ = frame.shape
            feedback = check_posture_landmarks(result.pose_landmarks.landmark, width, height)

            print(f"🎞️ Frame {total_frames}: {feedback}")

            if any("⚠️" in f for f in feedback):
                bad_frames += 1
            elif any("🛌" in f for f in feedback):
                lying_frames += 1

    cap.release()
    print(f"✅ Total: {total_frames} | Bad: {bad_frames} | Lying: {lying_frames}")

    if total_frames == 0:
        return {"feedback": "❌ No frames processed", "score": 0}

    # 🎯 Scoring logic (variable)
    if bad_frames + lying_frames == total_frames:
        score = 50 if lying_frames == 0 else 70
    else:
        score = int(((total_frames - bad_frames) / total_frames) * 100)
        score = max(score, 50)

    return {
        "feedback": f"✅ Analyzed {total_frames} frames. Bad: {bad_frames}, Lying: {lying_frames}",
        "score": score
    }

# -------------------------------------------
# Webcam Snapshot Analysis
# -------------------------------------------
@app.post("/analyze_webcam")
async def analyze_webcam(data: WebcamFrame):
    try:
        header, encoded = data.image.split(",", 1)
        image_data = base64.b64decode(encoded)
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose = mp_pose.Pose()
        result = pose.process(frame_rgb)

        if result.pose_landmarks:
            height, width, _ = frame.shape
            feedback = check_posture_landmarks(result.pose_landmarks.landmark, width, height)

            # Improved score calculation based on number of warnings
            bad_count = sum(1 for f in feedback if "⚠️" in f)
            lying = any("🛌" in f for f in feedback)

            if lying:
                score = 70
            elif bad_count == 0:
                score = 100
            else:
                penalty = bad_count * 15
                score = max(100 - penalty, 50)

            return {
                "feedback": " | ".join(feedback),
                "score": score
            }
        else:
            return {"feedback": "❌ No posture detected", "score": 0}

    except Exception as e:
        return {"feedback": f"⚠️ Error: {str(e)}", "score": 0}

