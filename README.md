## Smart Motion-Triggered CCTV System

This project implements a **low-cost, autonomous edge-based CCTV system using a Raspberry Pi 4 and OV5647 camera**. It continuously monitors the environment for motion and automatically records only when significant movement is detected.

* Uses a **dual-stream camera configuration**:

   **320×240 YUV420** stream for lightweight motion detection.
   **1280×720** stream for video recording.
* Motion detection is performed using **OpenCV frame differencing**, Gaussian filtering, thresholding, dilation, and contour-area analysis.
* When motion is detected, **H.264 recording starts automatically at approximately 30 FPS**.
* Recording continues while motion is detected and stops after **10 seconds without motion**.
* Each motion event is saved as a **separate MP4 file**, and the camera remains active between events so subsequent recordings can start automatically.
* The system operates locally on the Raspberry Pi without requiring cloud processing.
* **systemd integration** enables automatic startup after Raspberry Pi boot.
* Night/IR operation was successfully demonstrated.

### Measured Performance

* Video: **1280×720, ~30 FPS, H.264**
* Measured bitrate: **10.003 Mbps**
* Example 67.2-second recording: **84.03 MB**
* Observed CPU usage: **38.5% monitoring / 47.2% recording**
* Observed RAM usage: **4.4%**
* Sequential recording test: **10/10 successful events**
* Active cooling thermal test: **38.4°C initial → 44.8°C maximum over 1 hour**
* Throttling status: **`0x0`**

### Key Contribution

The project focuses on integrating **low-resolution motion analysis, high-resolution hardware video encoding, event-based storage, persistent camera operation, sequential recording, and autonomous boot-time operation** into a compact Raspberry Pi-based surveillance platform.
