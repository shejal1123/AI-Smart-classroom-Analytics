#!/usr/bin/env python3
"""
Simple camera test script to debug camera access issues
"""

import cv2
import time

def test_camera(camera_index=0):
    print(f"Testing camera {camera_index}...")
    
    # Test 1: Basic camera access
    print("\n=== Test 1: Basic Camera Access ===")
    cap = cv2.VideoCapture(camera_index)
    if cap.isOpened():
        print("✓ Camera opened successfully")
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"✓ Frame captured: {frame.shape}")
        else:
            print("✗ Failed to capture frame")
    else:
        print("✗ Failed to open camera")
    cap.release()
    
    # Test 2: DirectShow backend (Windows)
    print("\n=== Test 2: DirectShow Backend ===")
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if cap.isOpened():
        print("✓ Camera opened with DirectShow")
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        
        # Warm up
        time.sleep(0.5)
        
        # Clear buffer
        for i in range(5):
            ret, frame = cap.read()
            
        if ret and frame is not None:
            print(f"✓ Frame captured after buffer clear: {frame.shape}")
        else:
            print("✗ Failed to capture frame after buffer clear")
    else:
        print("✗ Failed to open camera with DirectShow")
    cap.release()
    
    # Test 3: Multiple access simulation
    print("\n=== Test 3: Multiple Access Simulation ===")
    cap1 = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if cap1.isOpened():
        print("✓ First camera instance opened")
        
        # Try to open second instance (this should fail or conflict)
        cap2 = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if cap2.isOpened():
            print("⚠ Second camera instance also opened (potential conflict)")
            
            # Try to read from both
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()
            
            print(f"First instance read: {ret1}, shape: {frame1.shape if ret1 else None}")
            print(f"Second instance read: {ret2}, shape: {frame2.shape if ret2 else None}")
            
            cap2.release()
        else:
            print("✓ Second camera instance failed to open (expected)")
        
        cap1.release()
    else:
        print("✗ Failed to open first camera instance")
    
    print("\n=== Camera Test Complete ===")

if __name__ == "__main__":
    test_camera(0) 