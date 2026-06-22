import logging.config
import os
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    
    'formatters': {
        'simple': {
            'format': '%(levelname)s - %(name)s - %(message)s'
        },
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'json_style': {
            'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        }
    },
    
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'WARNING',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file_all': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': str(LOG_DIR / 'spynet_all.log'),
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
            'encoding': 'utf-8'
        },
        'file_errors': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': str(LOG_DIR / 'spynet_errors.log'),
            'maxBytes': 5242880,
            'backupCount': 3,
            'encoding': 'utf-8'
        },
        'file_analyzer': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': str(LOG_DIR / 'analyzer.log'),
            'maxBytes': 5242880,
            'backupCount': 3,
            'encoding': 'utf-8'
        },
        'file_services': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': str(LOG_DIR / 'services.log'),
            'maxBytes': 5242880,
            'backupCount': 3,
            'encoding': 'utf-8'
        },
        'file_detectors': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': str(LOG_DIR / 'detectors.log'),
            'maxBytes': 5242880,
            'backupCount': 3,
            'encoding': 'utf-8'
        }
    },
    
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_all', 'file_errors']
        },
        
        'spynet.analyzer': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_analyzer', 'file_errors'],
            'propagate': False
        },
        
        'spynet.detectors': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_detectors', 'file_errors'],
            'propagate': False
        },
        'spynet.detectors.frontend': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_detectors', 'file_errors'],
            'propagate': False
        },
        'spynet.detectors.backend': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_detectors', 'file_errors'],
            'propagate': False
        },
        'spynet.detectors.cdn': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_detectors', 'file_errors'],
            'propagate': False
        },
        
        'spynet.core': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_all', 'file_errors'],
            'propagate': False
        },

        'spynet.services': {
            'level': 'INFO',
            'handlers': ['console', 'file_services', 'file_errors'],
            'propagate': False
        },
        'spynet.services.dns': {
            'level': 'INFO',
            'handlers': ['console', 'file_services', 'file_errors'],
            'propagate': False
        },
        'spynet.services.whois': {
            'level': 'INFO',
            'handlers': ['console', 'file_services', 'file_errors'],
            'propagate': False
        },
        'spynet.services.geo': {
            'level': 'INFO',
            'handlers': ['console', 'file_services', 'file_errors'],
            'propagate': False
        },
        'spynet.services.wayback': {
            'level': 'INFO',
            'handlers': ['console', 'file_services', 'file_errors'],
            'propagate': False
        },
        
        'spynet.api': {
            'level': 'INFO',
            'handlers': ['console', 'file_all', 'file_errors'],
            'propagate': False
        }
    }
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
    root_logger = logging.getLogger()
    root_logger.info("=" * 60)
    root_logger.info("Spynet Logger initialized successfully")
    root_logger.info("=" * 60)