"""
Email Categorizer Service (stub)
"""

from app.models.email import EmailCategory


class EmailCategorizer:
    """Categorizzatore email basato su regole e ML"""

    def categorize(self, mittente: str, oggetto: str, corpo: str) -> tuple:
        """
        Categorizza una email

        Returns:
            tuple: (categoria, confidence)
        """
        # Implementazione stub - logica base
        oggetto_lower = oggetto.lower()
        corpo_lower = corpo.lower()

        # Convocazioni
        if "convocazione" in oggetto_lower or "convocazione" in corpo_lower:
            if "rsu" in oggetto_lower or "scuola" in mittente.lower():
                return (EmailCategory.CONVOCAZIONE_SCUOLA, 0.85)
            elif "snals" in mittente.lower():
                return (EmailCategory.CONVOCAZIONE_SNALS, 0.85)

        # Richieste assistenza
        if any(word in oggetto_lower for word in ["assistenza", "aiuto", "problema", "questione"]):
            return (EmailCategory.RICHIESTA_ASSISTENZA, 0.75)

        # Contenzioso
        if any(word in oggetto_lower for word in ["ricorso", "contenzioso", "tribunale", "legale"]):
            return (EmailCategory.CONTENZIOSO, 0.80)

        # Circolari
        if "circolare" in oggetto_lower:
            return (EmailCategory.CIRCOLARE, 0.90)

        # Default
        return (EmailCategory.INFO_GENERICHE, 0.60)
