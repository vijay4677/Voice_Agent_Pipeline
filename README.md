# Voice_Agent
Voice_Agent End to End Implementation both Frontend and Backend

## 📋 Project Description

A production-ready AI voice agent for appointment booking built with LiveKit Agents. Features real-time voice conversation, appointment management tools, cost tracking, and optional avatar video integration.

**Key Features:**
-  Natural voice conversation (Speech-to-Text + Text-to-Speech)
-  7 appointment management tools (book, cancel, modify, etc.)
-  Real-time cost tracking
-  Optional avatar video integration
-  Call summaries with detailed breakdowns

## 🚀 Quick Start Commands

### 1. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend/voice-agent-frontend
npm install
```

### 2. Set Environment Variables

Create `.env` file in `backend/` directory:

```bash
LIVEKIT_URL=wss://your-server.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
DEEPGRAM_API_KEY=your_key
CARTESIA_API_KEY=your_key
OPENAI_API_KEY=your_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_key
```

### 3. Run the Application

**Option A: Single Command (Recommended - Runs Both Backend Services)**
```bash
cd backend
python railway_start.py
```

**Option B: Separate Terminals (For Development)**

**Terminal 1 - FastAPI Server:**
```bash
cd backend
python main.py api 
```

**Terminal 2 - LiveKit Agent:**
```bash
cd backend
python agents/agent_server.py dev
```

**Terminal 3 - Frontend:**
```bash
cd frontend/voice-agent-frontend
npm run dev
```

### 4. Access Application

Open browser: **http://localhost:3000**

## 🛠️ Available Tools

1. `identify_user` - Find/validate users
2. `fetch_slots` - Get available time slots
3. `book_appointment` - Book appointments
4. `retrieve_appointments` - View bookings
5. `cancel_appointment` - Cancel bookings
6. `modify_appointment` - Reschedule appointments
7. `end_conversation` - End call and generate summary

