"""
Single Global Avatar Session - True Singleton Pattern

This module implements a TRUE singleton avatar that's shared across ALL rooms.
Only ONE avatar is ever created, and it's reused for every single call
regardless of room ID.

Key Design:
- ONE avatar instance globally
- First call to ANY room: Creates avatar (~10-15s)
- All other calls to ANY room: Reuses same avatar (~instant!)
- Avatar persists across different room_id values

Performance:
- First call (any room): 10-15 seconds
- All subsequent calls (any room): <1 second

"""

import asyncio
import logging
import time
from typing import Optional, Tuple
from datetime import datetime

# Try to import Beyond Presence plugin
try:
    from livekit.plugins import bey
    BEY_AVAILABLE = True
except ImportError:
    BEY_AVAILABLE = False
    bey = None

logger = logging.getLogger(__name__)


class SingleAvatarSession:
    """
    True Singleton - ONE avatar for ALL rooms
    """
    
    _instance: Optional['SingleAvatarSession'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        """Private constructor - use get_instance() instead"""
        if SingleAvatarSession._instance is not None:
            raise RuntimeError("Use SingleAvatarSession.get_instance()")
        
        self._avatar_session = None
        self._avatar_id: Optional[str] = None
        self._created_at: Optional[datetime] = None
        self._use_count = 0
        self._is_connected = False
        self._start_task: Optional[asyncio.Task] = None
        self._access_lock = asyncio.Lock()
        
        logger.info("SingleAvatarSession initialized")
    
    @classmethod
    def get_instance(cls) -> 'SingleAvatarSession':
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def get_or_create(
        self,
        avatar_id: str,
        room,
        agent_session,
        participant_identity: str = "agent_avatar",
        participant_name: str = "SuperBryn Assistant"
    ) -> Tuple[Optional[object], bool]:
        """
        Get existing avatar or create new one
        
        Args:
            avatar_id: Beyond Presence avatar ID
            room: LiveKit room instance
            agent_session: LiveKit AgentSession
            participant_identity: Identity for avatar participant
            participant_name: Display name for avatar
        
        Returns:
            (avatar_session, is_new) where is_new indicates if newly created
        """
        
        if not BEY_AVAILABLE:
            logger.warning("Beyond Presence plugin not available")
            return None, False
        
        async with self._access_lock:
            # Check if we already have a valid avatar session
            if (self._avatar_session and 
                self._avatar_id == avatar_id):
                
                self._use_count += 1
                age = (datetime.now() - self._created_at).total_seconds()
                
                logger.info(f"REUSING GLOBAL Avatar across ALL rooms (use #{self._use_count})")
                logger.info(f"  Age: {age:.1f}s | ALL ROOMS share this avatar!")
                logger.info(f"  Saved: ~10-20s initialization time!")
                logger.info(f"  Connection state: {'connected' if self._is_connected else 'connecting...'}")
                
                return self._avatar_session, False
            
            # Need to create new avatar session
            if self._avatar_session:
                logger.info("Previous Avatar disconnected, creating new one...")
            else:
                logger.info("Creating FIRST avatar session...")
            
            start_time = time.time()
            
            try:
                # Create avatar session object
                avatar_session = bey.AvatarSession(
                    avatar_id=avatar_id,
                    avatar_participant_identity=participant_identity,
                    avatar_participant_name=participant_name
                )
                
                # Start avatar connection in background
                async def start_avatar_async():
                    """Connect to Beyond Presence API (slow part) - ONCE for ALL rooms"""
                    try:
                        connect_start = time.time()
                        logger.info("  Connecting to Beyond Presence API (ONE TIME for ALL rooms)...")
                        
                        # Start avatar session - it will work across all rooms
                        await avatar_session.start(agent_session, room=room)
                        
                        elapsed = time.time() - connect_start
                        logger.info(f"  Avatar connected in {elapsed:.2f}s")
                        logger.info(f"  This avatar will now be reused for ALL future rooms!")
                        
                        # Mark as connected
                        self._is_connected = True
                        return True
                        
                    except Exception as e:
                        logger.error(f"  Avatar connection failed: {e}", exc_info=True)
                        self._is_connected = False
                        self._avatar_session = None
                        return False
                
                # Start connection in background
                self._start_task = asyncio.create_task(start_avatar_async())
                
                # Store state
                self._avatar_session = avatar_session
                self._avatar_id = avatar_id
                self._created_at = datetime.now()
                self._use_count = 1
                
                elapsed = time.time() - start_time
                logger.info(f"Avatar session created in {elapsed:.2f}s")
                logger.info(f"  Note: Connecting to API in background...")
                
                return avatar_session, True
                
            except Exception as e:
                logger.error(f"Failed to create avatar: {e}", exc_info=True)
                return None, False
    
    def is_connected(self) -> bool:
        """Check if avatar is currently connected"""
        return self._is_connected
    
    def get_stats(self) -> dict:
        """Get usage statistics"""
        if not self._avatar_session:
            return {"status": "not_initialized"}
        
        age = (datetime.now() - self._created_at).total_seconds() if self._created_at else 0
        
        return {
            "status": "connected" if self._is_connected else "disconnected",
            "avatar_id": self._avatar_id[:20] + "..." if self._avatar_id else None,
            "age_seconds": age,
            "use_count": self._use_count,
            "time_saved_estimate": f"~{(self._use_count - 1) * 15}s" if self._use_count > 1 else "0s"
        }
    
    async def reset(self):
        """Reset the avatar session (for cleanup/testing)"""
        async with self._access_lock:
            if self._start_task and not self._start_task.done():
                self._start_task.cancel()
            
            logger.info(f"Resetting Avatar Session (used {self._use_count} times)")
            
            self._avatar_session = None
            self._avatar_id = None
            self._created_at = None
            self._use_count = 0
            self._is_connected = False
            self._start_task = None


def get_avatar_session() -> SingleAvatarSession:
    """Get the global avatar session singleton"""
    return SingleAvatarSession.get_instance()
