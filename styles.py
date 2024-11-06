class Styles:
    @staticmethod
    def get_main_window_style():
        return """
            * {
                font-family: '맑은 고딕';
            }
            QMainWindow {
                background-color: #f5f6fa;
            }
            QGroupBox {
                background-color: white;
                border: none;
                border-radius: 10px;
                margin-top: 20px;
                padding: 15px;
                font-size: 13px;
            }
            QGroupBox::title {
                color: #2c3e50;
                font-size: 14px;
                font-weight: bold;
                padding: 0 15px;
                background-color: transparent;
                subcontrol-position: top left;
                subcontrol-origin: margin;
                left: 15px;
                top: 10px;
            }
            QLabel {
                color: #34495e;
                font-size: 13px;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #3498db;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #3498db;
                padding: 5px;
                font-size: 13px;
            }
            QPushButton {
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                min-width: 120px;
                min-height: 35px;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            QStatusBar {
                background-color: white;
                color: #2c3e50;
                border-top: 1px solid #e0e0e0;
                padding: 5px;
                font-size: 13px;
            }
        """

    @staticmethod
    def get_url_input_style():
        return """
            QLineEdit {
                background-color: #f8f9fa;
                border: 2px solid #e0e0e0;
                padding: 10px;
            }
        """

    @staticmethod
    def get_video_label_style():
        return """
            QLabel {
                background-color: #f8f9fa;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                min-height: 400px;
            }
        """

    @staticmethod
    def get_log_label_style():
        return """
            font-weight: bold; 
            color: #2c3e50;
            font-family: '맑은 고딕';
            font-size: 13px;
            margin-bottom: 5px;
        """

    @staticmethod
    def get_log_text_style():
        return """
            QTextEdit {
                background-color: #f8f9fa;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
                font-family: '맑은 고딕';
                font-size: 12px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 14px;
                margin: 15px 0 15px 0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                min-height: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 15px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
            QScrollBar::add-line:vertical {
                border: none;
                background: none;
                height: 15px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                width: 0;
                height: 0;
            }
            QScrollBar::sub-page:vertical, QScrollBar::add-page:vertical {
                background: none;
            }
        """

    @staticmethod
    def get_button_style(base_color):
        return f"""
            QPushButton {{
                background-color: {base_color};
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {ColorUtils.adjust_color(base_color, 1.1)};
            }}
            QPushButton:pressed {{
                background-color: {ColorUtils.adjust_color(base_color, 0.9)};
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}
        """

    @staticmethod
    def get_success_banner_style():
        return """
            QFrame {
                background-color: #2ecc71;
                border-radius: 6px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
        """

class ColorUtils:
    @staticmethod
    def adjust_color(color, factor):
        """색상 밝기 조정"""
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return f'#{r:02x}{g:02x}{b:02x}'

class Colors:
    PRIMARY = "#3498db"
    DANGER = "#e74c3c"
    WARNING = "#f1c40f"
    SUCCESS = "#2ecc71"
    GRAY = "#bdc3c7"
    TEXT = "#2c3e50"
    BORDER = "#e0e0e0"
    BACKGROUND = "#f5f6fa"