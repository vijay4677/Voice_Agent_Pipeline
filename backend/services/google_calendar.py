"""
Google Calendar Integration Service

"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

# Check if Google Calendar libraries are available
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False
    logger.warning("Google Calendar libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


class GoogleCalendarService:
    """
    Service for integrating with Google Calendar
    
    Supports two authentication methods:
    1. Service Account (recommended for server-side)
    2. OAuth 2.0 (for user-specific calendars)
    """
    
    def __init__(self):
        """Initialize Google Calendar service"""
        self.service = None
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        
        if not GOOGLE_CALENDAR_AVAILABLE:
            logger.warning("Google Calendar integration disabled - missing dependencies")
            return
        
        # Try to initialize the service
        try:
            self._initialize_service()
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {e}")
    
    def _initialize_service(self):
        """
        Initialize Google Calendar API service
        
        Tries multiple authentication methods:
        1. OAuth Refresh Token (recommended for personal calendars)
        2. Service Account File
        3. Service Account JSON
        
        """
        # Method 1: OAuth Refresh Token (BEST for personal calendars)
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if refresh_token and client_id and client_secret:
            try:
                logger.info("Authenticating with Google Calendar using OAuth refresh token...")
                
                from google.oauth2.credentials import Credentials
                
                credentials = Credentials(
                    None,  # No access token yet
                    refresh_token=refresh_token,
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                
                self.service = build('calendar', 'v3', credentials=credentials)
                logger.info("Google Calendar service initialized with OAuth")
                return
                
            except Exception as e:
                logger.error(f"OAuth refresh token authentication failed: {e}")
        
        # Method 2: Service Account (from file)
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        
        if service_account_file and os.path.exists(service_account_file):
            try:
                logger.info("Authenticating with Google Calendar using service account...")
                
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_file,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                
                self.service = build('calendar', 'v3', credentials=credentials)
                logger.info("Google Calendar service initialized successfully")
                return
                
            except Exception as e:
                logger.error(f"Service account authentication failed: {e}")
        
        # Method 3: Service Account JSON (from environment variable)
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        
        if service_account_json:
            try:
                logger.info("Authenticating with Google Calendar using service account JSON...")
                
                service_account_info = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                
                self.service = build('calendar', 'v3', credentials=credentials)
                logger.info("Google Calendar service initialized successfully")
                return
                
            except Exception as e:
                logger.error(f"Service account JSON authentication failed: {e}")
        
        logger.warning("Google Calendar not configured. Set one of: GOOGLE_REFRESH_TOKEN (OAuth) or GOOGLE_SERVICE_ACCOUNT_FILE")
    
    def is_enabled(self) -> bool:
        """Check if Google Calendar integration is enabled"""
        return self.service is not None
    
    async def create_appointment_event(
        self,
        name: str,
        date: str,
        time: str,
        purpose: str,
        phone: str,
        duration_minutes: int = 30,
        attendee_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a calendar event for an appointment
        
        Args:
            name: Patient/client name
            date: Appointment date (YYYY-MM-DD)
            time: Appointment time (HH:MM in 24hr format)
            purpose: Purpose of appointment
            phone: Contact phone number
            duration_minutes: Duration in minutes (default: 30)
            attendee_email: Optional attendee email for sending invites
        
        Returns:
            Dict with success status and event details
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "Google Calendar not configured",
                "message": "Google Calendar integration is not enabled"
            }
        
        try:
            # Parse date and time
            start_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            
            # Format for Google Calendar API
            start_time_str = start_datetime.isoformat()
            end_time_str = end_datetime.isoformat()
            
            # Get timezone (you can make this configurable)
            timezone = os.getenv("CALENDAR_TIMEZONE", "Asia/Kolkata")
            
            # Create event body
            event = {
                'summary': f'Appointment: {name}',
                'description': f"""
Appointment Details:
- Name: {name}
- Purpose: {purpose}
- Phone: {phone}
- Booked via: VoiceFlow AI Voice Assistant
                """.strip(),
                'start': {
                    'dateTime': start_time_str,
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time_str,
                    'timeZone': timezone,
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 60},       # 1 hour before
                    ],
                },
                'colorId': '9',  # Blue color
            }
            
            # Add attendee if email provided (works with OAuth, not service accounts)
            if attendee_email:
                event['attendees'] = [
                    {'email': attendee_email}
                ]
                logger.info(f"Adding attendee: {attendee_email}")
            
            # Create the event
            logger.info(f"Creating Google Calendar event for {name} on {date} at {time}")
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event,
                sendNotifications=bool(attendee_email)  # Send email if attendee provided
            ).execute()
            
            event_link = created_event.get('htmlLink')
            event_id = created_event.get('id')
            
            logger.info(f"Calendar event created: {event_id}")
            logger.info(f"   Link: {event_link}")
            
            return {
                "success": True,
                "event_id": event_id,
                "event_link": event_link,
                "message": f"Calendar event created for {name} on {date} at {time}"
            }
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create calendar event due to API error"
            }
        
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create calendar event"
            }
    
    async def update_appointment_event(
        self,
        event_id: str,
        new_date: str,
        new_time: str,
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Update an existing calendar event
        
        Args:
            event_id: Google Calendar event ID
            new_date: New appointment date (YYYY-MM-DD)
            new_time: New appointment time (HH:MM)
            duration_minutes: Duration in minutes
        
        Returns:
            Dict with success status
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "Google Calendar not configured"
            }
        
        try:
            # Parse new date and time
            start_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            
            timezone = os.getenv("CALENDAR_TIMEZONE", "Asia/Kolkata")
            
            # Get existing event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Update times
            event['start'] = {
                'dateTime': start_datetime.isoformat(),
                'timeZone': timezone,
            }
            event['end'] = {
                'dateTime': end_datetime.isoformat(),
                'timeZone': timezone,
            }
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event,
                sendNotifications=True
            ).execute()
            
            logger.info(f"Calendar event updated: {event_id}")
            
            return {
                "success": True,
                "event_id": updated_event.get('id'),
                "event_link": updated_event.get('htmlLink'),
                "message": f"Calendar event updated to {new_date} at {new_time}"
            }
            
        except Exception as e:
            logger.error(f"Error updating calendar event: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update calendar event"
            }
    
    async def cancel_appointment_event(self, event_id: str) -> Dict[str, Any]:
        """
        Cancel (delete) a calendar event
        
        Args:
            event_id: Google Calendar event ID
        
        Returns:
            Dict with success status
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "Google Calendar not configured"
            }
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id,
                sendNotifications=True
            ).execute()
            
            logger.info(f"Calendar event cancelled: {event_id}")
            
            return {
                "success": True,
                "message": "Calendar event cancelled successfully"
            }
            
        except Exception as e:
            logger.error(f"Error cancelling calendar event: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to cancel calendar event"
            }


# Global singleton instance
_google_calendar_service = None

def get_google_calendar_service() -> GoogleCalendarService:
    """Get or create the global Google Calendar service instance"""
    global _google_calendar_service
    
    if _google_calendar_service is None:
        _google_calendar_service = GoogleCalendarService()
    
    return _google_calendar_service

