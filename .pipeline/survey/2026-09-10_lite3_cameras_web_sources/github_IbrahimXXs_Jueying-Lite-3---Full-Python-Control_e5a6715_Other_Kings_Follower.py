import cv2
import socket
import struct
import time
from ultralytics import YOLO  # YOLOv8 for object detection

# Robot's motion host information
MOTION_HOST_IP = "192.168.1.120"
MOTION_HOST_PORT = 43893

def send_velocity_command(angular_velocity, linear_velocity_x, linear_velocity_y):
    """
    Sends velocity commands to the robot.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Pack Angular Velocity Command
        angular_command_head = struct.pack('<III', 0x0141, 8, 1)  # Command code, parameter size, type
        angular_command_value = struct.pack('<d', angular_velocity)  # Double precision value
        angular_command = angular_command_head + angular_command_value
        sock.sendto(angular_command, (MOTION_HOST_IP, MOTION_HOST_PORT))

        # Pack Linear Velocity in X Command
        linear_x_command_head = struct.pack('<III', 0x0140, 8, 1)
        linear_x_command_value = struct.pack('<d', linear_velocity_x)
        linear_x_command = linear_x_command_head + linear_x_command_value
        sock.sendto(linear_x_command, (MOTION_HOST_IP, MOTION_HOST_PORT))

        # Pack Linear Velocity in Y Command
        linear_y_command_head = struct.pack('<III', 0x0145, 8, 1)
        linear_y_command_value = struct.pack('<d', linear_velocity_y)
        linear_y_command = linear_y_command_head + linear_y_command_value
        sock.sendto(linear_y_command, (MOTION_HOST_IP, MOTION_HOST_PORT))
    except Exception as e:
        print(f"Error sending velocity command: {e}")
    finally:
        sock.close()

def access_camera_and_follow_person():
    """
    Access the robot's wide-angle camera and control the robot to follow a person detected in the frame.
    """
    # Replace with the correct RTSP URL for the robot
    rtsp_url = "rtsp://192.168.1.120:8554/test"

    # Open the video stream
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("Failed to open video stream. Please check the RTSP URL and robot connection.")
        return

    # Load YOLOv8 model
    model = YOLO("/home/ibrahim/Documents/Lite 3 Full Control (Python)/Other/Object_Assets/yolov8l.pt")  # Lightweight YOLOv8 Nano model

    print("Press 'q' to stop the robot and exit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame from the video stream.")
                break

            # Run YOLOv8 object detection
            results = model(frame)

            # Get the detected objects (filter for person class only)
            persons = []
            for result in results[0].boxes.data.tolist():
                x_min, y_min, x_max, y_max, confidence, class_id = result
                if int(class_id) == 0 and confidence > 0.3:  # Class ID 0 is 'person' in COCO
                    persons.append((x_min, y_min, x_max, y_max))

            # Check if exactly one person is fully visible in the frame
            frame_height, frame_width, _ = frame.shape
            if len(persons) == 1:
                x_min, y_min, x_max, y_max = persons[0]
                
                # Ensure the person is fully visible
                person_width = x_max - x_min
                person_height = y_max - y_min
                frame_width_threshold = frame_width * 0.9  # Allow a margin for near full width
                frame_height_threshold = frame_height * 0.9

                if (
                    x_min >= 0 and x_max <= frame_width and  # Entire bounding box is inside the frame
                    y_min >= 0 and y_max <= frame_height and
                    person_width < frame_width_threshold and
                    person_height < frame_height_threshold
                ):
                    # Calculate the person's center position
                    person_center_x = (x_min + x_max) / 2
                    frame_center_x = frame_width / 2

                    # Control logic to follow the person
                    linear_velocity_x = 0.3  # Constant forward speed
                    angular_velocity = 0.0

                    # Adjust angular velocity to center the person in the frame
                    if person_center_x < frame_center_x - 50:  # Person is to the left
                        angular_velocity = -0.5  # Turn right
                    elif person_center_x > frame_center_x + 50:  # Person is to the right
                        angular_velocity = 0.5  # Turn left

                    # Send velocity commands to the robot
                    send_velocity_command(angular_velocity, linear_velocity_x, 0.0)

                    # Draw bounding box and center line
                    cv2.rectangle(frame, (int(x_min), int(y_min)), (int(x_max), int(y_max)), (0, 255, 0), 2)
                    cv2.putText(frame, "Following", (int(x_min), int(y_min) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                else:
                    # Person is not fully visible; stop the robot
                    send_velocity_command(0.0, 0.0, 0.0)
                    cv2.putText(frame, "Person not fully visible", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                # Stop the robot if no person or multiple persons are visible
                send_velocity_command(0.0, 0.0, 0.0)

            # Display the frame
            cv2.imshow("Jueying Lite3 Person Following", frame)

            # Exit when 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Exiting and stopping the robot.")
                send_velocity_command(0.0, 0.0, 0.0)  # Stop the robot
                break
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        # Release the video capture and close all OpenCV windows
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    access_camera_and_follow_person()
