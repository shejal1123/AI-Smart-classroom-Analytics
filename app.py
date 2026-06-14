from flask import Flask, request, render_template, redirect, url_for, jsonify, make_response, Response
from datetime import datetime
import emotions
import cv2
import os
import json
import threading
import time
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os.path
from collections import Counter
import hashlib

app = Flask(__name__)

# Global camera object for video streaming
camera = None
camera_lock = threading.Lock()

# Ensure we have an absolute path for the database
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

# Create instance directory if it doesn't exist
os.makedirs(INSTANCE_DIR, exist_ok=True)

# SQLite database setup with explicit file path
DB_PATH = os.path.join(INSTANCE_DIR, 'smart_classroom.db')
DATABASE_URI = f'sqlite:///{DB_PATH}'
print(f"Using database at: {DB_PATH}")

Base = declarative_base()
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

# Define database models
class Class(Base):
    __tablename__ = 'classes'
    
    id = Column(Integer, primary_key=True)
    teacher_id = Column(String(50))
    subject = Column(String(100))
    date = Column(DateTime)
    summary = Column(Text)
    notes = Column(Text)
    readings = relationship("Reading", back_populates="class_")
    attendances = relationship("Attendance", back_populates="class_")
    
    def __repr__(self):
        return f"<Class(id={self.id}, teacher={self.teacher_id}, subject={self.subject})>"

class Reading(Base):
    __tablename__ = 'readings'
    
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey('classes.id'))
    timestamp = Column(DateTime)
    emotion = Column(String(50))
    confidence = Column(Float, default=0.0)
    face_count = Column(Integer, default=0)
    image_path = Column(String(255))
    class_ = relationship("Class", back_populates="readings")
    
    def __repr__(self):
        return f"<Reading(id={self.id}, emotion={self.emotion})>"

class Student(Base):
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(String(50), unique=True)
    name = Column(String(100))
    attendances = relationship("Attendance", back_populates="student")
    
    def __repr__(self):
        return f"<Student(id={self.id}, student_id={self.student_id}, name={self.name})>"

class Attendance(Base):
    __tablename__ = 'attendances'
    
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey('classes.id'))
    student_id = Column(Integer, ForeignKey('students.id'))
    status = Column(String(20))  # Present, Absent, Late
    class_ = relationship("Class", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")
    
    def __repr__(self):
        return f"<Attendance(class_id={self.class_id}, student_id={self.student_id}, status={self.status})>"

# Add Teacher model after the Student model
class Teacher(Base):
    __tablename__ = 'teachers'
    
    id = Column(Integer, primary_key=True)
    teacher_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Teacher(id={self.id}, teacher_id={self.teacher_id}, name={self.name})>"

# Try to create database tables
try:
    Base.metadata.create_all(engine)
    print("Database tables created successfully")
except Exception as e:
    print(f"Error creating database tables: {str(e)}")

# Get available cameras
def get_available_cameras():
    available_cameras = []
    try:
        # Only check camera 0 to avoid obsensor errors
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                available_cameras.append(0)
                print("Camera 0 detected and working")
        cap.release()
    except Exception as e:
        print(f"Error detecting cameras: {str(e)}")
    
    # Always include at least camera 0 as fallback
    if not available_cameras:
        available_cameras.append(0)
        print("Using camera 0 as fallback")
    
    return available_cameras

# Emotion information for insights
emotion_info = {
    'happy': {
        'description': 'Students are showing positive engagement and enjoyment.',
        'educational_impact': 'High receptivity to learning, good retention of information.',
        'teaching_tip': 'Continue with current teaching approach, consider introducing more challenging material.'
    },
    'sad': {
        'description': 'Students may be experiencing difficulty or disengagement.',
        'educational_impact': 'Potential for reduced learning effectiveness and retention.',
        'teaching_tip': 'Check for understanding, provide encouragement, consider breaking down complex topics.'
    },
    'angry': {
        'description': 'Students may be frustrated or experiencing stress.',
        'educational_impact': 'Learning may be hindered by emotional barriers.',
        'teaching_tip': 'Take a break, address concerns, adjust teaching pace or approach.'
    },
    'fear': {
        'description': 'Students may feel anxious or uncertain about the material.',
        'educational_impact': 'Anxiety can significantly impact learning and participation.',
        'teaching_tip': 'Provide reassurance, create a supportive environment, simplify explanations.'
    },
    'surprise': {
        'description': 'Students are encountering unexpected or novel information.',
        'educational_impact': 'Can enhance memory formation and engagement when positive.',
        'teaching_tip': 'Capitalize on curiosity, encourage questions and exploration.'
    },
    'neutral': {
        'description': 'Students are in a calm, focused state.',
        'educational_impact': 'Good baseline for learning, neither hindering nor enhancing.',
        'teaching_tip': 'Consider adding engaging elements to increase interest and participation.'
    },
    'disgust': {
        'description': 'Students may be experiencing aversion or strong dislike.',
        'educational_impact': 'Negative emotions can create lasting negative associations with subject matter.',
        'teaching_tip': 'Identify source of aversion, change approach, make content more relatable.'
    }
}

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hash_password):
    """Verify password against hash"""
    return hashlib.sha256(password.encode()).hexdigest() == hash_password

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        name = request.form.get('name')
        password = request.form.get('password')
        
        try:
            session = Session()
            
            # Check if teacher ID already exists
            existing_teacher = session.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
            
            if existing_teacher:
                error = "Teacher ID already exists"
            else:
                new_teacher = Teacher(
                    teacher_id=teacher_id,
                    name=name,
                    password_hash=hash_password(password)
                )
                session.add(new_teacher)
                session.commit()
                
                # Set session cookie and redirect to home
                response = redirect(url_for('home'))
                response.set_cookie('teacher_id', teacher_id)
                response.set_cookie('teacher_name', name)
                session.close()
                return response
            
            session.close()
        except Exception as e:
            print(f"Error registering teacher: {str(e)}")
            error = "Database error occurred"
    
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        password = request.form.get('password')
        
        try:
            session = Session()
            teacher = session.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
            
            if teacher and verify_password(password, teacher.password_hash):
                # Set session cookie and redirect to home
                response = redirect(url_for('home'))
                response.set_cookie('teacher_id', teacher.teacher_id)
                response.set_cookie('teacher_name', teacher.name)
                session.close()
                return response
            else:
                error = "Invalid teacher ID or password"
            
            session.close()
        except Exception as e:
            print(f"Error logging in: {str(e)}")
            error = "Database error occurred"
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    response = redirect(url_for('home'))
    response.set_cookie('teacher_id', '', expires=0)
    response.set_cookie('teacher_name', '', expires=0)
    return response

@app.route('/quickstart', methods=['GET', 'POST'])
def quickstart():
    """Quick start route that doesn't require authentication"""
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id') or 'QuickStart'
        subject = request.form.get('subject')
        camera_index = int(request.form.get('camera_index', 0))
        
        try:
            # Create new class in database with exact timestamp
            session = Session()
            exact_time = datetime.now()
            new_class = Class(
                teacher_id=teacher_id,
                subject=subject,
                date=exact_time
            )
            print(f"Creating new class at exact time: {exact_time.strftime('%Y-%m-%d %H:%M:%S')}")
            session.add(new_class)
            session.commit()
            class_id = new_class.id
            session.close()
            
            # Redirect to class page with cookies
            response = redirect(url_for('class_view'))
            response.set_cookie('class_id', str(class_id))
            response.set_cookie('camera_index', str(camera_index))
            response.set_cookie('teacher_id', teacher_id)  # Set for quick start
            return response
        except Exception as e:
            print(f"Error creating class: {str(e)}")
            # Return to quickstart page with error
            cameras = get_available_cameras()
            return render_template('quickstart.html', cameras=cameras, error="Database error. Please try again.")
    
    cameras = get_available_cameras()
    return render_template('quickstart.html', cameras=cameras)

@app.route('/', methods=['GET', 'POST'])
def home():
    # Check if user is already logged in
    teacher_id = request.cookies.get('teacher_id')
    
    if request.method == 'POST':
        if 'start_class' in request.form:
            # Must be logged in to start a class from home
            if not teacher_id:
                return redirect(url_for('login'))
            
            subject = request.form.get('subject')
            camera_index = int(request.form.get('camera_index', 0))
            
            try:
                # Create new class in database with exact timestamp
                session = Session()
                exact_time = datetime.now()
                new_class = Class(
                    teacher_id=teacher_id,
                    subject=subject,
                    date=exact_time
                )
                print(f"Creating new class at exact time: {exact_time.strftime('%Y-%m-%d %H:%M:%S')}")
                session.add(new_class)
                session.commit()
                class_id = new_class.id
                session.close()
                
                # Redirect to class page with cookies
                response = redirect(url_for('class_view'))
                response.set_cookie('class_id', str(class_id))
                response.set_cookie('camera_index', str(camera_index))
                return response
            except Exception as e:
                print(f"Error creating class: {str(e)}")
                # Return to home page with error
                cameras = get_available_cameras()
                return render_template('index.html', cameras=cameras, error="Database error. Please try again.")
    
    # Redirect to login if not logged in
    if not teacher_id:
        return redirect(url_for('login'))
    
    # Get list of available cameras
    cameras = get_available_cameras()
    return render_template('index.html', cameras=cameras)

# Helper functions for emotion display
@app.context_processor
def utility_processor():
    def get_emotion_color(emotion):
        emotion_colors = {
            'happy': 'warning',
            'sad': 'primary',
            'angry': 'danger',
            'fear': 'dark',
            'surprise': 'success',
            'neutral': 'secondary',
            'disgust': 'info'
        }
        return emotion_colors.get(emotion.lower(), 'secondary')
    
    def get_emotion_icon(emotion):
        emotion_icons = {
            'happy': 'fa-smile',
            'sad': 'fa-frown',
            'angry': 'fa-angry',
            'fear': 'fa-surprise',
            'surprise': 'fa-surprise',
            'neutral': 'fa-meh',
            'disgust': 'fa-grimace'
        }
        return emotion_icons.get(emotion.lower(), 'fa-meh')
    
    def format_datetime(dt):
        if dt:
            return dt.strftime('%B %d, %Y at %I:%M %p')
        return 'N/A'
    
    return dict(
        get_emotion_color=get_emotion_color,
        get_emotion_icon=get_emotion_icon,
        format_datetime=format_datetime,
        emotion_info=emotion_info
    )

@app.route('/class', methods=['GET'])
def class_view():
    class_id = request.cookies.get('class_id')
    camera_index = request.cookies.get('camera_index', 0)
    
    class_info = None
    readings = []
    
    try:
        session = Session()
        if class_id:
            class_info = session.query(Class).filter(Class.id == class_id).first()
            readings = session.query(Reading).filter(Reading.class_id == class_id).order_by(Reading.timestamp.desc()).all()
        session.close()
    except Exception as e:
        print(f"Error retrieving class data: {str(e)}")
    
    return render_template('class.html', 
                         class_info=class_info, 
                         readings=readings, 
                         camera_index=camera_index,
                         emotion_info=emotion_info)

@app.route('/students', methods=['GET', 'POST'])
def students():
    error = None
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        
        try:
            session = Session()
            
            # Check if student ID already exists
            existing_student = session.query(Student).filter(Student.student_id == student_id).first()
            if existing_student:
                error = "Student ID already exists"
            else:
                new_student = Student(student_id=student_id, name=name)
                session.add(new_student)
                session.commit()
            
            session.close()
        except Exception as e:
            print(f"Error adding student: {str(e)}")
            error = "Database error occurred"
    
    # Get all students
    students_list = []
    try:
        session = Session()
        students_list = session.query(Student).all()
        session.close()
    except Exception as e:
        print(f"Error retrieving students: {str(e)}")
    
    return render_template('students.html', students=students_list, error=error)

@app.route('/student/<int:student_id>')
def view_student(student_id):
    """View student details"""
    try:
        session = Session()
        student = session.query(Student).filter(Student.id == student_id).first()
        
        if not student:
            session.close()
            return redirect(url_for('students'))
        
        # Get attendance history for this student
        attendances = session.query(Attendance, Class).join(Class).filter(
            Attendance.student_id == student_id
        ).order_by(Class.date.desc()).all()
        
        session.close()
        
        return render_template('student_detail.html', student=student, attendances=attendances)
    
    except Exception as e:
        print(f"Error viewing student: {str(e)}")
        return redirect(url_for('students'))

@app.route('/student/<int:student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit student information"""
    try:
        session = Session()
        student = session.query(Student).filter(Student.id == student_id).first()
        
        if not student:
            session.close()
            return redirect(url_for('students'))
        
        error = None
        
        if request.method == 'POST':
            new_student_id = request.form.get('student_id')
            new_name = request.form.get('name')
            
            # Check if student ID already exists (excluding current student)
            existing_student = session.query(Student).filter(
                Student.student_id == new_student_id,
                Student.id != student_id
            ).first()
            
            if existing_student:
                error = "Student ID already exists"
            else:
                student.student_id = new_student_id
                student.name = new_name
                session.commit()
                session.close()
                return redirect(url_for('view_student', student_id=student_id))
        
        session.close()
        return render_template('edit_student.html', student=student, error=error)
    
    except Exception as e:
        print(f"Error editing student: {str(e)}")
        return redirect(url_for('students'))

@app.route('/student/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    """Delete a student"""
    try:
        session = Session()
        student = session.query(Student).filter(Student.id == student_id).first()
        
        if student:
            # Delete associated attendance records first
            session.query(Attendance).filter(Attendance.student_id == student_id).delete()
            # Delete the student
            session.delete(student)
            session.commit()
        
        session.close()
        return jsonify({'status': 'success', 'message': 'Student deleted successfully'})
    
    except Exception as e:
        print(f"Error deleting student: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/analytics/<int:class_id>')
def analytics(class_id):
    try:
        session = Session()
        class_info = session.query(Class).filter(Class.id == class_id).first()
        readings = session.query(Reading).filter(Reading.class_id == class_id).order_by(Reading.timestamp).all()
        
        if not class_info:
            session.close()
            return redirect(url_for('home'))
        
        # Calculate analytics data
        emotions_data = {}
        timeline_data = []
        total_face_count = 0
        
        for reading in readings:
            # Count emotions
            emotions_data[reading.emotion] = emotions_data.get(reading.emotion, 0) + 1
            
            # Timeline data
            timeline_data.append({
                'timestamp': reading.timestamp.strftime('%H:%M:%S'),
                'emotion': reading.emotion
            })
            
            # Face count
            total_face_count += reading.face_count
        
        avg_face_count = total_face_count / len(readings) if readings else 0
        
        session.close()
        
        return render_template('analytics.html',
                             class_info=class_info,
                             readings=readings,
                             emotions_data=emotions_data,
                             timeline_data=json.dumps(timeline_data),
                             avg_face_count=avg_face_count,
                             emotion_info=emotion_info)
    
    except Exception as e:
        print(f"Error in analytics: {str(e)}")
        return redirect(url_for('home'))

@app.route('/attendance/<int:class_id>', methods=['GET', 'POST'])
def attendance(class_id):
    try:
        session = Session()
        class_info = session.query(Class).filter(Class.id == class_id).first()
        students_list = session.query(Student).all()
        
        if not class_info:
            session.close()
            return redirect(url_for('home'))
        
        # Get existing attendance records for this class
        existing_attendance = session.query(Attendance).filter(Attendance.class_id == class_id).all()
        attendance_dict = {att.student_id: att.status for att in existing_attendance}
        
        if request.method == 'POST':
            # Process attendance form submission
            for student in students_list:
                status_key = f'status_{student.id}'
                if status_key in request.form:
                    status = request.form[status_key]
                    
                    # Check if attendance record exists
                    existing = session.query(Attendance).filter(
                        Attendance.class_id == class_id,
                        Attendance.student_id == student.id
                    ).first()
                    
                    if existing:
                        existing.status = status
                    else:
                        new_attendance = Attendance(
                            class_id=class_id,
                            student_id=student.id,
                            status=status
                        )
                        session.add(new_attendance)
                    
                    attendance_dict[student.id] = status
            
            session.commit()
            session.close()
            
            # Redirect back to the same attendance page with success message
            return redirect(url_for('attendance', class_id=class_id))
        
        session.close()
        
        return render_template('attendance.html',
                             class_info=class_info,
                             students=students_list,
                             attendance=attendance_dict)
    
    except Exception as e:
        print(f"Error in attendance: {str(e)}")
        return redirect(url_for('home'))

@app.route('/capture_emotion', methods=['POST'])
def capture_emotion():
    class_id = request.cookies.get('class_id')
    camera_index = int(request.cookies.get('camera_index', 0))
    
    print(f"Capture emotion request - Class ID: {class_id}, Camera: {camera_index}")
    
    if not class_id:
        return jsonify({'status': 'error', 'message': 'No active class session found'})
    
    # Capture and analyze emotion (try stream camera first)
    result = emotions.detect_emotion_detailed(camera_index, use_stream_camera=True)
    
    print(f"Emotion detection result: {result}")
    
    if result and class_id:
        try:
            # Store in database
            session = Session()
            new_reading = Reading(
                class_id=class_id,
                timestamp=datetime.now(),
                emotion=result['emotion'],
                confidence=float(result.get('confidence', 0.0)),  # Convert to Python float
                face_count=int(result.get('face_count', 0)),      # Convert to Python int
                image_path=result.get('image_path', None)
            )
            session.add(new_reading)
            session.commit()
            session.close()
            
            return jsonify({
                'status': 'success', 
                'data': {
                    'emotion': result['emotion'],
                    'confidence': float(result.get('confidence', 0.0)),  # Convert to Python float
                    'face_count': int(result.get('face_count', 0)),      # Convert to Python int
                    'image_path': result.get('image_path', None)
                }
            })
        except Exception as e:
            print(f"Error saving emotion: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'})
    
    if not class_id:
        return jsonify({'status': 'error', 'message': 'No active class session. Please start a class first.'})
    else:
        return jsonify({'status': 'error', 'message': 'Could not detect emotion. Please ensure camera is active and try again.'})

@app.route('/get_readings/<class_id>', methods=['GET'])
def get_readings(class_id):
    result = []
    try:
        session = Session()
        readings = session.query(Reading).filter(Reading.class_id == class_id).order_by(Reading.timestamp.desc()).all()
        
        for reading in readings:
            result.append({
                'id': reading.id,
                'timestamp': reading.timestamp.strftime('%H:%M:%S'),
                'emotion': reading.emotion,
                'confidence': reading.confidence,
                'face_count': reading.face_count,
                'image_path': reading.image_path
            })
        
        session.close()
    except Exception as e:
        print(f"Error getting readings: {str(e)}")
    
    return jsonify(result)

@app.route('/update_notes/<int:class_id>', methods=['POST'])
def update_notes(class_id):
    try:
        session = Session()
        class_obj = session.query(Class).filter(Class.id == class_id).first()
        
        if class_obj:
            class_obj.notes = request.form.get('notes', '')
            class_obj.summary = request.form.get('summary', '')
            session.commit()
            session.close()
            return jsonify({'status': 'success'})
        else:
            session.close()
            return jsonify({'status': 'error', 'message': 'Class not found'})
    
    except Exception as e:
        print(f"Error updating notes: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/recent_classes')
def recent_classes():
    try:
        session = Session()
        classes = session.query(Class).order_by(Class.date.desc()).limit(10).all()
        
        result = []
        for cls in classes:
            # Get dominant emotion for this class
            readings = session.query(Reading).filter(Reading.class_id == cls.id).all()
            emotion_counts = Counter([r.emotion for r in readings])
            dominant_emotion = emotion_counts.most_common(1)[0][0] if emotion_counts else 'neutral'
            
            result.append({
                'id': cls.id,
                'date': cls.date.strftime('%Y-%m-%d'),
                'subject': cls.subject,
                'teacher_id': cls.teacher_id,
                'dominant_emotion': dominant_emotion
            })
        
        session.close()
        return jsonify(result)
    
    except Exception as e:
        print(f"Error getting recent classes: {str(e)}")
        return jsonify([])

@app.route('/continue_class/<int:class_id>')
def continue_class(class_id):
    """Continue an existing class session"""
    try:
        session = Session()
        class_info = session.query(Class).filter(Class.id == class_id).first()
        session.close()
        
        if not class_info:
            return redirect(url_for('home'))
        
        # Set cookies for the existing class
        response = redirect(url_for('class_view'))
        response.set_cookie('class_id', str(class_id))
        response.set_cookie('camera_index', '0')
        return response
        
    except Exception as e:
        print(f"Error continuing class: {str(e)}")
        return redirect(url_for('home'))

# Video streaming functions
class VideoCamera:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.is_active = False
        
    def start(self):
        """Start the camera stream with optimizations"""
        try:
            if self.cap is None or not self.cap.isOpened():
                print(f"Initializing camera {self.camera_index} with optimized settings...")
                self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)  # Use DirectShow backend on Windows
                
                if self.cap.isOpened():
                    # Set camera properties for better performance and stability
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.cap.set(cv2.CAP_PROP_FPS, 30)  # Higher FPS for smoother video
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer to reduce lag
                    self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # MJPEG codec
                    
                    # Quick test to ensure camera is working
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None:
                        self.is_active = True
                        print(f"Camera {self.camera_index} started successfully with DirectShow backend")
                        print(f"Global camera initialized and started: active={self.is_active}")
                    else:
                        print(f"Camera {self.camera_index} opened but cannot capture frames")
                        self.cap.release()
                        self.cap = None
                else:
                    print(f"Failed to open camera {self.camera_index}")
        except Exception as e:
            print(f"Error starting camera {self.camera_index}: {str(e)}")
            if self.cap:
                self.cap.release()
                self.cap = None
                
    def stop(self):
        """Stop the camera stream"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            self.is_active = False
            print(f"Camera {self.camera_index} stopped")
    
    def get_frame(self):
        """Get a frame from the camera"""
        if self.cap is not None and self.cap.isOpened():
            # Clear buffer by reading multiple frames quickly
            for _ in range(2):
                ret, frame = self.cap.read()
                if not ret:
                    break
            
            if ret and frame is not None:
                # Encode frame as JPEG
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ret:
                    return jpeg.tobytes()
        return None

def generate_frames():
    """Generate video frames for streaming"""
    global camera
    while True:
        if camera and camera.is_active:
            frame = camera.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.1)
        else:
            time.sleep(0.5)

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_camera')
def start_camera():
    """Start the camera for the current session"""
    global camera
    camera_index = int(request.cookies.get('camera_index', 0))
    
    with camera_lock:
        if camera is None or not camera.is_active:
            camera = VideoCamera(camera_index)
            camera.start()
            print(f"Global camera initialized and started: active={camera.is_active}")
            return jsonify({'status': 'success', 'message': 'Camera started'})
        else:
            print(f"Camera already active: {camera.is_active}")
            return jsonify({'status': 'info', 'message': 'Camera already active'})

@app.route('/stop_camera')
def stop_camera():
    """Stop the camera"""
    global camera
    
    with camera_lock:
        if camera and camera.is_active:
            camera.stop()
            return jsonify({'status': 'success', 'message': 'Camera stopped'})
        else:
            return jsonify({'status': 'info', 'message': 'Camera not active'})

@app.route('/camera_status')
def camera_status():
    """Get current camera status for debugging"""
    global camera
    
    status = {
        'camera_exists': camera is not None,
        'camera_active': camera.is_active if camera else False,
        'camera_cap_opened': camera.cap.isOpened() if camera and camera.cap else False,
        'camera_index': camera.camera_index if camera else None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Test frame capture if camera exists
    if camera and camera.cap and camera.cap.isOpened():
        try:
            ret, frame = camera.cap.read()
            status['can_capture_frame'] = ret and frame is not None
            if ret and frame is not None:
                status['frame_shape'] = f"{frame.shape[1]}x{frame.shape[0]}"
            else:
                status['frame_shape'] = None
        except Exception as e:
            status['can_capture_frame'] = False
            status['frame_shape'] = None
            status['capture_error'] = str(e)
    else:
        status['can_capture_frame'] = False
        status['frame_shape'] = None
    
    print(f"Camera status check: {status}")
    return jsonify(status)

if __name__ == '__main__':
    # Use SQLite file database
    app.run(debug=True)