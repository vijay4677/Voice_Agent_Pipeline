"""
Cost tracking service for monitoring API usage costs

"""

from collections import defaultdict
from typing import Dict, Optional, Any
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class CostTracker:
    """
    Track costs for STT, TTS, LLM, and tool calls
    """
    PRICING = {
        # Deepgram Nova-2 STT
        "deepgram_stt_per_minute": 0.0077,  # $0.462/hour
        
        # Cartesia Sonic TTS
        "cartesia_tts_per_char": 0.00005,
        
        "openai_input_per_1k": 0.00015,  # $0.150 per 1M input tokens
        "openai_output_per_1k": 0.0006,   # $0.600 per 1M output tokens
        
        "claude_input_per_1k": 0.003,
        "claude_output_per_1k": 0.015,
        
        "livekit_connection_per_minute": 0.01,
        
        "avatar_per_minute": 0.015,
        
        "tool_call": 0.0001,
    }
    
    def __init__(self, room=None):
        """
        Initialize cost tracker
        
        Args:
            room: Optional LiveKit room object for sending real-time updates
        """
        self.costs = defaultdict(float)
        self.usage_stats = {
            "stt_minutes": 0,
            "tts_characters": 0,
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "tool_calls": 0,
            "connection_minutes": 0,
            "avatar_minutes": 0,
        }
        # Track last seen values to calculate deltas from cumulative metrics
        self._last_seen = {
            "stt_seconds": 0,
            "tts_characters": 0,
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
        }
        self._room = room
        self._start_time = datetime.now()
        logger.info("Cost tracker initialized")
    
    def track_stt(self, duration_minutes: float):
        """
        Track speech-to-text costs
        
        Args:
            duration_minutes: Duration of speech in minutes
        """
        cost = duration_minutes * self.PRICING["deepgram_stt_per_minute"]
        self.costs["stt"] += cost
        self.usage_stats["stt_minutes"] += duration_minutes
        logger.info(f"📊 STT: +{duration_minutes:.3f} min = +${cost:.4f} (total: ${self.costs['stt']:.4f})")
    
    def track_tts(self, characters: int):
        """
        Track text-to-speech costs
        
        Args:
            characters: Number of characters synthesized
        """
        cost = characters * self.PRICING["cartesia_tts_per_char"]
        self.costs["tts"] += cost
        self.usage_stats["tts_characters"] += characters
        logger.info(f"📊 TTS: +{characters} chars = +${cost:.4f} (total: ${self.costs['tts']:.4f})")
    
    def track_llm(self, input_tokens: int, output_tokens: int, model: str = "openai"):
        """
        Track LLM API costs
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model type ("openai" or "claude")
        """
        input_cost_key = f"{model}_input_per_1k"
        output_cost_key = f"{model}_output_per_1k"
        
        input_cost = (input_tokens / 1000) * self.PRICING.get(input_cost_key, 0.01)
        output_cost = (output_tokens / 1000) * self.PRICING.get(output_cost_key, 0.03)
        
        total_cost = input_cost + output_cost
        self.costs["llm_input"] += input_cost
        self.costs["llm_output"] += output_cost
        
        self.usage_stats["llm_input_tokens"] += input_tokens
        self.usage_stats["llm_output_tokens"] += output_tokens
        
        # Removed verbose logging
    
    def track_tool_call(self, tool_name: str):
        """
        Track tool call overhead
        
        Args:
            tool_name: Name of the tool called
        """
        cost = self.PRICING["tool_call"]
        self.costs["tools"] += cost
        self.usage_stats["tool_calls"] += 1
        logger.debug(f"Tool call tracked: {tool_name} = ${cost:.4f}")
    
    def get_total(self) -> Dict:
        """
        Get total costs and breakdown
        
        Returns:
            Dict with cost breakdown and usage stats
        """
        total_cost = sum(self.costs.values())
        
        breakdown = {
            "stt_cost": round(self.costs.get("stt", 0), 4),
            "tts_cost": round(self.costs.get("tts", 0), 4),
            "llm_input_cost": round(self.costs.get("llm_input", 0), 4),
            "llm_output_cost": round(self.costs.get("llm_output", 0), 4),
            "tools_cost": round(self.costs.get("tools", 0), 4),
            "connection_cost": round(self.costs.get("connection", 0), 4),
            "avatar_cost": round(self.costs.get("avatar", 0), 4),
            "total_cost": round(total_cost, 4),
        }
        
        return {
            "breakdown": breakdown,
            "usage_stats": self.usage_stats,
            "total_usd": round(total_cost, 4)
        }
    
    def reset(self):
        """Reset all tracked costs and stats"""
        self.costs = defaultdict(float)
        self.usage_stats = {
            "stt_minutes": 0,
            "tts_characters": 0,
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "tool_calls": 0,
            "connection_minutes": 0,
            "avatar_minutes": 0,
        }
        self._start_time = datetime.now()
        logger.info("Cost tracker reset")
    
    async def _send_cost_update(self):
        """
        Send real-time cost update to frontend via data channel
        
        """
        if not self._room:
            return
        
        try:
            cost_data = self.get_total()
            event = {
                "type": "cost_update",
                "data": cost_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await self._room.local_participant.publish_data(
                json.dumps(event).encode('utf-8'),
                reliable=True
            )
            logger.debug(f"Cost update sent: ${cost_data['total_usd']:.4f}")
        except Exception as e:
            logger.error(f"Error sending cost update: {e}")
    
    def track_connection_time(self, duration_minutes: float):
        """
        Track LiveKit connection time costs
        
        Args:
            duration_minutes: Duration of connection in minutes
        """
        cost = duration_minutes * self.PRICING["livekit_connection_per_minute"]
        self.costs["connection"] += cost
        self.usage_stats["connection_minutes"] += duration_minutes
        logger.info(f"📊 Connection: +{duration_minutes:.3f} min = +${cost:.4f} (total: ${self.costs['connection']:.4f})")
    
    def track_avatar_time(self, duration_minutes: float):
        """
        Track avatar streaming costs
        
        Args:
            duration_minutes: Duration of avatar streaming in minutes
        """
        cost = duration_minutes * self.PRICING["avatar_per_minute"]
        self.costs["avatar"] += cost
        self.usage_stats["avatar_minutes"] += duration_minutes
        logger.info(f"📊 Avatar: +{duration_minutes:.3f} min = +${cost:.4f} (total: ${self.costs['avatar']:.4f})")
    
    async def track_stt_async(self, duration_minutes: float):
        """
        Track STT costs and send update to frontend
        
        """
        self.track_stt(duration_minutes)
        await self._send_cost_update()
    
    async def track_tts_async(self, characters: int):
        """
        Track TTS costs and send update to frontend
        
        """
        self.track_tts(characters)
        await self._send_cost_update()
    
    async def track_llm_async(self, input_tokens: int, output_tokens: int, model: str = "openai"):
        """
        Track LLM costs and send update to frontend
        
        """
        self.track_llm(input_tokens, output_tokens, model)
        await self._send_cost_update()
    
    def get_session_duration(self) -> float:
        """
        Get current session duration in minutes
        
        Returns:
            Duration in minutes
        """
        elapsed = (datetime.now() - self._start_time).total_seconds()
        return elapsed / 60.0
    
    def track_from_cumulative_metrics(self, summary):
        """
        Track costs from cumulative metrics by calculating deltas
        
        Args:
            summary: UsageSummary object with cumulative metrics
        """
        # Removed verbose logging - only track costs silently
        
        # STT: Convert cumulative seconds to delta minutes
        if hasattr(summary, 'stt_audio_duration'):
            current_stt_seconds = summary.stt_audio_duration
            delta_seconds = current_stt_seconds - self._last_seen["stt_seconds"]
            if delta_seconds > 0:
                delta_minutes = delta_seconds / 60.0
                self.track_stt(delta_minutes)
                self._last_seen["stt_seconds"] = current_stt_seconds
        
        # TTS: Calculate character delta
        if hasattr(summary, 'tts_characters_count'):
            current_chars = summary.tts_characters_count
            delta_chars = current_chars - self._last_seen["tts_characters"]
            if delta_chars > 0:
                self.track_tts(delta_chars)
                self._last_seen["tts_characters"] = current_chars
        
        # LLM: Calculate token deltas
        if hasattr(summary, 'llm_prompt_tokens') and hasattr(summary, 'llm_completion_tokens'):
            current_input = summary.llm_prompt_tokens
            current_output = summary.llm_completion_tokens
            
            delta_input = current_input - self._last_seen["llm_input_tokens"]
            delta_output = current_output - self._last_seen["llm_output_tokens"]
            
            if delta_input > 0 or delta_output > 0:
                self.track_llm(delta_input, delta_output, model="openai")
                self._last_seen["llm_input_tokens"] = current_input
                self._last_seen["llm_output_tokens"] = current_output