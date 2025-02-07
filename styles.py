STYLE_SHEET = """
QMainWindow {
    background-color: #f0f0f0;
}

QWidget {
    min-width: 10px;
    min-height: 10px;
}

QGroupBox {
    background-color: white;
    border: 1px solid #cccccc;
    border-radius: 5px;
    margin-top: 1em;
    padding-top: 10px;
    min-width: 200px;
    min-height: 50px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 5px;
    color: #333333;
}

QLineEdit {
    padding: 5px;
    border: 1px solid #cccccc;
    border-radius: 3px;
    background-color: white;
    min-height: 25px;
    min-width: 200px;
}

QLineEdit:focus {
    border: 1px solid #4a90e2;
}

QPushButton {
    background-color: #4a90e2;
    color: white;
    border: none;
    padding: 8px 15px;
    border-radius: 4px;
    min-width: 100px;
    min-height: 30px;
}

QPushButton:hover {
    background-color: #357abd;
}

QPushButton:pressed {
    background-color: #2a5885;
}

QPushButton:disabled {
    background-color: #cccccc;
}

QLabel {
    color: #333333;
}

QTextEdit {
    border: 1px solid #cccccc;
    border-radius: 3px;
    background-color: white;
    padding: 5px;
}

QLabel#videoLabel {
    background-color: #2c2c2c;
    border: 1px solid #cccccc;
    border-radius: 5px;
}
"""