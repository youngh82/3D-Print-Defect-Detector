# config.py
import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

# python-dotenv 로드 및 예외 처리
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    def load_dotenv():
        logging.warning("python-dotenv is not installed. Environment variables may not be loaded properly.")
        return None

@dataclass
class MonitoringConfig:
    """모니터링 관련 설정"""
    frame_skip: int = 2
    processing_threshold: float = 0.5
    processing_interval: float = 1.0  # 프레임 처리 간격(초)
    
    # 크롭 설정
    initial_width_ratio: float = 0.35
    fixed_top_ratio: float = 0.2
    initial_bottom_ratio: float = 0.3
    max_width_ratio: float = 0.7
    max_bottom_ratio: float = 0.6
    width_growth_per_minute: float = 0.05
    bottom_growth_per_minute: float = 0.05

    def validate(self) -> bool:
        """설정값 유효성 검사"""
        try:
            assert 0 < self.frame_skip < 10, "frame_skip must be between 1 and 10"
            assert 0 < self.processing_threshold < 1, "processing_threshold must be between 0 and 1"
            assert 0 < self.processing_interval < 10, "processing_interval must be between 0 and 10"
            assert 0 < self.initial_width_ratio < 1, "initial_width_ratio must be between 0 and 1"
            assert 0 < self.fixed_top_ratio < 1, "fixed_top_ratio must be between 0 and 1"
            assert 0 < self.initial_bottom_ratio < 1, "initial_bottom_ratio must be between 0 and 1"
            assert 0 < self.max_width_ratio <= 1, "max_width_ratio must be between 0 and 1"
            assert 0 < self.max_bottom_ratio <= 1, "max_bottom_ratio must be between 0 and 1"
            return True
        except AssertionError as e:
            logging.error(f"MonitoringConfig validation failed: {str(e)}")
            return False

@dataclass
class DetectionConfig:
    """결함 감지 관련 설정"""
    detection_threshold: float = 0.7
    defects_dir: str = "defects"
    save_detected_images: bool = True
    api_base_url: str = "https://eastus.api.cognitive.microsoft.com/customvision/v3.0/Prediction"

    @property
    def prediction_key(self) -> str:
        """Azure Custom Vision API 키"""
        key = os.getenv('CUSTOM_VISION_KEY')
        if not key:
            logging.warning("CUSTOM_VISION_KEY is not set in environment variables")
        return key or ''

    @property
    def project_id(self) -> str:
        """Azure Custom Vision 프로젝트 ID"""
        id = os.getenv('CUSTOM_VISION_PROJECT_ID')
        if not id:
            logging.warning("CUSTOM_VISION_PROJECT_ID is not set in environment variables")
        return id or ''

    @property
    def iteration_name(self) -> str:
        """Azure Custom Vision 반복 이름"""
        name = os.getenv('CUSTOM_VISION_ITERATION_NAME')
        if not name:
            logging.warning("CUSTOM_VISION_ITERATION_NAME is not set in environment variables")
        return name or ''

    def validate(self) -> bool:
        """설정값 유효성 검사"""
        try:
            assert 0 < self.detection_threshold <= 1, "detection_threshold must be between 0 and 1"
            assert os.path.exists(self.defects_dir) or os.makedirs(self.defects_dir), "Failed to create defects directory"
            assert self.prediction_key, "CUSTOM_VISION_KEY is not set"
            assert self.project_id, "CUSTOM_VISION_PROJECT_ID is not set"
            assert self.iteration_name, "CUSTOM_VISION_ITERATION_NAME is not set"
            return True
        except AssertionError as e:
            logging.error(f"DetectionConfig validation failed: {str(e)}")
            return False

@dataclass
class NetworkConfig:
    """네트워크 관련 설정"""
    request_timeout: int = 5
    max_retries: int = 3
    retry_delay: int = 1
    default_headers: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """기본값 초기화"""
        if self.default_headers is None:
            self.default_headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'image/jpeg, image/png, */*'
            }

    def validate(self) -> bool:
        """설정값 유효성 검사"""
        try:
            assert 0 < self.request_timeout <= 30, "request_timeout must be between 1 and 30"
            assert 0 < self.max_retries <= 5, "max_retries must be between 1 and 5"
            assert 0 < self.retry_delay <= 5, "retry_delay must be between 1 and 5"
            assert isinstance(self.default_headers, dict), "default_headers must be a dictionary"
            return True
        except AssertionError as e:
            logging.error(f"NetworkConfig validation failed: {str(e)}")
            return False

@dataclass
class LoggingConfig:
    """로깅 관련 설정"""
    log_level: str = "INFO"
    log_format: str = "[%(asctime)s] [%(levelname)s] %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S"
    log_file: str = "print_monitor.log"
    max_log_size: int = 1024 * 1024  # 1MB
    backup_count: int = 5

    def validate(self) -> bool:
        """설정값 유효성 검사"""
        try:
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            assert self.log_level in valid_levels, f"log_level must be one of {valid_levels}"
            assert self.max_log_size > 0, "max_log_size must be positive"
            assert self.backup_count >= 0, "backup_count must be non-negative"
            return True
        except AssertionError as e:
            logging.error(f"LoggingConfig validation failed: {str(e)}")
            return False

class ConfigManager:
    """설정 관리자"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """설정 초기화"""
        self.config_file = 'config.json'
        self.last_load_time = None
        
        # 기본 설정 초기화
        self.monitoring = MonitoringConfig()
        self.detection = DetectionConfig()
        self.network = NetworkConfig()
        self.logging = LoggingConfig()
        
        # 설정 파일 로드
        self._load_config()
        
        # 로깅 설정
        self._setup_logging()
        
        # 필수 디렉토리 생성
        self._create_directories()

    def _create_directories(self):
        """필요한 디렉토리 생성"""
        try:
            os.makedirs(self.detection.defects_dir, exist_ok=True)
            os.makedirs("logs", exist_ok=True)
            logging.info("Required directories created successfully")
        except Exception as e:
            logging.error(f"Failed to create directories: {str(e)}")
            raise
    
    def _setup_logging(self):
        """로깅 설정"""
        try:
            log_file = Path("logs") / self.logging.log_file
            
            # 로깅 핸들러 설정
            handlers = [
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
            
            # 로깅 포맷 설정
            logging.basicConfig(
                level=getattr(logging, self.logging.log_level),
                format=self.logging.log_format,
                datefmt=self.logging.log_date_format,
                handlers=handlers
            )
            
            logging.info("Logging setup completed successfully")
        except Exception as e:
            print(f"Failed to setup logging: {str(e)}")
            raise
    
    def _load_config(self):
        """설정 파일 로드"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 각 섹션별 설정 업데이트
                if 'monitoring' in config_data:
                    self.monitoring = MonitoringConfig(**config_data['monitoring'])
                if 'detection' in config_data:
                    detection_config = config_data['detection']
                    if not self.detection.prediction_key:
                        detection_config['prediction_key'] = os.getenv('CUSTOM_VISION_KEY', '')
                    if not self.detection.project_id:
                        detection_config['project_id'] = os.getenv('CUSTOM_VISION_PROJECT_ID', '')
                    if not self.detection.iteration_name:
                        detection_config['iteration_name'] = os.getenv('CUSTOM_VISION_ITERATION_NAME', '')
                    self.detection = DetectionConfig(**detection_config)
                if 'network' in config_data:
                    self.network = NetworkConfig(**config_data['network'])
                if 'logging' in config_data:
                    self.logging = LoggingConfig(**config_data['logging'])
                
                self.last_load_time = datetime.now()
                logging.info("Configuration loaded successfully")
                
            except Exception as e:
                logging.error(f"Failed to load configuration: {str(e)}")
                # 기본값 유지
    
    def validate_all(self) -> bool:
        """모든 설정의 유효성 검사"""
        validations = [
            self.monitoring.validate(),
            self.detection.validate(),
            self.network.validate(),
            self.logging.validate()
        ]
        return all(validations)

    def save_config(self):
        """현재 설정을 파일로 저장"""
        try:
            config_data = {
                'monitoring': asdict(self.monitoring),
                'detection': {
                    k: v for k, v in asdict(self.detection).items()
                    if k not in ['prediction_key', 'project_id', 'iteration_name']
                },
                'network': asdict(self.network),
                'logging': asdict(self.logging)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            logging.info("Configuration saved successfully")
            
        except Exception as e:
            logging.error(f"Failed to save configuration: {str(e)}")
            raise

    def get_all_config(self) -> Dict[str, Any]:
        """모든 설정값 반환"""
        return {
            'monitoring': asdict(self.monitoring),
            'detection': {
                k: v for k, v in asdict(self.detection).items()
                if k not in ['prediction_key', 'project_id', 'iteration_name']
            },
            'network': asdict(self.network),
            'logging': asdict(self.logging)
        }

    def reload_config(self):
        """설정 재로드"""
        try:
            self._load_config()
            self._setup_logging()
            if not self.validate_all():
                raise ValueError("Configuration validation failed after reload")
            logging.info("Configuration reloaded successfully")
        except Exception as e:
            logging.error(f"Failed to reload configuration: {str(e)}")
            raise

    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance