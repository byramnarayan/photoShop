import sys
import os
import io
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QFileDialog, QScrollArea, QFrame, QGridLayout,
                             QMessageBox, QSlider, QComboBox, QGroupBox, QDialog)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush
from PyQt5.QtCore import Qt, QSize, QBuffer, QRect
import mysql.connector
from PIL import Image, ImageEnhance, ImageFilter

class DatabaseHandler:
    def __init__(self):
        self.connection = None
        self.connect_to_database()
        self.create_tables()
        
    def connect_to_database(self):
        try:
            self.connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="mini@123",
                database="photo_editor_db"
            )
            print("Connected to database successfully")
        except mysql.connector.Error as err:
            if err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
                # Database doesn't exist, create it
                temp_conn = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="m"
                )
                cursor = temp_conn.cursor()
                cursor.execute("CREATE DATABASE photo_editor_db")
                cursor.close()
                temp_conn.close()
                
                # Connect to the newly created database
                self.connection = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="",
                    database="photo_editor_db"
                )
                print("Created and connected to database successfully")
            else:
                print(f"Database connection error: {err}")
                sys.exit(1)
    
    def create_tables(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                image_data LONGBLOB NOT NULL,
                image_type VARCHAR(10) NOT NULL
            )
        """)
        self.connection.commit()
        cursor.close()
    
    def save_image(self, name, image_data, image_type):
        cursor = self.connection.cursor()
        query = "INSERT INTO images (name, image_data, image_type) VALUES (%s, %s, %s)"
        cursor.execute(query, (name, image_data, image_type))
        self.connection.commit()
        image_id = cursor.lastrowid
        cursor.close()
        return image_id
    
    def update_image(self, image_id, image_data):
        cursor = self.connection.cursor()
        query = "UPDATE images SET image_data = %s WHERE id = %s"
        cursor.execute(query, (image_data, image_id))
        self.connection.commit()
        cursor.close()
    
    def get_all_images(self):
        cursor = self.connection.cursor()
        query = "SELECT id, name, image_data, image_type FROM images"
        cursor.execute(query)
        images = cursor.fetchall()
        cursor.close()
        return images
    
    def get_image_by_id(self, image_id):
        cursor = self.connection.cursor()
        query = "SELECT id, name, image_data, image_type FROM images WHERE id = %s"
        cursor.execute(query, (image_id,))
        image = cursor.fetchone()
        cursor.close()
        return image
    
    def delete_image(self, image_id):
        cursor = self.connection.cursor()
        query = "DELETE FROM images WHERE id = %s"
        cursor.execute(query, (image_id,))
        self.connection.commit()
        cursor.close()
    
    def close(self):
        if self.connection:
            self.connection.close()

            
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_handler = DatabaseHandler()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Photo Editor App")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create buttons
        self.upload_btn = QPushButton("Upload Image to Database")
        self.select_btn = QPushButton("Select from Database")
        
        self.select_btn.setStyleSheet("background-color: green; color: white;")


        # Set button size
        self.upload_btn.setMinimumSize(300, 80)
        self.select_btn.setMinimumSize(300, 80)
        
        # Add buttons to layout with some spacing
        button_layout = QVBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.upload_btn, alignment=Qt.AlignCenter)
        button_layout.addSpacing(20)
        button_layout.addWidget(self.select_btn, alignment=Qt.AlignCenter)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.upload_btn.clicked.connect(self.upload_image)
        self.select_btn.clicked.connect(self.view_database)
    
    def upload_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.jpg *.jpeg *.png)"
        )
        
        if file_path:
            # Get file details
            file_info = QFileInfo(file_path)
            filename = file_info.fileName()
            file_extension = file_info.suffix().lower()
            
            if file_extension not in ['jpg', 'jpeg', 'png']:
                QMessageBox.warning(self, "Invalid File", "Only JPG and PNG files are allowed.")
                return
                
            # Read image data
            with open(file_path, 'rb') as file:
                image_data = file.read()
            
            # Save to database
            self.db_handler.save_image(filename, image_data, file_extension)
            QMessageBox.information(self, "Success", "Image uploaded successfully!")
    
    def view_database(self):
        self.database_view = DatabaseView(self.db_handler)
        self.database_view.show()
        self.hide()

class DatabaseView(QMainWindow):
    def __init__(self, db_handler):
        super().__init__()
        self.db_handler = db_handler
        self.init_ui()
        self.load_images()
        
    def init_ui(self):
        self.setWindowTitle("Database Images")
        self.setGeometry(100, 100, 900, 700)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Top buttons
        top_layout = QHBoxLayout()
        self.back_btn = QPushButton("Back to Main")
        self.refresh_btn = QPushButton("Refresh")
        self.upload_btn = QPushButton("Upload New Image")
        
        top_layout.addWidget(self.back_btn)
        top_layout.addWidget(self.refresh_btn)
        top_layout.addWidget(self.upload_btn)
        
        main_layout.addLayout(top_layout)
        
        # Scroll area for images
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)
        
        # Connect signals
        self.back_btn.clicked.connect(self.go_back)
        self.refresh_btn.clicked.connect(self.load_images)
        self.upload_btn.clicked.connect(self.upload_image)
    
    def go_back(self):
        # Show main window and close this one
        self.parent_window = [x for x in QApplication.topLevelWidgets() if isinstance(x, MainWindow)][0]
        self.parent_window.show()
        self.close()
    
    def upload_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.jpg *.jpeg *.png)"
        )
        
        if file_path:
            file_info = QFileInfo(file_path)
            filename = file_info.fileName()
            file_extension = file_info.suffix().lower()
            
            if file_extension not in ['jpg', 'jpeg', 'png']:
                QMessageBox.warning(self, "Invalid File", "Only JPG and PNG files are allowed.")
                return
                
            # Read image data
            with open(file_path, 'rb') as file:
                image_data = file.read()
            
            # Save to database
            self.db_handler.save_image(filename, image_data, file_extension)
            QMessageBox.information(self, "Success", "Image uploaded successfully!")
            self.load_images()
            
    def load_images(self):
        # Clear existing images
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Get all images from database
        images = self.db_handler.get_all_images()
        
        if not images:
            no_images_label = QLabel("No images found in database")
            no_images_label.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(no_images_label)
            return
            
        # Add each image to the layout
        for image_id, name, image_data, image_type in images:
            image_frame = QFrame()
            image_frame.setFrameShape(QFrame.Box)
            image_frame.setLineWidth(1)
            
            frame_layout = QHBoxLayout(image_frame)
            
            # Image thumbnail
            image = QImage.fromData(image_data)
            pixmap = QPixmap.fromImage(image)
            pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            image_label = QLabel()
            image_label.setPixmap(pixmap)
            image_label.setFixedSize(200, 150)
            image_label.setAlignment(Qt.AlignCenter)
            
            # Image details
            details_layout = QVBoxLayout()
            id_label = QLabel(f"ID: {image_id}")
            name_label = QLabel(f"Name: {name}")
            type_label = QLabel(f"Type: {image_type}")
            
            details_layout.addWidget(id_label)
            details_layout.addWidget(name_label)
            details_layout.addWidget(type_label)
            details_layout.addStretch()
            
            # Buttons
            buttons_layout = QVBoxLayout()
            view_btn = QPushButton("Read")
            update_btn = QPushButton("Update")
            
            delete_btn = QPushButton("Delete")
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("background-color: red; color: white;")  # Change button color to red


            select_btn = QPushButton("Select")
            
            buttons_layout.addWidget(view_btn)
            buttons_layout.addWidget(update_btn)
            buttons_layout.addWidget(delete_btn)
            buttons_layout.addWidget(select_btn)
            buttons_layout.addStretch()
            
            # Connect button signals
            view_btn.clicked.connect(lambda checked, img_id=image_id: self.view_image(img_id))
            update_btn.clicked.connect(lambda checked, img_id=image_id: self.update_image(img_id))
            delete_btn.clicked.connect(lambda checked, img_id=image_id: self.delete_image(img_id))
            select_btn.clicked.connect(lambda checked, img_id=image_id: self.edit_image(img_id))
            
            # Add to frame layout
            frame_layout.addWidget(image_label)
            frame_layout.addLayout(details_layout)
            frame_layout.addStretch()
            frame_layout.addLayout(buttons_layout)
            
            # Add frame to scroll layout
            self.scroll_layout.addWidget(image_frame)
    
    def view_image(self, image_id):
        image = self.db_handler.get_image_by_id(image_id)
        if image:
            _, name, image_data, image_type = image
            
            # Create a new window to display the image
            view_dialog = QDialog(self)
            view_dialog.setWindowTitle(f"View Image: {name}")
            view_dialog.setGeometry(200, 200, 800, 600)
            
            layout = QVBoxLayout(view_dialog)
            
            # Display image
            qimg = QImage.fromData(image_data)
            pixmap = QPixmap.fromImage(qimg)
            
            image_label = QLabel()
            image_label.setPixmap(pixmap.scaled(
                700, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            image_label.setAlignment(Qt.AlignCenter)
            
            layout.addWidget(image_label)
            
            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(view_dialog.close)
            layout.addWidget(close_btn, alignment=Qt.AlignCenter)
            
            view_dialog.exec_()
    
    def update_image(self, image_id):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Select New Image", "", "Image Files (*.jpg *.jpeg *.png)"
        )
        
        if file_path:
            file_info = QFileInfo(file_path)
            file_extension = file_info.suffix().lower()
            
            if file_extension not in ['jpg', 'jpeg', 'png']:
                QMessageBox.warning(self, "Invalid File", "Only JPG and PNG files are allowed.")
                return
                
            # Read image data
            with open(file_path, 'rb') as file:
                image_data = file.read()
            
            # Update in database
            self.db_handler.update_image(image_id, image_data)
            QMessageBox.information(self, "Success", "Image updated successfully!")
            self.load_images()
    
    def delete_image(self, image_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this image?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            self.db_handler.delete_image(image_id)
            QMessageBox.information(self, "Success", "Image deleted successfully!")
            self.load_images()
    
    def edit_image(self, image_id):
        image = self.db_handler.get_image_by_id(image_id)
        if image:
            self.editor = ImageEditor(self.db_handler, image)
            self.editor.show()
            self.hide()

class ImageEditor(QMainWindow):
    def __init__(self, db_handler, image_data):
        super().__init__()
        self.db_handler = db_handler
        self.image_id, self.image_name, self.original_image_data, self.image_type = image_data
        
        # Convert image data to PIL Image
        self.original_pil_image = Image.open(io.BytesIO(self.original_image_data))
        self.current_pil_image = self.original_pil_image.copy()
        
        self.init_ui()
        self.update_preview()
        
    def init_ui(self):
        self.setWindowTitle(f"Editing: {self.image_name}")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left side - Image preview
        self.preview_frame = QFrame()
        self.preview_frame.setFrameShape(QFrame.Box)
        self.preview_frame.setLineWidth(1)
        self.preview_frame.setMinimumWidth(600)
        
        preview_layout = QVBoxLayout(self.preview_frame)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.image_label)
        
        # Right side - Editing options
        options_widget = QWidget()
        options_layout = QVBoxLayout(options_widget)
        
        # Rotate & Flip
        rotate_flip_group = QGroupBox("Rotate & Flip")
        rotate_flip_layout = QHBoxLayout(rotate_flip_group)
        
        self.rotate_left_btn = QPushButton("Rotate Left")
        self.rotate_right_btn = QPushButton("Rotate Right")
        self.flip_h_btn = QPushButton("Flip Horizontal")
        self.flip_v_btn = QPushButton("Flip Vertical")
        
        rotate_flip_layout.addWidget(self.rotate_left_btn)
        rotate_flip_layout.addWidget(self.rotate_right_btn)
        rotate_flip_layout.addWidget(self.flip_h_btn)
        rotate_flip_layout.addWidget(self.flip_v_btn)
        
        options_layout.addWidget(rotate_flip_group)
        
        # Adjust Brightness & Contrast
        adjust_group = QGroupBox("Adjust Brightness & Contrast")
        adjust_layout = QVBoxLayout(adjust_group)
        
        self.brightness_btn = QPushButton("Increase Brightness")
        self.darkness_btn = QPushButton("Decrease Brightness")
        self.contrast_inc_btn = QPushButton("Increase Contrast")
        self.contrast_dec_btn = QPushButton("Decrease Contrast")
        
        adjust_layout.addWidget(self.brightness_btn)
        adjust_layout.addWidget(self.darkness_btn)
        adjust_layout.addWidget(self.contrast_inc_btn)
        adjust_layout.addWidget(self.contrast_dec_btn)
        
        options_layout.addWidget(adjust_group)
        
        # Grayscale
        grayscale_group = QGroupBox("Convert to Grayscale")
        grayscale_layout = QHBoxLayout(grayscale_group)
        
        self.grayscale_btn = QPushButton("Convert to Grayscale")
        
        grayscale_layout.addWidget(self.grayscale_btn)
        
        options_layout.addWidget(grayscale_group)
        
        # Apply Filters
        filters_group = QGroupBox("Apply Filters")
        filters_layout = QHBoxLayout(filters_group)
        
        self.sepia_btn = QPushButton("Sepia")
        self.blur_btn = QPushButton("Blur")
        self.sharpen_btn = QPushButton("Sharpen")
        
        filters_layout.addWidget(self.sepia_btn)
        filters_layout.addWidget(self.blur_btn)
        filters_layout.addWidget(self.sharpen_btn)
        
        options_layout.addWidget(filters_group)
        
        # Save and Cancel buttons
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save to Database")
        self.cancel_btn = QPushButton("Cancel")
        self.reset_btn = QPushButton("Reset Changes")
        
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        options_layout.addLayout(buttons_layout)
        options_layout.addStretch()
        
        # Add to main layout
        main_layout.addWidget(self.preview_frame)
        main_layout.addWidget(options_widget)
        
        # Connect signals
        self.rotate_left_btn.clicked.connect(lambda: self.rotate_image(-90))
        self.rotate_right_btn.clicked.connect(lambda: self.rotate_image(90))
        self.flip_h_btn.clicked.connect(lambda: self.flip_image("horizontal"))
        self.flip_v_btn.clicked.connect(lambda: self.flip_image("vertical"))
        
        self.brightness_btn.clicked.connect(lambda: self.adjust_brightness(1.2))
        self.darkness_btn.clicked.connect(lambda: self.adjust_brightness(0.8))
        self.contrast_inc_btn.clicked.connect(lambda: self.adjust_contrast(1.2))
        self.contrast_dec_btn.clicked.connect(lambda: self.adjust_contrast(0.8))
        
        self.grayscale_btn.clicked.connect(self.convert_to_grayscale)
        
        self.sepia_btn.clicked.connect(lambda: self.apply_filter("sepia"))
        self.blur_btn.clicked.connect(lambda: self.apply_filter("blur"))
        self.sharpen_btn.clicked.connect(lambda: self.apply_filter("sharpen"))
        
        self.save_btn.clicked.connect(self.save_image)
        self.reset_btn.clicked.connect(self.reset_image)
        self.cancel_btn.clicked.connect(self.cancel_editing)
    
    def update_preview(self):
        # Convert PIL image to QPixmap for display
        img_bytes = io.BytesIO()
        self.current_pil_image.save(img_bytes, format=self.image_type.upper())
        img_bytes.seek(0)
        
        img_data = img_bytes.read()
        qimg = QImage.fromData(img_data)
        pixmap = QPixmap.fromImage(qimg)
        
        # Scale pixmap to fit the label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.preview_frame.width() - 20,
            self.preview_frame.height() - 20,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)
    
    def rotate_image(self, degrees):
        self.current_pil_image = self.current_pil_image.rotate(degrees, expand=True)
        self.update_preview()
    
    def flip_image(self, direction):
        if direction == "horizontal":
            self.current_pil_image = self.current_pil_image.transpose(Image.FLIP_LEFT_RIGHT)
        else:
            self.current_pil_image = self.current_pil_image.transpose(Image.FLIP_TOP_BOTTOM)
        self.update_preview()
    
    def adjust_brightness(self, factor):
        enhancer = ImageEnhance.Brightness(self.current_pil_image)
        self.current_pil_image = enhancer.enhance(factor)
        self.update_preview()
    
    def adjust_contrast(self, factor):
        enhancer = ImageEnhance.Contrast(self.current_pil_image)
        self.current_pil_image = enhancer.enhance(factor)
        self.update_preview()
    
    def convert_to_grayscale(self):
        self.current_pil_image = self.current_pil_image.convert("L").convert("RGB")
        self.update_preview()
    
    def apply_filter(self, filter_type):
        if filter_type == "sepia":
            # Sepia filter implementation
            width, height = self.current_pil_image.size
            pixels = self.current_pil_image.load()
            
            sepia_img = Image.new("RGB", (width, height))
            sepia_pixels = sepia_img.load()
            
            for i in range(width):
                for j in range(height):
                    r, g, b = pixels[i, j]
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    
                    # Ensure values are in valid range
                    sepia_pixels[i, j] = (
                        min(255, tr), 
                        min(255, tg), 
                        min(255, tb)
                    )
            
            self.current_pil_image = sepia_img
            
        elif filter_type == "blur":
            self.current_pil_image = self.current_pil_image.filter(ImageFilter.BLUR)
            
        elif filter_type == "sharpen":
            self.current_pil_image = self.current_pil_image.filter(ImageFilter.SHARPEN)
        
        self.update_preview()
    
    def save_image(self):
        # Convert PIL image to bytes
        img_bytes = io.BytesIO()
        self.current_pil_image.save(img_bytes, format=self.image_type.upper())
        img_bytes.seek(0)
        
        # Update in database
        self.db_handler.update_image(self.image_id, img_bytes.read())
        QMessageBox.information(self, "Success", "Image saved successfully!")
        
        # Return to database view
        self.go_back()
    
    def reset_image(self):
        self.current_pil_image = self.original_pil_image.copy()
        self.update_preview()
    
    def cancel_editing(self):
        self.go_back()
    
    def go_back(self):
        # Return to database view
        self.db_view = DatabaseView(self.db_handler)
        self.db_view.show()
        self.close()
    
    def resizeEvent(self, event):
        self.update_preview()
        super().resizeEvent(event)

from PyQt5.QtCore import QFileInfo

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()