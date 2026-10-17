

#ifndef SENDER_WRAPPED_H_
#define SENDER_WRAPPED_H_

#include <stdint.h>
#include "robot_types.h"

#define SDK 2
#define ROBOT 1

#ifdef __cplusplus
extern "C" {
#endif

/// @brief Opaque handle to the Sender object
typedef void* SenderHandle;

/// @brief Create a Sender object with default IP and port
/// @return Handle to the created Sender object, or NULL on failure
SenderHandle Sender_create();

/// @brief Create a Sender object with specified IP and port
/// @param[in] ip The IP address to send data to (null-terminated string)
/// @param[in] port The port number to send data to
/// @return Handle to the created Sender object, or NULL on failure
SenderHandle Sender_createWithIpPort(const char* ip, uint16_t port);

/// @brief Destroy a Sender object
/// @param[in] handle Handle to the Sender object
void Sender_destroy(SenderHandle handle);

/// @brief Send RobotCmd through UDP socket
/// @param[in] handle Handle to the Sender object
/// @param[in] robot_cmd Pointer to the RobotCmd struct to be sent
void Sender_sendCmd(SenderHandle handle, const RobotCmd* robot_cmd);

/// @brief Send control_get command with specified mode
/// @param[in] handle Handle to the Sender object
/// @param[in] mode The mode of control_get command (SDK or ROBOT)
void Sender_controlGet(SenderHandle handle, uint32_t mode);

/// @brief Send a command to make all joints return to the zero position and acquire control
/// @param[in] handle Handle to the Sender object
void Sender_allJointBackZero(SenderHandle handle);

/// @brief Make all joints return to the zero position
/// @param[in] handle Handle to the Sender object
void Sender_robotStateInit(SenderHandle handle);

/// @brief Set the value of a command
/// @param[in] handle Handle to the Sender object
/// @param[in] code The code of the command
/// @param[in] value The value to be set
void Sender_setCmd(SenderHandle handle, uint32_t code, uint32_t value);

#ifdef __cplusplus
}
#endif

#endif // SENDER_C_H_