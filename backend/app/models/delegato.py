"""
Modelli per gestione delegati e zone per contrattazioni
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base


# Tabella associativa per relazione molti-a-molti tra Delegati e Zone
delegato_zona = Table(
    'delegato_zona',
    Base.metadata,
    Column('delegato_id', Integer, ForeignKey('delegati.id', ondelete='CASCADE')),
    Column('zona_id', Integer, ForeignKey('zone.id', ondelete='CASCADE'))
)


class Zona(Base):
    """Zone geografiche per suddivisione territorio"""
    __tablename__ = 'zone'

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False, index=True)
    descrizione = Column(String)
    attiva = Column(Boolean, default=True)
    comuni = Column(String, default='[]')  # JSON array di comuni (es: ["LATERZA", "GINOSA"])

    # Relazioni
    delegati = relationship('Delegato', secondary=delegato_zona, back_populates='zone')

    def get_comuni(self):
        """Ritorna lista comuni"""
        import json
        return json.loads(self.comuni) if self.comuni else []

    def set_comuni(self, comuni_list: list):
        """Imposta lista comuni"""
        import json
        self.comuni = json.dumps([c.upper() for c in comuni_list])

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descrizione': self.descrizione,
            'attiva': self.attiva,
            'comuni': self.get_comuni(),
            'num_delegati': len(self.delegati) if self.delegati else 0,
        }


class Delegato(Base):
    """Delegati per gestione contrattazioni"""
    __tablename__ = 'delegati'

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    cognome = Column(String, nullable=False)
    email = Column(String, nullable=False)
    telefono = Column(String)
    attivo = Column(Boolean, default=True)
    note = Column(String)

    # Relazioni
    zone = relationship('Zona', secondary=delegato_zona, back_populates='delegati')

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'cognome': self.cognome,
            'nome_completo': f"{self.nome} {self.cognome}",
            'email': self.email,
            'telefono': self.telefono,
            'attivo': self.attivo,
            'note': self.note,
            'zone': [{'id': z.id, 'nome': z.nome} for z in self.zone] if self.zone else []
        }
