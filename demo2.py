import sys
import os
import io
import mysql.connector
from mysql.connector import Error
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QFileDialog, QGridLayout, 
                            QScrollArea, QFrame, QSlider, QComboBox, QMessageBox, QTabWidget,
                            QSplitter)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QByteArray, QBuffer
from PIL import Image, ImageEnhance, ImageFilter
from PIL.ImageQt import toqimage

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'photo_editor_db',
    'user': 'root',
    'password': 'mini@123'
}

def create_database():
    """Create database and tables if they don't exist"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        
        if conn.is_connected():
            cursor = conn.cursor()
            
            # Create database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
            
            # Connect to the database
            conn.database = DB_CONFIG['database']
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(50) NOT NULL
                )
            """)
            
            # Create images table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    title VARCHAR(100) NOT NULL,
                    image LONGBLOB NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Add a test user if none exists
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users (username, password) VALUES ('test', 'test')")
                
            conn.commit()
            cursor.close()
            conn.close()
            print("Database initialized successfully")
            
    except Error as e:
        print(f"Error: {e}")


class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Editor - Login")
        self.setGeometry(300, 300, 400, 200)
        
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Username and password fields
        form_layout = QGridLayout()
        
        username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username_input, 0, 1)
        
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_input, 1, 1)
        
        main_layout.addLayout(form_layout)
        
        # Login button
        login_button = QPushButton("Login")
        login_button.clicked.connect(self.login)
        main_layout.addWidget(login_button)
        
    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both username and password")
            return
        
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                cursor = conn.cursor()
                query = "SELECT id FROM users WHERE username = %s AND password = %s"
                cursor.execute(query, (username, password))
                result = cursor.fetchone()
                
                if result:
                    user_id = result[0]
                    self.hide()
                    self.select_window = SelectWindow(user_id)
                    self.select_window.show()
                else:
                    QMessageBox.warning(self, "Login Error", "Invalid username or password")
                
                cursor.close()
                conn.close()
                
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not connect to database: {e}")


class SelectWindow(QMainWindow):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("Photo Editor - Select Image")
        self.setGeometry(200, 200, 800, 600)
        
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Upload tab
        upload_tab = QWidget()
        upload_layout = QVBoxLayout(upload_tab)
        
        upload_title_layout = QHBoxLayout()
        upload_title_label = QLabel("Image Title:")
        self.upload_title_input = QLineEdit()
        upload_title_layout.addWidget(upload_title_label)
        upload_title_layout.addWidget(self.upload_title_input)
        
        upload_layout.addLayout(upload_title_layout)
        
        browse_button = QPushButton("Browse Image")
        browse_button.clicked.connect(self.browse_image)
        upload_layout.addWidget(browse_button)
        
        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setMinimumSize(300, 300)
        self.image_preview_label.setStyleSheet("border: 1px solid gray;")
        upload_layout.addWidget(self.image_preview_label)
        
        upload_button = QPushButton("Upload to Database")
        upload_button.clicked.connect(self.upload_to_database)
        upload_layout.addWidget(upload_button)
        
        tabs.addTab(upload_tab, "Upload Image")
        
        # Gallery tab
        gallery_tab = QWidget()
        gallery_layout = QVBoxLayout(gallery_tab)
        
        refresh_button = QPushButton("Refresh Gallery")
        refresh_button.clicked.connect(self.load_images)
        gallery_layout.addWidget(refresh_button)
        
        # Scroll area for gallery
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        gallery_layout.addWidget(scroll_area)
        
        self.gallery_content = QWidget()
        self.gallery_grid = QGridLayout(self.gallery_content)
        scroll_area.setWidget(self.gallery_content)
        
        tabs.addTab(gallery_tab, "Gallery")
        
        # Initial image data
        self.current_image_path = None
        self.current_image = None
        
        # Load images on start
        self.load_images()

    def browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        
        if file_path:
            self.current_image_path = file_path
            pixmap = QPixmap(file_path)
            
            # Scale pixmap if needed
            if pixmap.width() > 300 or pixmap.height() > 300:
                pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
            self.image_preview_label.setPixmap(pixmap)
            
            # Open with PIL for later use
            self.current_image = Image.open(file_path)
    
    def upload_to_database(self):
        if not self.current_image:
            QMessageBox.warning(self, "Upload Error", "Please select an image first")
            return
            
        image_title = self.upload_title_input.text()
        if not image_title:
            QMessageBox.warning(self, "Upload Error", "Please provide a title for the image")
            return
            
        try:
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            self.current_image.save(img_byte_arr, format=self.current_image.format or 'PNG')
            image_data = img_byte_arr.getvalue()
            
            # Save to database
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                cursor = conn.cursor()
                query = "INSERT INTO images (user_id, title, image) VALUES (%s, %s, %s)"
                cursor.execute(query, (self.user_id, image_title, image_data))
                conn.commit()
                cursor.close()
                conn.close()
                
                QMessageBox.information(self, "Upload Success", "Image uploaded successfully")
                self.upload_title_input.clear()
                self.image_preview_label.clear()
                self.current_image = None
                self.current_image_path = None
                
                # Refresh gallery
                self.load_images()
                
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not upload image: {e}")
    
    def load_images(self):
        # Clear existing items
        while self.gallery_grid.count():
            item = self.gallery_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                cursor = conn.cursor()
                query = "SELECT id, title, image FROM images WHERE user_id = %s"
                cursor.execute(query, (self.user_id,))
                results = cursor.fetchall()
                
                row, col = 0, 0
                max_cols = 3  # Number of columns in the grid
                
                for idx, (image_id, title, image_data) in enumerate(results):
                    # Create a frame for each image
                    image_frame = QFrame()
                    image_frame.setFrameShape(QFrame.Box)
                    image_frame.setLineWidth(1)
                    frame_layout = QVBoxLayout(image_frame)
                    
                    # Image title
                    title_label = QLabel(title)
                    title_label.setAlignment(Qt.AlignCenter)
                    frame_layout.addWidget(title_label)
                    
                    # Convert bytes to QPixmap
                    pixmap = self.bytes_to_pixmap(image_data)
                    if pixmap.width() > 200 or pixmap.height() > 200:
                        pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    image_label = QLabel()
                    image_label.setPixmap(pixmap)
                    image_label.setAlignment(Qt.AlignCenter)
                    frame_layout.addWidget(image_label)
                    
                    # Buttons layout
                    buttons_layout = QHBoxLayout()
                    
                    view_button = QPushButton("View")
                    view_button.clicked.connect(lambda checked, id=image_id: self.view_image(id))
                    buttons_layout.addWidget(view_button)
                    
                    update_button = QPushButton("Update")
                    update_button.clicked.connect(lambda checked, id=image_id: self.update_image(id))
                    buttons_layout.addWidget(update_button)
                    
                    delete_button = QPushButton("Delete")
                    delete_button.clicked.connect(lambda checked, id=image_id: self.delete_image(id))
                    buttons_layout.addWidget(delete_button)
                    
                    frame_layout.addLayout(buttons_layout)
                    
                    # Add to grid
                    self.gallery_grid.addWidget(image_frame, row, col)
                    
                    # Update row and column
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
                
                cursor.close()
                conn.close()
                
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not load images: {e}")
    
    def bytes_to_pixmap(self, image_data):
        qimg = QImage.fromData(QByteArray(image_data))
        return QPixmap.fromImage(qimg)
    
    def view_image(self, image_id):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                cursor = conn.cursor()
                query = "SELECT title, image FROM images WHERE id = %s"
                cursor.execute(query, (image_id,))
                result = cursor.fetchone()
                
                if result:
                    title, image_data = result
                    
                    # Create a simple viewer
                    viewer = QMainWindow(self)
                    viewer.setWindowTitle(f"View Image - {title}")
                    viewer.setGeometry(300, 300, 600, 500)
                    
                    central_widget = QWidget()
                    viewer.setCentralWidget(central_widget)
                    layout = QVBoxLayout(central_widget)
                    
                    image_label = QLabel()
                    pixmap = self.bytes_to_pixmap(image_data)
                    image_label.setPixmap(pixmap)
                    image_label.setAlignment(Qt.AlignCenter)
                    layout.addWidget(image_label)
                    
                    close_button = QPushButton("Close")
                    close_button.clicked.connect(viewer.close)
                    layout.addWidget(close_button)
                    
                    viewer.show()
                
                cursor.close()
                conn.close()
                
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not view image: {e}")
    
    def update_image(self, image_id):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                cursor = conn.cursor()
                query = "SELECT title, image FROM images WHERE id = %s"
                cursor.execute(query, (image_id,))
                result = cursor.fetchone()
                
                if result:
                    title, image_data = result
                    
                    # Convert bytes to PIL image
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Open editor window
                    self.editor_window = EditorWindow(image, image_id, title, self.user_id, self)
                    self.editor_window.show()
                
                cursor.close()
                conn.close()
                
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not load image for editing: {e}")
    
    def delete_image(self, image_id):
        reply = QMessageBox.question(self, "Confirm Delete", 
                                      "Are you sure you want to delete this image?",
                                      QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                conn = mysql.connector.connect(**DB_CONFIG)
                if conn.is_connected():
                    cursor = conn.cursor()
                    query = "DELETE FROM images WHERE id = %s"
                    cursor.execute(query, (image_id,))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    QMessageBox.information(self, "Delete Success", "Image deleted successfully")
                    self.load_images()  # Refresh gallery
                    
            except Error as e:
                QMessageBox.critical(self, "Database Error", f"Could not delete image: {e}")


class EditorWindow(QMainWindow):
    def __init__(self, image, image_id, title, user_id, parent=None):
        super().__init__(parent)
        self.image = image
        self.original_image = image.copy()  # Keep a copy of the original
        self.image_id = image_id
        self.title = title
        self.user_id = user_id
        
        self.setWindowTitle(f"Photo Editor - {title}")
        self.setGeometry(100, 100, 1000, 700)
        
        # Main layout with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left side - Image view
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.image_label)
        
        splitter.addWidget(left_widget)
        
        # Right side - Controls
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Title editing
        title_layout = QHBoxLayout()
        title_label = QLabel("Title:")
        self.title_input = QLineEdit(title)
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_input)
        right_layout.addLayout(title_layout)
        
        # Rotate & Flip options
        rotate_group = QFrame()
        rotate_group.setFrameShape(QFrame.StyledPanel)
        rotate_layout = QVBoxLayout(rotate_group)
        
        rotate_label = QLabel("Rotate & Flip")
        rotate_label.setStyleSheet("font-weight: bold;")
        rotate_layout.addWidget(rotate_label)
        
        rotate_buttons = QHBoxLayout()
        
        rotate_left_btn = QPushButton("Rotate Left")
        rotate_left_btn.clicked.connect(lambda: self.rotate_image(-90))
        rotate_buttons.addWidget(rotate_left_btn)
        
        rotate_right_btn = QPushButton("Rotate Right")
        rotate_right_btn.clicked.connect(lambda: self.rotate_image(90))
        rotate_buttons.addWidget(rotate_right_btn)
        
        flip_h_btn = QPushButton("Flip Horizontal")
        flip_h_btn.clicked.connect(lambda: self.flip_image("horizontal"))
        rotate_buttons.addWidget(flip_h_btn)
        
        flip_v_btn = QPushButton("Flip Vertical")
        flip_v_btn.clicked.connect(lambda: self.flip_image("vertical"))
        rotate_buttons.addWidget(flip_v_btn)
        
        rotate_layout.addLayout(rotate_buttons)
        right_layout.addWidget(rotate_group)
        
        # Brightness & Contrast
        adjust_group = QFrame()
        adjust_group.setFrameShape(QFrame.StyledPanel)
        adjust_layout = QVBoxLayout(adjust_group)
        
        adjust_label = QLabel("Adjust Brightness & Contrast")
        adjust_label.setStyleSheet("font-weight: bold;")
        adjust_layout.addWidget(adjust_label)
        
        # Brightness slider
        brightness_layout = QHBoxLayout()
        brightness_label = QLabel("Brightness:")
        brightness_layout.addWidget(brightness_label)
        
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 200)
        self.brightness_slider.setValue(100)  # Default value (100%)
        self.brightness_slider.setTickPosition(QSlider.TicksBelow)
        self.brightness_slider.setTickInterval(25)
        self.brightness_slider.valueChanged.connect(self.apply_brightness_contrast)
        brightness_layout.addWidget(self.brightness_slider)
        
        brightness_value = QLabel("100%")
        self.brightness_slider.valueChanged.connect(lambda value: brightness_value.setText(f"{value}%"))
        brightness_layout.addWidget(brightness_value)
        
        adjust_layout.addLayout(brightness_layout)
        
        # Contrast slider
        contrast_layout = QHBoxLayout()
        contrast_label = QLabel("Contrast:")
        contrast_layout.addWidget(contrast_label)
        
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(0, 200)
        self.contrast_slider.setValue(100)  # Default value (100%)
        self.contrast_slider.setTickPosition(QSlider.TicksBelow)
        self.contrast_slider.setTickInterval(25)
        self.contrast_slider.valueChanged.connect(self.apply_brightness_contrast)
        contrast_layout.addWidget(self.contrast_slider)
        
        contrast_value = QLabel("100%")
        self.contrast_slider.valueChanged.connect(lambda value: contrast_value.setText(f"{value}%"))
        contrast_layout.addWidget(contrast_value)
        
        adjust_layout.addLayout(contrast_layout)
        right_layout.addWidget(adjust_group)
        
        # Grayscale option
        grayscale_group = QFrame()
        grayscale_group.setFrameShape(QFrame.StyledPanel)
        grayscale_layout = QVBoxLayout(grayscale_group)
        
        grayscale_label = QLabel("Convert to Grayscale")
        grayscale_label.setStyleSheet("font-weight: bold;")
        grayscale_layout.addWidget(grayscale_label)
        
        grayscale_btn = QPushButton("Apply Grayscale")
        grayscale_btn.clicked.connect(self.apply_grayscale)
        grayscale_layout.addWidget(grayscale_btn)
        
        right_layout.addWidget(grayscale_group)
        
        # Filters
        filter_group = QFrame()
        filter_group.setFrameShape(QFrame.StyledPanel)
        filter_layout = QVBoxLayout(filter_group)
        
        filter_label = QLabel("Apply Filters")
        filter_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(filter_label)
        
        filter_combo = QComboBox()
        filter_combo.addItems(["None", "Blur", "Sharpen", "Edge Enhance"])
        filter_layout.addWidget(filter_combo)
        
        apply_filter_btn = QPushButton("Apply Filter")
        apply_filter_btn.clicked.connect(lambda: self.apply_filter(filter_combo.currentText()))
        filter_layout.addWidget(apply_filter_btn)
        
        right_layout.addWidget(filter_group)
        
        # Save and reset buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset Image")
        reset_btn.clicked.connect(self.reset_image)
        button_layout.addWidget(reset_btn)
        
        save_btn = QPushButton("Save to Database")
        save_btn.clicked.connect(self.save_to_database)
        button_layout.addWidget(save_btn)
        
        right_layout.addLayout(button_layout)
        
        # Add a spacer to push everything up
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        
        # Set initial splitter position
        splitter.setSizes([650, 350])
        
        # Update the image display
        self.update_display()
    
    def update_display(self):
    # Convert PIL image to QPixmap using a buffer
        img_byte_arr = io.BytesIO()
        self.image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        data = img_byte_arr.read()
        
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        
        # Scale if needed
        max_width = self.image_label.width() - 20  # Padding
        max_height = self.image_label.height() - 20  # Padding
        
        if max_width > 0 and max_height > 0:
            if pixmap.width() > max_width or pixmap.height() > max_height:
                pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.image_label.setPixmap(pixmap)
    
    def rotate_image(self, degrees):
        self.image = self.image.rotate(degrees, expand=True)
        self.update_display()
    
    def flip_image(self, direction):
        if direction == "horizontal":
            self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
        elif direction == "vertical":
            self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
        self.update_display()
    
    def apply_brightness_contrast(self):
        # Get slider values
        brightness_factor = self.brightness_slider.value() / 100.0
        contrast_factor = self.contrast_slider.value() / 100.0
        
        # Apply to a copy of the original image
        img = self.original_image.copy()
        
        # Apply brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness_factor)
        
        # Apply contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_factor)
        
        self.image = img
        self.update_display()
    
    def apply_grayscale(self):
        self.image = self.image.convert('L').convert('RGB')
        self.update_display()
    
    def apply_filter(self, filter_name):
        if filter_name == "None":
            return
        
        img = self.image.copy()
        
        if filter_name == "Blur":
            img = img.filter(ImageFilter.GaussianBlur(radius=2))
            
        elif filter_name == "Sharpen":
            img = img.filter(ImageFilter.SHARPEN)
            
        elif filter_name == "Edge Enhance":
            img = img.filter(ImageFilter.EDGE_ENHANCE)
        
        self.image = img
        self.update_display()
    
    def reset_image(self):
        self.image = self.original_image.copy()
        self.brightness_slider.setValue(100)
        self.contrast_slider.setValue(100)
        self.update_display()
    
    def save_to_database(self):
        new_title = self.title_input.text()
        if not new_title:
            QMessageBox.warning(self, "Save Error", "Please provide a title for the image")
            return
        
        try:
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            self.image.save(img_byte_arr, format=self.image.format or 'PNG')
            image_data = img_byte_arr.getvalue()
            
            # Update in database
            conn = mysql.connector.connect(**DB_CONFIG)
            if conn.is_connected():
                cursor = conn.cursor()
                query = "UPDATE images SET title = %s, image = %s WHERE id = %s"
                cursor.execute(query, (new_title, image_data, self.image_id))
                conn.commit()
                cursor.close()
                conn.close()
                
                QMessageBox.information(self, "Save Success", "Image updated successfully")
                
                # Update the parent's gallery
                if isinstance(self.parent(), SelectWindow):
                    self.parent().load_images()
                
        except Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not save image: {e}")
    
    def resizeEvent(self, event):
        # Update the display when window is resized
        super().resizeEvent(event)
        self.update_display()


if __name__ == "__main__":
    # Initialize the database
    create_database()
    
    # Start the application
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())