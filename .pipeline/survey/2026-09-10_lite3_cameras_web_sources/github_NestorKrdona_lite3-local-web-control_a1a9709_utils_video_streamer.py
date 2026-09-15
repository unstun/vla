#!/usr/bin/env python3
"""
Video Streaming Module for Jueying Lite3 Robot Dog
Converts RTSP stream to web-compatible format using OpenCV
"""

import cv2
import threading
import time
import logging
from typing import Optional, Generator
import numpy as np

logger = logging.getLogger(__name__)

class RTSPStreamer:
    """RTSP video streamer that converts RTSP to MJPEG for web browsers"""
    
    def __init__(self, rtsp_url: str, fps: int = 30, quality: int = 80):
        """
        Initialize RTSP streamer
        
        Args:
            rtsp_url: RTSP stream URL (e.g., "rtsp://192.168.1.120:8554/test")
            fps: Target frames per second
            quality: JPEG quality (1-100, higher = better quality)
        """
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.quality = quality
        self.frame_interval = 1.0 / fps
        
        # Video capture and threading
        self.cap = None
        self.frame = None
        self.frame_lock = threading.Lock()
        self.capture_thread = None
        self.is_streaming = False
        self.last_frame_time = 0
        
        # Statistics
        self.frame_count = 0
        self.connection_attempts = 0
        self.last_successful_frame = 0
        
    def start_streaming(self) -> bool:
        """
        Start the RTSP streaming
        
        Returns:
            bool: True if streaming started successfully
        """
        if self.is_streaming:
            logger.warning("Streaming is already active")
            return True
            
        logger.info(f"Starting RTSP stream: {self.rtsp_url}")
        
        try:
            # Initialize video capture with optimized settings
            self.cap = cv2.VideoCapture(self.rtsp_url)
            
            # Set buffer size to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Set connection timeout
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            
            # Test connection
            if not self.cap.isOpened():
                logger.error("Failed to open RTSP stream")
                return False
                
            # Try to read a test frame
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                logger.error("Failed to read test frame from RTSP stream")
                self.cap.release()
                return False
                
            logger.info(f"RTSP stream opened successfully. Frame size: {test_frame.shape}")
            
            # Start capture thread
            self.is_streaming = True
            self.capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.capture_thread.start()
            
            logger.info("RTSP streaming started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting RTSP stream: {e}")
            if self.cap:
                self.cap.release()
            return False
    
    def stop_streaming(self):
        """Stop the RTSP streaming"""
        logger.info("Stopping RTSP stream")
        
        self.is_streaming = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
            
        if self.cap:
            self.cap.release()
            self.cap = None
            
        with self.frame_lock:
            self.frame = None
            
        logger.info("RTSP stream stopped")
    
    def _capture_frames(self):
        """Capture frames from RTSP stream in separate thread"""
        consecutive_failures = 0
        max_failures = 10
        
        while self.is_streaming:
            try:
                if not self.cap or not self.cap.isOpened():
                    logger.warning("RTSP connection lost, attempting to reconnect...")
                    self._reconnect()
                    continue
                    
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    # Update frame with thread safety
                    with self.frame_lock:
                        self.frame = frame.copy()
                        
                    self.frame_count += 1
                    self.last_successful_frame = time.time()
                    consecutive_failures = 0
                    
                    # Control frame rate
                    current_time = time.time()
                    elapsed = current_time - self.last_frame_time
                    if elapsed < self.frame_interval:
                        time.sleep(self.frame_interval - elapsed)
                    self.last_frame_time = time.time()
                    
                else:
                    consecutive_failures += 1
                    logger.warning(f"Failed to read frame (attempt {consecutive_failures}/{max_failures})")
                    
                    if consecutive_failures >= max_failures:
                        logger.error("Too many consecutive frame failures, attempting reconnection")
                        self._reconnect()
                        consecutive_failures = 0
                    else:
                        time.sleep(0.1)
                        
            except Exception as e:
                logger.error(f"Error in frame capture: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    self._reconnect()
                    consecutive_failures = 0
                time.sleep(0.1)
    
    def _reconnect(self):
        """Attempt to reconnect to RTSP stream"""
        self.connection_attempts += 1
        logger.info(f"Reconnection attempt #{self.connection_attempts}")
        
        try:
            if self.cap:
                self.cap.release()
                
            time.sleep(1)  # Wait before reconnecting
            
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            
            if self.cap.isOpened():
                logger.info("RTSP reconnection successful")
            else:
                logger.error("RTSP reconnection failed")
                
        except Exception as e:
            logger.error(f"Error during RTSP reconnection: {e}")
    
    def get_frame_jpeg(self) -> Optional[bytes]:
        """
        Get current frame as JPEG bytes
        
        Returns:
            bytes: JPEG encoded frame or None if no frame available
        """
        with self.frame_lock:
            if self.frame is None:
                return None
                
            try:
                # Encode frame as JPEG with specified quality
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
                ret, jpeg_buffer = cv2.imencode('.jpg', self.frame, encode_params)
                
                if ret:
                    return jpeg_buffer.tobytes()
                else:
                    logger.error("Failed to encode frame as JPEG")
                    return None
                    
            except Exception as e:
                logger.error(f"Error encoding frame: {e}")
                return None
    
    def generate_frames(self) -> Generator[bytes, None, None]:
        """
        Generate frames for streaming (for use with Flask streaming response)
        
        Yields:
            bytes: Multipart frame data for HTTP streaming
        """
        while self.is_streaming:
            jpeg_data = self.get_frame_jpeg()
            
            if jpeg_data:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data + b'\r\n')
            else:
                # Send a placeholder frame or wait
                time.sleep(0.1)
    
    def is_connected(self) -> bool:
        """
        Check if RTSP stream is connected and receiving frames
        
        Returns:
            bool: True if connected and receiving frames
        """
        if not self.is_streaming or not self.cap:
            return False
            
        # Check if we've received a frame recently (within last 5 seconds)
        current_time = time.time()
        return (current_time - self.last_successful_frame) < 5.0
    
    def get_stats(self) -> dict:
        """
        Get streaming statistics
        
        Returns:
            dict: Statistics about the streaming session
        """
        current_time = time.time()
        return {
            'is_streaming': self.is_streaming,
            'is_connected': self.is_connected(),
            'frame_count': self.frame_count,
            'connection_attempts': self.connection_attempts,
            'last_frame_age': current_time - self.last_successful_frame if self.last_successful_frame > 0 else -1,
            'fps': self.fps,
            'quality': self.quality,
            'rtsp_url': self.rtsp_url
        }