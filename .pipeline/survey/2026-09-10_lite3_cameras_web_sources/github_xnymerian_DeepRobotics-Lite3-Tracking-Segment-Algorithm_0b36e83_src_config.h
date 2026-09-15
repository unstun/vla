#pragma once

// Model Settings
#define MODEL_WIDTH 320 
#define MODEL_HEIGHT 320
#define OBJ_THRESH 0.45f 
#define NMS_THRESH 0.45f

// Distance Calibration
#define DISTANCE_FACTOR 10000.0f 

// Communication
#define PC_IP "192.168.1.50"      
#define ROBOT_MOTION_IP "127.0.0.1" 
#define MOTION_PORT 43893         
#define VIDEO_PORT 5000
#define CMD_PORT   5001   

// Control
#define DEADZONE 5             
#define MAX_POWER_LIMIT 32000 
