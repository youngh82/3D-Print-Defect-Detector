# print_monitor_main.py
import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import logging

# python-dotenv가 설치되어 있지 않은 경우를 대비한 예외 처리
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        logging.warning("python-dotenv is not installed. Environment variables may not be loaded properly.")
        return None

from di_container import DIContainer
from config import ConfigManager

class PrintMonitor:
    def __init__(self):
        try:
            # 로깅 초기화
            self._setup_logging()
            self.logger = logging.getLogger(__name__)
            
            # 의존성 주입 컨테이너 초기화
            self.logger.info("의존성 주입 컨테이너 초기화 중...")
            self.di_container = DIContainer()  # DIContainer 인스턴스 생성
            self.container = self.di_container.get_instance()  # Container 참조 가져오기
            self.di_container.initialize_components()  # 컴포넌트 초기화
            
            # 컴포넌트 참조 가져오기
            self.ui = self.container.ui
            self.printer_control = self.container.printer_control
            self.defect_detection = self.container.defect_detection
            self.monitoring = self.container.monitoring
            
            # 이벤트 연결 설정
            self.setup_connections()
            
            # 초기 설정 및 체크
            self.initialize_system()
            
            self.logger.info("PrintMonitor 초기화가 완료되었습니다.")
            
        except Exception as e:
            logging.error(f"PrintMonitor 초기화 중 오류 발생: {str(e)}")
            raise

    def _setup_logging(self):
        """로깅 시스템 초기화"""
        config = ConfigManager.get_instance()
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / config.logging.log_file
        
        logging.basicConfig(
            level=getattr(logging, config.logging.log_level),
            format=config.logging.log_format,
            datefmt=config.logging.log_date_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def setup_connections(self):
        """이벤트 핸들러 연결"""
        try:
            self.logger.debug("이벤트 핸들러 연결 중...")
            
            # 모니터링 버튼 연결
            self.ui.monitoring_start_button.clicked.connect(
                self.monitoring.start_monitoring
            )
            self.ui.monitoring_stop_button.clicked.connect(
                self.monitoring.stop_monitoring
            )
            
            # 프린터 제어 버튼 연결
            self.ui.pause_button.clicked.connect(
                self.printer_control.pause_print
            )
            self.ui.resume_button.clicked.connect(
                self.printer_control.resume_print
            )
            
            # URL 적용 버튼 연결
            self.ui.webcam_apply_btn.clicked.connect(
                self.monitoring.apply_webcam_url
            )
            self.ui.moonraker_apply_btn.clicked.connect(
                self.printer_control.apply_moonraker_url
            )
            
            self.logger.debug("이벤트 핸들러 연결이 완료되었습니다.")
            
        except Exception as e:
            self.logger.error(f"이벤트 핸들러 연결 중 오류 발생: {str(e)}")
            raise

    def initialize_system(self):
        """시스템 초기화 및 설정"""
        try:
            self.logger.info("시스템 초기화 중...")
            
            # 작업 디렉토리 생성
            config = ConfigManager.get_instance()
            os.makedirs(config.detection.defects_dir, exist_ok=True)
            
            # 초기 프린터 상태 확인
            printer_status = self.printer_control.get_printer_status()
            self.printer_control.update_printer_status(printer_status)
            
            # 초기 로그 메시지
            self.ui.status_text.append("시스템이 초기화되었습니다.")
            self.logger.info("시스템 초기화가 완료되었습니다.")
            
        except Exception as e:
            self.logger.error(f"시스템 초기화 중 오류 발생: {str(e)}")
            self.ui.status_text.append(f"시스템 초기화 중 오류 발생: {str(e)}")
            raise

    def cleanup(self):
        """응용 프로그램 정리"""
        try:
            self.logger.info("응용 프로그램 종료 중...")
            
            # DI 컨테이너 정리
            di_container = DIContainer.get_instance()
            di_container.cleanup()
            
            # 설정 저장
            config = ConfigManager.get_instance()
            config.save_config()
            
            self.logger.info("응용 프로그램이 정상적으로 종료되었습니다.")
            
        except Exception as e:
            self.logger.error(f"응용 프로그램 종료 중 오류 발생: {str(e)}")

def setup_qt_application():
    """Qt 애플리케이션 설정"""
    # DPI 설정
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    return QApplication(sys.argv)

def main():
    try:
        # 환경 변수 로드
        load_dotenv()
        
        # Qt 애플리케이션 생성
        app = setup_qt_application()
        
        # 메인 애플리케이션 객체 생성
        print_monitor = PrintMonitor()
        
        # UI 표시
        print_monitor.ui.show()
        
        # 종료 시 정리 작업 설정
        app.aboutToQuit.connect(print_monitor.cleanup)
        
        # 이벤트 루프 시작
        sys.exit(app.exec_())
        
    except Exception as e:
        logging.error(f"애플리케이션 시작 중 오류 발생: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()