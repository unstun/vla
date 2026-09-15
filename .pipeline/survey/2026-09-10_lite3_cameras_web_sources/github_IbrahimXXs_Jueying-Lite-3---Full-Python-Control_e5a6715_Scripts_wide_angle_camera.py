import cv2
import subprocess

def access_wide_angle_camera():
    """
    Access the wide-angle camera of the robot and display the video stream in real time using GStreamer.
    """
    # Replace with the correct RTSP URL for the robot
    rtsp_url = "rtsp://192.168.1.120:8554/test"

    # GStreamer command for streaming
    gstreamer_command = [
        "gst-launch-1.0",
        f"rtspsrc location={rtsp_url} latency=0",
        "!",
        "rtph264depay",
        "!",
        "h264parse",
        "!",
        "nvh264dec",
        "!",
        "videoconvert",
        "!",
        "autovideosink"
    ]

    try:
        # Run GStreamer command as a subprocess
        print("Starting GStreamer pipeline...")
        gst_process = subprocess.Popen(" ".join(gstreamer_command), shell=True)

        print("Press 'q' to terminate the stream.")

        # Optional: Wait for the user to terminate the process with 'q'
        while True:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Terminating the GStreamer pipeline.")
                gst_process.terminate()
                break

    except Exception as e:
        print(f"Error occurred while running GStreamer pipeline: {e}")
    finally:
        # Ensure the subprocess is terminated if an error occurs
        if gst_process:
            gst_process.terminate()
            print("GStreamer pipeline terminated.")

if __name__ == "__main__":
    access_wide_angle_camera()
