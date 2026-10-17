#include "data_logger.h"
#include <sstream>
#include <iomanip>
#include <ctime>

DataLogger::DataLogger(const std::string& base_filename) 
    : base_filename_(base_filename), initialized_(false) {
    
    // 生成带时间戳的文件名
    std::time_t now = std::time(nullptr);
    std::tm* ltm = std::localtime(&now);
    
    std::ostringstream oss;
    oss << base_filename_ << "_" 
        << std::setfill('0') << std::setw(4) << (1900 + ltm->tm_year) << "-"
        << std::setfill('0') << std::setw(2) << (1 + ltm->tm_mon) << "-"
        << std::setfill('0') << std::setw(2) << ltm->tm_mday << "_"
        << std::setfill('0') << std::setw(2) << ltm->tm_hour << "-"
        << std::setfill('0') << std::setw(2) << ltm->tm_min << "-"
        << std::setfill('0') << std::setw(2) << ltm->tm_sec;
    
    std::string timestamp_suffix = oss.str();
    
    observation_filename_ = timestamp_suffix + "_observation.csv";
    raw_action_filename_ = timestamp_suffix + "_raw_action.csv";
    action_filename_ = timestamp_suffix + "_action.csv";
}

DataLogger::~DataLogger() {
    Close();
}

bool DataLogger::Initialize() {
    // 打开观察数据文件
    observation_file_.open(observation_filename_, std::ios::out);
    if (!observation_file_.is_open()) {
        std::cerr << "Failed to open observation file: " << observation_filename_ << std::endl;
        return false;
    }
    
    // 打开原始动作数据文件
    raw_action_file_.open(raw_action_filename_, std::ios::out);
    if (!raw_action_file_.is_open()) {
        std::cerr << "Failed to open raw action file: " << raw_action_filename_ << std::endl;
        observation_file_.close();
        return false;
    }
    
    // 打开处理后动作数据文件
    action_file_.open(action_filename_, std::ios::out);
    if (!action_file_.is_open()) {
        std::cerr << "Failed to open action file: " << action_filename_ << std::endl;
        observation_file_.close();
        raw_action_file_.close();
        return false;
    }
    
    // 写入CSV头部
    WriteCSVHeader(observation_file_, 65, "obs");  // Observation有65个数据点
    WriteCSVHeader(raw_action_file_, 12, "raw_action");  // Raw action有12个数据点
    WriteCSVHeader(action_file_, 12, "action");  // Action有12个数据点
    
    initialized_ = true;
    std::cout << "Data logger initialized successfully." << std::endl;
    std::cout << "Observation file: " << observation_filename_ << std::endl;
    std::cout << "Raw action file: " << raw_action_filename_ << std::endl;
    std::cout << "Action file: " << action_filename_ << std::endl;
    
    return true;
}

bool DataLogger::SaveObservation(int timestamp, const Observation& observation) {
    if (!initialized_) {
        std::cerr << "Data logger not initialized!" << std::endl;
        return false;
    }
    
    WriteCSVRow(observation_file_, timestamp, observation.data);
    return true;
}

bool DataLogger::SaveRawAction(int timestamp, const std::vector<float>& raw_action) {
    if (!initialized_) {
        std::cerr << "Data logger not initialized!" << std::endl;
        return false;
    }
    
    WriteCSVRow(raw_action_file_, timestamp, raw_action);
    return true;
}

bool DataLogger::SaveAction(int timestamp, const RobotAction& action) {
    if (!initialized_) {
        std::cerr << "Data logger not initialized!" << std::endl;
        return false;
    }
    
    WriteCSVRow(action_file_, timestamp, action.data);
    return true;
}

void DataLogger::Close() {
    if (observation_file_.is_open()) {
        observation_file_.close();
    }
    if (raw_action_file_.is_open()) {
        raw_action_file_.close();
    }
    if (action_file_.is_open()) {
        action_file_.close();
    }
    initialized_ = false;
}

void DataLogger::WriteCSVHeader(std::ofstream& file, size_t data_size, const std::string& prefix) {
    if (!file.is_open()) {
        return;
    }
    
    file << "timestamp";
    for (size_t i = 0; i < data_size; ++i) {
        file << "," << prefix << "_" << i;
    }
    file << std::endl;
}

void DataLogger::WriteCSVRow(std::ofstream& file, int timestamp, const std::vector<float>& data) {
    if (!file.is_open()) {
        return;
    }
    
    file << timestamp;
    for (const auto& value : data) {
        file << "," << std::fixed << std::setprecision(6) << value;
    }
    file << std::endl;
} 