"""Configuration management for B2 Sync tool."""

import shutil
import yaml
from pathlib import Path
from typing import Dict, Set, Optional, Any


class Config:
    """Configuration management for the Backblaze B2 Image Sync tool."""
    
    # CLI Tool Paths
    B2_CLI: Optional[str] = shutil.which("b2")
    OP_CLI: Optional[str] = shutil.which("op")
    
    # Default Settings
    DEFAULT_CONFIG = {
        "b2": {
            "bucket_name": "fal-bucket",
            "sync_threads": 10,
            "retry_attempts": 3,
            "sync_timeout": 1800,
            "max_file_size_gb": 5
        },
        "1password": {
            "item_name": "B2 Application Key Fal"
        },
        "processing": {
            "supported_formats": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
            "exclude_patterns": [r".*\.DS_Store", r".*Thumbs\.db"]
        }
    }
    
    # Directory Settings (following new structure)
    PROJECT_ROOT = Path(__file__).parent.parent
    USER_FILES = PROJECT_ROOT / "USER-FILES"
    CONFIG_DIR = USER_FILES / "01.CONFIG"
    INPUT_DIR = USER_FILES / "04.INPUT"
    OUTPUT_DIR = USER_FILES / "05.OUTPUT"
    
    # Config file path
    CONFIG_FILE = CONFIG_DIR / "b2_sync_config.yml"
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration from file or defaults."""
        self.config_file = config_file or self.CONFIG_FILE
        self.config_data = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file or use defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                # Merge with defaults
                config = self.DEFAULT_CONFIG.copy()
                self._deep_merge(config, user_config)
                return config
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_file}: {e}")
                print("Using default configuration")
        return self.DEFAULT_CONFIG.copy()
    
    def _deep_merge(self, base: Dict, updates: Dict) -> None:
        """Deep merge updates into base dictionary."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save_config(self) -> None:
        """Save current configuration to YAML file."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config_data, f, default_flow_style=False, sort_keys=False)
    
    @property
    def bucket_name(self) -> str:
        """Get configured bucket name."""
        return self.config_data["b2"]["bucket_name"]
    
    @property
    def op_item_name(self) -> str:
        """Get 1Password item name."""
        return self.config_data["1password"]["item_name"]
    
    @property
    def supported_formats(self) -> Set[str]:
        """Get supported file formats."""
        return set(self.config_data["processing"]["supported_formats"])
    
    @property
    def sync_threads(self) -> int:
        """Get number of sync threads."""
        return self.config_data["b2"]["sync_threads"]
    
    @property
    def retry_attempts(self) -> int:
        """Get number of retry attempts."""
        return self.config_data["b2"]["retry_attempts"]
    
    @property
    def sync_timeout(self) -> int:
        """Get sync timeout in seconds."""
        return self.config_data["b2"]["sync_timeout"]
    
    @property
    def max_file_size(self) -> int:
        """Get max file size in bytes."""
        BYTES_PER_GB = 1024 * 1024 * 1024
        return self.config_data["b2"]["max_file_size_gb"] * BYTES_PER_GB
    
    @property
    def exclude_patterns(self) -> list:
        """Get file exclusion patterns."""
        return self.config_data["processing"]["exclude_patterns"]
    
    @classmethod
    def get_input_path(cls) -> Path:
        """Get the input directory path."""
        return cls.INPUT_DIR
    
    @classmethod
    def get_output_path(cls) -> Path:
        """Get the output directory path."""
        return cls.OUTPUT_DIR
    
    @classmethod
    def validate_environment(cls) -> bool:
        """Validate that required tools and directories are available."""
        errors = []
        
        # Check CLI tools
        if not cls.B2_CLI:
            errors.append("B2 CLI tool not found in PATH. Please install it first.")
        
        if not cls.OP_CLI:
            errors.append("1Password CLI tool not found in PATH. Please install it first.")
        
        # Check directories
        if not cls.get_input_path().exists():
            errors.append(f"Input directory '{cls.INPUT_DIR}' does not exist.")
        
        # Create output directory if it doesn't exist
        cls.get_output_path().mkdir(parents=True, exist_ok=True)
        
        if errors:
            print("Environment validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def is_supported_format(self, file_path: Path) -> bool:
        """Check if a file has a supported image format."""
        return file_path.suffix.lower() in self.supported_formats