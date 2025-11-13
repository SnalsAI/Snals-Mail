"""
Test categorizzatore
"""

import pytest
from app.services.categorizer import EmailCategorizer
from app.models.email import EmailCategory


def test_categorize_convocazione():
    """Test categorizzazione convocazione"""
    categorizer = EmailCategorizer()

    categoria, confidence = categorizer.categorize(
        mittente="scuola@example.it",
        oggetto="Convocazione RSU del 15 novembre",
        corpo="Si convoca riunione RSU per il giorno 15 novembre alle ore 15:00..."
    )

    assert categoria == EmailCategory.CONVOCAZIONE_SCUOLA
    assert confidence > 0.7


def test_categorize_info():
    """Test categorizzazione info generiche"""
    categorizer = EmailCategorizer()

    categoria, confidence = categorizer.categorize(
        mittente="utente@example.com",
        oggetto="Informazioni su pensione",
        corpo="Vorrei avere informazioni riguardo la mia pensione anticipata..."
    )

    assert categoria == EmailCategory.INFO_GENERICHE
    assert confidence > 0.6
