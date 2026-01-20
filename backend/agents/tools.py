"""
Tool functions for the voice assistant
"""

import re
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


async def identify_user(phone_number: str, supabase) -> Dict[str, Any]:
    """
    Identify or create user by phone number
    
    Args:
        phone_number: User's phone number
        supabase: Supabase client instance
        
    Returns:
        Dict with user_id and phone
    """
    try:
        # Validate phone number
        cleaned_phone = re.sub(r'[^\d+]', '', phone_number)
        if len(cleaned_phone) < 10:
            return {"error": "Invalid phone number. Please provide at least 10 digits."}
        
        # Get or create user (synchronous call)
        user = supabase.get_or_create_user(cleaned_phone)
        
        return {
            "success": True,
            "user_id": user["id"],
            "phone": cleaned_phone,
            "message": f"User identified with phone number {cleaned_phone}"
        }
    except Exception as e:
        logger.error(f"Error identifying user: {e}")
        return {"error": str(e)}


async def fetch_slots(date: str) -> Dict[str, Any]:
    """
    Fetch available appointment slots for a date
    (Hardcoded slots as per requirements)
    
    Args:
        date: Date in YYYY-MM-DD format
        
    Returns:
        Dict with available slots
    """
    try:
        # Validate date format
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return {"error": "Invalid date format. Please use YYYY-MM-DD"}
        
        # Check if date is in the past
        if date_obj.date() < datetime.now().date():
            return {"error": "Cannot fetch slots for past dates"}
        
        # Hardcoded available slots (9 AM - 5 PM, hourly)
        all_slots = [
            "09:00", "10:00", "11:00", "12:00",
            "13:00", "14:00", "15:00", "16:00", "17:00"
        ]
        
        # Simulate some slots being unavailable
        # In production, check database for booked slots
        day_of_week = date_obj.weekday()
        
        # Weekend - fewer slots
        if day_of_week >= 5:
            available_slots = ["09:00", "10:00", "11:00", "14:00", "15:00"]
        else:
            # Weekday - most slots available
            available_slots = all_slots
        
        return {
            "success": True,
            "date": date,
            "available_slots": available_slots,
            "total_slots": len(available_slots)
        }
    except Exception as e:
        logger.error(f"Error fetching slots: {e}")
        return {"error": str(e)}


async def book_appointment(
    user_id: str,
    phone: str,
    date: str,
    time: str,
    name: str,
    purpose: str,
    supabase
) -> Dict[str, Any]:
    """
    Book an appointment for a user
    
    Args:
        user_id: User's UUID
        phone: User's phone number
        date: Appointment date (YYYY-MM-DD)
        time: Appointment time (HH:MM)
        name: Patient/client name
        purpose: Purpose of appointment
        supabase: Supabase client
        
    Returns:
        Dict with booking confirmation or error
    """
    try:
        # Validate date and time
        try:
            appt_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return {"error": "Invalid date or time format"}
        
        # Check if appointment is in the past
        if appt_datetime < datetime.now():
            return {"error": "Cannot book appointments in the past"}
        
        # Check business hours (9 AM - 5 PM)
        if not (9 <= appt_datetime.hour <= 17):
            return {"error": "Appointments only available between 9 AM and 5 PM"}
        
        # Check if slot is available
        is_available = supabase.check_slot_availability(date, time)
        if not is_available:
            return {
                "error": f"The slot at {time} on {date} is already booked. Please choose another time."
            }
        
        # Create appointment
        appointment = supabase.create_appointment({
            "user_id": user_id,
            "date": date,
            "time": time,
            "name": name,
            "purpose": purpose,
            "status": "confirmed"
        })
        
        return {
            "success": True,
            "appointment_id": appointment["id"],
            "date": date,
            "time": time,
            "name": name,
            "purpose": purpose,
            "message": f"Appointment booked successfully for {name} on {date} at {time}"
        }
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        return {"error": str(e)}


async def retrieve_appointments(user_id: str, supabase) -> Dict[str, Any]:
    """
    Retrieve all appointments for a user
    
    Args:
        user_id: User's UUID
        supabase: Supabase client
        
    Returns:
        Dict with list of appointments
    """
    try:
        appointments = supabase.get_user_appointments(user_id)
        
        # Format appointments for better readability
        formatted_appointments = []
        for appt in appointments:
            formatted_appointments.append({
                "id": appt["id"],
                "date": appt["date"],
                "time": appt["time"],
                "name": appt["name"],
                "purpose": appt["purpose"],
                "status": appt["status"]
            })
        
        return {
            "success": True,
            "appointments": formatted_appointments,
            "total": len(formatted_appointments)
        }
    except Exception as e:
        logger.error(f"Error retrieving appointments: {e}")
        return {"error": str(e)}


async def cancel_appointment(appointment_id: str, supabase) -> Dict[str, Any]:
    """
    Cancel an appointment
    
    Args:
        appointment_id: Appointment UUID
        supabase: Supabase client
        
    Returns:
        Dict with cancellation confirmation
    """
    try:
        # Update appointment status to cancelled
        result = supabase.cancel_appointment(appointment_id)
        
        if result:
            return {
                "success": True,
                "appointment_id": appointment_id,
                "message": "Appointment cancelled successfully"
            }
        else:
            return {"error": "Appointment not found"}
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        return {"error": str(e)}


async def modify_appointment(
    user_id: str,
    new_date: str,
    new_time: str,
    supabase,
    appointment_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Modify an existing appointment - automatically finds the most recent appointment
    
    Args:
        user_id: User's UUID (to find their appointments)
        new_date: New date (YYYY-MM-DD)
        new_time: New time (HH:MM)
        supabase: Supabase client
        appointment_id: Optional specific appointment ID (if known)
        
    Returns:
        Dict with modification confirmation
    """
    try:
        # If no appointment_id provided, find the user's most recent upcoming appointment
        if not appointment_id:
            logger.info(f"🔍 Auto-detecting appointment for user {user_id}")
            
            # Get user's upcoming appointments (not cancelled)
            appointments = supabase.get_user_appointments(user_id)
            upcoming = [
                apt for apt in appointments 
                if apt.get("status") != "cancelled" and 
                datetime.strptime(apt.get("date"), "%Y-%m-%d") >= datetime.now()
            ]
            
            if not upcoming:
                return {
                    "error": "No upcoming appointments found to modify. Please book an appointment first."
                }
            
            # If multiple appointments, use the earliest one
            upcoming.sort(key=lambda x: (x.get("date"), x.get("time")))
            appointment_to_modify = upcoming[0]
            appointment_id = appointment_to_modify["id"]
            
            logger.info(f"✓ Found appointment: {appointment_to_modify['date']} at {appointment_to_modify['time']}")
        
        # Validate new date and time
        try:
            new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            if new_datetime < datetime.now():
                return {"error": "Cannot reschedule to a past date/time"}
        except ValueError:
            return {"error": "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time"}
        
        # Check if new slot is available (excluding current appointment)
        is_available = supabase.check_slot_availability(
            new_date, new_time, exclude_id=appointment_id
        )
        
        if not is_available:
            return {
                "error": f"The slot at {new_time} on {new_date} is already booked. Please choose a different time."
            }
        
        # Update appointment
        result = supabase.modify_appointment(appointment_id, new_date, new_time)
        
        if result:
            logger.info(f"✓ Appointment {appointment_id} rescheduled to {new_date} at {new_time}")
            return {
                "success": True,
                "appointment_id": appointment_id,
                "new_date": new_date,
                "new_time": new_time,
                "message": f"Great! Your appointment has been rescheduled to {new_date} at {new_time}. You'll receive a confirmation."
            }
        else:
            return {"error": "Could not update appointment. Please try again."}
            
    except Exception as e:
        logger.error(f"Error modifying appointment: {e}")
        return {"error": f"An error occurred: {str(e)}"}


async def end_conversation(
    user_id: str,
    conversation_history: List[Dict],
    tool_calls: List[Dict],
    start_time: datetime,
    supabase,
    llm,
    cost_tracker
) -> Dict[str, Any]:
    """
    End conversation and generate summary
    
    Args:
        user_id: User's UUID (can be None if user never identified)
        conversation_history: List of conversation messages
        tool_calls: List of tool calls made during conversation
        start_time: Conversation start time
        supabase: Supabase client
        llm: LLM instance for summary generation
        cost_tracker: Cost tracker instance
        
    Returns:
        Dict with conversation summary
    """
    try:
        duration = (datetime.now() - start_time).seconds
        end_timestamp = datetime.now().isoformat()
        
        logger.info("📝 Generating conversation summary...")
        logger.info(f"   Duration: {duration}s | Tool calls: {len(tool_calls)}")
        logger.info(f"   User ID: {user_id or 'Not identified'}")
        
        # Generate comprehensive AI summary (< 10 seconds)
        summary_text = await generate_summary_text(
            conversation_history, tool_calls
        )
        
        # Get cost breakdown
        cost_breakdown = cost_tracker.get_total()
        
        # Extract booked appointments for structured data
        booked_appointments = [
            {
                "name": tc.get("args", {}).get("name"),
                "date": tc.get("args", {}).get("date"),
                "time": tc.get("args", {}).get("time"),
                "purpose": tc.get("args", {}).get("purpose")
            }
            for tc in tool_calls 
            if tc.get("name") == "book_appointment" and tc.get("result", {}).get("success")
        ]
        
        if user_id:
            logger.info("💾 Saving conversation to database...")
            try:
                supabase.save_conversation({
                    "user_id": user_id,
                    "transcript": json.dumps(conversation_history),
                    "summary": summary_text,
                    "tool_calls": json.dumps(tool_calls),
                    "duration_seconds": duration,
                    "cost_breakdown": json.dumps(cost_breakdown)
                })
                logger.info("✓ Conversation saved to database")
            except Exception as db_error:
                logger.error(f"⚠️ Failed to save conversation to DB: {db_error}")
                logger.info("   Continuing with summary generation anyway...")
        else:
            logger.warning("⚠️ No user_id - skipping database save")
        
        # Prepare complete summary for frontend
        complete_summary = {
            "text": summary_text,
            "duration_seconds": duration,
            "timestamp": end_timestamp,
            "appointments_count": len(booked_appointments),
            "appointments": booked_appointments,
            "tool_calls_count": len(tool_calls),
            "cost_breakdown": cost_breakdown
        }
        
        logger.info("✓ Summary generation completed")
        logger.info(f"   Appointments booked: {len(booked_appointments)}")
        logger.info(f"   Total cost: ${cost_breakdown.get('total_usd', 0):.4f}")
        
        return {
            "success": True,
            "summary": complete_summary,
            "message": "Call ended. Thank you for using SuperBryn!"
        }
    except Exception as e:
        logger.error(f"Error ending conversation: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Could not generate summary"
        }


async def generate_summary_text(conversation_history: List[Dict], tool_calls: List[Dict]) -> str:
    """
    Generate a comprehensive conversation summary using OpenAI GPT-4o-mini
    
    Requirements:
    - Generate within 10 seconds
    - Include discussion summary
    - List booked appointments
    - Extract user preferences
    - Professional and concise
    
    """
    start_time = time.time()
    
    # Wrap the entire function in a timeout to prevent hanging
    try:
        return await asyncio.wait_for(
            _generate_summary_impl(conversation_history, tool_calls, start_time),
            timeout=8.0  # Maximum 8 seconds total
        )
    except asyncio.TimeoutError:
        logger.error("⚠️ Summary generation timed out after 8 seconds - using quick fallback")
        return _quick_fallback_summary(conversation_history, tool_calls)


async def _generate_summary_impl(conversation_history: List[Dict], tool_calls: List[Dict], start_time: float) -> str:
    """Internal implementation of summary generation"""
    
    # Handle empty conversation
    if not conversation_history and not tool_calls:
        logger.warning("⚠️ No conversation history or tool calls - returning minimal summary")
        return """**Discussion Summary:**
The user connected but ended the call before any conversation took place.

**Appointments Booked:**
• No appointments were booked during this call

**User Preferences/Notes:**
None mentioned

**Next Steps:**
Call ended without completing any actions"""
    
    try:
        import openai
        import os
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        conversation_text = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
            for msg in conversation_history[-15:]
        ]) if conversation_history else "No conversation recorded"
        
        # Extract appointments from tool calls
        appointments = [
            tc for tc in tool_calls 
            if tc.get("name") == "book_appointment" and tc.get("result", {}).get("success")
        ]
        
        # Format appointments for context
        appointments_text = ""
        if appointments:
            appointments_text = "\n".join([
                f"- {apt.get('args', {}).get('name', 'Unknown')} on {apt.get('args', {}).get('date', 'N/A')} "
                f"at {apt.get('args', {}).get('time', 'N/A')} for {apt.get('args', {}).get('purpose', 'N/A')}"
                for apt in appointments
            ])
        
        # Create focused summary prompt
        prompt = f"""Generate a professional call summary in exactly this format:

**Discussion Summary:**
[2-3 sentences about what was discussed]

**Appointments Booked:**
{appointments_text if appointments else "• No appointments were booked during this call"}

**User Preferences/Notes:**
[Any preferences, special requests, or important notes mentioned by the user. If none, write "None mentioned"]

**Next Steps:**
[What should happen next, if anything. If none, write "Call completed"]

Conversation:
{conversation_text}

Keep it concise, professional, and actionable. Maximum 150 words total."""

        logger.info("🤖 Generating AI summary with GPT-4o-mini...")
        
        # Use gpt-4o-mini for fast, cost-effective summarization
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Fast model (~2-5 seconds)
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional call summarizer. Create clear, actionable summaries."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,  # Enough for comprehensive summary
            temperature=0.3,  # Focused output
            timeout=5  # Reduced to 5 seconds for faster fallback
        )
        
        summary_text = response.choices[0].message.content.strip()
        
        elapsed = time.time() - start_time
        logger.info(f"✓ AI summary generated in {elapsed:.2f}s ({len(summary_text)} chars)")
        
        return summary_text
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ Error generating AI summary after {elapsed:.2f}s: {e}")
        
        # Fast fallback template if AI fails
        logger.info("⚠️ Using fallback template summary")
        
        # Extract appointments
        appointments = [
            tc for tc in tool_calls 
            if tc.get("name") == "book_appointment" and tc.get("result", {}).get("success")
        ]
        
        summary_parts = [
            "**Discussion Summary:**",
            f"The user had a {'brief' if len(conversation_history) < 5 else 'detailed'} conversation regarding appointment scheduling.",
            "",
            "**Appointments Booked:**"
        ]
        
        if appointments:
            for apt in appointments:
                args = apt.get("args", {})
                summary_parts.append(
                    f"• {args.get('name', 'Unknown')} on {args.get('date', 'N/A')} "
                    f"at {args.get('time', 'N/A')} for {args.get('purpose', 'N/A')}"
                )
        else:
            summary_parts.append("• No appointments were booked during this call")
        
        summary_parts.extend([
            "",
            "**User Preferences/Notes:**",
            "See conversation transcript for details" if conversation_history else "None mentioned",
            "",
            "**Next Steps:**",
            "Confirmation sent. User will receive appointment reminder." if appointments else "Call completed"
        ])
        
        fallback_summary = "\n".join(summary_parts)
        elapsed = time.time() - start_time
        logger.info(f"✓ Fallback summary generated in {elapsed:.2f}s")
        
        return fallback_summary


def _quick_fallback_summary(conversation_history: List[Dict], tool_calls: List[Dict]) -> str:
    """
    Ultra-fast fallback summary when API times out
    
    """
    # Extract appointments
    appointments = [
        tc for tc in tool_calls 
        if tc.get("name") == "book_appointment" and tc.get("result", {}).get("success")
    ]
    
    summary_parts = [
        "**Discussion Summary:**",
        f"The user had a conversation with the AI assistant regarding appointment scheduling.",
        "",
        "**Appointments Booked:**"
    ]
    
    if appointments:
        for apt in appointments:
            args = apt.get("args", {})
            summary_parts.append(
                f"• {args.get('name', 'Unknown')} on {args.get('date', 'N/A')} "
                f"at {args.get('time', 'N/A')} for {args.get('purpose', 'N/A')}"
            )
    else:
        summary_parts.append("• No appointments were booked during this call")
    
    summary_parts.extend([
        "",
        "**User Preferences/Notes:**",
        "See conversation details for more information" if conversation_history else "None mentioned",
        "",
        "**Next Steps:**",
        "Confirmation sent. User will receive appointment reminder." if appointments else "Call completed"
    ])
    
    return "\n".join(summary_parts)