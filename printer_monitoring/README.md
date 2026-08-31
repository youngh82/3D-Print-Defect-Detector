# printer_monitoring

Refactored production version of the Nopaghetti 3D printer defect detection system.

See the [root README](../README.md) for full project documentation.

## Quick Start

```bash
cp .env.example .env   # Configure API keys and printer URLs
pip install -r requirements.txt
python main.py
```

## Module Overview

| Module | Description |
|--------|------------|
| `src/core/defect_detector.py` | Azure Custom Vision API integration, bounding box rendering |
| `src/core/image_processor.py` | Webcam frame capture, adaptive ROI cropping algorithm |
| `src/core/printer_monitor.py` | Moonraker API wrapper for pause/resume/status |
| `src/ui/main_window.py` | Application shell, timer orchestration, event wiring |
| `src/ui/control_panel.py` | URL configuration, monitoring controls, real-time log |
| `src/ui/video_widget.py` | Dual video display (live webcam + detection overlay) |
| `src/utils/api_client.py` | HTTP client with retry, timeout, event emission |
| `src/utils/env_loader.py` | `.env` file loading and validation |
| `src/constants/settings.py` | Centralized configuration constants |

## Runtime Flow

1. `main.py` creates `MainWindow`, which initializes UI, factories, and timers
2. User clicks "Start Monitoring" -> `QTimer` fires every 1 second
3. `ImageProcessor.capture_frame()` fetches a snapshot from the webcam URL
4. `ImageProcessor.process_frame()` applies dynamic ROI cropping
5. `DefectDetector.detect_defect()` sends the cropped frame to Azure Custom Vision
6. If defect confidence > 70%, `PrinterMonitor.pause_print()` calls Moonraker API
7. All events are displayed in the control panel log and status bar
