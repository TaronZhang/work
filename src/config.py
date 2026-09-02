"""Configuration module — loads settings from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment."""

    flask_debug: bool = os.environ.get('FLASK_DEBUG', '0') == '1'
    host: str = os.environ.get('HOST', '127.0.0.1')
    port: int = int(os.environ.get('PORT', '29661'))

    max_content_length: int = int(
        os.environ.get('MAX_CONTENT_LENGTH_MB', '500')
    ) * 1024 * 1024

    openai_api_key: str = os.environ.get('OPENAI_API_KEY', '')
    openai_base_url: str = os.environ.get(
        'OPENAI_BASE_URL', 'https://api.openai.com/v1'
    )
    openai_model: str = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    auto_split_threshold: int = int(
        os.environ.get('AUTO_SPLIT_THRESHOLD_MB', '10')
    ) * 1024 * 1024
    auto_split_max_chars: int = int(
        os.environ.get('AUTO_SPLIT_MAX_CHARS', '100000')
    )

    upload_folder: str = os.environ.get(
        'UPLOAD_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads'),
    )


config = Config()
