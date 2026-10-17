#ifndef DATA_LOGGER_H
#define DATA_LOGGER_H

#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include "grpc_client.h"

/// @brief 数据记录器类，用于保存机器人数据到CSV文件
class DataLogger {
public:
    /// @brief 构造函数
    /// @param base_filename 基础文件名（不包含扩展名）
    explicit DataLogger(const std::string& base_filename);
    
    /// @brief 析构函数
    ~DataLogger();
    
    /// @brief 初始化数据记录器
    /// @return 是否成功初始化
    bool Initialize();
    
    /// @brief 保存观察数据
    /// @param timestamp 时间戳
    /// @param observation 观察数据
    /// @return 是否成功保存
    bool SaveObservation(int timestamp, const Observation& observation);
    
    /// @brief 保存原始动作数据
    /// @param timestamp 时间戳
    /// @param raw_action 原始动作数据
    /// @return 是否成功保存
    bool SaveRawAction(int timestamp, const std::vector<float>& raw_action);
    
    /// @brief 保存处理后的动作数据
    /// @param timestamp 时间戳
    /// @param action 处理后的动作数据
    /// @return 是否成功保存
    bool SaveAction(int timestamp, const RobotAction& action);
    
    /// @brief 关闭所有文件
    void Close();
    
    /// @brief 检查是否已初始化
    /// @return 是否已初始化
    bool IsInitialized() const { return initialized_; }

private:
    std::string base_filename_;
    bool initialized_;
    
    // 文件流
    std::ofstream observation_file_;
    std::ofstream raw_action_file_;
    std::ofstream action_file_;
    
    // 文件名
    std::string observation_filename_;
    std::string raw_action_filename_;
    std::string action_filename_;
    
    /// @brief 写入CSV头部
    /// @param file 文件流
    /// @param data_size 数据大小
    /// @param prefix 列名前缀
    void WriteCSVHeader(std::ofstream& file, size_t data_size, const std::string& prefix);
    
    /// @brief 写入CSV数据行
    /// @param file 文件流
    /// @param timestamp 时间戳
    /// @param data 数据向量
    void WriteCSVRow(std::ofstream& file, int timestamp, const std::vector<float>& data);
};

#endif // DATA_LOGGER_H 