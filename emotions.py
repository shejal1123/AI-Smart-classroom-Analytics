import cv2
from deepface import DeepFace
import numpy as np
import os
import time
from datetime import datetime

def detect_emotion(camera_index=0):
    """
    Capture an image from the specified camera and detect the dominant emotion.
    
    Args:
        camera_index (int): Index of the camera to use
        
    Returns:
        str: The dominant emotion detected, or None if no faces/emotions were detected
    """
    try:
        # Initialize camera
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"Error: Could not open camera {camera_index}")
            return None
        
        # Capture frame
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Could not read frame from camera")
            cap.release()
            return None
        
        # Analyze emotions using DeepFace
        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        
        # Release camera
        cap.release()
        
        # Count emotions across all detected faces
        emotion_counts = {}
        
        # Handle both single face and multiple faces
        if isinstance(result, list):
            faces = result
        else:
            faces = [result]
            
        for face in faces:
            dominant_emotion = face['dominant_emotion']
            emotion_counts[dominant_emotion] = emotion_counts.get(dominant_emotion, 0) + 1
        
        # Determine the dominant emotion overall
        if emotion_counts:
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)
            print(f"Dominant emotion detected: {dominant_emotion}")
            return dominant_emotion
        else:
            print("No emotions detected")
            return None
            
    except Exception as e:
        print(f"Error in emotion detection: {str(e)}")
        return None

def detect_emotion_detailed(camera_index=0, use_stream_camera=True):
    """
    Capture an image from the specified camera and detect emotions with detailed information.
    
    Args:
        camera_index (int): Index of the camera to use
        use_stream_camera (bool): Whether to use the global streaming camera
        
    Returns:
        dict: Detailed emotion data including confidence, face count, and image path
    """
    try:
        frame = None
        
        # Always try to get frame from global streaming camera first to avoid conflicts
        if use_stream_camera:
            try:
                from app import camera, camera_lock
                print(f"Global camera status - exists: {camera is not None}, active: {camera.is_active if camera else False}")
                
                if camera and camera.is_active:
                    with camera_lock:
                        if camera.cap and camera.cap.isOpened():
                            print("Attempting to capture frame from global streaming camera...")
                            # Try multiple times to get a good frame
                            for attempt in range(3):
                                ret, frame = camera.cap.read()
                                print(f"Capture attempt {attempt + 1}: ret={ret}, frame shape={frame.shape if frame is not None else None}")
                                if ret and frame is not None:
                                    print("Successfully captured frame from global camera")
                                    break
                                time.sleep(0.1)  # Brief pause between attempts
                else:
                    print("Global camera not available or not active")
            except ImportError as e:
                print(f"Cannot import global camera: {e}")
            except Exception as e:
                print(f"Error accessing global camera: {e}")
        
        # Fall back to direct camera access if streaming camera failed
        if frame is None:
            print(f"Falling back to direct camera access for camera {camera_index}")
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)  # Use DirectShow on Windows
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to get fresh frames
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            
            if not cap.isOpened():
                print(f"Error: Could not open camera {camera_index} for direct access")
                return None
            
            # Allow camera to warm up
            time.sleep(0.5)
            
            # Clear buffer and capture fresh frame
            for _ in range(5):
                ret, frame = cap.read()
            
            if not ret or frame is None:
                print("Error: Could not read frame from direct camera access")
                cap.release()
                return None
            
            print(f"Successfully captured frame via direct access: {frame.shape}")
            # Release camera immediately to avoid conflicts
            cap.release()
        
        if frame is None:
            print("Could not capture frame from any source")
            return None
        
        # Save captured image
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_filename = f"capture_{timestamp}.jpg"
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        os.makedirs(static_dir, exist_ok=True)
        image_path = os.path.join(static_dir, image_filename)
        
        # Save the original frame
        cv2.imwrite(image_path, frame)
        
        # Analyze emotions using DeepFace
        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        
        # Process results
        emotion_counts = {}
        total_confidence = 0
        face_count = 0
        
        # Handle both single face and multiple faces
        if isinstance(result, list):
            faces = result
        else:
            faces = [result]
        
        face_count = len([face for face in faces if 'emotion' in face])
        
        for face in faces:
            if 'emotion' in face:
                dominant_emotion = face['dominant_emotion']
                emotion_counts[dominant_emotion] = emotion_counts.get(dominant_emotion, 0) + 1
                
                # Get confidence for the dominant emotion
                if dominant_emotion in face['emotion']:
                    total_confidence += face['emotion'][dominant_emotion]
        
        # Determine the dominant emotion overall
        if emotion_counts:
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)
            avg_confidence = total_confidence / len([f for f in faces if 'emotion' in f]) if faces else 0
            
            print(f"Dominant emotion detected: {dominant_emotion} (Confidence: {avg_confidence:.1f}%, Faces: {face_count})")
            
            return {
                'emotion': dominant_emotion,
                'confidence': float(avg_confidence),  # Convert numpy float to Python float
                'face_count': int(face_count),        # Convert to Python int
                'image_path': image_filename  # Return relative path for static serving
            }
        else:
            print("No emotions detected")
            return {
                'emotion': 'neutral',
                'confidence': float(0.0),  # Ensure Python float
                'face_count': int(0),      # Ensure Python int
                'image_path': image_filename
            }
            
    except Exception as e:
        print(f"Error in detailed emotion detection: {str(e)}")
        return None

def get_emotion_color(emotion):
    """
    Returns a color (BGR format) associated with each emotion for visualization
    
    Args:
        emotion (str): Detected emotion
        
    Returns:
        tuple: BGR color values
    """
    emotion_colors = {
        'happy': (0, 255, 255),    # Yellow
        'sad': (255, 0, 0),        # Blue
        'angry': (0, 0, 255),      # Red
        'fear': (255, 0, 255),     # Magenta
        'surprise': (0, 255, 0),   # Green
        'neutral': (255, 255, 255), # White
        'disgust': (0, 165, 255)   # Orange
    }
    
    return emotion_colors.get(emotion, (200, 200, 200))  # Default gray