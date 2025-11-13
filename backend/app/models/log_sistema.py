"""
Model per log sistema
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Index
from datetime import datetime
import enum

from app.database import Base


class LivelloLog(enum.Enum):
    """Livelli log"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogSistema(Base):
    """Log eventi sistema"""
    
    __tablename__ = "log_sistema"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Dettagli log
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    livello = Column(Enum(LivelloLog), nullable=False, index=True)
    componente = Column(String(100), index=True)
    messaggio = Column(Text, nullable=False)
    
    # Extra context
    extra = Column(Text)
    
    # Indice composto per query efficienti
    __table_args__ = (
        Index('idx_log_timestamp_livello', 'timestamp', 'livello'),
    )
    
    def __repr__(self):
        return f"<LogSistema {self.id}: {self.livello.value}>"
