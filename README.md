# PhotoShop Project Setup Instructions

## Installation Instructions for Windows

### 1. Clone the Repository

Open Command Prompt and clone the repository:
```
git clone https://github.com/byramnarayan/photoShop.git
cd photoShop
```

### 2. Set Up the Virtual Environment

The repository already includes a `venv` folder with the virtual environment. You just need to activate it:

```
venv\Scripts\activate
```

You'll know it's activated when you see `(venv)` at the beginning of your command prompt line.

If for any reason you need to recreate the virtual environment:
```
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

With the virtual environment activated, install all the required packages:
```
pip install -r requirements.txt
```

This will install:
- mysql-connector-python 9.2.0
- pillow 11.1.0
- PyQt5 5.15.11
- PyQt5-Qt5 5.15.16
- PyQt5_sip 12.17.0

### 4. Running the Application

To run the demo version:
```
python demo3.py
```

## Troubleshooting

### PyQt5 Installation Issues on Windows

If you encounter issues with PyQt5:

1. Update pip:
   ```
   pip install --upgrade pip
   ```

2. Install the Visual C++ Redistributable for Visual Studio:
   - Download from [Microsoft's website](https://visualstudio.microsoft.com/downloads/)
   - This is required for many Python packages with C extensions on Windows

### MySQL Connection Issues

If you have trouble connecting to MySQL:
1. Ensure MySQL Server is installed and running on your Windows machine
2. Verify your database credentials in the application code
3. Check that the MySQL service is running in Windows Services
