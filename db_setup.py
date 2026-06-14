import os
import sqlite3

# Create instance directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

# Database file path
DB_PATH = os.path.join(INSTANCE_DIR, 'smart_classroom.db')

# Create and initialize the database directly with SQLite
def init_db():
    # Check if database already exists
    if os.path.exists(DB_PATH):
        print(f"Database already exists at {DB_PATH}")
        return
    
    print(f"Creating new database at {DB_PATH}")
    
    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create classes table
    c.execute('''
    CREATE TABLE classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id TEXT,
        subject TEXT,
        date TIMESTAMP,
        summary TEXT,
        notes TEXT
    )
    ''')
    
    # Create readings table
    c.execute('''
    CREATE TABLE readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER,
        timestamp TIMESTAMP,
        emotion TEXT,
        confidence REAL DEFAULT 0.0,
        face_count INTEGER DEFAULT 0,
        image_path TEXT,
        FOREIGN KEY (class_id) REFERENCES classes (id)
    )
    ''')
    
    # Create students table
    c.execute('''
    CREATE TABLE students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE,
        name TEXT
    )
    ''')
    
    # Create attendances table
    c.execute('''
    CREATE TABLE attendances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER,
        student_id INTEGER,
        status TEXT,
        FOREIGN KEY (class_id) REFERENCES classes (id),
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
    ''')
    
    # Create teachers table
    c.execute('''
    CREATE TABLE teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database schema created successfully")

def upgrade_existing_db():
    """
    Upgrade existing database to add new columns and tables
    """
    if not os.path.exists(DB_PATH):
        print("No existing database found. Please run init_db() first.")
        return
    
    print(f"Upgrading existing database at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Check if classes table needs new columns
        c.execute("PRAGMA table_info(classes)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'summary' not in columns:
            c.execute('ALTER TABLE classes ADD COLUMN summary TEXT')
            print("Added summary column to classes table")
        
        if 'notes' not in columns:
            c.execute('ALTER TABLE classes ADD COLUMN notes TEXT')
            print("Added notes column to classes table")
        
        # Check if readings table needs new columns
        c.execute("PRAGMA table_info(readings)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'confidence' not in columns:
            c.execute('ALTER TABLE readings ADD COLUMN confidence REAL DEFAULT 0.0')
            print("Added confidence column to readings table")
        
        if 'face_count' not in columns:
            c.execute('ALTER TABLE readings ADD COLUMN face_count INTEGER DEFAULT 0')
            print("Added face_count column to readings table")
        
        if 'image_path' not in columns:
            c.execute('ALTER TABLE readings ADD COLUMN image_path TEXT')
            print("Added image_path column to readings table")
        
        # Check if students table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students'")
        if not c.fetchone():
            c.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE,
                name TEXT
            )
            ''')
            print("Created students table")
        
        # Check if attendances table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendances'")
        if not c.fetchone():
            c.execute('''
            CREATE TABLE attendances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER,
                student_id INTEGER,
                status TEXT,
                FOREIGN KEY (class_id) REFERENCES classes (id),
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
            ''')
            print("Created attendances table")
        
        # Check if teachers table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='teachers'")
        if not c.fetchone():
            c.execute('''
            CREATE TABLE teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            print("Created teachers table")
        
        conn.commit()
        print("Database upgrade completed successfully")
        
    except Exception as e:
        print(f"Error during database upgrade: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def add_sample_data():
    """
    Add some sample students to prevent division by zero errors
    """
    if not os.path.exists(DB_PATH):
        print("No database found. Please run init_db() first.")
        return
    
    print(f"Adding sample data to database at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Check if there are already students
        c.execute("SELECT COUNT(*) FROM students")
        student_count = c.fetchone()[0]
        
        if student_count == 0:
            # Add sample students
            sample_students = [
                ('S001', 'John Smith'),
                ('S002', 'Emma Johnson'),
                ('S003', 'Michael Brown'),
                ('S004', 'Sarah Davis'),
                ('S005', 'David Wilson')
            ]
            
            for student_id, name in sample_students:
                c.execute("INSERT INTO students (student_id, name) VALUES (?, ?)", (student_id, name))
            
            print(f"Added {len(sample_students)} sample students")
        else:
            print(f"Students table already has {student_count} students")
        
        conn.commit()
        print("Sample data added successfully")
        
    except Exception as e:
        print(f"Error adding sample data: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        print("Existing database found. Running upgrade...")
        upgrade_existing_db()
        add_sample_data()
    else:
        print("No existing database found. Creating new database...")
        init_db()
        add_sample_data()
    
    print(f"Database setup complete. Path: {DB_PATH}")