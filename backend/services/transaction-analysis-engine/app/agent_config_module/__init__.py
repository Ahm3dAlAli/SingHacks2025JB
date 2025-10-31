"""
Configuration modules for Transaction Analysis Engine.
"""

# Import from original config.py
import sys
from pathlib import Path

# Add parent directory to path to access config.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Settings, get_settings, settings

# Import agent config
from app.agent_config_module.agent_config import (
    AgentConfig,
    SeverityConfig,
    JurisdictionConfig,
    AlertThresholdsConfig,
    GeographicRiskConfig,
    BehavioralThresholdsConfig,
    AgentExecutionConfig,
    get_agent_config,
    set_agent_config,
    reset_agent_config,
)

__all__ = [
    # Original config
    "Settings",
    "get_settings",
    "settings",
    # Agent config
    "AgentConfig",
    "SeverityConfig",
    "JurisdictionConfig",
    "AlertThresholdsConfig",
    "GeographicRiskConfig",
    "BehavioralThresholdsConfig",
    "AgentExecutionConfig",
    "get_agent_config",
    "set_agent_config",
    "reset_agent_config",
]
