from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def parse_created_at(created_at_str: str = None) -> datetime:
    """Parseia a data da Blaze de forma segura com fallback em UTC naive"""
    if not created_at_str:
        return datetime.utcnow()
    try:
        if created_at_str.endswith('Z'):
            created_at_str = created_at_str[:-1]
        return datetime.fromisoformat(created_at_str)
    except Exception as e:
        logger.error(f"Erro ao parsear data {created_at_str}: {e}")
        return datetime.utcnow()
