#!/usr/bin/env python3
import sys
import os

# printer_monitoring 디렉토리를 모듈 검색 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    """메인 애플리케이션 실행"""
    try:
        app = QApplication(sys.argv)

        main_window = MainWindow()
        main_window.show()

        sys.exit(app.exec_())

    except Exception as e:
        print(f"애플리케이션 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
