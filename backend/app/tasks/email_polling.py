"""
Email Polling Task (stub con integrazione regole)
"""

import logging
from app.services.rules_engine import RulesEngine

logger = logging.getLogger(__name__)


def process_email(email_record):
    """
    Processa una email dopo interpretazione

    Args:
        email_record: Record Email dal database
    """
    logger.info(f"Processing email {email_record.id}")

    # Dopo salvataggio interpretazione...

    # Applica regole (FASE 7)
    rules_engine = RulesEngine()
    rule_actions = rules_engine.apply_rules(email_record)

    # Esegui azioni da regole
    if rule_actions:
        rules_engine.execute_rule_actions(rule_actions, email_record)
        logger.info(f"Eseguite {len(rule_actions)} azioni da regole per email {email_record.id}")
