Overview

Smart Classroom is an intelligent classroom monitoring system built using Flask and computer vision technologies. The application enables teachers to monitor student engagement in real time through facial emotion recognition. By analyzing students' emotional responses during lectures, the system provides actionable insights that help educators adapt their teaching strategies and improve learning outcomes.

Objectives

Monitor student engagement during classroom sessions.
Detect and analyze student emotions in real time.
Provide teachers with data-driven teaching recommendations.
Track attendance and classroom participation.
Visualize emotional trends throughout the lecture.

Key Features

Real-Time Emotion Detection
Captures student facial expressions through webcams.
Uses AI-based emotion recognition to identify emotions such as:
Happy
Neutral
Sad
Angry
Fear
Surprise
Disgust

Camera Selection
Supports multiple camera devices.
Allows teachers to choose the preferred webcam.

Advanced Analytics Dashboard
Displays emotion distribution using interactive charts.
Tracks engagement patterns over time.
Provides visual insights into classroom sentiment.

Teaching Insights
Generates recommendations based on detected emotional states.
Helps teachers identify:
Student confusion
Lack of attention
Positive engagement
Classroom stress levels

Student Management
Add and manage student records.
Maintain classroom attendance information.
Monitor participation statistics.

Emotion Timeline
Records emotional states throughout the session.
Enables teachers to review engagement fluctuations.
Image Capture and Storage
Saves captured classroom snapshots.
Allows review of images associated with emotion readings.

Multi-Face Detection
Detects multiple students simultaneously.
Counts the number of faces present in each frame.

Class Notes
Teachers can add notes and summaries for each session.
Supports post-class analysis and reporting.

Local Database Support
Uses SQLite for lightweight and easy deployment.
No external database installation required.

Technology Used
| Component           | Technology                         |
| ------------------- | ---------------------------------- |
| Backend             | Python, Flask                      |
| Frontend            | Bootstrap 5, HTML, CSS, JavaScript |
| Database            | SQLite, SQLAlchemy                 |
| Computer Vision     | OpenCV                             |
| Emotion Recognition | DeepFace                           |
| Charts & Analytics  | Chart.js                           |
| Icons               | Font Awesome                       |

System Architecture
Webcam Input
      │
      ▼
OpenCV Face Detection
      │
      ▼
DeepFace Emotion Analysis
      │
      ▼
Flask Backend
      │
 ┌────┴────┐
 ▼         ▼
SQLite   Analytics Engine
Database
 │
 ▼
Teacher Dashboard

Installation

1. Clone the Repository
   git clone https://github.com/yourusername/smart-classroom.git
   cd smart-classroom

2. Create a Virtual Environment
   python -m venv venv

Activate:  Linux/macOS
  source venv/bin/activate

Windows
   venv\Scripts\activate

3. Install Dependencies
   venv\Scripts\activate

4. Initialize Database
   python app.py

5. Run the Application
   python app.py


Check console logs and ensure the SQLite database file exists inside:

instance/
User Workflow
Step 1: Start Class
Enter Teacher ID.
Enter Subject Name.
Select Camera Device.
Click Start Class.
Step 2: Capture Emotions
Click Capture Emotion for a manual reading.
Enable Auto-Capture for continuous monitoring.
Review detected emotions instantly.
Step 3: Analyze Engagement

Teachers can:

View emotion distribution graphs.
Monitor emotional trends.
Receive teaching recommendations.
Step 4: Manage Students
Add student records.
Mark attendance.
Review participation statistics.

Key Directories and Files
/app.py - Main application file
/emotions.py - Emotion detection module
/db_setup.py - Database initialization
/static/ - CSS and captured images
/templates/ - HTML templates
/instance/ - SQLite database
