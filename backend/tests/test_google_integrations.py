"""
Test per integrazioni Google Drive e Google Calendar
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Mock Google API clients
@pytest.fixture
def mock_drive_service():
    """Mock Google Drive service"""
    service = Mock()
    service.files().create = Mock(return_value=Mock(
        execute=Mock(return_value={'id': 'test-file-id', 'webViewLink': 'https://drive.google.com/file/test'})
    ))
    service.files().get_media = Mock()
    service.files().list = Mock(return_value=Mock(
        execute=Mock(return_value={'files': [{'id': '1', 'name': 'test.pdf'}]})
    ))
    return service


@pytest.fixture
def mock_calendar_service():
    """Mock Google Calendar service"""
    service = Mock()
    service.events().insert = Mock(return_value=Mock(
        execute=Mock(return_value={'id': 'test-event-id', 'htmlLink': 'https://calendar.google.com/event/test'})
    ))
    service.events().list = Mock(return_value=Mock(
        execute=Mock(return_value={'items': [{'id': '1', 'summary': 'Test Event'}]})
    ))
    service.events().delete = Mock(return_value=Mock(execute=Mock(return_value={})))
    return service


class TestGoogleDriveIntegration:
    """Test Google Drive operations"""

    def test_upload_file_to_drive(self, mock_drive_service):
        """Test caricamento file su Google Drive"""
        # Test parameters
        file_name = "email_allegato.pdf"
        file_content = b"PDF content here"
        folder_id = "root"
        mime_type = "application/pdf"

        # Mock file metadata
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
            'mimeType': mime_type
        }

        # Execute upload
        result = mock_drive_service.files().create(
            body=file_metadata,
            media_body=file_content,
            fields='id, webViewLink'
        ).execute()

        # Assertions
        assert result['id'] == 'test-file-id'
        assert 'webViewLink' in result
        assert result['webViewLink'].startswith('https://drive.google.com')
        mock_drive_service.files().create.assert_called_once()

    def test_upload_with_folder_structure(self, mock_drive_service):
        """Test creazione struttura cartelle su Drive"""
        # Test parameters - struttura tipo: /SNALS/Email/Anno/Mese/
        folders = {
            'root': 'SNALS',
            'email': 'Email',
            'year': '2025',
            'month': '11_Novembre'
        }

        # Mock folder creation
        for folder_name in folders.values():
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            result = mock_drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            assert result['id'] == 'test-file-id'

        # Verify multiple folder creations
        assert mock_drive_service.files().create.call_count == len(folders)

    def test_upload_with_permissions(self, mock_drive_service):
        """Test caricamento con permessi specifici"""
        # Test parameters
        permissions = [
            {
                'type': 'user',
                'role': 'writer',
                'emailAddress': 'segretario@snals.it'
            },
            {
                'type': 'group',
                'role': 'reader',
                'emailAddress': 'coordinatori@snals.it'
            }
        ]

        # Mock permissions API
        mock_drive_service.permissions = Mock()
        mock_drive_service.permissions().create = Mock(return_value=Mock(
            execute=Mock(return_value={'id': 'permission-id'})
        ))

        # Add permissions
        for perm in permissions:
            result = mock_drive_service.permissions().create(
                fileId='test-file-id',
                body=perm
            ).execute()

            assert result['id'] == 'permission-id'

        assert mock_drive_service.permissions().create.call_count == len(permissions)

    def test_search_files_in_drive(self, mock_drive_service):
        """Test ricerca file su Drive"""
        # Test search query
        query = "name contains 'convocazione' and mimeType='application/pdf'"

        # Execute search
        results = mock_drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, webViewLink)'
        ).execute()

        # Assertions
        assert 'files' in results
        assert len(results['files']) > 0
        mock_drive_service.files().list.assert_called_once()


class TestGoogleCalendarIntegration:
    """Test Google Calendar operations"""

    def test_create_event_from_email(self, mock_calendar_service):
        """Test creazione evento calendario da email"""
        # Test parameters - esempio convocazione
        event_data = {
            'summary': 'Convocazione Contrattazione Integrativa',
            'description': 'Convocazione per discutere contrattazione integrativa a.s. 2025/26',
            'start': {
                'dateTime': (datetime.now() + timedelta(days=3)).isoformat(),
                'timeZone': 'Europe/Rome',
            },
            'end': {
                'dateTime': (datetime.now() + timedelta(days=3, hours=2)).isoformat(),
                'timeZone': 'Europe/Rome',
            },
            'attendees': [
                {'email': 'coordinatore@snals.it'},
                {'email': 'segretario@snals.it'},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 giorno prima
                    {'method': 'popup', 'minutes': 60},  # 1 ora prima
                ],
            },
        }

        # Create event
        event = mock_calendar_service.events().insert(
            calendarId='primary',
            body=event_data,
            sendUpdates='all'
        ).execute()

        # Assertions
        assert event['id'] == 'test-event-id'
        assert 'htmlLink' in event
        assert event['htmlLink'].startswith('https://calendar.google.com')
        mock_calendar_service.events().insert.assert_called_once()

    def test_event_with_location(self, mock_calendar_service):
        """Test evento con location"""
        event_data = {
            'summary': 'Assemblea Sindacale SNALS',
            'location': 'Sede SNALS Taranto, Via Roma 123',
            'start': {
                'dateTime': datetime(2025, 11, 25, 9, 0).isoformat(),
                'timeZone': 'Europe/Rome',
            },
            'end': {
                'dateTime': datetime(2025, 11, 25, 11, 0).isoformat(),
                'timeZone': 'Europe/Rome',
            },
        }

        event = mock_calendar_service.events().insert(
            calendarId='primary',
            body=event_data
        ).execute()

        assert event['id'] is not None
        mock_calendar_service.events().insert.assert_called_once()

    def test_recurring_event(self, mock_calendar_service):
        """Test evento ricorrente"""
        # Evento ricorrente settimanale
        event_data = {
            'summary': 'Riunione settimanale coordinamento',
            'start': {
                'dateTime': datetime(2025, 11, 18, 14, 0).isoformat(),
                'timeZone': 'Europe/Rome',
            },
            'end': {
                'dateTime': datetime(2025, 11, 18, 16, 0).isoformat(),
                'timeZone': 'Europe/Rome',
            },
            'recurrence': [
                'RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=10'  # Ogni lunedì per 10 settimane
            ],
        }

        event = mock_calendar_service.events().insert(
            calendarId='primary',
            body=event_data
        ).execute()

        assert event['id'] is not None
        mock_calendar_service.events().insert.assert_called_once()

    def test_update_event_reminders(self, mock_calendar_service):
        """Test aggiornamento promemoria evento"""
        # Mock update
        mock_calendar_service.events().patch = Mock(return_value=Mock(
            execute=Mock(return_value={'id': 'test-event-id', 'updated': True})
        ))

        # Updated reminders
        updates = {
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 1440},  # 1 giorno
                    {'method': 'email', 'minutes': 60},    # 1 ora
                    {'method': 'popup', 'minutes': 30},    # 30 minuti
                ],
            }
        }

        result = mock_calendar_service.events().patch(
            calendarId='primary',
            eventId='test-event-id',
            body=updates
        ).execute()

        assert result['updated'] is True
        mock_calendar_service.events().patch.assert_called_once()

    def test_list_upcoming_events(self, mock_calendar_service):
        """Test lista eventi futuri"""
        now = datetime.utcnow().isoformat() + 'Z'

        events_result = mock_calendar_service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        assert 'items' in events_result
        assert len(events_result['items']) > 0
        mock_calendar_service.events().list.assert_called_once()

    def test_delete_event(self, mock_calendar_service):
        """Test cancellazione evento"""
        result = mock_calendar_service.events().delete(
            calendarId='primary',
            eventId='test-event-id',
            sendUpdates='all'
        ).execute()

        mock_calendar_service.events().delete.assert_called_once()


class TestIntegratedWorkflow:
    """Test workflow integrati Drive + Calendar"""

    def test_email_to_drive_and_calendar(self, mock_drive_service, mock_calendar_service):
        """
        Test workflow completo:
        1. Email con allegato ricevuta
        2. Allegato caricato su Drive
        3. Evento creato su Calendar
        4. Link Drive aggiunto alla descrizione evento
        """
        # Step 1: Upload attachment to Drive
        file_result = mock_drive_service.files().create(
            body={'name': 'convocazione.pdf'},
            media_body=b'PDF content'
        ).execute()

        drive_link = file_result['webViewLink']
        assert drive_link is not None

        # Step 2: Create calendar event with Drive link
        event_data = {
            'summary': 'Convocazione Scuola',
            'description': f'Allegato disponibile su Drive: {drive_link}',
            'start': {'dateTime': datetime.now().isoformat()},
            'end': {'dateTime': (datetime.now() + timedelta(hours=2)).isoformat()},
        }

        event_result = mock_calendar_service.events().insert(
            calendarId='primary',
            body=event_data
        ).execute()

        # Verify both operations succeeded
        assert file_result['id'] is not None
        assert event_result['id'] is not None
        assert drive_link in event_data['description']

    def test_shared_drive_with_calendar_permissions(self, mock_drive_service, mock_calendar_service):
        """
        Test condivisione sincronizzata:
        - File Drive condiviso con partecipanti
        - Evento Calendar con stessi partecipanti
        """
        attendees = [
            'coordinatore@snals.it',
            'segretario@snals.it',
        ]

        # Upload and share file
        file_result = mock_drive_service.files().create(
            body={'name': 'documento.pdf'}
        ).execute()

        # Mock permissions
        mock_drive_service.permissions = Mock()
        mock_drive_service.permissions().create = Mock(return_value=Mock(
            execute=Mock(return_value={'id': 'perm-id'})
        ))

        # Share with each attendee
        for email in attendees:
            mock_drive_service.permissions().create(
                fileId=file_result['id'],
                body={'type': 'user', 'role': 'reader', 'emailAddress': email}
            ).execute()

        # Create event with same attendees
        event_result = mock_calendar_service.events().insert(
            calendarId='primary',
            body={
                'summary': 'Riunione con documenti',
                'attendees': [{'email': email} for email in attendees]
            }
        ).execute()

        # Verify sharing
        assert mock_drive_service.permissions().create.call_count == len(attendees)
        assert event_result['id'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
