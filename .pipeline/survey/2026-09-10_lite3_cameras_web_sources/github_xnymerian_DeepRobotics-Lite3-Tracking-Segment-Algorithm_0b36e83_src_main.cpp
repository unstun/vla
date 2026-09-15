#include <iostream>
#include <thread>
#include <vector>
#include <cstdlib>
#include <opencv2/opencv.hpp>
#include "rknn_api.h"

#include "config.h"
#include "network.h"
#include "model_loader.h"
#include "detector.h"
#include "visualizer.h"
#include "robot_controller.h"

int main() {
    setbuf(stdout, NULL);
    std::string model_path = "./yolo11n-seg-320.rknn"; 
    std::string video_source = "rtsp://127.0.0.1:8554/test"; 
    
    // Start background threads
    std::thread cmd_thread(command_listener);
    cmd_thread.detach(); 
    std::thread hb_thread(heartbeat_loop);
    hb_thread.detach();

    printf("\n=== LITE3 TRACKER (MULTI-DETECT + TARGETING) ===\n");
    
    // Initialize RGA
    init_rga();
    
    // Load model
    int m_size;
    unsigned char* m_data = load_model(model_path.c_str(), &m_size);
    if (!m_data) {
        printf("ERROR: Model not found!\n");
        return -1;
    }
    
    // Initialize RKNN
    rknn_context ctx;
    rknn_init(&ctx, m_data, m_size, 0, NULL);
    
    rknn_input_output_num io_num;
    rknn_query(ctx, RKNN_QUERY_IN_OUT_NUM, &io_num, sizeof(io_num));
    
    std::vector<rknn_tensor_attr> out_attrs(io_num.n_output);
    int detect_idx = -1;
    for (uint32_t i = 0; i < io_num.n_output; ++i) {
        out_attrs[i].index = i;
        rknn_query(ctx, RKNN_QUERY_OUTPUT_ATTR, &out_attrs[i], sizeof(rknn_tensor_attr));
        if (out_attrs[i].n_dims != 4 || (out_attrs[i].dims[1] != 32 && out_attrs[i].dims[3] != 32)) {
            detect_idx = i;
        }
    }

    // Open video capture
    cv::VideoCapture cap(video_source);
    if (!cap.isOpened()) {
        printf("ERROR: Cannot open video source!\n");
        return -1;
    }
    
    // Set camera to full resolution (1280x720)
    cap.set(cv::CAP_PROP_FRAME_WIDTH, 1280);
    cap.set(cv::CAP_PROP_FRAME_HEIGHT, 720);

    // Fast streaming: Scale down to 640x360 and send (No zoom, No lag)
    std::string gst_out = "appsrc ! videoconvert ! video/x-raw,format=BGR ! "
                          "videoscale ! video/x-raw,width=640,height=360 ! "
                          "queue max-size-buffers=1 leaky=downstream ! "
                          "videoconvert ! video/x-raw,format=I420 ! "
                          "x264enc tune=zerolatency bitrate=2000 speed-preset=ultrafast key-int-max=15 ! "
                          "rtph264pay config-interval=1 pt=96 ! "
                          "udpsink host=" PC_IP " port=" + std::to_string(VIDEO_PORT) + " sync=false";

    cv::VideoWriter writer;
    // Writer receives 1280x720 (Original) size data
    writer.open(gst_out, cv::CAP_GSTREAMER, 0, 30, cv::Size(1280, 720), true);
    
    cv::Mat frame, img_input;

    while (true) {
        if (!cap.read(frame)) break;
        
        float center_x = frame.cols / 2.0f;
        float center_y = frame.rows / 2.0f;
        
        if (show_segmentation) {
            cv::resize(frame, img_input, cv::Size(MODEL_WIDTH, MODEL_HEIGHT));
            cv::cvtColor(img_input, img_input, cv::COLOR_BGR2RGB);

            rknn_input inputs[1];
            memset(inputs, 0, sizeof(inputs));
            inputs[0].index = 0;
            inputs[0].type = RKNN_TENSOR_UINT8;
            inputs[0].fmt = RKNN_TENSOR_NHWC;
            inputs[0].size = MODEL_WIDTH * MODEL_HEIGHT * 3;
            inputs[0].buf = img_input.data;
            rknn_inputs_set(ctx, io_num.n_input, inputs);
            rknn_run(ctx, NULL);

            std::vector<rknn_output> outputs(io_num.n_output);
            for (uint32_t i = 0; i < io_num.n_output; i++) {
                outputs[i].want_float = 1;
                outputs[i].index = i;
            }
            rknn_outputs_get(ctx, io_num.n_output, outputs.data(), NULL);

            auto objects = decode_yolo_seg(
                (float*)outputs[detect_idx].buf, 
                out_attrs[detect_idx].dims[2], 
                (float)frame.cols / MODEL_WIDTH, 
                (float)frame.rows / MODEL_HEIGHT
            );

            if (!objects.empty()) {
                // Step 1: Draw all detected objects on screen
                for (const auto& obj : objects) {
                    float dist = DISTANCE_FACTOR / obj.rect.width;
                    draw_hud_box(frame, obj.rect, dist);
                }

                // Step 2: Lock onto the first one (front of list)
                const auto& target = objects[0];
                draw_target_line(frame, target.rect, center_x, center_y);

                // Motor calculations (for target)
                float obj_x = target.rect.x + (target.rect.width / 2);
                float obj_y = target.rect.y + (target.rect.height / 2);
                
                float error_x = center_x - obj_x; 
                float error_y = center_y - obj_y; 

                // YAW (LEFT/RIGHT)
                if (abs(error_x) > DEADZONE) {
                    int dir_x = (error_x > 0) ? -1 : 1; 
                    int min_power_x = 11000;
                    int extra_x = abs(error_x) * 150; 
                    int32_t yaw_cmd = dir_x * (min_power_x + extra_x);
                    
                    if (yaw_cmd > MAX_POWER_LIMIT) yaw_cmd = MAX_POWER_LIMIT;
                    if (yaw_cmd < -MAX_POWER_LIMIT) yaw_cmd = -MAX_POWER_LIMIT;
                    
                    send_udp_packet(0x21010135, yaw_cmd, "Yaw");
                } else {
                    send_udp_packet(0x21010135, 0, "Yaw Stop");
                }

                // PITCH (UP/DOWN)
                if (abs(error_y) > DEADZONE) {
                    int dir_y = (error_y > 0) ? -1 : 1; 
                    int min_power_y = 11000; 
                    int extra_y = abs(error_y) * 50; 
                    int32_t pitch_cmd = dir_y * (min_power_y + extra_y);
                    
                    if (pitch_cmd > MAX_POWER_LIMIT) pitch_cmd = MAX_POWER_LIMIT;
                    if (pitch_cmd < -MAX_POWER_LIMIT) pitch_cmd = -MAX_POWER_LIMIT;

                    send_udp_packet(0x21010130, pitch_cmd, "Pitch");
                } else {
                    send_udp_packet(0x21010130, 0, "Pitch Stop");
                }

            } else {
                // No one detected, stop
                send_udp_packet(0x21010135, 0, "Stop");
                send_udp_packet(0x21010130, 0, "Stop");
            }
            rknn_outputs_release(ctx, io_num.n_output, outputs.data());
        }

        if (writer.isOpened()) {
            writer.write(frame);
        }
    }
    
    program_running = false;
    rknn_destroy(ctx);
    free(m_data);
    return 0;
}

