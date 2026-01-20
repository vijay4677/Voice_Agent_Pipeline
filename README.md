# VoiceFlow Voice Agent
VoiceFlow Voice Agent - End to End Implementation both Frontend and Backend

##  Project Description

A production-ready AI voice agent for appointment booking built with LiveKit Agents. Features real-time voice conversation, appointment management tools, cost tracking, and optional avatar video integration.

**Key Features:**
-  Natural voice conversation (Speech-to-Text + Text-to-Speech)
-  7 appointment management tools (book, cancel, modify, etc.)
-  Real-time cost tracking
-  Optional avatar video integration (Beyond Presence)
-  Google Calendar integration for appointment syncing
-  Call summaries with detailed breakdowns

##  Tech Stack

This project uses the following technologies and services. Click the links to get your API keys:

### Core Infrastructure
- **[LiveKit](https://livekit.io/)** - Real-time communication platform
  - Get API keys: [LiveKit Cloud](https://cloud.livekit.io/) or [Self-hosted](https://docs.livekit.io/deploy/)

### AI & Voice Services
- **[OpenAI](https://openai.com/)** - Large Language Model (GPT-4o-mini)
  - Get API key: [OpenAI Platform](https://platform.openai.com/api-keys)
- **[Deepgram](https://deepgram.com/)** - Speech-to-Text (Nova-2 model)
  - Get API key: [Deepgram Console](https://console.deepgram.com/)
- **[Cartesia](https://cartesia.ai/)** - Text-to-Speech (Sonic model)
  - Get API key: [Cartesia Dashboard](https://dashboard.cartesia.ai/)

### Avatar Integration (Optional)
- **[Beyond Presence](https://beyondpresence.ai/)** - AI Avatar video integration
  - Get API key: [Beyond Presence Dashboard](https://beyondpresence.ai/)
  - Requires: `BEY_API_KEY` and `BEY_AVATAR_ID`
  - Install plugin: `pip install livekit-plugins-bey`

### Database
- **[Supabase](https://supabase.com/)** - PostgreSQL database and backend
  - Get credentials: [Supabase Dashboard](https://app.supabase.com/)

### Calendar Integration (Optional)
- **[Google Calendar API](https://developers.google.com/calendar)** - Appointment calendar syncing
  - Setup guide: [Google Cloud Console](https://console.cloud.google.com/)
  - Supports OAuth 2.0 or Service Account authentication

### Frontend
- **[Next.js](https://nextjs.org/)** - React framework
- **[LiveKit Components](https://github.com/livekit/components-react)** - React components for LiveKit
- **[TypeScript](https://www.typescriptlang.org/)** - Type-safe JavaScript
- **[Tailwind CSS](https://tailwindcss.com/)** - Utility-first CSS framework

##  Quick Start Commands

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

#### Required Variables

```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-server.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# AI Services
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
```

#### Optional Variables

```bash
# Beyond Presence Avatar (Optional - for video avatar integration)
BEY_API_KEY=your_beyond_presence_api_key
BEY_AVATAR_ID=your_avatar_id

# Google Calendar Integration (Optional)
GOOGLE_REFRESH_TOKEN=your_refresh_token
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_CALENDAR_ID=primary  # Default: "primary"
CALENDAR_TIMEZONE=Asia/Kolkata  # Default: "Asia/Kolkata"
```

**Note:** 
- Beyond Presence keys are optional. If not provided, the system will use an animated fallback avatar.
- Google Calendar integration is optional. If not configured, appointments will still be saved to the database.

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

##  Available Tools

1. `identify_user` - Find/validate users
2. `fetch_slots` - Get available time slots
3. `book_appointment` - Book appointments
4. `retrieve_appointments` - View bookings
5. `cancel_appointment` - Cancel bookings
6. `modify_appointment` - Reschedule appointments
7. `end_conversation` - End call and generate summary

##  Getting API Keys

### Beyond Presence Setup

1. **Sign up** at [Beyond Presence](https://beyondpresence.ai/)
2. **Create an avatar** in the dashboard
3. **Get your API key** from the API settings
4. **Copy your Avatar ID** from the avatar details page
5. Add to `.env`:
   ```bash
   BEY_API_KEY=your_api_key_here
   BEY_AVATAR_ID=your_avatar_id_here
   ```
6. **Install the plugin** (already in requirements.txt):
   ```bash
   pip install livekit-plugins-bey
   ```

### Google Calendar Setup

**Option 1: OAuth 2.0 (For Personal Calendars)**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Get refresh token using OAuth flow
6. Add to `.env`:
   ```bash
   GOOGLE_REFRESH_TOKEN=your_refresh_token
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```


##  Project Structure

```
Voice_Agent_Pipeline/
├── backend/
│   ├── agents/
│   │   ├── agent_server.py    # Main LiveKit agent
│   │   ├── avatar_manager.py  # Avatar session management
│   │   ├── prompts.py         # AI prompts
│   │   └── tools.py           # Tool functions
│   ├── db/
│   │   └── supabase_client.py # Database client
│   ├── services/
│   │   ├── google_calendar.py # Calendar integration
│   │   └── cost_tracker.py   # Cost tracking
│   ├── main.py               # FastAPI server
│   └── railway_start.py      # Production entrypoint
└── frontend/
    └── voice-agent-frontend/
        ├── app/              # Next.js app directory
        └── components/      # React components
```