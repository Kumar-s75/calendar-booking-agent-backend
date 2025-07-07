from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
from typing import List, Dict, Optional
import json

class CalendarService:
    def __init__(self):
        self.service = self._authenticate()
        self.calendar_id = 'primary'  # Use primary calendar
    
    def _authenticate(self):
        """Authenticate using service account credentials"""
        try:
            # Load service account credentials from environment variable
            credentials_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            if not credentials_json:
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set")
            
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            return build('calendar', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Authentication error: {e}")
            raise
    
    def get_available_slots(self, date: str, duration_minutes: int = 60) -> List[Dict]:
        """Get available time slots for a given date"""
        try:
            # Parse the date
            target_date = datetime.strptime(date, '%Y-%m-%d')
            
            # Set time range (9 AM to 5 PM)
            start_time = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_time = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
            
            # Get existing events
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Generate available slots
            available_slots = []
            current_time = start_time
            
            while current_time + timedelta(minutes=duration_minutes) <= end_time:
                slot_end = current_time + timedelta(minutes=duration_minutes)
                
                # Check if this slot conflicts with any existing event
                is_available = True
                for event in events:
                    event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')).replace('Z', '+00:00'))
                    event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')).replace('Z', '+00:00'))
                    
                    # Remove timezone info for comparison
                    event_start = event_start.replace(tzinfo=None)
                    event_end = event_end.replace(tzinfo=None)
                    
                    if (current_time < event_end and slot_end > event_start):
                        is_available = False
                        break
                
                if is_available:
                    available_slots.append({
                        'start_time': current_time.strftime('%H:%M'),
                        'end_time': slot_end.strftime('%H:%M'),
                        'datetime': current_time.isoformat()
                    })
                
                current_time += timedelta(minutes=30)  # 30-minute intervals
            
            return available_slots
            
        except Exception as e:
            print(f"Error getting available slots: {e}")
            return []
    
    def create_event(self, title: str, start_datetime: str, duration_minutes: int = 60, description: str = "") -> Dict:
        """Create a new calendar event"""
        try:
            start_time = datetime.fromisoformat(start_datetime)
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            return {
                'success': True,
                'event_id': created_event['id'],
                'event_link': created_event.get('htmlLink', ''),
                'message': f"Event '{title}' created successfully"
            }
            
        except Exception as e:
            print(f"Error creating event: {e}")
            return {
                'success': False,
                'message': f"Failed to create event: {str(e)}"
            }
    
    def get_events(self, date: str) -> List[Dict]:
        """Get events for a specific date"""
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d')
            start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                formatted_events.append({
                    'title': event.get('summary', 'No Title'),
                    'start_time': start,
                    'description': event.get('description', '')
                })
            
            return formatted_events
            
        except Exception as e:
            print(f"Error getting events: {e}")
            return []
