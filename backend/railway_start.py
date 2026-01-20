#!/usr/bin/env python3
"""
Production entrypoint for Railway deployment
Runs both FastAPI server and LiveKit agent in one process
"""


import os
import sys
import subprocess
import signal
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

api_process = None
agent_process = None

def cleanup(signum=None, frame=None):
    """Cleanup processes on exit"""
    logger.info("Shutting down services...")
    
    if api_process:
        logger.info("  Stopping FastAPI server...")
        api_process.terminate()
        api_process.wait(timeout=5)
    
    if agent_process:
        logger.info("  Stopping LiveKit agent...")
        agent_process.terminate()
        agent_process.wait(timeout=5)
    
    logger.info("Cleanup complete")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

def run_api_server():
    """Run FastAPI server as subprocess"""
    global api_process
    try:
        logger.info("Starting FastAPI API Server...")
        
        port = os.getenv("PORT", "8000")
        
        # Run uvicorn as subprocess
        api_process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "main:app",
                "--host", "0.0.0.0",
                "--port", port,
                "--log-level", "info"
            ],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=os.environ.copy()
        )
        
        logger.info(f"FastAPI server started on port {port} (PID: {api_process.pid})")
        return api_process
        
    except Exception as e:
        logger.error(f"Failed to start API Server: {e}")
        return None

def run_livekit_agent():
    """Run LiveKit agent as subprocess"""
    global agent_process
    try:
        logger.info("Starting LiveKit Agent...")
        
        # Run agent using python directly (it will call cli.run_app internally)
        # Use 'start' for production (listens to all rooms)
        agent_process = subprocess.Popen(
            [
                sys.executable,
                "agents/agent_server.py",
                "start"  # 'start' listens to all rooms, 'connect' needs --room
            ],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=os.environ.copy()
        )
        
        logger.info(f"LiveKit Agent started (PID: {agent_process.pid})")
        return agent_process
        
    except Exception as e:
        logger.error(f"Failed to start LiveKit Agent: {e}")
        return None

def main():
    """Main entrypoint - runs both services"""
    logger.info("=" * 60)
    logger.info("SuperBryn Voice Agent - Production Mode")
    logger.info("=" * 60)
    
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY", 
        "LIVEKIT_API_SECRET",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "OPENAI_API_KEY",
        "DEEPGRAM_API_KEY",
        "CARTESIA_API_KEY"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    
    logger.info("All environment variables set")
    
    # Start both services as subprocesses
    api_proc = run_api_server()
    time.sleep(2)  # Give API a moment to start
    
    agent_proc = run_livekit_agent()
    time.sleep(2)  # Give agent a moment to start
    
    if not api_proc or not agent_proc:
        logger.error("Failed to start services")
        cleanup()
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("All services started successfully!")
    logger.info("=" * 60)
    
    # Wait for processes (keeps Railway alive)
    try:
        while True:
            # Check if processes are still running
            api_status = api_proc.poll()
            agent_status = agent_proc.poll()
            
            if api_status is not None:
                logger.error(f"API server exited with code {api_status}")
                cleanup()
                sys.exit(1)
            
            if agent_status is not None:
                logger.error(f"LiveKit agent exited with code {agent_status}")
                cleanup()
                sys.exit(1)
            
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal")
        cleanup()

if __name__ == "__main__":
    main()

