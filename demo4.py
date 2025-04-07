import sys  # Import the system module to access system-specific parameters and functions
import os  # Import operating system module for file and directory operations
import io  # Import input/output module for handling byte streams
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,  # Import various PyQt5 widget classes
                             QWidget, QLabel, QFileDialog, QScrollArea, QFrame, QGridLayout,  # Import more widget classes
                             QMessageBox, QSlider, QComboBox, QGroupBox, QDialog)  # Import even more widget classes
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush  # Import PyQt5 graphics classes
from PyQt5.QtCore import Qt, QSize, QBuffer, QRect  # Import PyQt5 core classes
import mysql.connector  # Import MySQL connector for database operations
from PIL import Image, ImageEnhance, ImageFilter  # Import PIL (Pillow) for image processing

class DatabaseHandler:  # Define a class to handle database operations
    def __init__(self):  # Constructor method
        self.connection = None  # Initialize connection attribute as None
        self.connect_to_database()  # Call method to connect to database
        self.create_tables()  # Call method to create necessary tables
        
    def connect_to_database(self):  # Method to establish database connection
        try:  # Try to connect to the database
            self.connection = mysql.connector.connect(  # Attempt to connect to MySQL
                host="localhost",  # Connect to local MySQL server
                user="root",  # Use root username
                password="mini@123",  # Use this password
                database="photo_editor_db"  # Connect to this database
            )
            print("Connected to database successfully")  # Print success message
        except mysql.connector.Error as err:  # Handle database connection errors
            if err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:  # If database doesn't exist
                # Database doesn't exist, create it
                temp_conn = mysql.connector.connect(  # Create temporary connection
                    host="localhost",  # Connect to local MySQL server
                    user="root",  # Use root username
                    password="m"  # Use this password (note: inconsistent with previous password)
                )
                cursor = temp_conn.cursor()  # Create a cursor to execute SQL commands
                cursor.execute("CREATE DATABASE photo_editor_db")  # Create the database
                cursor.close()  # Close the cursor
                temp_conn.close()  # Close the temporary connection
                
                # Connect to the newly created database
                self.connection = mysql.connector.connect(  # Connect to the new database
                    host="localhost",  # Connect to local MySQL server
                    user="root",  # Use root username
                    password="",  # Use empty password (note: inconsistent with previous passwords)
                    database="photo_editor_db"  # Connect to this database
                )
                print("Created and connected to database successfully")  # Print success message
            else:  # If there's another error
                print(f"Database connection error: {err}")  # Print error message
                sys.exit(1)  # Exit the program with error code 1
    
    def create_tables(self):  # Method to create database tables
        cursor = self.connection.cursor()  # Create a cursor to execute SQL commands
        cursor.execute("""  # Execute SQL command to create table if it doesn't exist
            CREATE TABLE IF NOT EXISTS images (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                image_data LONGBLOB NOT NULL,
                image_type VARCHAR(10) NOT NULL
            )
        """)
        self.connection.commit()  # Commit the changes to the database
        cursor.close()  # Close the cursor
    
    def save_image(self, name, image_data, image_type):  # Method to save image to database
        cursor = self.connection.cursor()  # Create a cursor to execute SQL commands
        query = "INSERT INTO images (name, image_data, image_type) VALUES (%s, %s, %s)"  # SQL query to insert data
        cursor.execute(query, (name, image_data, image_type))  # Execute query with parameters
        self.connection.commit()  # Commit the changes to the database
        image_id = cursor.lastrowid  # Get the ID of the inserted row
        cursor.close()  # Close the cursor
        return image_id  # Return the image ID
    
    def update_image(self, image_id, image_data):  # Method to update image in database
        cursor = self.connection.cursor()  # Create a cursor to execute SQL commands
        query = "UPDATE images SET image_data = %s WHERE id = %s"  # SQL query to update data
        cursor.execute(query, (image_data, image_id))  # Execute query with parameters
        self.connection.commit()  # Commit the changes to the database
        cursor.close()  # Close the cursor
    
    def get_all_images(self):  # Method to retrieve all images from database
        cursor = self.connection.cursor()  # Create a cursor to execute SQL commands
        query = "SELECT id, name, image_data, image_type FROM images"  # SQL query to get all images
        cursor.execute(query)  # Execute the query
        images = cursor.fetchall()  # Fetch all results
        cursor.close()  # Close the cursor
        return images  # Return the images
    
    def get_image_by_id(self, image_id):  # Method to retrieve a specific image by ID
        cursor = self.connection.cursor()  # Create a cursor to execute SQL commands
        query = "SELECT id, name, image_data, image_type FROM images WHERE id = %s"  # SQL query to get image by ID
        cursor.execute(query, (image_id,))  # Execute query with parameter
        image = cursor.fetchone()  # Fetch one result
        cursor.close()  # Close the cursor
        return image  # Return the image
    
    def delete_image(self, image_id):  # Method to delete an image from database
        cursor = self.connection.cursor()  # Create a cursor to execute SQL commands
        query = "DELETE FROM images WHERE id = %s"  # SQL query to delete image
        cursor.execute(query, (image_id,))  # Execute query with parameter
        self.connection.commit()  # Commit the changes to the database
        cursor.close()  # Close the cursor
    
    def close(self):  # Method to close database connection
        if self.connection:  # If connection exists
            self.connection.close()  # Close the connection

            
class MainWindow(QMainWindow):  # Define the main application window class
    def __init__(self):  # Constructor method
        super().__init__()  # Call parent class constructor
        self.db_handler = DatabaseHandler()  # Create database handler instance
        self.init_ui()  # Initialize the user interface
        
    def init_ui(self):  # Method to set up the user interface
        self.setWindowTitle("Photo Editor App")  # Set window title
        self.setGeometry(100, 100, 800, 600)  # Set window size and position
        
        # Create central widget
        central_widget = QWidget()  # Create widget to serve as central widget
        self.setCentralWidget(central_widget)  # Set it as the central widget
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)  # Create vertical box layout for central widget
        
        # Create buttons
        self.upload_btn = QPushButton("Upload Image to Database")  # Create upload button
        self.select_btn = QPushButton("Select from Database")  # Create select button
        
        self.select_btn.setStyleSheet("background-color: green; color: white;")  # Set select button to green with white text

        # Set button size
        self.upload_btn.setMinimumSize(300, 80)  # Set minimum size for upload button
        self.select_btn.setMinimumSize(300, 80)  # Set minimum size for select button
        
        # Add buttons to layout with some spacing
        button_layout = QVBoxLayout()  # Create vertical layout for buttons
        button_layout.addStretch()  # Add stretch space before buttons
        button_layout.addWidget(self.upload_btn, alignment=Qt.AlignCenter)  # Add upload button centered
        button_layout.addSpacing(20)  # Add 20 pixels of vertical space
        button_layout.addWidget(self.select_btn, alignment=Qt.AlignCenter)  # Add select button centered
        button_layout.addStretch()  # Add stretch space after buttons
        
        main_layout.addLayout(button_layout)  # Add button layout to main layout
        
        # Connect signals
        self.upload_btn.clicked.connect(self.upload_image)  # Connect upload button to upload_image method
        self.select_btn.clicked.connect(self.view_database)  # Connect select button to view_database method
    
    def upload_image(self):  # Method to handle image upload
        file_dialog = QFileDialog()  # Create file dialog
        file_path, _ = file_dialog.getOpenFileName(  # Show open file dialog
            self, "Select Image", "", "Image Files (*.jpg *.jpeg *.png)"  # Set title and file filters
        )
        
        if file_path:  # If a file was selected
            # Get file details
            file_info = QFileInfo(file_path)  # Create file info object
            filename = file_info.fileName()  # Get filename
            file_extension = file_info.suffix().lower()  # Get file extension in lowercase
            
            if file_extension not in ['jpg', 'jpeg', 'png']:  # Check if file extension is allowed
                QMessageBox.warning(self, "Invalid File", "Only JPG and PNG files are allowed.")  # Show warning message
                return  # Exit method
                
            # Read image data
            with open(file_path, 'rb') as file:  # Open file in binary read mode
                image_data = file.read()  # Read file data
            
            # Save to database
            self.db_handler.save_image(filename, image_data, file_extension)  # Save image to database
            QMessageBox.information(self, "Success", "Image uploaded successfully!")  # Show success message
    
    def view_database(self):  # Method to view database images
        self.database_view = DatabaseView(self.db_handler)  # Create database view instance
        self.database_view.show()  # Show database view
        self.hide()  # Hide main window

class DatabaseView(QMainWindow):  # Define database view window class
    def __init__(self, db_handler):  # Constructor method
        super().__init__()  # Call parent class constructor
        self.db_handler = db_handler  # Store database handler
        self.init_ui()  # Initialize the user interface
        self.load_images()  # Load images from database
        
    def init_ui(self):  # Method to set up the user interface
        self.setWindowTitle("Database Images")  # Set window title
        self.setGeometry(100, 100, 900, 700)  # Set window size and position
        
        # Create central widget
        central_widget = QWidget()  # Create widget to serve as central widget
        self.setCentralWidget(central_widget)  # Set it as the central widget
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)  # Create vertical box layout for central widget
        
        # Top buttons
        top_layout = QHBoxLayout()  # Create horizontal layout for top buttons
        self.back_btn = QPushButton("Back to Main")  # Create back button
        self.refresh_btn = QPushButton("Refresh")  # Create refresh button
        self.upload_btn = QPushButton("Upload New Image")  # Create upload button
        
        top_layout.addWidget(self.back_btn)  # Add back button to top layout
        top_layout.addWidget(self.refresh_btn)  # Add refresh button to top layout
        top_layout.addWidget(self.upload_btn)  # Add upload button to top layout
        
        main_layout.addLayout(top_layout)  # Add top layout to main layout
        
        # Scroll area for images
        self.scroll_area = QScrollArea()  # Create scroll area for images
        self.scroll_area.setWidgetResizable(True)  # Make scroll area resizable
        
        self.scroll_content = QWidget()  # Create widget for scroll content
        self.scroll_layout = QVBoxLayout(self.scroll_content)  # Create vertical layout for scroll content
        
        self.scroll_area.setWidget(self.scroll_content)  # Set scroll content widget
        main_layout.addWidget(self.scroll_area)  # Add scroll area to main layout
        
        # Connect signals
        self.back_btn.clicked.connect(self.go_back)  # Connect back button to go_back method
        self.refresh_btn.clicked.connect(self.load_images)  # Connect refresh button to load_images method
        self.upload_btn.clicked.connect(self.upload_image)  # Connect upload button to upload_image method
    
    def go_back(self):  # Method to go back to main window
        # Show main window and close this one
        self.parent_window = [x for x in QApplication.topLevelWidgets() if isinstance(x, MainWindow)][0]  # Find main window
        self.parent_window.show()  # Show main window
        self.close()  # Close database view
    
    def upload_image(self):  # Method to handle image upload
        file_dialog = QFileDialog()  # Create file dialog
        file_path, _ = file_dialog.getOpenFileName(  # Show open file dialog
            self, "Select Image", "", "Image Files (*.jpg *.jpeg *.png)"  # Set title and file filters
        )
        
        if file_path:  # If a file was selected
            file_info = QFileInfo(file_path)  # Create file info object
            filename = file_info.fileName()  # Get filename
            file_extension = file_info.suffix().lower()  # Get file extension in lowercase
            
            if file_extension not in ['jpg', 'jpeg', 'png']:  # Check if file extension is allowed
                QMessageBox.warning(self, "Invalid File", "Only JPG and PNG files are allowed.")  # Show warning message
                return  # Exit method
                
            # Read image data
            with open(file_path, 'rb') as file:  # Open file in binary read mode
                image_data = file.read()  # Read file data
            
            # Save to database
            self.db_handler.save_image(filename, image_data, file_extension)  # Save image to database
            QMessageBox.information(self, "Success", "Image uploaded successfully!")  # Show success message
            self.load_images()  # Reload images
            
    def load_images(self):  # Method to load images from database
        # Clear existing images
        while self.scroll_layout.count():  # While there are items in the layout
            child = self.scroll_layout.takeAt(0)  # Take the first item
            if child.widget():  # If the item is a widget
                child.widget().deleteLater()  # Schedule it for deletion
        
        # Get all images from database
        images = self.db_handler.get_all_images()  # Get all images from database
        
        if not images:  # If no images were found
            no_images_label = QLabel("No images found in database")  # Create label
            no_images_label.setAlignment(Qt.AlignCenter)  # Center align the label
            self.scroll_layout.addWidget(no_images_label)  # Add label to layout
            return  # Exit method
            
        # Add each image to the layout
        for image_id, name, image_data, image_type in images:  # Loop through each image
            image_frame = QFrame()  # Create frame for image
            image_frame.setFrameShape(QFrame.Box)  # Set frame shape to box
            image_frame.setLineWidth(1)  # Set frame line width
            
            frame_layout = QHBoxLayout(image_frame)  # Create horizontal layout for frame
            
            # Image thumbnail
            image = QImage.fromData(image_data)  # Create QImage from image data
            pixmap = QPixmap.fromImage(image)  # Create QPixmap from QImage
            pixmap = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Scale pixmap
            
            image_label = QLabel()  # Create label for image
            image_label.setPixmap(pixmap)  # Set pixmap on label
            image_label.setFixedSize(200, 150)  # Set fixed size for label
            image_label.setAlignment(Qt.AlignCenter)  # Center align the image
            
            # Image details
            details_layout = QVBoxLayout()  # Create vertical layout for details
            id_label = QLabel(f"ID: {image_id}")  # Create label for ID
            name_label = QLabel(f"Name: {name}")  # Create label for name
            type_label = QLabel(f"Type: {image_type}")  # Create label for type
            
            details_layout.addWidget(id_label)  # Add ID label to details layout
            details_layout.addWidget(name_label)  # Add name label to details layout
            details_layout.addWidget(type_label)  # Add type label to details layout
            details_layout.addStretch()  # Add stretch space after labels
            
            # Buttons
            buttons_layout = QVBoxLayout()  # Create vertical layout for buttons
            view_btn = QPushButton("Read")  # Create view button
            update_btn = QPushButton("Update")  # Create update button
            
            delete_btn = QPushButton("Delete")  # Create delete button
            delete_btn = QPushButton("Delete")  # Create delete button again (redundant)
            delete_btn.setStyleSheet("background-color: red; color: white;")  # Set delete button to red with white text

            select_btn = QPushButton("Select")  # Create select button
            
            buttons_layout.addWidget(view_btn)  # Add view button to buttons layout
            buttons_layout.addWidget(update_btn)  # Add update button to buttons layout
            buttons_layout.addWidget(delete_btn)  # Add delete button to buttons layout
            buttons_layout.addWidget(select_btn)  # Add select button to buttons layout
            buttons_layout.addStretch()  # Add stretch space after buttons
            
            # Connect button signals
            view_btn.clicked.connect(lambda checked, img_id=image_id: self.view_image(img_id))  # Connect view button
            update_btn.clicked.connect(lambda checked, img_id=image_id: self.update_image(img_id))  # Connect update button
            delete_btn.clicked.connect(lambda checked, img_id=image_id: self.delete_image(img_id))  # Connect delete button
            select_btn.clicked.connect(lambda checked, img_id=image_id: self.edit_image(img_id))  # Connect select button
            
            # Add to frame layout
            frame_layout.addWidget(image_label)  # Add image label to frame layout
            frame_layout.addLayout(details_layout)  # Add details layout to frame layout
            frame_layout.addStretch()  # Add stretch space
            frame_layout.addLayout(buttons_layout)  # Add buttons layout to frame layout
            
            # Add frame to scroll layout
            self.scroll_layout.addWidget(image_frame)  # Add image frame to scroll layout
    
    def view_image(self, image_id):  # Method to view an image
        image = self.db_handler.get_image_by_id(image_id)  # Get image by ID
        if image:  # If image was found
            _, name, image_data, image_type = image  # Unpack image data
            
            # Create a new window to display the image
            view_dialog = QDialog(self)  # Create dialog
            view_dialog.setWindowTitle(f"View Image: {name}")  # Set dialog title
            view_dialog.setGeometry(200, 200, 800, 600)  # Set dialog size and position
            
            layout = QVBoxLayout(view_dialog)  # Create vertical layout for dialog
            
            # Display image
            qimg = QImage.fromData(image_data)  # Create QImage from image data
            pixmap = QPixmap.fromImage(qimg)  # Create QPixmap from QImage
            
            image_label = QLabel()  # Create label for image
            image_label.setPixmap(pixmap.scaled(  # Set scaled pixmap on label
                700, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation  # Scale parameters
            ))
            image_label.setAlignment(Qt.AlignCenter)  # Center align the image
            
            layout.addWidget(image_label)  # Add image label to layout
            
            # Close button
            close_btn = QPushButton("Close")  # Create close button
            close_btn.clicked.connect(view_dialog.close)  # Connect close button to close dialog
            layout.addWidget(close_btn, alignment=Qt.AlignCenter)  # Add close button to layout, centered
            
            view_dialog.exec_()  # Show dialog as modal
    
    def update_image(self, image_id):  # Method to update an image
        file_dialog = QFileDialog()  # Create file dialog
        file_path, _ = file_dialog.getOpenFileName(  # Show open file dialog
            self, "Select New Image", "", "Image Files (*.jpg *.jpeg *.png)"  # Set title and file filters
        )
        
        if file_path:  # If a file was selected
            file_info = QFileInfo(file_path)  # Create file info object
            file_extension = file_info.suffix().lower()  # Get file extension in lowercase
            
            if file_extension not in ['jpg', 'jpeg', 'png']:  # Check if file extension is allowed
                QMessageBox.warning(self, "Invalid File", "Only JPG and PNG files are allowed.")  # Show warning message
                return  # Exit method
                
            # Read image data
            with open(file_path, 'rb') as file:  # Open file in binary read mode
                image_data = file.read()  # Read file data
            
            # Update in database
            self.db_handler.update_image(image_id, image_data)  # Update image in database
            QMessageBox.information(self, "Success", "Image updated successfully!")  # Show success message
            self.load_images()  # Reload images
    
    def delete_image(self, image_id):  # Method to delete an image
        confirm = QMessageBox.question(  # Show confirmation dialog
            self, "Confirm Delete",  # Set dialog title
            "Are you sure you want to delete this image?",  # Set dialog message
            QMessageBox.Yes | QMessageBox.No  # Set dialog buttons
        )
        
        if confirm == QMessageBox.Yes:  # If user confirmed deletion
            self.db_handler.delete_image(image_id)  # Delete image from database
            QMessageBox.information(self, "Success", "Image deleted successfully!")  # Show success message
            self.load_images()  # Reload images
    
    def edit_image(self, image_id):  # Method to edit an image
        image = self.db_handler.get_image_by_id(image_id)  # Get image by ID
        if image:  # If image was found
            self.editor = ImageEditor(self.db_handler, image)  # Create image editor instance
            self.editor.show()  # Show editor
            self.hide()  # Hide database view

class ImageEditor(QMainWindow):  # Define image editor window class
    def __init__(self, db_handler, image_data):  # Constructor method
        super().__init__()  # Call parent class constructor
        self.db_handler = db_handler  # Store database handler
        self.image_id, self.image_name, self.original_image_data, self.image_type = image_data  # Unpack image data
        
        # Convert image data to PIL Image
        self.original_pil_image = Image.open(io.BytesIO(self.original_image_data))  # Open image with PIL
        self.current_pil_image = self.original_pil_image.copy()  # Create a copy to work with
        
        self.init_ui()  # Initialize the user interface
        self.update_preview()  # Update the image preview
        
    def init_ui(self):  # Method to set up the user interface
        self.setWindowTitle(f"Editing: {self.image_name}")  # Set window title
        self.setGeometry(100, 100, 1000, 700)  # Set window size and position
        
        # Create central widget
        central_widget = QWidget()  # Create widget to serve as central widget
        self.setCentralWidget(central_widget)  # Set it as the central widget
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)  # Create horizontal box layout for central widget
        
        # Left side - Image preview
        self.preview_frame = QFrame()  # Create frame for image preview
        self.preview_frame.setFrameShape(QFrame.Box)  # Set frame shape to box
        self.preview_frame.setLineWidth(1)  # Set frame line width
        self.preview_frame.setMinimumWidth(600)  # Set minimum width for preview frame
        
        preview_layout = QVBoxLayout(self.preview_frame)  # Create vertical layout for preview frame
        
        self.image_label = QLabel()  # Create label for image
        self.image_label.setAlignment(Qt.AlignCenter)  # Center align the image
        preview_layout.addWidget(self.image_label)  # Add image label to preview layout
        
        # Right side - Editing options
        options_widget = QWidget()  # Create widget for editing options
        options_layout = QVBoxLayout(options_widget)  # Create vertical layout for options widget
        
        # Rotate & Flip
        rotate_flip_group = QGroupBox("Rotate & Flip")  # Create group box for rotate and flip options
        rotate_flip_layout = QHBoxLayout(rotate_flip_group)  # Create horizontal layout for group box
        
        self.rotate_left_btn = QPushButton("Rotate Left")  # Create rotate left button
        self.rotate_right_btn = QPushButton("Rotate Right")  # Create rotate right button
        self.flip_h_btn = QPushButton("Flip Horizontal")  # Create flip horizontal button
        self.flip_v_btn = QPushButton("Flip Vertical")  # Create flip vertical button
        
        rotate_flip_layout.addWidget(self.rotate_left_btn)  # Add rotate left button to layout
        rotate_flip_layout.addWidget(self.rotate_right_btn)  # Add rotate right button to layout
        rotate_flip_layout.addWidget(self.flip_h_btn)  # Add flip horizontal button to layout
        rotate_flip_layout.addWidget(self.flip_v_btn)  # Add flip vertical button to layout
        
        options_layout.addWidget(rotate_flip_group)  # Add rotate & flip group to options layout
        
        # Adjust Brightness & Contrast
        adjust_group = QGroupBox("Adjust Brightness & Contrast")  # Create group box for adjustment options
        adjust_layout = QVBoxLayout(adjust_group)  # Create vertical layout for group box
        
        self.brightness_btn = QPushButton("Increase Brightness")  # Create increase brightness button
        self.darkness_btn = QPushButton("Decrease Brightness")  # Create decrease brightness button
        self.contrast_inc_btn = QPushButton("Increase Contrast")  # Create increase contrast button
        self.contrast_dec_btn = QPushButton("Decrease Contrast")  # Create decrease contrast button
        
        adjust_layout.addWidget(self.brightness_btn)  # Add brightness button to layout
        adjust_layout.addWidget(self.darkness_btn)  # Add darkness button to layout
        adjust_layout.addWidget(self.contrast_inc_btn)  # Add contrast increase button to layout
        adjust_layout.addWidget(self.contrast_dec_btn)  # Add contrast decrease button to layout
        
        options_layout.addWidget(adjust_group)  # Add adjust group to options layout
        
        # Grayscale
        grayscale_group = QGroupBox("Convert to Grayscale")  # Create group box for grayscale option
        grayscale_layout = QHBoxLayout(grayscale_group)  # Create horizontal layout for group box
        
        self.grayscale_btn = QPushButton("Convert to Grayscale")  # Create grayscale button
        
        grayscale_layout.addWidget(self.grayscale_btn)  # Add grayscale button to layout
        
        options_layout.addWidget(grayscale_group)  # Add grayscale group to options layout
        
        # Apply Filters
        filters_group = QGroupBox("Apply Filters")  # Create group box for filter options
        filters_layout = QHBoxLayout(filters_group)  # Create horizontal layout for group box
        
        self.sepia_btn = QPushButton("Sepia")  # Create sepia filter button
        self.blur_btn = QPushButton("Blur")  # Create blur filter button
        self.sharpen_btn = QPushButton("Sharpen")  # Create sharpen filter button
        
        filters_layout.addWidget(self.sepia_btn)  # Add sepia button to layout
        filters_layout.addWidget(self.blur_btn)  # Add blur button to layout
        filters_layout.addWidget(self.sharpen_btn)  # Add sharpen button to layout
        
        options_layout.addWidget(filters_group)  # Add filters group to options layout
        
        # Save and Cancel buttons
        buttons_layout = QHBoxLayout()  # Create horizontal layout for buttons
        
        self.save_btn = QPushButton("Save to Database")  # Create save button
        self.cancel_btn = QPushButton("Cancel")  # Create cancel button
        self.reset_btn = QPushButton("Reset Changes")  # Create reset button
        
        buttons_layout.addWidget(self.save_btn)  # Add save button to layout
        buttons_layout.addWidget(self.reset_btn)  # Add reset button to layout
        buttons_layout.addWidget(self.cancel_btn)  # Add cancel button to layout
        
        options_layout.addLayout(buttons_layout)  # Add buttons layout to options layout
        options_layout.addStretch()  # Add stretch space at the end
        
        # Add to main layout
        main_layout.addWidget(self.preview_frame)  # Add preview frame to main layout
        main_layout.addWidget(options_widget)  # Add options widget to main layout
        
        # Connect signals
        self.rotate_left_btn.clicked.connect(lambda: self.rotate_image(-90))  # Connect rotate left button
        self.rotate_right_btn.clicked.connect(lambda: self.rotate_image(90))  # Connect rotate right button
        self.flip_h_btn.clicked.connect(lambda: self.flip_image("horizontal"))  # Connect flip horizontal button
        self.flip_v_btn.clicked.connect(lambda: self.flip_image("vertical"))  # Connect flip vertical button
        
        self.brightness_btn.clicked.connect(lambda: self.adjust_brightness(1.2))  # Connect brightness increase button
        self.darkness_btn.clicked.connect(lambda: self.adjust_brightness(0.8))  # Connect brightness decrease button
        self.contrast_inc_btn.clicked.connect(lambda: self.adjust_contrast(1.2))  # Connect contrast increase button
        self.contrast_dec_btn.clicked.connect(lambda: self.adjust_contrast(0.8))  # Connect contrast decrease button
        
        self.grayscale_btn.clicked.connect(self.convert_to_grayscale)  # Connect grayscale button
        
        self.sepia_btn.clicked.connect(lambda: self.apply_filter("sepia"))  # Connect sepia button
        self.blur_btn.clicked.connect(lambda: self.apply_filter("blur