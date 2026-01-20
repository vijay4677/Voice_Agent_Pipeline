"""
Supabase database client - Global Singleton

Thread-safe singleton instance initialized once at application startup
and reused throughout the application lifecycle.

"""

import os
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
import logging
from datetime import datetime
from threading import Lock as ThreadLock

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Thread-safe Supabase singleton client
    
    This class ensures only ONE Supabase client instance exists globally,
    initialized once at startup and reused by all threads/rooms.
    
    Benefits:
    - Connection pooling
    - No repeated initialization overhead
    - Thread-safe operations
    - Efficient resource usage
    """
    
    _instance: Optional['SupabaseClient'] = None
    _lock = ThreadLock()
    
    def __new__(cls):
        """Singleton pattern - return existing instance or create new one"""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance
    
    def __init__(self):
        """Initialize Supabase client (only runs once due to singleton)"""
        # Skip if already initialized
        if hasattr(self, '_initialized'):
            return
            
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        
        self.client: Client = create_client(url, key)
        self._initialized = True
        logger.info("🗄️  Supabase singleton client initialized (global instance)")
    
    def get_or_create_user(self, contact_number: str) -> Dict[str, Any]:
        """
        Get existing user or create new one by phone number
        
        Args:
            contact_number: User's phone number
            
        Returns:
            User record dict
        """
        try:
            # Check if user exists
            response = self.client.table("users").select("*").eq(
                "contact_number", contact_number
            ).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Found existing user: {contact_number}")
                return response.data[0]
            
            # Create new user
            new_user = {
                "contact_number": contact_number,
                "created_at": datetime.now().isoformat()
            }
            
            response = self.client.table("users").insert(new_user).execute()
            logger.info(f"Created new user: {contact_number}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            raise
    
    def check_slot_availability(
        self, 
        date: str, 
        time: str, 
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Check if a time slot is available
        
        Args:
            date: Appointment date (YYYY-MM-DD)
            time: Appointment time (HH:MM)
            exclude_id: Appointment ID to exclude (for modifications)
            
        Returns:
            True if slot is available, False otherwise
        """
        try:
            query = self.client.table("appointments").select("id").eq(
                "date", date
            ).eq("time", time).neq("status", "cancelled")
            
            if exclude_id:
                query = query.neq("id", exclude_id)
            
            response = query.execute()
            
            # Slot is available if no appointments found
            is_available = len(response.data) == 0
            logger.info(f"Slot {date} {time} availability: {is_available}")
            return is_available
            
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            raise
    
    def create_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new appointment
        
        Args:
            appointment_data: Dict with appointment details
            
        Returns:
            Created appointment record
        """
        try:
            appointment_data["created_at"] = datetime.now().isoformat()
            
            response = self.client.table("appointments").insert(
                appointment_data
            ).execute()
            
            logger.info(f"Created appointment: {response.data[0]['id']}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise
    
    def get_user_appointments(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all appointments for a user
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of appointment records
        """
        try:
            response = self.client.table("appointments").select("*").eq(
                "user_id", user_id
            ).order("date", desc=False).order("time", desc=False).execute()
            
            logger.info(f"Retrieved {len(response.data)} appointments for user {user_id}")
            return response.data
            
        except Exception as e:
            logger.error(f"Error retrieving appointments: {e}")
            raise
    
    def cancel_appointment(self, appointment_id: str) -> bool:
        """
        Cancel an appointment (mark as cancelled)
        
        Args:
            appointment_id: Appointment UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.table("appointments").update({
                "status": "cancelled"
            }).eq("id", appointment_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"Cancelled appointment: {appointment_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            raise
    
    def modify_appointment(
        self, 
        appointment_id: str, 
        new_date: str, 
        new_time: str
    ) -> bool:
        """
        Modify an appointment's date/time
        
        Args:
            appointment_id: Appointment UUID
            new_date: New date (YYYY-MM-DD)
            new_time: New time (HH:MM)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.table("appointments").update({
                "date": new_date,
                "time": new_time
            }).eq("id", appointment_id).execute()
            
            success = len(response.data) > 0
            if success:
                logger.info(f"Modified appointment {appointment_id} to {new_date} {new_time}")
            return success
            
        except Exception as e:
            logger.error(f"Error modifying appointment: {e}")
            raise
    
    def save_conversation(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save conversation summary and details
        
        Args:
            conversation_data: Dict with conversation details
            
        Returns:
            Created conversation record
        """
        try:
            conversation_data["created_at"] = datetime.now().isoformat()
            
            response = self.client.table("conversations").insert(
                conversation_data
            ).execute()
            
            logger.info(f"Saved conversation: {response.data[0]['id']}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            raise

       
def get_supabase_client() -> SupabaseClient:
    """
    Get the global Supabase singleton instance
    
    Returns:
        The shared SupabaseClient instance
    
    Example:
        from services.supabase_client import get_supabase_client
        
        supabase = get_supabase_client()  # Always returns same instance
        user = supabase.get_or_create_user(phone)
    """
    return SupabaseClient()