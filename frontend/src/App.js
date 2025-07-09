import React, { useRef, useState, useEffect } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import "./App.css";

function App() {
  const webcamRef = useRef(null);
  const [postureResult, setPostureResult] = useState("");
  const [postureScore, setPostureScore] = useState(null);
  const [isSending, setIsSending] = useState(false);
  const [mode, setMode] = useState("auto");

  useEffect(() => {
    let interval = null;
    if (mode === "auto") {
      interval = setInterval(() => {
        captureAndSendFrame();
      }, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [mode]);

  const captureAndSendFrame = async () => {
    if (
      webcamRef.current &&
      webcamRef.current.video.readyState === 4 &&
      !isSending
    ) {
      const imageSrc = webcamRef.current.getScreenshot();

      if (imageSrc) {
        setIsSending(true);
        try {
          const response = await axios.post("http://127.0.0.1:8000/analyze_webcam", {
            image: imageSrc,
          });

          if (response.data) {
            setPostureResult(response.data.feedback || "");
            setPostureScore(response.data.score || null);
          }
        } catch (error) {
          console.error("Error sending frame:", error.message);
        }
        setIsSending(false);
      }
    }
  };

  const handleModeToggle = () => {
    setMode((prev) => (prev === "auto" ? "manual" : "auto"));
    setPostureResult("");
    setPostureScore(null);
  };

  const handleVideoUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://127.0.0.1:8000/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (response.data) {
        setPostureResult(response.data.feedback || "");
        setPostureScore(response.data.score || null);
      }

      event.target.value = ""; // Reset input
    } catch (error) {
      console.error("Error uploading video:", error.message);
    }
  };

  return (
    <div className="App">
    <h2>🧍 Realfy Posture Detection</h2>

    <button onClick={handleModeToggle}>
      Switch to {mode === "auto" ? "Manual" : "Auto"} Mode
    </button>

    {/* Main Content Row */}
    <div className="main-section-container">
      {/* Webcam Section */}
      <div className="section-card webcam-section">
        <h3>🎥 Webcam Mode ({mode === "auto" ? "Auto" : "Manual"})</h3>
        <Webcam
          audio={false}
          ref={webcamRef}
          screenshotFormat="image/jpeg"
          width={500}
          videoConstraints={{
            width: 500,
            height: 300,
            facingMode: "user",
          }}
        />
        {mode === "manual" && (
          <button onClick={captureAndSendFrame}>📸 Capture and Analyze</button>
        )}
      </div>

      {/* Feedback Section */}
      <div className="section-card result">
        <h3>📝 Posture Feedback:</h3>
        <p>{postureResult || "Waiting for input..."}</p>

        {postureScore !== null && (
          <div className="score-section">
            <h4>📊 Posture Score: {postureScore} / 100</h4>
            <div className="score-bar-container">
              <div
                className="score-bar"
                style={{
                  width: `${postureScore}%`,
                  backgroundColor: postureScore >= 80 ? "#4caf50" : "#ff9800",
                }}
              ></div>
            </div>
          </div>
        )}
      </div>
    </div>

    {/* Video Upload goes below */}
    <div className="upload-container">
      <div className="section-card upload-section">
        <h3>📁 Upload a Video</h3>
        <input type="file" accept="video/*" onChange={handleVideoUpload} />
      </div>
    </div>
  </div>
  );
}

export default App;
