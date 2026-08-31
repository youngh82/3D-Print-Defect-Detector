import json
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class MonitoringConfig:
    """모니터링 설정"""
    detection_threshold: float = 0.7
    frame_interval: float = 1.0
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class URLConfig:
    """URL 설정"""
    moonraker_base_url: str = "http://3dro.kr:3002"
    webcam_url: str = "http://3dro.kr:3002/webcam/"

@dataclass
class VisionConfig:
    """Custom Vision 설정"""
    prediction_key: str = ""
    project_id: str = ""
    iteration_name: str = "Iteration3"

@dataclass
class CropConfig:
    """이미지 크롭 설정"""
    initial_width_ratio: float = 0.45
    fixed_top_ratio: float = 0.4
    initial_bottom_ratio: float = 0.35
    max_width_ratio: float = 0.8
    max_bottom_ratio: float = 0.65
    width_growth_rate: float = 0.05
    bottom_growth_rate: float = 0.05

class Config:
    """설정 관리 클래스"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        설정 초기화
        Args:
            config_file (str): 설정 파일 경로
        """
        self.config_file = config_file
        self.monitoring = MonitoringConfig()
        self.urls = URLConfig()
        self.vision = VisionConfig()
        self.crop = CropConfig()
        self.load_config()

    def load_config(self):
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 각 설정 섹션 업데이트
                    if 'monitoring' in data:
                        self.monitoring = MonitoringConfig(**data['monitoring'])
                    if 'urls' in data:
                        self.urls = URLConfig(**data['urls'])
                    if 'vision' in data:
                        self.vision = VisionConfig(**data['vision'])
                    if 'crop' in data:
                        self.crop = CropConfig(**data['crop'])
        except Exception as e:
            print(f"설정 파일 로드 실패: {str(e)}")
            self.save_config()  # 기본 설정 저장

    def save_config(self):
        """현재 설정을 파일로 저장"""
        try:
            config_data = {
                'monitoring': asdict(self.monitoring),
                'urls': asdict(self.urls),
                'vision': asdict(self.vision),
                'crop': asdict(self.crop)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            print(f"설정 파일 저장 실패: {str(e)}")

    def get_section(self, section: str) -> Optional[Dict[str, Any]]:
        """특정 섹션의 설정 반환"""
        if hasattr(self, section):
            return asdict(getattr(self, section))
        return None

    def update_section(self, section: str, values: Dict[str, Any]) -> bool:
        """특정 섹션의 설정 업데이트"""
        try:
            if hasattr(self, section):
                current = getattr(self, section)
                for key, value in values.items():
                    if hasattr(current, key):
                        setattr(current, key, value)
                self.save_config()
                return True
            return False
        except Exception:
            return False

    def reset_to_default(self, section: Optional[str] = None):
        """설정을 기본값으로 초기화"""
        if section is None:
            # 모든 섹션 초기화
            self.monitoring = MonitoringConfig()
            self.urls = URLConfig()
            self.vision = VisionConfig()
            self.crop = CropConfig()
        elif hasattr(self, section):
            # 특정 섹션만 초기화
            if section == 'monitoring':
                self.monitoring = MonitoringConfig()
            elif section == 'urls':
                self.urls = URLConfig()
            elif section == 'vision':
                self.vision = VisionConfig()
            elif section == 'crop':
                self.crop = CropConfig()
        
        self.save_config()

    @property
    def as_dict(self) -> Dict[str, Any]:
        """전체 설정을 딕셔너리로 반환"""
        return {
            'monitoring': asdict(self.monitoring),
            'urls': asdict(self.urls),
            'vision': asdict(self.vision),
            'crop': asdict(self.crop)
        }