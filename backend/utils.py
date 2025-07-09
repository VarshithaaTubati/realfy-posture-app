import cv2
import mediapipe as mp
import numpy as np

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

def calculate_angle(a, b, c):
    a = np.array(a)  # First point
    b = np.array(b)  # Middle point
    c = np.array(c)  # End point

    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

def analyze_frame(image, mode="squat"):
    results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    if not results.pose_landmarks:
        return {"bad_posture": False, "issues": []}

    landmarks = results.pose_landmarks.landmark
    h, w, _ = image.shape

    def get_coords(index):
        lm = landmarks[index]
        return [int(lm.x * w), int(lm.y * h)]

    issues = []

    try:
        shoulder = get_coords(mp_pose.PoseLandmark.LEFT_SHOULDER.value)
        hip = get_coords(mp_pose.PoseLandmark.LEFT_HIP.value)
        knee = get_coords(mp_pose.PoseLandmark.LEFT_KNEE.value)
        ankle = get_coords(mp_pose.PoseLandmark.LEFT_ANKLE.value)
        ear = get_coords(mp_pose.PoseLandmark.LEFT_EAR.value)

        if mode == "squat":
            back_angle = calculate_angle(shoulder, hip, knee)
            if back_angle < 150:
                issues.append("Back angle < 150°")

            if knee[0] > toe[0]:  # Replace toe with ankle if toe not available
                issues.append("Knee over toe")

        if mode == "desk":
            neck_angle = calculate_angle(shoulder, ear, [ear[0], ear[1] - 100])
            back_angle = calculate_angle(shoulder, hip, knee)
            if neck_angle > 30:
                issues.append("Neck bend > 30°")
            if back_angle < 150:
                issues.append("Back not straight")

    except:
        pass

    return {"bad_posture": len(issues) > 0, "issues": issues}
