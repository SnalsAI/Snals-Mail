"""
Model per classi di concorso
"""
from sqlalchemy import Column, Integer, String, Index
from app.database import Base


class ClasseConcorso(Base):
    """Classe di concorso (da DPR 19/2016)"""

    __tablename__ = "classi_concorso"

    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String(10), unique=True, nullable=False, index=True)  # A-01, A028, AA25
    codice_sidi = Column(String(10), nullable=False)  # A001, AA25
    grado = Column(String(20), nullable=False)  # I GRADO, II GRADO
    descrizione = Column(String(500), nullable=False)  # ARTE E IMMAGINE...
    area = Column(String(100))  # matematica, lingue, arte, etc (opzionale)

    # Indice per ricerche veloci
    __table_args__ = (
        Index('ix_classi_concorso_codice', 'codice'),
        Index('ix_classi_concorso_codice_sidi', 'codice_sidi'),
    )

    def __repr__(self):
        return f"<ClasseConcorso {self.codice}: {self.descrizione}>"
