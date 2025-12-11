"""
Servizio per la generazione automatica di slot prenotabili.

Logica:
1. Prende una disponibilità (es. 9:00-13:00)
2. Per ogni tipo appuntamento gestito dallo staff:
   - Calcola la durata (personalizzata o default)
   - Genera N slot consecutivi che coprono la fascia oraria
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, date, time, timedelta
from typing import List, Optional
import logging

from app.models.booking import (
    BookingDisponibilita, BookingSlot, BookingStaff,
    BookingStaffCompetenza, BookingTipoAppuntamento,
    StatoSlot
)

logger = logging.getLogger(__name__)


class SlotGeneratorService:
    """Genera slot prenotabili dalle disponibilità staff."""

    def __init__(self, db: Session):
        self.db = db

    def genera_slots_da_disponibilita(
        self,
        disponibilita_id: int,
        tipi_appuntamento_ids: Optional[List[int]] = None
    ) -> int:
        """
        Genera slot da una singola disponibilità.

        Args:
            disponibilita_id: ID della disponibilità
            tipi_appuntamento_ids: Lista di tipi da generare (None = tutti)

        Returns:
            Numero di slot generati
        """
        disponibilita = self.db.query(BookingDisponibilita).get(disponibilita_id)
        if not disponibilita or not disponibilita.attivo:
            logger.warning(f"Disponibilità {disponibilita_id} non trovata o non attiva")
            return 0

        return self._genera_slots_per_disponibilita(disponibilita, tipi_appuntamento_ids)

    def genera_slots_periodo(
        self,
        staff_id: int,
        data_inizio: date,
        data_fine: date,
        tipi_appuntamento_ids: Optional[List[int]] = None
    ) -> int:
        """
        Genera slot per tutte le disponibilità di uno staff in un periodo.

        Args:
            staff_id: ID dello staff
            data_inizio: Data inizio periodo
            data_fine: Data fine periodo
            tipi_appuntamento_ids: Lista di tipi da generare (None = tutti)

        Returns:
            Numero totale di slot generati
        """
        disponibilita_list = self.db.query(BookingDisponibilita).filter(
            BookingDisponibilita.staff_id == staff_id,
            BookingDisponibilita.attivo == True,
            BookingDisponibilita.data >= data_inizio,
            BookingDisponibilita.data <= data_fine
        ).all()

        total = 0
        for disponibilita in disponibilita_list:
            count = self._genera_slots_per_disponibilita(disponibilita, tipi_appuntamento_ids)
            total += count
            logger.info(f"Generati {count} slot per disponibilità {disponibilita.id} ({disponibilita.data})")

        return total

    def _genera_slots_per_disponibilita(
        self,
        disponibilita: BookingDisponibilita,
        tipi_appuntamento_ids: Optional[List[int]] = None
    ) -> int:
        """
        Genera slot per una disponibilità.

        Per ogni tipo appuntamento gestito dallo staff,
        crea slot consecutivi che coprono la fascia oraria.
        """
        staff = disponibilita.staff
        if not staff or not staff.attivo:
            return 0

        # Ottieni competenze dello staff
        competenze_query = self.db.query(BookingStaffCompetenza).filter(
            BookingStaffCompetenza.staff_id == staff.id,
            BookingStaffCompetenza.attivo == True
        )

        if tipi_appuntamento_ids:
            competenze_query = competenze_query.filter(
                BookingStaffCompetenza.tipo_appuntamento_id.in_(tipi_appuntamento_ids)
            )

        competenze = competenze_query.all()

        if not competenze:
            logger.warning(f"Staff {staff.id} non ha competenze attive")
            return 0

        count = 0

        for competenza in competenze:
            tipo = competenza.tipo_appuntamento
            if not tipo or not tipo.attivo:
                continue

            # Calcola durata (override o default)
            durata_minuti = competenza.durata_minuti or tipo.durata_default_minuti

            # Genera slot
            slots_creati = self._genera_slots_fascia(
                disponibilita=disponibilita,
                tipo_appuntamento=tipo,
                durata_minuti=durata_minuti
            )
            count += slots_creati

        return count

    def _genera_slots_fascia(
        self,
        disponibilita: BookingDisponibilita,
        tipo_appuntamento: BookingTipoAppuntamento,
        durata_minuti: int
    ) -> int:
        """
        Genera slot consecutivi per una fascia oraria.

        Es: 9:00-13:00 con durata 30 min → 8 slot
        """
        # Combina data e ora
        data = disponibilita.data
        ora_inizio = datetime.combine(data, disponibilita.ora_inizio)
        ora_fine = datetime.combine(data, disponibilita.ora_fine)

        # Verifica che non sia nel passato
        if ora_fine <= datetime.now():
            logger.debug(f"Disponibilità {disponibilita.id} nel passato, skip")
            return 0

        # Calcola slot
        durata = timedelta(minutes=durata_minuti)
        current = ora_inizio
        count = 0

        while current + durata <= ora_fine:
            slot_inizio = current
            slot_fine = current + durata

            # Verifica se slot esiste già
            existing = self.db.query(BookingSlot).filter(
                BookingSlot.staff_id == disponibilita.staff_id,
                BookingSlot.tipo_appuntamento_id == tipo_appuntamento.id,
                BookingSlot.data_ora_inizio == slot_inizio
            ).first()

            if not existing:
                # Crea nuovo slot
                slot = BookingSlot(
                    disponibilita_id=disponibilita.id,
                    staff_id=disponibilita.staff_id,
                    sede_id=disponibilita.sede_id,
                    tipo_appuntamento_id=tipo_appuntamento.id,
                    data_ora_inizio=slot_inizio,
                    data_ora_fine=slot_fine,
                    stato=StatoSlot.LIBERO
                )
                self.db.add(slot)
                count += 1

            current = slot_fine

        self.db.commit()
        return count

    def blocca_slot(self, slot_id: int, note: str = None) -> bool:
        """
        Blocca uno slot (non prenotabile).

        Args:
            slot_id: ID dello slot
            note: Motivo del blocco

        Returns:
            True se bloccato, False se già prenotato
        """
        slot = self.db.query(BookingSlot).get(slot_id)
        if not slot:
            return False

        if slot.stato == StatoSlot.PRENOTATO:
            return False  # Non può bloccare slot già prenotato

        slot.stato = StatoSlot.BLOCCATO
        slot.note = note
        slot.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def sblocca_slot(self, slot_id: int) -> bool:
        """
        Sblocca uno slot precedentemente bloccato.

        Returns:
            True se sbloccato, False se non era bloccato
        """
        slot = self.db.query(BookingSlot).get(slot_id)
        if not slot or slot.stato != StatoSlot.BLOCCATO:
            return False

        slot.stato = StatoSlot.LIBERO
        slot.note = None
        slot.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def elimina_slots_futuri(
        self,
        staff_id: int,
        data_da: date = None,
        solo_liberi: bool = True
    ) -> int:
        """
        Elimina slot futuri per uno staff.

        Utile quando si modifica la disponibilità.

        Args:
            staff_id: ID staff
            data_da: Data da cui eliminare (default: oggi)
            solo_liberi: Se True, elimina solo slot liberi

        Returns:
            Numero slot eliminati
        """
        if not data_da:
            data_da = date.today()

        query = self.db.query(BookingSlot).filter(
            BookingSlot.staff_id == staff_id,
            BookingSlot.data_ora_inizio >= datetime.combine(data_da, time.min)
        )

        if solo_liberi:
            query = query.filter(BookingSlot.stato == StatoSlot.LIBERO)

        count = query.count()
        query.delete(synchronize_session=False)
        self.db.commit()

        return count
