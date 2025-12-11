"""
Modello per impostazioni di sistema
"""

from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base


class SystemSettings(Base):
    """Impostazioni globali del sistema"""
    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text)
    value_type = Column(String)  # 'bool', 'int', 'str', 'json'
    description = Column(String)

    def get_typed_value(self):
        """Ritorna il valore convertito al tipo corretto"""
        if self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        else:
            return self.value
