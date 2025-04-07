import os
import mysql.connector
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QListWidget, QComboBox, QVBoxLayout, QHBoxLayout, QFileDialog, QInputDialog, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PIL import Image, ImageFilter, ImageEnhance

# Database configuration - hardcoded credentials
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'mini@123',  # Set your MySQL password here
    'database': 'photo_editor'
}

# Initialize database connection
def init_db():
    try:
        # First try to connect to the specified database
        conn = mysql.connector.connect(**DB_CONFIG)
        
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            # Database doesn't exist, try to create it
            config = DB_CONFIG.copy()
            config.pop('database')
            try:
                conn = mysql.connector.connect(**config)
                cursor = conn.cursor()
                cursor.execute(f"CREATE DATABASE {DB_CONFIG['database']}")
                conn.database = DB_CONFIG['database']
                
            except mysql.connector.Error as err:
                QMessageBox.critical(None, "Database Error", f"Failed to create database: {err}")
                return None
                
        else:
            QMessageBox.critical(None, "Database Error", f"Connection failed: {err}")
            return None
    
    # Create tables
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS images (
        id INT AUTO_INCREMENT PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        filepath VARCHAR(255) NOT NULL,
        original_path VARCHAR(255) NOT NULL,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS edits (
        id INT AUTO_INCREMENT PRIMARY KEY,
        image_id INT,
        filter_name VARCHAR(50) NOT NULL,
        edit_path VARCHAR(255) NOT NULL,
        date_edited TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
    )
    ''')
    
    conn.commit()
    return conn

app = QApplication([])
main_window = QWidget()
main_window.setWindowTitle("Photoshop with MySQL")
main_window.resize(800, 600)

# UI Elements
btn_folder = QPushButton("Select New photo")
file_list = QListWidget()

btn_left = QPushButton("Left")
btn_right = QPushButton("Right")
mirror = QPushButton("Mirror")
sharpness = QPushButton("Sharpness")
gray = QPushButton("Gray")
saturation = QPushButton("Saturation")
contrast = QPushButton("Contrast")
blur = QPushButton("Blur")

# Database action buttons
btn_add_description = QPushButton("Add Description")
btn_view_history = QPushButton("View Edit History")
btn_delete_image = QPushButton("Delete Image")
btn_reconnect_db = QPushButton("Reconnect to Database")

filter_box = QComboBox()
filter_box.addItems(["Original", "Left", "Right", "Mirror", "Sharpness", "B/W", "Saturation", "Contrast", "Blur"])

picture_box = QLabel("Image Preview")

master_layout = QHBoxLayout()
col1 = QVBoxLayout()
col2 = QVBoxLayout()

col1.addWidget(btn_folder)
col1.addWidget(file_list)
col1.addWidget(filter_box)
col1.addWidget(btn_left)
col1.addWidget(btn_right)
col1.addWidget(mirror)
col1.addWidget(sharpness)
col1.addWidget(gray)
col1.addWidget(saturation)
col1.addWidget(contrast)
col1.addWidget(blur)

# Add database action buttons
col1.addWidget(QLabel("Database Actions:"))
col1.addWidget(btn_add_description)
col1.addWidget(btn_view_history)
col1.addWidget(btn_delete_image)
col1.addWidget(btn_reconnect_db)

col2.addWidget(picture_box)

master_layout.addLayout(col1, 20)
master_layout.addLayout(col2, 80)
main_window.setLayout(master_layout)

working_directory = ""
conn = init_db()

def filter_files(files, extensions):
    return [file for file in files if any(file.endswith(ext) for ext in extensions)]

def getWorkDirectory():
    global working_directory
    file_list.clear()
    working_directory = QFileDialog.getExistingDirectory(main_window, "Select Directory")
    if working_directory:
        files = os.listdir(working_directory)
        filtered_files = filter_files(files, ['.jpg', '.png', '.jpeg'])
        file_list.addItems(filtered_files)

def reconnect_database():
    global conn
    if conn:
        conn.close()
    conn = init_db()
    if conn:
        QMessageBox.information(main_window, "Success", "Database connection established")
    else:
        QMessageBox.warning(main_window, "Warning", "Failed to connect to database")

class Editor():
    def __init__(self):
        self.image = None
        self.original = None
        self.filename = None
        self.save_folder = "edits/"
        self.current_image_id = None
        
    def load_image(self, filename):
        if not conn:
            QMessageBox.warning(main_window, "Warning", "No database connection")
            return
            
        self.filename = filename
        fullname = os.path.join(working_directory, filename)
        self.image = Image.open(fullname)
        self.original = self.image.copy()
        
        # Check if image exists in database, if not, add it
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT id FROM images WHERE filename = %s AND filepath = %s", 
                      (filename, working_directory))
        result = cursor.fetchone()
        
        if result:
            self.current_image_id = result[0]
        else:
            # Create new image record
            cursor.execute(
                "INSERT INTO images (filename, filepath, original_path) VALUES (%s, %s, %s)",
                (filename, working_directory, fullname)
            )
            conn.commit()
            self.current_image_id = cursor.lastrowid
            
    def save_image(self):
        path = os.path.join(working_directory, self.save_folder)
        os.makedirs(path, exist_ok=True)
        fullname = os.path.join(path, self.filename)
        self.image.save(fullname)
        return fullname

    def show_image(self, path):
        picture_box.hide()
        image = QPixmap(path)
        w, h = picture_box.width(), picture_box.height()
        image = image.scaled(w, h, Qt.KeepAspectRatio)
        picture_box.setPixmap(image)
        picture_box.show()

    def transformImage(self, transformation):
        if not conn:
            QMessageBox.warning(main_window, "Warning", "No database connection")
            return
            
        transformations = {
            "Original": lambda img: self.original.copy(),
            "Left": lambda img: img.rotate(270),
            "Right": lambda img: img.rotate(90),
            "Mirror": lambda img: img.transpose(Image.FLIP_LEFT_RIGHT),
            "Sharpness": lambda img: ImageEnhance.Sharpness(img).enhance(2.0),
            "B/W": lambda img: img.convert("L"),
            "Saturation": lambda img: ImageEnhance.Color(img).enhance(2.0),
            "Contrast": lambda img: ImageEnhance.Contrast(img).enhance(2.0),
            "Blur": lambda img: img.filter(ImageFilter.BLUR),
        }
        if transformation in transformations:
            self.image = transformations[transformation](self.image)
            saved_path = self.save_image()
            
            # Log edit in database
            if self.current_image_id:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO edits (image_id, filter_name, edit_path) VALUES (%s, %s, %s)",
                    (self.current_image_id, transformation, saved_path)
                )
                conn.commit()
                
        self.show_image(os.path.join(working_directory, self.save_folder, self.filename))

    def apply_filter(self, filter_name):
        if not conn:
            QMessageBox.warning(main_window, "Warning", "No database connection")
            return
            
        if filter_name == "Original":
            self.image = self.original.copy()
        else:
            self.transformImage(filter_name)
        saved_path = self.save_image()
        
        # Log edit in database
        if self.current_image_id:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO edits (image_id, filter_name, edit_path) VALUES (%s, %s, %s)",
                (self.current_image_id, filter_name, saved_path)
            )
            conn.commit()
            
        self.show_image(os.path.join(working_directory, self.save_folder, self.filename))
        
    # CRUD Methods
    def add_description(self):
        if not conn:
            QMessageBox.warning(main_window, "Warning", "No database connection")
            return
            
        if not self.current_image_id:
            QMessageBox.warning(main_window, "Warning", "No image selected")
            return
            
        description, ok = QInputDialog.getText(
            main_window, 
            "Add Description", 
            "Enter a description for this image:"
        )
        
        if ok and description:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE images SET description = %s WHERE id = %s",
                (description, self.current_image_id)
            )
            conn.commit()
            QMessageBox.information(main_window, "Success", "Description added successfully")
    
    def get_edit_history(self):
        if not conn:
            QMessageBox.warning(main_window, "Warning", "No database connection")
            return
            
        if not self.current_image_id:
            QMessageBox.warning(main_window, "Warning", "No image selected")
            return
            
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT filter_name, date_edited 
            FROM edits 
            WHERE image_id = %s 
            ORDER BY date_edited DESC
            """, 
            (self.current_image_id,)
        )
        
        history = cursor.fetchall()
        
        if not history:
            QMessageBox.information(main_window, "Edit History", "No edits found for this image")
            return
            
        history_text = "Edit History:\n\n"
        for i, (filter_name, date_edited) in enumerate(history, 1):
            history_text += f"{i}. {filter_name} - {date_edited}\n"
            
        QMessageBox.information(main_window, "Edit History", history_text)
    
    def delete_image_record(self):
        if not conn:
            QMessageBox.warning(main_window, "Warning", "No database connection")
            return
            
        if not self.current_image_id:
            QMessageBox.warning(main_window, "Warning", "No image selected")
            return
            
        reply = QMessageBox.question(
            main_window, 
            "Confirm Delete", 
            "Are you sure you want to delete this image record from the database?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            cursor = conn.cursor()
            # With ON DELETE CASCADE, we only need to delete the image record
            cursor.execute("DELETE FROM images WHERE id = %s", (self.current_image_id,))
            conn.commit()
            
            QMessageBox.information(main_window, "Success", "Image record deleted successfully")
            self.current_image_id = None
            file_list.clearSelection()

def handle_filter():
    if file_list.currentRow() >= 0:
        selected_filter = filter_box.currentText()
        main.apply_filter(selected_filter)

def displayImage():
    if file_list.currentRow() >= 0:
        filename = file_list.currentItem().text()
        main.load_image(filename)
        main.show_image(os.path.join(working_directory, main.filename))

main = Editor()
btn_folder.clicked.connect(getWorkDirectory)
file_list.currentRowChanged.connect(displayImage)
filter_box.currentTextChanged.connect(handle_filter)

# Connect filter buttons
gray.clicked.connect(lambda: main.transformImage("B/W"))
btn_left.clicked.connect(lambda: main.transformImage("Left"))
btn_right.clicked.connect(lambda: main.transformImage("Right"))
mirror.clicked.connect(lambda: main.transformImage("Mirror"))
sharpness.clicked.connect(lambda: main.transformImage("Sharpness"))
saturation.clicked.connect(lambda: main.transformImage("Saturation"))
contrast.clicked.connect(lambda: main.transformImage("Contrast"))
blur.clicked.connect(lambda: main.transformImage("Blur"))

# Connect database action buttons
btn_add_description.clicked.connect(main.add_description)
btn_view_history.clicked.connect(main.get_edit_history)
btn_delete_image.clicked.connect(main.delete_image_record)
btn_reconnect_db.clicked.connect(reconnect_database)

main_window.show()
app.exec_()

# Close database connection when app closes
if conn:
    conn.close()
