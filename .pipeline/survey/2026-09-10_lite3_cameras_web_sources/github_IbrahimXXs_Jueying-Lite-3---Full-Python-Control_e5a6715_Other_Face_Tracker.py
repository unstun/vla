import cv2
import socket
import struct
import time

# Robot motion host and port
MOTION_HOST_IP = "192.168.1.120"
MOTION_HOST_PORT = 43893

# RTSP URL for the camera
RTSP_URL = "rtsp://192.168.1.120:8554/test"

# Angular velocity settings
ANGULAR_VELOCITY_MAX = 0.7  # Max angular velocity (rad/s)
CENTER_THRESHOLD = 50  # Threshold for how close the face is to the center (in pixels)

def send_angular_velocity(angular_velocity):
    """
    Sends an angular velocity command to the robot.
    """
    try:
        # Pack the angular velocity command
        command_code = 0x0141
        parameter_size = 8  # double size
        command_type = 1  # Complex command
        command_head = struct.pack('<III', command_code, parameter_size, command_type)
        command_value = struct.pack('<d', angular_velocity)  # Double precision value
        command = command_head + command_value

        # Send the command to the robot
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(command, (MOTION_HOST_IP, MOTION_HOST_PORT))
        sock.close()
    except Exception as e:
        print(f"Error sending angular velocity command: {e}")

def track_face():
    """
    Accesses the wide-angle camera and tracks a detected face by adjusting the robot's angular velocity.
    """
    # Load pre-trained Haar cascade for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if face_cascade.empty():
        print("Error: Failed to load Haar cascade for face detection.")
        return

    # Open the video stream
    cap = cv2.VideoCapture(RTSP_URL)
    if not cap.isOpened():
        print("Failed to open video stream. Please check the RTSP URL and robot connection.")
        return

    print("Press 'q' to exit the video stream.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame from the video stream.")
                break

            # Convert the frame to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces in the frame
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))

            # Check if any face is detected
            if len(faces) > 0:
                # Assume the first detected face
                x, y, w, h = faces[0]

                # Calculate the horizontal center of the face
                face_center_x = x + w // 2
                frame_center_x = frame.shape[1] // 2  # Center of the frame

                # Calculate the offset from the center
                offset_x = face_center_x - frame_center_x

                # Determine angular velocity based on offset
                if abs(offset_x) > CENTER_THRESHOLD:
                    angular_velocity = ANGULAR_VELOCITY_MAX * (offset_x / abs(offset_x))  # Positive for right, negative for left
                    send_angular_velocity(angular_velocity)
                    print(f"Face detected. Adjusting angular velocity: {angular_velocity:.2f} rad/s")
                else:
                    send_angular_velocity(0.0)  # Stop rotation if the face is near the center
                    print("Face centered. Stopping angular velocity.")
            else:
                send_angular_velocity(0.0)  # Stop rotation if no face is detected
                print("No face detected. Stopping angular velocity.")

            # Draw detected faces on the frame
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # Display the frame
            cv2.imshow("Jueying Lite3 Wide-Angle Camera", frame)

            # Exit when 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Exiting the video stream.")
                break
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        # Release the video capture and close all OpenCV windows
        cap.release()
        cv2.destroyAllWindows()
        send_angular_velocity(0.0)  # Ensure the robot stops rotating

if __name__ == "__main__":
    track_face()
