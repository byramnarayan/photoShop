import os
import mysql.connector
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QListWidget, 
                             QComboBox, QVBoxLayout, QHBoxLayout, QFileDialog, 
                             QInputDialog, QMessageBox, QLineEdit, QSlider)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from PIL import Image, ImageFilter, ImageEnhance
import sys


# If get database error:
# sudo mysql
# > ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'mini@123';
# > FLUSH PRIVILEGES;




class PhotoEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self.edited_image = None
        self.original_image = None
        self.db_connection = None
        self.init_ui()
        self.connect_to_database()
        self.load_saved_images()
        
    def init_ui(self):
        # Main layout
        main_layout = QHBoxLayout()
        
        # Left panel for saved images and database operations
        left_panel = QVBoxLayout()
        
        # Saved images list
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.load_image_from_db)
        left_panel.addWidget(QLabel("Saved Images:"))
        left_panel.addWidget(self.image_list)
        
        # Database operation buttons
        db_buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save to DB")
        self.save_btn.clicked.connect(self.save_to_database)
        self.save_btn.setEnabled(False)
        
        self.update_btn = QPushButton("Update in DB")
        self.update_btn.clicked.connect(self.update_in_database)
        self.update_btn.setEnabled(False)
        
        self.delete_btn = QPushButton("Delete from DB")
        self.delete_btn.clicked.connect(self.delete_from_database)
        self.delete_btn.setEnabled(False)
        
        db_buttons_layout.addWidget(self.save_btn)
        db_buttons_layout.addWidget(self.update_btn)
        db_buttons_layout.addWidget(self.delete_btn)
        
        left_panel.addLayout(db_buttons_layout)
        
        # Center panel for image display and basic operations
        center_panel = QVBoxLayout()
        
        # Image display
        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 400)
        center_panel.addWidget(self.image_label)
        
        # Basic operation buttons
        basic_ops_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load Image")
        self.load_btn.clicked.connect(self.load_image)
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_image)
        self.reset_btn.setEnabled(False)
        
        self.save_file_btn = QPushButton("Save to File")
        self.save_file_btn.clicked.connect(self.save_to_file)
        self.save_file_btn.setEnabled(False)
        
        basic_ops_layout.addWidget(self.load_btn)
        basic_ops_layout.addWidget(self.reset_btn)
        basic_ops_layout.addWidget(self.save_file_btn)
        
        center_panel.addLayout(basic_ops_layout)
        
        # Right panel for editing operations
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Edit Options:"))
        
        # Filter combobox
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["None", "Blur", "Contour", "Sharpen", "Smooth", "Emboss"])
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        right_panel.addWidget(QLabel("Filters:"))
        right_panel.addWidget(self.filter_combo)
        
        # Brightness adjustment
        right_panel.addWidget(QLabel("Brightness:"))
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 200)
        self.brightness_slider.setValue(100)
        self.brightness_slider.valueChanged.connect(self.adjust_brightness)
        right_panel.addWidget(self.brightness_slider)
        
        # Contrast adjustment
        right_panel.addWidget(QLabel("Contrast:"))
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(0, 200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.adjust_contrast)
        right_panel.addWidget(self.contrast_slider)
        
        # Add all panels to main layout
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(center_panel, 2)
        main_layout.addLayout(right_panel, 1)
        
        # Set the main layout and window properties
        self.setLayout(main_layout)
        self.setWindowTitle("PhotoEditor")
        self.setMinimumSize(800, 600)
        self.show()
        
    def connect_to_database(self):
        try:
            self.db_connection = mysql.connector.connect(
                host="localhost",
                user="root",  
                password="mini@123", 
                database="photo_editors"
            )
            
            # Create table if it doesn't exist
            cursor = self.db_connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    path VARCHAR(255) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.db_connection.commit()
            cursor.close()
            
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Database Error", f"Could not connect to database: {err}")
            
    def load_saved_images(self):
        if not self.db_connection:
            return
            
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT id, name FROM images ORDER BY created_at DESC")
            results = cursor.fetchall()
            
            self.image_list.clear()
            for id, name in results:
                self.image_list.addItem(f"{id}: {name}")
                
            cursor.close()
            
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Database Error", f"Could not load saved images: {err}")
            
    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            # Check if the file is a JPG or PNG
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in ['.jpg', '.jpeg', '.png']:
                QMessageBox.warning(self, "Invalid Format", "Only JPG and PNG formats are supported.")
                return
                
            try:
                self.current_image_path = file_path
                self.original_image = Image.open(file_path)
                self.edited_image = self.original_image.copy()
                self.display_image(self.edited_image)
                
                self.reset_btn.setEnabled(True)
                self.save_file_btn.setEnabled(True)
                self.save_btn.setEnabled(True)
                
                # Reset filters and adjustments
                self.filter_combo.setCurrentIndex(0)
                self.brightness_slider.setValue(100)
                self.contrast_slider.setValue(100)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load image: {e}")
                
    def load_image_from_db(self, item):
        if not self.db_connection:
            return
            
        try:
            # Extract ID from the item text
            item_id = int(item.text().split(":")[0])
            
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT path FROM images WHERE id = %s", (item_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result and os.path.exists(result[0]):
                # Check file extension
                file_ext = os.path.splitext(result[0])[1].lower()
                if file_ext not in ['.jpg', '.jpeg', '.png']:
                    QMessageBox.warning(self, "Invalid Format", "Only JPG and PNG formats are supported.")
                    return
                    
                self.current_image_path = result[0]
                self.original_image = Image.open(result[0])
                self.edited_image = self.original_image.copy()
                self.display_image(self.edited_image)
                
                self.reset_btn.setEnabled(True)
                self.save_file_btn.setEnabled(True)
                self.update_btn.setEnabled(True)
                self.delete_btn.setEnabled(True)
                
                # Reset filters and adjustments
                self.filter_combo.setCurrentIndex(0)
                self.brightness_slider.setValue(100)
                self.contrast_slider.setValue(100)
            else:
                QMessageBox.warning(self, "Warning", "Image file no longer exists at the saved location.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load image from database: {e}")
            
    def display_image(self, pil_image):
        # Convert PIL image to QPixmap and display it
        if pil_image:
            # Resize image if it's too large while maintaining aspect ratio
            pil_image.thumbnail((800, 800))
            
            # Convert PIL image to QPixmap
            pil_image_rgb = pil_image.convert("RGB")
            data = pil_image_rgb.tobytes("raw", "RGB")
            qimage = QImage(data, pil_image_rgb.width, pil_image_rgb.height, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage)
            self.image_label.setPixmap(pixmap)
            self.image_label.setScaledContents(True)
            
    def reset_image(self):
        if self.original_image:
            self.edited_image = self.original_image.copy()
            self.display_image(self.edited_image)
            
            # Reset filters and adjustments
            self.filter_combo.setCurrentIndex(0)
            self.brightness_slider.setValue(100)
            self.contrast_slider.setValue(100)
            
    def apply_filter(self):
        if not self.edited_image:
            return
            
        filter_name = self.filter_combo.currentText()
        
        # Start with the original image
        self.edited_image = self.original_image.copy()
        
        # Apply current brightness and contrast
        brightness = self.brightness_slider.value() / 100
        if brightness != 1:
            enhancer = ImageEnhance.Brightness(self.edited_image)
            self.edited_image = enhancer.enhance(brightness)
            
        contrast = self.contrast_slider.value() / 100
        if contrast != 1:
            enhancer = ImageEnhance.Contrast(self.edited_image)
            self.edited_image = enhancer.enhance(contrast)
        
        # Apply selected filter
        if filter_name == "Blur":
            self.edited_image = self.edited_image.filter(ImageFilter.BLUR)
        elif filter_name == "Contour":
            self.edited_image = self.edited_image.filter(ImageFilter.CONTOUR)
        elif filter_name == "Sharpen":
            self.edited_image = self.edited_image.filter(ImageFilter.SHARPEN)
        elif filter_name == "Smooth":
            self.edited_image = self.edited_image.filter(ImageFilter.SMOOTH)
        elif filter_name == "Emboss":
            self.edited_image = self.edited_image.filter(ImageFilter.EMBOSS)
            
        self.display_image(self.edited_image)
        
    def adjust_brightness(self):
        if not self.edited_image:
            return
            
        # Apply current filter again with new brightness
        self.apply_filter()
        
    def adjust_contrast(self):
        if not self.edited_image:
            return
            
        # Apply current filter again with new contrast
        self.apply_filter()
        
    def save_to_file(self):
        if not self.edited_image:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG (*.png);;JPEG (*.jpg)"
        )
        
        if file_path:
            # Ensure extension is either .jpg or .png
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in ['.jpg', '.jpeg', '.png']:
                if '.jpg' in _:
                    file_path += '.jpg'
                else:
                    file_path += '.png'
                    
            try:
                self.edited_image.save(file_path)
                QMessageBox.information(self, "Success", "Image saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save image: {e}")
                
    def save_to_database(self):
        if not self.edited_image or not self.db_connection:
            return
            
        # Get a name for the image
        name, ok = QInputDialog.getText(self, "Save to Database", "Enter a name for this image:")
        
        if ok and name:
            try:
                # Save the edited image to a file
                save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_images")
                os.makedirs(save_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                
                # Get the original extension or default to PNG
                original_ext = os.path.splitext(self.current_image_path)[1].lower() if self.current_image_path else '.png'
                if original_ext not in ['.jpg', '.jpeg', '.png']:
                    original_ext = '.png'
                    
                save_path = os.path.join(save_dir, f"{timestamp}_{name}{original_ext}")
                self.edited_image.save(save_path)
                
                # Save the record to database
                cursor = self.db_connection.cursor()
                cursor.execute(
                    "INSERT INTO images (name, path) VALUES (%s, %s)",
                    (name, save_path)
                )
                self.db_connection.commit()
                cursor.close()
                
                QMessageBox.information(self, "Success", "Image saved to database successfully!")
                self.load_saved_images()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save to database: {e}")
                
    def update_in_database(self):
        if not self.edited_image or not self.db_connection:
            return
            
        # Check if an image is selected in the list
        if not self.image_list.currentItem():
            QMessageBox.warning(self, "Warning", "Please select an image from the list to update.")
            return
            
        item_id = int(self.image_list.currentItem().text().split(":")[0])
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT path FROM images WHERE id = %s", (item_id,))
            result = cursor.fetchone()
            
            if result:
                # Save edited image to the same path
                save_path = result[0]
                
                # Check file extension
                file_ext = os.path.splitext(save_path)[1].lower()
                if file_ext not in ['.jpg', '.jpeg', '.png']:
                    QMessageBox.warning(self, "Invalid Format", "Only JPG and PNG formats are supported.")
                    return
                    
                self.edited_image.save(save_path)
                
                QMessageBox.information(self, "Success", "Image updated successfully!")
            else:
                QMessageBox.warning(self, "Warning", "Image not found in database.")
                
            cursor.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update image: {e}")
            
    def delete_from_database(self):
        if not self.db_connection:
            return
            
        # Check if an image is selected in the list
        if not self.image_list.currentItem():
            QMessageBox.warning(self, "Warning", "Please select an image from the list to delete.")
            return
            
        item_id = int(self.image_list.currentItem().text().split(":")[0])
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this image?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                cursor = self.db_connection.cursor()
                
                # Get the file path before deleting the record
                cursor.execute("SELECT path FROM images WHERE id = %s", (item_id,))
                result = cursor.fetchone()
                
                # Delete the record from the database
                cursor.execute("DELETE FROM images WHERE id = %s", (item_id,))
                self.db_connection.commit()
                
                # Delete the file if it exists
                if result and os.path.exists(result[0]):
                    os.remove(result[0])
                    
                cursor.close()
                
                QMessageBox.information(self, "Success", "Image deleted successfully!")
                self.load_saved_images()
                
                # Clear the image display if the deleted image was being displayed
                if self.current_image_path == result[0]:
                    self.image_label.setText("No image loaded")
                    self.current_image_path = None
                    self.original_image = None
                    self.edited_image = None
                    self.reset_btn.setEnabled(False)
                    self.save_file_btn.setEnabled(False)
                    self.save_btn.setEnabled(False)
                    self.update_btn.setEnabled(False)
                    self.delete_btn.setEnabled(False)
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete image: {e}")
                
    def closeEvent(self, event):
        if self.db_connection:
            self.db_connection.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = PhotoEditor()
    sys.exit(app.exec_())