import os
import mysql.connector
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QListWidget, QComboBox, QVBoxLayout, QHBoxLayout, QFileDialog, QInputDialog, QMessageBox, QLineEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PIL import Image, ImageFilter, ImageEnhance

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'mini@123',  # Set your MySQL password here
    'database': 'photo_editor_crud'
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
    CREATE TABLE IF NOT EXISTS original_images (
        id INT AUTO_INCREMENT PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        filepath VARCHAR(255) NOT NULL,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS edited_images (
        id INT AUTO_INCREMENT PRIMARY KEY,
        original_id INT,
        edit_name VARCHAR(255) NOT NULL,
        filter_applied VARCHAR(50) NOT NULL,
        edit_path VARCHAR(255) NOT NULL,
        date_edited TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (original_id) REFERENCES original_images(id) ON DELETE CASCADE
    )
    ''')
    
    conn.commit()
    return conn

class PhotoEditor:
    def __init__(self):
        self.app = QApplication([])
        self.main_window = QWidget()
        self.main_window.setWindowTitle("Photo Editor with CRUD")
        self.main_window.resize(1000, 700)
        
        self.working_directory = ""
        self.conn = init_db()
        
        self.setup_ui()
        self.editor = Editor(self.picture_box, self.conn)
        self.connect_signals()
        
    def setup_ui(self):
        # UI Elements
        self.btn_select_photo = QPushButton("Select New Photo")
        self.original_files_list = QListWidget()
        self.original_files_list.setMinimumWidth(180)
        self.edited_files_list = QListWidget()
        self.edited_files_list.setMinimumWidth(180)
        
        # Filter options
        self.filter_label = QLabel("Apply Filter:")
        self.filter_box = QComboBox()
        self.filter_box.addItems(["Original", "Left", "Right", "Mirror", "Sharpness", "B/W", "Saturation", "Contrast", "Blur"])
        
        # CRUD buttons
        self.btn_create = QPushButton("Create New Edit")
        self.btn_read = QPushButton("View Selected Edit")
        self.btn_update = QPushButton("Update Edit")
        self.btn_delete = QPushButton("Delete Edit")
        
        # Database utility buttons
        self.btn_reconnect_db = QPushButton("Reconnect to Database")
        self.btn_add_description = QPushButton("Add Description")
        
        # Edit name field for creating and updating edits
        self.edit_name_label = QLabel("Edit Name:")
        self.edit_name_input = QLineEdit()
        
        # Lists labels
        self.original_list_label = QLabel("Original Images:")
        self.edited_list_label = QLabel("Edited Images:")
        
        self.picture_box = QLabel("Image Preview")
        self.picture_box.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("Status: Ready")
        
        # Create layouts
        master_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()
        lists_layout = QHBoxLayout()
        edit_name_layout = QHBoxLayout()
        crud_buttons_layout = QHBoxLayout()
        
        # Lists section
        original_list_layout = QVBoxLayout()
        original_list_layout.addWidget(self.original_list_label)
        original_list_layout.addWidget(self.original_files_list)
        
        edited_list_layout = QVBoxLayout()
        edited_list_layout.addWidget(self.edited_list_label)
        edited_list_layout.addWidget(self.edited_files_list)
        
        lists_layout.addLayout(original_list_layout)
        lists_layout.addLayout(edited_list_layout)
        
        # Edit name field layout
        edit_name_layout.addWidget(self.edit_name_label)
        edit_name_layout.addWidget(self.edit_name_input)
        
        # CRUD buttons layout
        crud_buttons_layout.addWidget(self.btn_create)
        crud_buttons_layout.addWidget(self.btn_read)
        crud_buttons_layout.addWidget(self.btn_update)
        crud_buttons_layout.addWidget(self.btn_delete)
        
        # Assemble left panel
        left_panel.addWidget(self.btn_select_photo)
        left_panel.addLayout(lists_layout)
        left_panel.addWidget(self.filter_label)
        left_panel.addWidget(self.filter_box)
        left_panel.addLayout(edit_name_layout)
        left_panel.addLayout(crud_buttons_layout)
        left_panel.addWidget(self.btn_add_description)
        left_panel.addWidget(self.btn_reconnect_db)
        left_panel.addWidget(self.status_label)
        
        # Right panel just has the image preview
        right_panel.addWidget(self.picture_box)
        
        # Put it all together
        master_layout.addLayout(left_panel, 30)
        master_layout.addLayout(right_panel, 70)
        self.main_window.setLayout(master_layout)
    
    def connect_signals(self):
        self.btn_select_photo.clicked.connect(self.get_photo)
        self.original_files_list.currentRowChanged.connect(self.display_original_image)
        self.edited_files_list.currentRowChanged.connect(self.display_edited_image)
        self.filter_box.currentTextChanged.connect(self.preview_filter)
        
        # CRUD operations
        self.btn_create.clicked.connect(self.create_edit)
        self.btn_read.clicked.connect(self.read_edit)
        self.btn_update.clicked.connect(self.update_edit)
        self.btn_delete.clicked.connect(self.delete_edit)
        
        # Other buttons
        self.btn_add_description.clicked.connect(self.add_description)
        self.btn_reconnect_db.clicked.connect(self.reconnect_database)
    
    def filter_files(self, files, extensions):
        return [file for file in files if any(file.endswith(ext.lower()) for ext in extensions)]
    
    def get_photo(self):
        self.original_files_list.clear()
        self.edited_files_list.clear()
        
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg)")
        
        if file_dialog.exec_():
            filenames = file_dialog.selectedFiles()
            
            for file_path in filenames:
                filename = os.path.basename(file_path)
                directory = os.path.dirname(file_path)
                
                if self.conn:
                    cursor = self.conn.cursor()
                    
                    # Check if image already exists in database
                    cursor.execute("SELECT id FROM original_images WHERE filename = %s AND filepath = %s", 
                                (filename, directory))
                    result = cursor.fetchone()
                    
                    if not result:
                        # Create new image record
                        cursor.execute(
                            "INSERT INTO original_images (filename, filepath) VALUES (%s, %s)",
                            (filename, directory)
                        )
                        self.conn.commit()
                
                self.original_files_list.addItem(filename)
            
            self.status_label.setText(f"Status: Added {len(filenames)} image(s)")
            
            # Set the working directory to the directory of the first selected file
            if filenames:
                self.working_directory = os.path.dirname(filenames[0])
                self.editor.set_working_directory(self.working_directory)
    
    def display_original_image(self):
        if self.original_files_list.currentRow() >= 0:
            filename = self.original_files_list.currentItem().text()
            self.edited_files_list.clear()
            
            self.editor.load_original_image(filename)
            
            # Load any existing edits for this image
            if self.conn:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT e.edit_name FROM edited_images e
                    JOIN original_images o ON e.original_id = o.id
                    WHERE o.filename = %s AND o.filepath = %s
                """, (filename, self.working_directory))
                
                edits = cursor.fetchall()
                for edit in edits:
                    self.edited_files_list.addItem(edit[0])
    
    def display_edited_image(self):
        if self.edited_files_list.currentRow() >= 0 and self.original_files_list.currentRow() >= 0:
            original_filename = self.original_files_list.currentItem().text()
            edit_name = self.edited_files_list.currentItem().text()
            
            # Load the edited image
            if self.conn:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT e.edit_path, e.filter_applied, e.edit_name
                    FROM edited_images e
                    JOIN original_images o ON e.original_id = o.id
                    WHERE o.filename = %s AND o.filepath = %s AND e.edit_name = %s
                """, (original_filename, self.working_directory, edit_name))
                
                result = cursor.fetchone()
                if result:
                    edit_path, filter_name, edit_name = result
                    self.editor.load_edited_image(edit_path, filter_name)
                    self.edit_name_input.setText(edit_name)
                    
                    # Set filter box to match the filter used
                    index = self.filter_box.findText(filter_name)
                    if index >= 0:
                        self.filter_box.setCurrentIndex(index)
    
    def preview_filter(self):
        if self.original_files_list.currentRow() >= 0:
            filter_name = self.filter_box.currentText()
            self.editor.preview_filter(filter_name)
    
    def create_edit(self):
        if self.original_files_list.currentRow() >= 0:
            edit_name = self.edit_name_input.text().strip()
            if not edit_name:
                QMessageBox.warning(self.main_window, "Warning", "Please enter an edit name")
                return
            
            original_filename = self.original_files_list.currentItem().text()
            filter_name = self.filter_box.currentText()
            
            # Check if edit name already exists for this image
            if self.conn:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM edited_images e
                    JOIN original_images o ON e.original_id = o.id
                    WHERE o.filename = %s AND o.filepath = %s AND e.edit_name = %s
                """, (original_filename, self.working_directory, edit_name))
                
                count = cursor.fetchone()[0]
                if count > 0:
                    QMessageBox.warning(self.main_window, "Warning", "An edit with this name already exists")
                    return
            
            # Create the edit
            success = self.editor.create_edit(original_filename, filter_name, edit_name)
            if success:
                self.edited_files_list.addItem(edit_name)
                self.status_label.setText(f"Status: Created edit '{edit_name}'")
    
    def read_edit(self):
        if self.edited_files_list.currentRow() >= 0:
            edit_name = self.edited_files_list.currentItem().text()
            self.display_edited_image()
            self.status_label.setText(f"Status: Viewing edit '{edit_name}'")
    
    def update_edit(self):
        if self.edited_files_list.currentRow() >= 0 and self.original_files_list.currentRow() >= 0:
            original_edit_name = self.edited_files_list.currentItem().text()
            new_edit_name = self.edit_name_input.text().strip()
            original_filename = self.original_files_list.currentItem().text()
            filter_name = self.filter_box.currentText()
            
            if not new_edit_name:
                QMessageBox.warning(self.main_window, "Warning", "Please enter an edit name")
                return
            
            # Check if new edit name already exists (if it's different from original)
            if new_edit_name != original_edit_name and self.conn:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM edited_images e
                    JOIN original_images o ON e.original_id = o.id
                    WHERE o.filename = %s AND o.filepath = %s AND e.edit_name = %s
                """, (original_filename, self.working_directory, new_edit_name))
                
                count = cursor.fetchone()[0]
                if count > 0:
                    QMessageBox.warning(self.main_window, "Warning", "An edit with this name already exists")
                    return
            
            # Update the edit
            success = self.editor.update_edit(original_filename, original_edit_name, new_edit_name, filter_name)
            if success:
                # Refresh the edited files list
                current_row = self.edited_files_list.currentRow()
                self.edited_files_list.item(current_row).setText(new_edit_name)
                self.status_label.setText(f"Status: Updated edit to '{new_edit_name}'")
    
    def delete_edit(self):
        if self.edited_files_list.currentRow() >= 0 and self.original_files_list.currentRow() >= 0:
            edit_name = self.edited_files_list.currentItem().text()
            original_filename = self.original_files_list.currentItem().text()
            
            reply = QMessageBox.question(
                self.main_window, 
                "Confirm Delete", 
                f"Are you sure you want to delete the edit '{edit_name}'?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.editor.delete_edit(original_filename, edit_name)
                if success:
                    # Remove from the edited files list
                    self.edited_files_list.takeItem(self.edited_files_list.currentRow())
                    self.status_label.setText(f"Status: Deleted edit '{edit_name}'")
    
    def add_description(self):
        if self.original_files_list.currentRow() >= 0:
            filename = self.original_files_list.currentItem().text()
            
            description, ok = QInputDialog.getText(
                self.main_window, 
                "Add Description", 
                "Enter a description for this image:"
            )
            
            if ok and description and self.conn:
                cursor = self.conn.cursor()
                cursor.execute(
                    "UPDATE original_images SET description = %s WHERE filename = %s AND filepath = %s",
                    (description, filename, self.working_directory)
                )
                self.conn.commit()
                QMessageBox.information(self.main_window, "Success", "Description added successfully")
                self.status_label.setText("Status: Added description")
    
    def reconnect_database(self):
        if self.conn:
            self.conn.close()
        
        self.conn = init_db()
        self.editor.set_connection(self.conn)
        
        if self.conn:
            QMessageBox.information(self.main_window, "Success", "Database connection established")
            self.status_label.setText("Status: Database connected")
        else:
            QMessageBox.warning(self.main_window, "Warning", "Failed to connect to database")
            self.status_label.setText("Status: Database connection failed")
    
    def run(self):
        self.main_window.show()
        return self.app.exec_()

class Editor:
    def __init__(self, picture_box, db_conn):
        self.picture_box = picture_box
        self.conn = db_conn
        self.image = None
        self.original = None
        self.filename = None
        self.working_directory = ""
        self.edits_directory = "edits"
        self.current_original_id = None
        
    def set_working_directory(self, directory):
        self.working_directory = directory
        # Create edits directory if it doesn't exist
        self.edits_path = os.path.join(directory, self.edits_directory)
        os.makedirs(self.edits_path, exist_ok=True)
    
    def set_connection(self, conn):
        self.conn = conn
    
    def load_original_image(self, filename):
        self.filename = filename
        fullpath = os.path.join(self.working_directory, filename)
        self.image = Image.open(fullpath)
        self.original = self.image.copy()
        
        # Get original image ID from database
        if self.conn:
            cursor = self.conn.cursor(buffered=True)
            cursor.execute("SELECT id FROM original_images WHERE filename = %s AND filepath = %s", 
                        (filename, self.working_directory))
            result = cursor.fetchone()
            
            if result:
                self.current_original_id = result[0]
        
        self.show_image(fullpath)
    
    def load_edited_image(self, edit_path, filter_name):
        self.image = Image.open(edit_path)
        self.show_image(edit_path)
    
    def show_image(self, path):
        pixmap = QPixmap(path)
        w, h = self.picture_box.width(), self.picture_box.height()
        pixmap = pixmap.scaled(w, h, Qt.KeepAspectRatio)
        self.picture_box.setPixmap(pixmap)
    
    def apply_filter(self, filter_name):
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
        
        if filter_name in transformations:
            return transformations[filter_name](self.original)
        return self.original.copy()
    
    def preview_filter(self, filter_name):
        if self.original is None:
            return
        
        self.image = self.apply_filter(filter_name)
        # Save to a temporary file
        temp_path = os.path.join(self.edits_path, "temp_preview.png")
        self.image.save(temp_path)
        self.show_image(temp_path)
    
    def create_edit(self, original_filename, filter_name, edit_name):
        if not self.conn or not self.current_original_id:
            QMessageBox.warning(None, "Warning", "Database connection issue")
            return False
        
        # Apply the filter
        filtered_image = self.apply_filter(filter_name)
        
        # Save the edited image
        edit_filename = f"{edit_name}_{original_filename}"
        edit_path = os.path.join(self.edits_path, edit_filename)
        filtered_image.save(edit_path)
        
        # Add to database
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO edited_images (original_id, edit_name, filter_applied, edit_path) VALUES (%s, %s, %s, %s)",
            (self.current_original_id, edit_name, filter_name, edit_path)
        )
        self.conn.commit()
        
        return True
    
    def update_edit(self, original_filename, original_edit_name, new_edit_name, filter_name):
        if not self.conn or not self.current_original_id:
            QMessageBox.warning(None, "Warning", "Database connection issue")
            return False
        
        # Find the edit record
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, edit_path FROM edited_images 
            WHERE original_id = %s AND edit_name = %s
        """, (self.current_original_id, original_edit_name))
        
        result = cursor.fetchone()
        if not result:
            QMessageBox.warning(None, "Warning", "Edit not found")
            return False
        
        edit_id, old_edit_path = result
        
        # Apply the filter
        filtered_image = self.apply_filter(filter_name)
        
        # Save the edited image (potentially with new name)
        edit_filename = f"{new_edit_name}_{original_filename}"
        edit_path = os.path.join(self.edits_path, edit_filename)
        filtered_image.save(edit_path)
        
        # Update database
        cursor.execute(
            "UPDATE edited_images SET edit_name = %s, filter_applied = %s, edit_path = %s WHERE id = %s",
            (new_edit_name, filter_name, edit_path, edit_id)
        )
        self.conn.commit()
        
        # Remove old file if edit name changed
        if original_edit_name != new_edit_name and os.path.exists(old_edit_path):
            try:
                os.remove(old_edit_path)
            except:
                pass  # Ignore file deletion errors
        
        return True
    
    def delete_edit(self, original_filename, edit_name):
        if not self.conn or not self.current_original_id:
            QMessageBox.warning(None, "Warning", "Database connection issue")
            return False
        
        # Find the edit record
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, edit_path FROM edited_images 
            WHERE original_id = %s AND edit_name = %s
        """, (self.current_original_id, edit_name))
        
        result = cursor.fetchone()
        if not result:
            QMessageBox.warning(None, "Warning", "Edit not found")
            return False
        
        edit_id, edit_path = result
        
        # Delete from database
        cursor.execute("DELETE FROM edited_images WHERE id = %s", (edit_id,))
        self.conn.commit()
        
        # Delete file
        if os.path.exists(edit_path):
            try:
                os.remove(edit_path)
            except:
                pass  # Ignore file deletion errors
        
        return True

# Run the application
if __name__ == "__main__":
    editor = PhotoEditor()
    editor.run()