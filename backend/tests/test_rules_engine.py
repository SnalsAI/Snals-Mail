"""
Test motore regole
"""

import pytest
from app.services.rules_engine import RulesEngine
from app.models.email import Email, EmailCategory, AccountType, EmailStatus
from app.models.interpretazione import Interpretazione
from datetime import datetime


def test_evaluate_simple_condition():
    """Test valutazione condizione semplice"""
    engine = RulesEngine()

    email = Email(
        id=1,
        message_id="test",
        account_type=AccountType.NORMALE,
        mittente="test@example.it",
        destinatario="snals@example.it",
        oggetto="Test",
        corpo="Test corpo",
        data_ricezione=datetime.now(),
        categoria=EmailCategory.INFO_GENERICHE,
        stato=EmailStatus.RICEVUTA
    )

    interp = None

    condition = {
        "field": "categoria",
        "operator": "equals",
        "value": "info_generiche"
    }

    result = engine.evaluate_condition(condition, email, interp)
    assert result == True


def test_evaluate_and_conditions():
    """Test condizioni AND"""
    engine = RulesEngine()

    email = Email(
        id=1,
        message_id="test",
        account_type=AccountType.NORMALE,
        mittente="laterza@scuola.it",
        destinatario="snals@example.it",
        oggetto="Convocazione",
        corpo="Test",
        data_ricezione=datetime.now(),
        categoria=EmailCategory.CONVOCAZIONE_SCUOLA,
        stato=EmailStatus.RICEVUTA
    )

    interp = Interpretazione(
        id=1,
        email_id=1,
        categoria="convocazione_scuola",
        interpretazione_json={"scuola": "IC Laterza"},
        confidence=0.9
    )

    conditions_group = {
        "operator": "AND",
        "conditions": [
            {"field": "categoria", "operator": "equals", "value": "convocazione_scuola"},
            {"field": "mittente", "operator": "contains", "value": "laterza"}
        ]
    }

    result = engine.evaluate_conditions_group(conditions_group, email, interp)
    assert result == True
