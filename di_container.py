# di_container.py
from typing import Optional
from dataclasses import dataclass
import logging
from config import ConfigManager

# 필요한 클래스들 import
from print_monitor_ui import PrintMonitorUI
from print_monitor_control import PrintMonitorControl
from print_monitor_detection import PrintMonitorDetection
from print_monitor_monitoring import PrintMonitorMonitoring

@dataclass
class Container:
    """의존성 컨테이너"""
    config_manager: Optional[ConfigManager] = None
    ui: Optional[PrintMonitorUI] = None
    printer_control: Optional[PrintMonitorControl] = None
    defect_detection: Optional[PrintMonitorDetection] = None
    monitoring: Optional[PrintMonitorMonitoring] = None

class DIContainer:
    """의존성 주입 관리자"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """컨테이너 초기화"""
        self.container = Container()
        self.container.config_manager = ConfigManager.get_instance()
        self._setup_logging()
    
    def _setup_logging(self):
        """로깅 설정"""
        self.logger = logging.getLogger(__name__)
    
    def initialize_components(self):
        """컴포넌트 초기화 및 의존성 주입"""
        try:
            self._create_ui()
            self._create_printer_control()
            self._create_defect_detection()
            self._create_monitoring()
            self._validate_components()
            
            self.logger.info("모든 컴포넌트가 성공적으로 초기화되었습니다.")
        except Exception as e:
            self.logger.error(f"컴포넌트 초기화 중 오류 발생: {str(e)}")
            raise

    def _create_ui(self):
        """UI 컴포넌트 생성"""
        try:
            self.container.ui = PrintMonitorUI()
            self.logger.debug("UI 컴포넌트가 생성되었습니다.")
        except Exception as e:
            self.logger.error(f"UI 생성 중 오류 발생: {str(e)}")
            raise

    def _create_printer_control(self):
        """프린터 제어 컴포넌트 생성"""
        try:
            if not self.container.ui:
                raise RuntimeError("UI 컴포넌트가 필요합니다.")
            
            self.container.printer_control = PrintMonitorControl(
                ui=self.container.ui,
                network_config=self.container.config_manager.network
            )
            self.logger.debug("프린터 제어 컴포넌트가 생성되었습니다.")
        except Exception as e:
            self.logger.error(f"프린터 제어 컴포넌트 생성 중 오류 발생: {str(e)}")
            raise

    def _create_defect_detection(self):
        """결함 감지 컴포넌트 생성"""
        try:
            if not all([self.container.ui, self.container.printer_control]):
                raise RuntimeError("UI와 프린터 제어 컴포넌트가 필요합니다.")
            
            self.container.defect_detection = PrintMonitorDetection(
                ui=self.container.ui,
                printer_control=self.container.printer_control,
                detection_config=self.container.config_manager.detection
            )
            self.logger.debug("결함 감지 컴포넌트가 생성되었습니다.")
        except Exception as e:
            self.logger.error(f"결함 감지 컴포넌트 생성 중 오류 발생: {str(e)}")
            raise

    def _create_monitoring(self):
        """모니터링 컴포넌트 생성"""
        try:
            if not all([self.container.ui, self.container.defect_detection]):
                raise RuntimeError("UI와 결함 감지 컴포넌트가 필요합니다.")
            
            self.container.monitoring = PrintMonitorMonitoring(
                ui=self.container.ui,
                defect_detection=self.container.defect_detection,
                monitoring_config=self.container.config_manager.monitoring
            )
            self.logger.debug("모니터링 컴포넌트가 생성되었습니다.")
        except Exception as e:
            self.logger.error(f"모니터링 컴포넌트 생성 중 오류 발생: {str(e)}")
            raise

    def _validate_components(self):
        """모든 컴포넌트의 유효성 검사"""
        required_components = [
            ('ui', PrintMonitorUI),
            ('printer_control', PrintMonitorControl),
            ('defect_detection', PrintMonitorDetection),
            ('monitoring', PrintMonitorMonitoring)
        ]
        
        for component_name, component_type in required_components:
            component = getattr(self.container, component_name)
            if not component:
                raise RuntimeError(f"{component_name} 컴포넌트가 초기화되지 않았습니다.")
            if not isinstance(component, component_type):
                raise TypeError(f"{component_name} 컴포넌트의 타입이 올바르지 않습니다.")

    def reset_components(self):
        """컴포넌트 리셋"""
        try:
            # UI를 제외한 모든 컴포넌트 초기화
            self.container.printer_control = None
            self.container.defect_detection = None
            self.container.monitoring = None
            self.logger.info("컴포넌트가 리셋되었습니다.")
        except Exception as e:
            self.logger.error(f"컴포넌트 리셋 중 오류 발생: {str(e)}")

    @classmethod
    def get_instance(cls) -> Container:
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance.container

    def cleanup(self):
        """리소스 정리"""
        try:
            if self.container.monitoring:
                self.container.monitoring.stop_monitoring()
            self.reset_components()
            self.logger.info("모든 리소스가 정리되었습니다.")
        except Exception as e:
            self.logger.error(f"리소스 정리 중 오류 발생: {str(e)}")