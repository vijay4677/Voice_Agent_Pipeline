"""
VoiceFlow Voice Agent - Simplified Main Entry Point
Works with current LiveKit Agents API
"""

import asyncio
import logging
import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from livekit import api, rtc
from livekit.agents import JobContext, WorkerOptions, cli, llm, JobRequest
from livekit.plugins import deepgram, cartesia, openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
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
    """Generate LiveKit token for client connection"""
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

        return {
            "token": jwt_token,
            "url": os.getenv("LIVEKIT_URL"),
            "room_name": room_name
        }
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Simple agent entry point
async def entrypoint(ctx: JobContext):
    """
    Simplified agent entry point
    """
    logger.info(f"Agent starting for room: {ctx.room.name}")

    # Connect to room
    await ctx.connect(auto_subscribe=True)

    # Wait for participant
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant connected: {participant.identity}")

    # Simple greeting
    logger.info("Agent running. Waiting for audio...")

    # Keep connection alive
    while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
        await asyncio.sleep(1)

    logger.info("Agent disconnected")


# For local testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "start":
        # Start LiveKit agent worker
        logger.info("Starting LiveKit agent worker...")
        cli.run_app(
            WorkerOptions(
                entrypoint_fnc=entrypoint,
            )
        )
    # else:
        # Start FastAPI server
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))