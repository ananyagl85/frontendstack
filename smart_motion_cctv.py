from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

import cv2
import os
import time
import subprocess
import traceback
from datetime import datetime


# ============================================================
# SMART MOTION CCTV
# Raspberry Pi 4 + OV5647
#
# Features:
#   - Continuous motion monitoring
#   - Low-resolution motion detection
#   - 1280x720 H.264 recording
#   - Event-triggered recording
#   - 10-second no-motion timeout
#   - Multiple sequential recordings
#   - Camera remains active between recordings
#   - Automatic MP4 conversion
#   - Safe shutdown
#
# ============================================================


# ============================================================
# SETTINGS
# ============================================================

RECORD_FOLDER = os.path.expanduser(
    "~/Desktop/CCTV_Recordings"
)

# Recording stream
RECORD_WIDTH = 1280
RECORD_HEIGHT = 720
FPS = 30

# H.264 bitrate
BITRATE = 10_000_000

# Stop recording after this much continuous inactivity
NO_MOTION_TIMEOUT = 10

# Minimum contour area required to classify movement
MIN_CONTOUR_AREA = 2500

# Motion-processing stream
MOTION_WIDTH = 320
MOTION_HEIGHT = 240

# Motion detection threshold
MOTION_THRESHOLD = 25

# Gaussian blur
BLUR_KERNEL = (21, 21)

# Dilation iterations
DILATION_ITERATIONS = 2

# Delay between motion checks
FRAME_DELAY = 0.05


# ============================================================
# CREATE RECORDING DIRECTORY
# ============================================================

os.makedirs(
    RECORD_FOLDER,
    exist_ok=True
)


# ============================================================
# STARTUP INFORMATION
# ============================================================

print()
print("======================================")
print("          SMART MOTION CCTV")
print("======================================")
print("Platform : Raspberry Pi 4")
print("Camera   : OV5647")
print("Recording: 1280x720 @ 30 FPS")
print("Codec    : H.264")
print("Bitrate  : 10 Mbps")
print("Motion   : 320x240")
print("======================================")
print()


# ============================================================
# CAMERA SETUP
# ============================================================

print("Starting camera...")

picam2 = Picamera2()

config = picam2.create_video_configuration(

    main={
        "size": (
            RECORD_WIDTH,
            RECORD_HEIGHT
        ),
        "format": "RGB888"
    },

    lores={
        "size": (
            MOTION_WIDTH,
            MOTION_HEIGHT
        ),
        "format": "YUV420"
    },

    controls={
        "FrameDurationLimits": (
            33333,
            33333
        )
    }
)

picam2.configure(config)

picam2.start()

time.sleep(2)

print("Camera started")


# ============================================================
# STATE VARIABLES
# ============================================================

recording = False

encoder = None

h264_file = None
mp4_file = None

last_motion_time = 0


# ============================================================
# PREVIOUS MOTION FRAME
# ============================================================

previous_frame = picam2.capture_array("lores")

previous_frame = cv2.cvtColor(
    previous_frame,
    cv2.COLOR_YUV2GRAY_I420
)

previous_frame = cv2.GaussianBlur(
    previous_frame,
    BLUR_KERNEL,
    0
)


# ============================================================
# MOTION DETECTION
# ============================================================

def detect_motion():

    global previous_frame

    # Capture low-resolution frame
    current_frame = picam2.capture_array(
        "lores"
    )

    # Convert YUV420 → grayscale
    current_frame = cv2.cvtColor(
        current_frame,
        cv2.COLOR_YUV2GRAY_I420
    )

    # Reduce noise
    current_frame = cv2.GaussianBlur(
        current_frame,
        BLUR_KERNEL,
        0
    )

    # Calculate frame difference
    difference = cv2.absdiff(
        previous_frame,
        current_frame
    )

    # Threshold
    threshold = cv2.threshold(
        difference,
        MOTION_THRESHOLD,
        255,
        cv2.THRESH_BINARY
    )[1]

    # Join nearby motion regions
    threshold = cv2.dilate(
        threshold,
        None,
        iterations=DILATION_ITERATIONS
    )

    # Find contours
    contours, _ = cv2.findContours(
        threshold,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    motion_detected = False

    for contour in contours:

        area = cv2.contourArea(contour)

        if area >= MIN_CONTOUR_AREA:

            motion_detected = True

            break

    # Current frame becomes previous frame
    previous_frame = current_frame.copy()

    return motion_detected


# ============================================================
# START RECORDING
# ============================================================

def start_recording():

    global recording
    global encoder
    global h264_file
    global mp4_file
    global last_motion_time

    # Safety check
    if recording:
        return

    # Microseconds prevent filename collisions
    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S_%f"
    )

    h264_file = os.path.join(
        RECORD_FOLDER,
        timestamp + ".h264"
    )

    mp4_file = os.path.join(
        RECORD_FOLDER,
        timestamp + ".mp4"
    )

    print()
    print("======================================")
    print("MOTION DETECTED")
    print("STARTING RECORDING")
    print("======================================")
    print("File:", mp4_file)

    # Create a fresh encoder for every event
    encoder = H264Encoder(
        bitrate=BITRATE
    )

    # Start only the encoder.
    # The camera remains available for future motion detection.
    picam2.start_recording(
        encoder,
        h264_file
    )

    recording = True

    last_motion_time = time.monotonic()

    print("RECORDING ACTIVE")


# ============================================================
# STOP RECORDING
# ============================================================

def stop_recording():

    global recording
    global encoder
    global h264_file
    global mp4_file
    global last_motion_time

    if not recording:
        return

    print()
    print("======================================")
    print("NO MOTION FOR 10 SECONDS")
    print("STOPPING CURRENT RECORDING")
    print("======================================")

    # --------------------------------------------------------
    # Stop ONLY the encoder.
    # --------------------------------------------------------

    try:

        picam2.stop_encoder(
            encoder
        )

    except Exception as error:

        print(
            "Encoder stop error:",
            error
        )

        traceback.print_exc()

    recording = False

    # Allow filesystem to finish writing
    time.sleep(0.3)

    # --------------------------------------------------------
    # Convert H.264 → MP4
    # --------------------------------------------------------

    if (
        h264_file
        and os.path.exists(h264_file)
        and os.path.getsize(h264_file) > 0
    ):

        print("Converting H.264 to MP4...")

        command = [
            "ffmpeg",
            "-y",

            "-fflags",
            "+genpts",

            "-framerate",
            str(FPS),

            "-i",
            h264_file,

            "-c:v",
            "copy",

            "-movflags",
            "+faststart",

            mp4_file
        ]

        try:

            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode == 0:

                print()
                print("======================================")
                print("RECORDING SAVED")
                print(mp4_file)
                print("======================================")

                # Delete temporary H.264 file
                try:

                    os.remove(
                        h264_file
                    )

                except OSError:
                    pass

            else:

                print("FFMPEG ERROR:")
                print(result.stderr)

        except Exception as error:

            print(
                "FFMPEG execution error:",
                error
            )

            traceback.print_exc()

    else:

        print(
            "WARNING: H.264 file was not created."
        )

    # --------------------------------------------------------
    # Reset state
    # --------------------------------------------------------

    encoder = None
    h264_file = None
    mp4_file = None
    last_motion_time = 0

    print()
    print("CCTV WATCHING FOR MOTION")
    print()


# ============================================================
# MAIN LOOP
# ============================================================

print()
print("======================================")
print("     CCTV WATCHING FOR MOTION")
print("======================================")
print()

try:

    while True:

        try:

            motion = detect_motion()

            # =================================================
            # MOTION DETECTED
            # =================================================

            if motion:

                last_motion_time = time.monotonic()

                if not recording:

                    start_recording()

                else:

                    # Motion is still present
                    # so the timeout is continuously reset.
                    pass

            # =================================================
            # NO MOTION
            # =================================================

            elif recording:

                elapsed = (
                    time.monotonic()
                    - last_motion_time
                )

                if elapsed >= NO_MOTION_TIMEOUT:

                    stop_recording()

            # =================================================
            # CONTINUE MONITORING
            # =================================================

        except Exception as loop_error:

            print()
            print("LOOP ERROR:")
            print(loop_error)

            traceback.print_exc()

            # Don't let one bad frame terminate CCTV
            time.sleep(1)

        time.sleep(
            FRAME_DELAY
        )


# ============================================================
# SAFE SHUTDOWN
# ============================================================

except KeyboardInterrupt:

    print()
    print("Stopping CCTV...")


finally:

    # --------------------------------------------------------
    # Finish an active recording
    # --------------------------------------------------------

    if recording:

        try:

            stop_recording()

        except Exception as error:

            print(
                "Error while stopping recording:",
                error
            )

            traceback.print_exc()

    # --------------------------------------------------------
    # Stop camera
    # --------------------------------------------------------

    try:

        picam2.stop()

    except Exception:
        pass

    print("Camera stopped")
    print("CCTV shutdown complete.")
