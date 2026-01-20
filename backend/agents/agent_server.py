"""
VoiceFlow Voice Agent - Modern LiveKit Agent Implementation
"""


import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from livekit import rtc, api
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
    function_tool,
    RunContext,
    metrics,
)
import logging
logger = logging.getLogger("agent")
logger.info("Agent server initialized")

from livekit.plugins import noise_cancellation, silero, deepgram, cartesia, openai

BEY_AVAILABLE = False
try:
    from livekit.plugins import bey
    BEY_AVAILABLE = True
    logger.info("✓ Beyond Presence plugin available")
except ImportError:
    logger.info("ℹ️ Beyond Presence plugin not installed (avatar will use animated fallback)")
except Exception as e:
    logger.warning(f"⚠️ Could not load Beyond Presence plugin: {e}")

# Load environment variables
load_dotenv(".env.local")
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agent")


class Assistant(Agent):
    """Voice AI Assistant for VoiceFlow appointment booking system"""
    
    def __init__(self, cost_tracker=None, room_name=None) -> None:
        self._room = None  # Will be set when agent starts
        self._cost_tracker = cost_tracker
        self.user_id = None
        self.user_phone = None
        self.room_name = room_name  # Store room name
        self.tool_calls = []
        self.start_time = datetime.now()
        self._summary_generated = False  # Track if summary was already generated
        
        # Initialize conversation history for this instance
        self.conversation_history = []
        
        # Initialize conversation store for this room if not exists
        if room_name and room_name not in CONVERSATION_STORE:
            CONVERSATION_STORE[room_name] = []
            logger.info(f"📝 Created conversation store for room: {room_name}")
        
        super().__init__(
            instructions=f"""You are a helpful and friendly AI voice assistant for VoiceFlow, an appointment booking system.

Your responsibilities:
1. Help users with appointment bookings
2. Identify users by asking for their phone number (only registered users can book)
3. Help registered users book, retrieve, modify, or cancel appointments
4. Provide available time slots when requested
5. Confirm all appointment details before booking

Guidelines:
- Always be polite, patient, and professional
- Speak naturally as if having a real conversation
- IMPORTANT: Only registered users can use the system - if a phone number is not found, politely inform them to register first
- When booking appointments, confirm: date, time, name, and purpose
- **When modifying appointments, DO NOT ask for appointment ID** - automatically use their most recent appointment
- If a slot is unavailable, suggest alternative times
- Keep responses concise but complete (2-3 sentences max per response)
- Your responses should be conversational without complex formatting, emojis, asterisks, or symbols
- Business hours are 9 AM to 5 PM
- Today's date is {datetime.now().strftime("%Y-%m-%d")} and server timezone is {datetime.now().strftime("%Z")}

**CRITICAL - How to End Conversations:**
1. After completing ANY task (booking/cancellation/modification), you MUST:
   - Say "Thank you for using VoiceFlow. Have a great day!"
   - IMMEDIATELY call the end_conversation() function
   - Do this in ONE turn - speak and call function together

2. When user says goodbye/thanks/bye/done:
   - Say "Thank you! Goodbye!"
   - IMMEDIATELY call the end_conversation() function

3. If user is silent, doesn't respond, or says "no" when asked "anything else":
   - IMMEDIATELY call end_conversation() without saying anything
   - DO NOT wait or ask again - just end the call

4. NEVER wait for user response after saying thank you - just end the call

5. NEVER announce you're ending the call - just do it

Example flows:
User: "Book me for 2pm tomorrow"
You: [book appointment] "Your appointment is confirmed for 2 PM tomorrow. Thank you for using VoiceFlow!" [CALL end_conversation() NOW]

User: [silence after task completion]
You: [CALL end_conversation() immediately - no speech]

User: "No" or "Nothing else"
You: [CALL end_conversation() immediately - no speech]

Be curious, friendly, and helpful!""",
        )
    
    def add_to_conversation(self, role: str, content: str):
        """Add a message to conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to instance history
        self.conversation_history.append(message)
        
        # Add to room store
        if self.room_name and self.room_name in CONVERSATION_STORE:
            CONVERSATION_STORE[self.room_name].append(message)
            logger.info(f"💬 {role.capitalize()}: {content[:80]}...")
    
    async def _send_tool_call_to_ui(self, tool_name: str, args: dict, result: dict):
        if not self._room:
            logger.warning("Room not set, cannot send tool call to UI")
            return
        
        tool_call_record = {
            "name": tool_name,
            "args": args,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        self.tool_calls.append(tool_call_record)
            
        event = {
            "type": "tool_call",
            "data": {
                "id": f"{tool_name}_{int(datetime.now().timestamp() * 1000)}",
                "name": tool_name,
                "args": args,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            await self._room.local_participant.publish_data(
                json.dumps(event).encode('utf-8'),
                reliable=True
            )
            logger.info(f"✓ Tool call sent to UI: {tool_name}")
        except Exception as e:
            logger.error(f"Error sending tool call to UI: {e}")

    @function_tool
    async def identify_user(self, context: RunContext, phone_number: str):
        """
        Identify user by their phone number in the system
        Only registered users can use the system - does not create new users
        
        Args:
            phone_number: User's phone number (10 digits)
        
        Returns:
            User information if found, error if not registered
            """
        logger.info(f"🔍 Identifying user with phone: {phone_number}")
    
        try:
            # Use global Supabase singleton
            supabase = GLOBAL_SUPABASE
            
            # Check if user exists (registered users only)
            result = supabase.client.table("users").select("*").eq("contact_number", phone_number).execute()
            
            if result.data and len(result.data) > 0:
                user = result.data[0]
                logger.info(f"✓ User found: {user['id']}")

                self.user_id = user["id"]
                self.user_phone = phone_number
                logger.info(f"✓ User ID stored: {self.user_id}")
                
                response = {
                    "success": True,
                    "user_id": user["id"],
                    "contact_number": user["contact_number"],
                    "name": user.get("name", ""),
                    "message": f"Welcome back{', ' + user.get('name', '') if user.get('name') else ''}! I found your account."
                }
                await self._send_tool_call_to_ui("identify_user", {"phone_number": phone_number}, response)
                return response
            else:
                logger.warning(f"⚠️ User not registered: {phone_number}")
                response = {
                    "success": False,
                    "error": "User not registered",
                    "message": "I'm sorry, but I couldn't find an account with that phone number. Please make sure you're registered in our system before booking appointments."
                }
                await self._send_tool_call_to_ui("identify_user", {"phone_number": phone_number}, response)
                return response
        except Exception as e:
            logger.error(f"Error identifying user: {e}")
            response = {
                "success": False,
                "error": str(e),
                "message": "I'm having trouble accessing the system. Please try again."
            }
            await self._send_tool_call_to_ui("identify_user", {"phone_number": phone_number}, response)
            return response

    @function_tool
    async def fetch_available_slots(self, context: RunContext, date: str):
        """
        Fetch available appointment slots for a specific date
        
        Args:
            date: Date in YYYY-MM-DD format (e.g. 2026-01-20)
        
        Returns:
            List of available time slots
        """
        logger.info(f"📅 Fetching slots for date: {date}")
        
        try:
            supabase = GLOBAL_SUPABASE
            
            result = supabase.client.table("appointments")\
                .select("time")\
                .eq("date", date)\
                .eq("status", "confirmed")\
                .execute()
            
            all_slots = []
            for hour in range(9, 17):
                for minute in [0, 30]:
                    all_slots.append(f"{hour:02d}:{minute:02d}")
            
            booked_times = [appt["time"] for appt in result.data] if result.data else []
            available_slots = [slot for slot in all_slots if slot not in booked_times]
            
            logger.info(f"✓ Found {len(available_slots)} available slots")
            response = {
                "success": True,
                "date": date,
                "available_slots": available_slots,
                "total_slots": len(available_slots),
                "message": f"I found {len(available_slots)} available time slots for {date}"
            }
            await self._send_tool_call_to_ui("fetch_slots", {"date": date}, response)
            return response
        except Exception as e:
            logger.error(f"Error fetching slots: {e}")
            response = {
                "success": False,
                "error": str(e),
                "message": "I couldn't fetch available slots. Please try again."
            }
            await self._send_tool_call_to_ui("fetch_slots", {"date": date}, response)
            return response

    @function_tool
    async def book_appointment(
        self, 
        context: RunContext, 
        phone_number: str,
        date: str, 
        time: str, 
        name: str, 
        purpose: str = "General"
    ):
        """
        Book an appointment for the user
        
        Args:
            phone_number: User's phone number
            date: Appointment date (YYYY-MM-DD)
            time: Appointment time (HH:MM in 24hr format)
            name: Patient/client name
            purpose: Purpose of appointment
        
        Returns:
            Booking confirmation with appointment ID
        """
        logger.info(f"📝 Booking appointment: {date} {time} for {name}")
        
        try:
            # Use global Supabase singleton
            supabase = GLOBAL_SUPABASE

            user_result = supabase.client.table("users").select("*").eq("contact_number", phone_number).execute()
            
            if not user_result.data:
                logger.warning(f"⚠️ Attempted booking by unregistered user: {phone_number}")
                return {
                    "success": False,
                    "message": "I couldn't find your account. Please make sure you're registered before booking appointments."
                }
            
            user_id = user_result.data[0]["id"]
            user_email = user_result.data[0].get("email")  # Get email if available
            
            # Check if slot is available
            existing = supabase.client.table("appointments")\
                .select("*")\
                .eq("date", date)\
                .eq("time", time)\
                .eq("status", "confirmed")\
                .execute()
            
            if existing.data:
                logger.warning("⚠️ Slot already booked")
                response = {
                    "success": False,
                    "message": f"Sorry, the slot at {time} on {date} is already booked. Would you like to choose another time?"
                }
                await self._send_tool_call_to_ui("book_appointment", {
                    "phone_number": phone_number, "date": date, "time": time, "name": name, "purpose": purpose
                }, response)
                return response
            
            # Book appointment in database
            appointment = supabase.client.table("appointments").insert({
                "user_id": user_id,
                "date": date,
                "time": time,
                "name": name,
                "contact_number": phone_number,  # Store contact for reference
                "purpose": purpose,
                "status": "confirmed"
            }).execute()
            
            appointment_id = appointment.data[0]['id']
            logger.info(f"✓ Appointment booked in database: {appointment_id}")

            calendar_event_id = None
            calendar_link = None
            
            try:
                logger.info("📅 Adding appointment to Google Calendar...")
                calendar_result = await GOOGLE_CALENDAR.create_appointment_event(
                    name=name,
                    date=date,
                    time=time,
                    purpose=purpose,
                    phone=phone_number,
                    duration_minutes=30,  # Default 30 min appointments
                    attendee_email=user_email  # Send invite if email available
                )
                
                if calendar_result.get("success"):
                    calendar_event_id = calendar_result.get("event_id")
                    calendar_link = calendar_result.get("event_link")
                    logger.info(f"✓ Calendar event created: {calendar_event_id}")
                    
                    # Update database with calendar event ID
                    try:
                        supabase.client.table("appointments")\
                            .update({"calendar_event_id": calendar_event_id})\
                            .eq("id", appointment_id)\
                            .execute()
                    except Exception as db_error:
                        logger.warning(f"Could not save calendar_event_id to DB: {db_error}")
                else:
                    logger.warning(f"⚠️ Calendar event creation failed: {calendar_result.get('message')}")
                    
            except Exception as cal_error:
                logger.warning(f"⚠️ Google Calendar integration error: {cal_error}")
                logger.info("   Appointment still booked successfully in database")
            
            response = {
                "success": True,
                "appointment_id": appointment_id,
                "date": date,
                "time": time,
                "name": name,
                "purpose": purpose,
                "calendar_event_id": calendar_event_id,
                "calendar_link": calendar_link,
                "message": f"Perfect! I've booked your appointment for {name} on {date} at {time} for {purpose}." + 
                           (" It's also been added to Google Calendar." if calendar_event_id else "")
            }
            await self._send_tool_call_to_ui("book_appointment", {
                "phone_number": phone_number, "date": date, "time": time, "name": name, "purpose": purpose
            }, response)
            return response
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            response = {
                "success": False,
                "error": str(e),
                "message": "I couldn't complete the booking. Please try again."
            }
            await self._send_tool_call_to_ui("book_appointment", {
                "phone_number": phone_number, "date": date, "time": time, "name": name, "purpose": purpose
            }, response)
            return response

    @function_tool
    async def get_appointments(self, context: RunContext, phone_number: str):
        """
        Retrieve all appointments for a user
        
        Args:
            phone_number: User's phone number
        
        Returns:
            List of user's appointments
        """
        logger.info(f"📋 Fetching appointments for phone: {phone_number}")
        
        try:
            # Use global Supabase singleton
            supabase = GLOBAL_SUPABASE
            
            user_result = supabase.client.table("users").select("*").eq("contact_number", phone_number).execute()
            
            if not user_result.data:
                response = {
                    "success": False,
                    "message": "I couldn't find any account with that phone number."
                }
                await self._send_tool_call_to_ui("retrieve_appointments", {"phone_number": phone_number}, response)
                return response
            
            user_id = user_result.data[0]["id"]
            
            # Get appointments
            appointments = supabase.client.table("appointments")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("status", "confirmed")\
                .order("date", desc=False)\
                .execute()
            
            count = len(appointments.data) if appointments.data else 0
            logger.info(f"✓ Found {count} appointments")
            
            response = {
                "success": True,
                "appointments": appointments.data or [],
                "count": count,
                "total": count,
                "message": f"You have {count} appointment(s)." if count > 0 else "You don't have any appointments scheduled."
            }
            await self._send_tool_call_to_ui("retrieve_appointments", {"phone_number": phone_number}, response)
            return response
        except Exception as e:
            logger.error(f"Error fetching appointments: {e}")
            response = {
                "success": False,
                "error": str(e),
                "message": "I couldn't retrieve your appointments. Please try again."
            }
            await self._send_tool_call_to_ui("retrieve_appointments", {"phone_number": phone_number}, response)
            return response

    @function_tool
    async def cancel_appointment(self, context: RunContext, appointment_id: str):
        """
        Cancel an existing appointment
        
        Args:
            appointment_id: UUID of the appointment to cancel
        
        Returns:
            Cancellation confirmation
        """
        logger.info(f"❌ Cancelling appointment: {appointment_id}")
        
        try:
            supabase = GLOBAL_SUPABASE
            
            # Get appointment details first (to get calendar_event_id)
            appointment = supabase.client.table("appointments")\
                .select("*")\
                .eq("id", appointment_id)\
                .single()\
                .execute()
            
            if not appointment.data:
                response = {
                    "success": False,
                    "message": "I couldn't find that appointment. Please check the appointment ID."
                }
                await self._send_tool_call_to_ui("cancel_appointment", {"appointment_id": appointment_id}, response)
                return response
            
            calendar_event_id = appointment.data.get("calendar_event_id")
            
            # Cancel in database
            result = supabase.client.table("appointments")\
                .update({"status": "cancelled"})\
                .eq("id", appointment_id)\
                .execute()
            
            if result.data:
                logger.info("✓ Appointment cancelled in database")
                
                # Cancel in Google Calendar if event ID exists
                if calendar_event_id:
                    try:
                        logger.info(f"📅 Cancelling Google Calendar event: {calendar_event_id}")
                        calendar_result = await GOOGLE_CALENDAR.cancel_appointment_event(calendar_event_id)
                        
                        if calendar_result.get("success"):
                            logger.info("✓ Calendar event cancelled")
                        else:
                            logger.warning(f"⚠️ Could not cancel calendar event: {calendar_result.get('message')}")
                    except Exception as cal_error:
                        logger.warning(f"⚠️ Google Calendar cancellation error: {cal_error}")
                
                response = {
                    "success": True,
                    "message": "I've cancelled your appointment successfully." + 
                               (" It's also been removed from Google Calendar." if calendar_event_id else "")
                }
                await self._send_tool_call_to_ui("cancel_appointment", {"appointment_id": appointment_id}, response)
                return response
            else:
                response = {
                    "success": False,
                    "message": "I couldn't find that appointment. Please check the appointment ID."
                }
                await self._send_tool_call_to_ui("cancel_appointment", {"appointment_id": appointment_id}, response)
                return response
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            response = {
                "success": False,
                "error": str(e),
                "message": "I couldn't cancel the appointment. Please try again."
            }
            await self._send_tool_call_to_ui("cancel_appointment", {"appointment_id": appointment_id}, response)
            return response

    @function_tool
    async def modify_appointment(
        self, 
        context: RunContext, 
        new_date: str, 
        new_time: str
    ):
        """
        Modify/reschedule the user's appointment - automatically finds their appointment
        
        Args:
            new_date: New appointment date (YYYY-MM-DD format, e.g., 2026-01-25)
            new_time: New appointment time (HH:MM 24-hour format, e.g., 14:30)
        
        Returns:
            Modification confirmation or error
        """
        logger.info(f"✏️ Modifying appointment to {new_date} at {new_time}")
        
        if not self.user_id:
            return {
                "success": False,
                "message": "Please identify yourself first before modifying appointments."
            }
        
        try:
            # Use global Supabase singleton
            supabase = GLOBAL_SUPABASE
            
            from agents.tools import modify_appointment as modify_appt_tool

            result = await modify_appt_tool(
                user_id=self.user_id,
                new_date=new_date,
                new_time=new_time,
                supabase=supabase
            )
            
            await self._send_tool_call_to_ui("modify_appointment", {
                "new_date": new_date, 
                "new_time": new_time
            }, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error modifying appointment: {e}")
            response = {
                "success": False,
                "error": str(e),
                "message": "I couldn't modify the appointment. Please try again."
            }
            await self._send_tool_call_to_ui("modify_appointment", {
                "new_date": new_date, "new_time": new_time
            }, response)
            return response

    @function_tool
    async def end_conversation(self, context: RunContext):
        """
        End the conversation and generate a comprehensive summary
        Uses LiveKit's session.history for conversation tracking
        Reference: https://docs.livekit.io/deploy/observability/data/
        
        Args:
            context: RunContext object containing the conversation history
        
        Returns:
            Conversation summary with cost breakdown - triggers UI to end call
        """
        # Prevent duplicate summary generation
        if self._summary_generated:
            logger.warning("⚠️ Summary already generated, skipping...")
            return {"success": False, "error": "Summary already generated"}
        
        logger.info("👋 Ending conversation and generating summary...")
        
        try:
            from agents.tools import end_conversation as end_conv_tool
            
            conversation_to_use = []
            
            # Priority 1: Use LiveKit's built-in session.history (OFFICIAL METHOD)
            if hasattr(self, '_session') and self._session and hasattr(self._session, 'history'):
                try:
                    history = self._session.history
                    logger.info(f"✓ Found session.history object")
                    
                    # Convert history to dict format
                    if hasattr(history, 'to_dict'):
                        history_dict = history.to_dict()
                        logger.info(f"📊 History dict keys: {history_dict.keys()}")
                        
                        # Extract conversation items
                        if 'items' in history_dict:
                            items = history_dict['items']
                            logger.info(f"✓ Found {len(items)} conversation items in session.history")
                            
                            for item in items:
                                role = item.get('role', 'unknown')
                                
                                # Extract content from different possible formats
                                content = ""
                                if 'content' in item:
                                    if isinstance(item['content'], str):
                                        content = item['content']
                                    elif isinstance(item['content'], list):
                                        content_parts = []
                                        for part in item['content']:
                                            if isinstance(part, dict) and 'text' in part:
                                                content_parts.append(part['text'])
                                            elif isinstance(part, str):
                                                content_parts.append(part)
                                        content = " ".join(content_parts)
                                elif 'text' in item:
                                    content = item['text']
                                elif 'message' in item:
                                    content = item['message']
                                
                                if content and content.strip():
                                    conversation_to_use.append({
                                        "role": role,
                                        "content": content,
                                        "timestamp": item.get('timestamp', datetime.now().isoformat())
                                    })
                            
                            logger.info(f"✓ Extracted {len(conversation_to_use)} messages from session.history")
                        
                        elif 'messages' in history_dict:
                            messages = history_dict['messages']
                            logger.info(f"✓ Found {len(messages)} messages in session.history")
                            
                            for msg in messages:
                                role = msg.get('role', 'unknown')
                                content = msg.get('content', '') or msg.get('text', '')
                                
                                if content and content.strip():
                                    conversation_to_use.append({
                                        "role": role,
                                        "content": str(content),
                                        "timestamp": msg.get('timestamp', datetime.now().isoformat())
                                    })
                            
                            logger.info(f"✓ Extracted {len(conversation_to_use)} messages from session.history")
                    
                    # If to_dict didn't work, try direct access
                    elif hasattr(history, 'items'):
                        items = history.items
                        logger.info(f"✓ Found {len(items)} items via direct access")
                        
                        for item in items:
                            role = getattr(item, 'role', 'unknown')
                            content = getattr(item, 'content', '') or getattr(item, 'text', '')
                            
                            if isinstance(content, list):
                                content_parts = []
                                for part in content:
                                    if hasattr(part, 'text'):
                                        content_parts.append(part.text)
                                    elif isinstance(part, dict) and 'text' in part:
                                        content_parts.append(part['text'])
                                content = " ".join(content_parts)
                            
                            if content and str(content).strip():
                                conversation_to_use.append({
                                    "role": role,
                                    "content": str(content),
                                    "timestamp": datetime.now().isoformat()
                                })
                        
                        logger.info(f"✓ Extracted {len(conversation_to_use)} messages via direct access")
                    
                except Exception as history_error:
                    logger.error(f"❌ Error accessing session.history: {history_error}", exc_info=True)
            
            # Priority 2: Fallback to room store (from event listeners)
            if len(conversation_to_use) == 0 and self.room_name and self.room_name in CONVERSATION_STORE:
                conversation_to_use = CONVERSATION_STORE[self.room_name]
                logger.info(f"📊 Retrieved {len(conversation_to_use)} messages from room store (fallback)")
            
            # Priority 3: Fallback to instance conversation history
            if len(conversation_to_use) == 0 and hasattr(self, 'conversation_history') and self.conversation_history:
                conversation_to_use = self.conversation_history
                logger.info(f"📊 Retrieved {len(conversation_to_use)} messages from instance (fallback)")
            
            logger.info(f"📊 Summary will use {len(conversation_to_use)} conversation messages")
            
            # If still no conversation, log diagnostic info
            if len(conversation_to_use) == 0:
                logger.warning("⚠️ Could not find any conversation messages!")
                logger.warning(f"   Room store keys: {list(CONVERSATION_STORE.keys())}")
                logger.warning(f"   Instance history length: {len(self.conversation_history) if hasattr(self, 'conversation_history') else 'N/A'}")
                if hasattr(self, '_session'):
                    logger.warning(f"   Session has history attr: {hasattr(self._session, 'history')}")
                    if hasattr(self._session, 'history'):
                        logger.warning(f"   Session history type: {type(self._session.history)}")
                        logger.warning(f"   Session history attributes: {dir(self._session.history)}")
            
            result = await end_conv_tool(
                user_id=self.user_id,
                conversation_history=conversation_to_use,
                tool_calls=self.tool_calls,
                start_time=self.start_time,
                supabase=GLOBAL_SUPABASE,
                llm=None,
                cost_tracker=self._cost_tracker
            )
            
            logger.info(f"📊 Summary generation result: success={result.get('success')}")
            
            if result.get("success"):
                self._summary_generated = True
                
                # Clear the conversation stores
                if self.room_name and self.room_name in CONVERSATION_STORE:
                    msg_count = len(CONVERSATION_STORE[self.room_name])
                    CONVERSATION_STORE.pop(self.room_name)
                    logger.info(f"🧹 Cleared {msg_count} messages from room {self.room_name}")
                
                self.conversation_history.clear()
                
                summary_data = result.get("summary", {})
                
                logger.info(f"📋 Summary data keys: {summary_data.keys()}")
                logger.info(f"📝 Conversation messages used: {len(conversation_to_use)}")
                logger.info(f"🔧 Tool calls: {len(self.tool_calls)}")
                logger.info(f"💰 Total cost: ${summary_data.get('cost_breakdown', {}).get('total_usd', 0):.4f}")
                
                # Send summary to UI
                message_to_send = {
                    "type": "end_call",
                    "summary": summary_data,
                    "timestamp": datetime.now().isoformat()
                }
                
                try:
                    if self._room and self._room.local_participant:
                        # Send summary via data channel
                        await self._room.local_participant.publish_data(
                            json.dumps(message_to_send).encode('utf-8'),
                            reliable=True
                        )
                        logger.info("Summary sent via data channel")
                        
                        # Also send via tool_call message (backup method)
                        await self._send_tool_call_to_ui("end_conversation", {}, {
                            "success": True,
                            "summary": summary_data,
                            "message": "Thank you for using VoiceFlow! Your summary is ready."
                        })
                        logger.info("Summary sent via tool_call message")
                        
                        # Wait a moment to ensure message is delivered
                        import asyncio
                        await asyncio.sleep(1)
                        logger.info("Summary delivery confirmed - call ending")
                    else:
                        logger.error("❌ Cannot send summary - room or participant not available")
                except Exception as send_error:
                    logger.error(f"Error sending summary: {send_error}", exc_info=True)
                
                return result
            else:
                logger.error(f"Error generating summary: {result.get('error')}")
                return result
                
        except Exception as e:
            logger.error(f"Error ending conversation: {e}", exc_info=True)
            response = {
                "success": False,
                "error": str(e),
                "message": "Could not generate summary, but thank you for calling!"
            }
            await self._send_tool_call_to_ui("end_conversation", {}, response)
            return response


from agents.avatar_manager import get_avatar_session
from db.supabase_client import get_supabase_client
from services.google_calendar import get_google_calendar_service
from livekit.agents import WorkerOptions, WorkerType

GLOBAL_AVATAR = get_avatar_session()
GLOBAL_SUPABASE = get_supabase_client()
GOOGLE_CALENDAR = get_google_calendar_service()

# Global conversation store - key is room_name, value is list of messages
CONVERSATION_STORE = {}

logger.info("Global avatar singleton initialized (shared across ALL rooms)")
logger.info("Global Supabase singleton initialized (shared across ALL rooms)")
logger.info(f"Google Calendar integration: {'Enabled' if GOOGLE_CALENDAR.is_enabled() else 'Disabled'}")

# Initialize AgentServer with threading for shared memory
server = AgentServer()


def prewarm(proc: JobProcess):
    """
    Prewarm models for faster response
    """
    import threading
    thread_id = threading.current_thread().name
    
    proc.userdata["vad"] = silero.VAD.load()
    proc.userdata["thread_id"] = thread_id
    
    logger.info(f"Thread {thread_id} prewarmed")
    logger.info(f"  Using GLOBAL avatar singleton (shared across ALL threads/rooms)")


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    """
    Main agent entry point
    """
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    logger.info(f"Agent starting for room: {ctx.room.name}")
    
    from services.cost_tracker import CostTracker
    
    cost_tracker = CostTracker(room=ctx.room)
    
    # Use the global avatar singleton (shared across all threads/rooms!)
    import threading
    thread_name = threading.current_thread().name
    logger.info(f"   Thread: {thread_name}")
    logger.info(f"   Using GLOBAL avatar singleton (shared across ALL rooms)")

    timing_start = time.time()
    phase_times = {}
    
    def log_phase(phase_name: str):
        """Log time taken for a phase"""
        elapsed = time.time() - timing_start
        phase_times[phase_name] = elapsed
        logger.info(f"{phase_name}: {elapsed:.2f}s")
        return elapsed

    avatar_session = None
    is_new_avatar = False
    bey_api_key = os.getenv("BEY_API_KEY")
    bey_avatar_id = os.getenv("BEY_AVATAR_ID")
    
    if bey_api_key and bey_avatar_id:
        if not BEY_AVAILABLE:
            logger.warning("Avatar credentials found but plugin not installed!")
            logger.warning("   Run: pip install livekit-plugins-bey")
            logger.warning("   Continuing with animated fallback...")
        else:
            # Avatar will be initialized after room connection
            pass
    else:
        logger.info("Avatar not configured (using animated fallback)")
        if not bey_api_key:
            logger.info("   Missing: BEY_API_KEY")
        if not bey_avatar_id:
            logger.info("   Missing: BEY_AVATAR_ID")

    # Step 1: Connect to room FIRST (following official example)
    timing_start = time.time()
    await ctx.connect()
    log_phase("Room connection")
    logger.info("Agent connected to room")

    # Set up voice AI pipeline
    if ctx.proc.userdata["vad"] is None:
        logger.info("Loading VAD model on demand...")
        ctx.proc.userdata["vad"] = silero.VAD.load()
        logger.info("VAD loaded")
    
    session = AgentSession(
        # Speech-to-text - Deepgram Nova-2 (Direct API)
        stt=deepgram.STT(model="nova-2", language="en-US"),
        
        # Large Language Model - Direct OpenAI (bypasses LiveKit gateway)
        llm=openai.LLM(model="gpt-4o-mini"),
        
        # Text-to-speech - Direct Cartesia (bypasses LiveKit gateway)
        tts=cartesia.TTS(
            model="sonic-english",  # Cartesia's Sonic model
            voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"  # Friendly female voice
        ),
        
        # VAD for voice activity detection
        vad=ctx.proc.userdata["vad"],
        
        # Allow preemptive generation for faster responses
        preemptive_generation=True,
    )
    usage_collector = metrics.UsageCollector()
    
    @session.on("metrics_collected")
    def handle_metrics(event):
        """
        Handle metrics collected events for cost tracking
        
        Metrics from LiveKit are CUMULATIVE (total since session start),
        so we need to track deltas to avoid double-counting.
        """
        try:
            event_metrics = event.metrics
            usage_collector.collect(event_metrics)
            
            # Get cumulative summary
            summary = usage_collector.get_summary()
            
            # Use the cumulative metrics handler to calculate deltas
            cost_tracker.track_from_cumulative_metrics(summary)
            
        except Exception as e:
            logger.error(f"❌ Error handling metrics: {e}", exc_info=True)

    # Create assistant agent
    assistant = Assistant(cost_tracker=cost_tracker, room_name=ctx.room.name)
    assistant._room = ctx.room
    
    # Store reference to session for later access
    assistant._session = session
    
    # Use LiveKit's built-in conversation tracking events
    # Reference: https://docs.livekit.io/deploy/observability/data/
    
    @session.on("user_input_transcribed")
    def on_user_transcribed(event):
        """Track when user speech is transcribed - fires for each user utterance"""
        try:
            logger.debug(f"🎤 User input transcribed event: {event}")
            # Extract the transcribed text
            text = ""
            if hasattr(event, 'text'):
                text = event.text
            elif hasattr(event, 'transcript'):
                text = event.transcript
            elif hasattr(event, 'content'):
                text = event.content
            else:
                logger.debug(f"   Event attributes: {dir(event)}")
                text = str(event)
            
            if text and text.strip():
                assistant.add_to_conversation("user", text)
                logger.info(f"✓ Stored user message: {len(text)} chars")
        except Exception as e:
            logger.error(f"❌ Error in user_input_transcribed handler: {e}", exc_info=True)
    
    @session.on("conversation_item_added")
    def on_conversation_item(event):
        """Track conversation items as they're added - fires for both user and assistant"""
        try:
            logger.debug(f"💬 Conversation item added: {event}")
            # Extract role and content from the conversation item
            item = event.item if hasattr(event, 'item') else event
            
            role = getattr(item, 'role', None)
            content = ""
            
            # Try different content attributes
            if hasattr(item, 'content'):
                if isinstance(item.content, str):
                    content = item.content
                elif isinstance(item.content, list):
                    # Content might be a list of parts
                    content_parts = []
                    for part in item.content:
                        if hasattr(part, 'text'):
                            content_parts.append(part.text)
                        elif isinstance(part, dict) and 'text' in part:
                            content_parts.append(part['text'])
                        elif isinstance(part, str):
                            content_parts.append(part)
                    content = " ".join(content_parts)
            elif hasattr(item, 'text'):
                content = item.text
            elif hasattr(item, 'message'):
                content = item.message
            
            if role and content and content.strip():
                assistant.add_to_conversation(role, content)
                logger.info(f"✓ Stored {role} message: {len(content)} chars")
        except Exception as e:
            logger.error(f"❌ Error in conversation_item_added handler: {e}", exc_info=True)
    
    # Step 2: Start agent session (FAST - usually <1 second)
    logger.info("🚀 Starting agent session...")
    timing_start = time.time()
    
    await session.start(
        agent=assistant, 
        room=ctx.room
    )
    log_phase("AgentSession start")
    logger.info("Agent session started")
    
    @ctx.room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        """Handle data messages from frontend"""
        try:
            import asyncio
            message = json.loads(data.data.decode('utf-8'))
            
            if message.get("type") == "end_call_request":
                logger.info("📞 Frontend requested call end - generating summary...")
                
                async def trigger_end_conversation():
                    try:
                        result = await assistant.end_conversation(None)
                        logger.info("Summary generated and sent to frontend")
                    except Exception as e:
                        logger.error(f" Error generating summary: {e}", exc_info=True)
                
                asyncio.create_task(trigger_end_conversation())
                
        except Exception as e:
            logger.error(f"Error handling data message: {e}")
    
    avatar_session = None
    is_new_avatar = False
    
    if bey_api_key and bey_avatar_id and BEY_AVAILABLE:
        timing_start = time.time()
        logger.info("Getting global avatar session...")
        
        avatar_session, is_new_avatar = await GLOBAL_AVATAR.get_or_create(
            avatar_id=bey_avatar_id,
            room=ctx.room,
            agent_session=session,
            participant_identity="agent_avatar",
            participant_name="VoiceFlow Assistant"
        )
        
        log_phase(f"Avatar {'creation' if is_new_avatar else 'reuse'}")
        
        if avatar_session:
            if is_new_avatar:
                logger.info("NEW avatar created (first call EVER, connecting in background...)")
                logger.info("  Note: First call ~10-20s, ALL future calls instant!")
            else:
                logger.info("REUSING GLOBAL avatar (instant across ALL rooms!)")
                stats = GLOBAL_AVATAR.get_stats()
                logger.info(f"  Stats: {stats}")
        else:
            logger.warning("Avatar unavailable, using animated fallback")
    
    # Step 4: Send greeting immediately (don't wait for avatar!)
    logger.info("Sending automatic greeting NOW...")
    timing_start = time.time()
    
    try:
        greeting_text = "Hello! Welcome to VoiceFlow. I'm Klara ready to help you with appointment bookings. How can I assist you today?"
        
        logger.info(f"Synthesizing greeting...")
        
        await session.say(greeting_text)
        
        log_phase("Greeting TTS generation")
        logger.info("Greeting sent!")
        
        # Log total startup time
        total_time = sum(phase_times.values())
        logger.info(f"Total startup time: {total_time:.2f}s")
        logger.info(f"   Breakdown: {phase_times}")
            
    except Exception as e:
        logger.error(f"Error sending greeting: {e}", exc_info=True)
    
    logger.info("Agent ready and listening")

    @ctx.room.on("disconnected")
    def on_room_disconnected():
        """Generate summary when room is disconnected"""
        logger.info("Room disconnected - checking if summary was generated...")
        # The finally block will handle the summary generation
    
    import asyncio
    connection_start = datetime.now()
    update_interval = 120  
    
    try:
        # Monitor connection and periodically update costs (silently)
        while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(update_interval)
            
            # Calculate elapsed time since last update
            elapsed_minutes = (datetime.now() - connection_start).total_seconds() / 60.0
            
            # Update costs silently (removed logging)
            cost_tracker.track_connection_time(elapsed_minutes)
            
            # Update avatar cost if active
            if avatar_session:
                cost_tracker.track_avatar_time(elapsed_minutes)
            
            # Send cost update to frontend
            await cost_tracker._send_cost_update()
            
            # Reset connection start for next interval
            connection_start = datetime.now()
            
    except Exception as e:
        logger.error(f"Error in connection monitoring: {e}", exc_info=True)
    
    finally:
        logger.info("Call ending - generating comprehensive summary...")
        
        # Generate conversation summary
        if not assistant._summary_generated:
            try:
                logger.info("Generating conversation summary on disconnect...")
                
                # Use asyncio.wait_for to ensure summary generation completes quickly
                import asyncio
                result = await asyncio.wait_for(
                    assistant.end_conversation(None),
                    timeout=10.0  # Max 10 seconds for summary
                )
                
                if result.get("success"):
                    logger.info("Summary generated and sent successfully")
                else:
                    logger.error(f"Summary generation failed: {result.get('error')}")
                    
            except asyncio.TimeoutError:
                logger.error("Summary generation timed out after 10 seconds")
            except Exception as e:
                logger.error(f"Error generating summary on disconnect: {e}", exc_info=True)
        else:
            logger.info("Summary already generated earlier")
        
        # Send final cost summary
        final_costs = cost_tracker.get_total()
        logger.info(f"Total session cost: ${final_costs['total_usd']:.4f}")
        
        # Send final cost data to frontend (if connection still available)
        try:
            if ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                event = {
                    "type": "call_summary",
                    "data": {
                        "costs": final_costs,
                        "duration_minutes": cost_tracker.get_session_duration(),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                await ctx.room.local_participant.publish_data(
                    json.dumps(event).encode('utf-8'),
                    reliable=True
                )
        except Exception as e:
            logger.debug(f"Could not send final cost update: {e}")


from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VoiceFlow Voice Agent API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "VoiceFlow Voice Agent"}


@app.post("/api/get-token")
async def get_token(request: Request):
    """
    Generate LiveKit token for client connection
    
    """
    try:
        body = await request.json()
        room_name = body.get("room_name", f"room-{os.urandom(8).hex()}")
        participant_name = body.get("participant_name", "user")

        # Create token
        token = api.AccessToken(
            os.getenv("LIVEKIT_API_KEY"),
            os.getenv("LIVEKIT_API_SECRET")
        )
        token.with_identity(participant_name)
        token.with_name(participant_name)
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
            )
        )

        jwt_token = token.to_jwt()

        logger.info(f"Token generated for room: {room_name}")
        return {
            "token": jwt_token,
            "url": os.getenv("LIVEKIT_URL"),
            "room_name": room_name
        }
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        # Start FastAPI server for token generation
        import uvicorn
        logger.info("Starting FastAPI Token Server...")
        logger.info(f"Server will run on http://0.0.0.0:{os.getenv('PORT', 8000)}")
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    else:
        # Start LiveKit agent worker (pass through to LiveKit CLI)
        logger.info("Starting LiveKit Agent Worker (Threading Mode)")
        logger.info("=" * 60)
        logger.info("THREADING MODE ENABLED:")
        logger.info("  • ALL rooms share ONE avatar instance")
        logger.info("  • First room: ~10-15s | All other rooms: <1s")
        logger.info("  • True global singleton across ALL threads")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Required environment variables:")
        logger.info("  LIVEKIT_URL")
        logger.info("  LIVEKIT_API_KEY")
        logger.info("  LIVEKIT_API_SECRET")
        logger.info("  OPENAI_API_KEY")
        logger.info("  DEEPGRAM_API_KEY")
        logger.info("  CARTESIA_API_KEY")
        logger.info("  SUPABASE_URL")
        logger.info("  SUPABASE_KEY")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Note: Use 'dev' for development or 'connect' for production")
        logger.info("")
        
        # Run the server (uses threading by default for @server.rtc_session())
        cli.run_app(server)