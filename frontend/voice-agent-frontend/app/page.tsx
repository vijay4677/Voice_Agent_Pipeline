'use client';

import { useState } from 'react';
import { LiveKitRoom, RoomAudioRenderer } from '@livekit/components-react';
import VoiceCallUI from '@/components/VoiceCallUI';
import CallSummary from '@/components/CallSummary';
import '@livekit/components-styles';

interface Summary {
  text: string;
  duration_seconds: number;
  tool_calls_count: number;
  cost_breakdown: any;
}

export default function Home() {
  const [token, setToken] = useState<string>('');
  const [roomName, setRoomName] = useState<string>('');
  const [callEnded, setCallEnded] = useState(false);
  const [summary, setSummary] = useState<Summary | null>(null);

  const [waitingForSummary, setWaitingForSummary] = useState(false);
  const summaryTimeoutRef = useState<NodeJS.Timeout | null>(null);

  const startCall = async () => {
    try {
      const room = `voice-room-${Date.now()}`;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/get-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          room_name: room,
          participant_name: 'user',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get token');
      }

      const data = await response.json();
      setToken(data.token);
      setRoomName(data.room_name);
    } catch (error) {
      console.error('Error starting call:', error);
      alert('Failed to start call. Please check your configuration.');
    }
  };

  const handleCallEnd = (callSummary?: Summary) => {
    console.log('📞 handleCallEnd called');
    console.log('📋 Summary received:', callSummary);
    console.log('📊 Summary keys:', callSummary ? Object.keys(callSummary) : 'none');
    
    if (summaryTimeoutRef[0]) {
      clearTimeout(summaryTimeoutRef[0]);
      summaryTimeoutRef[0] = null;
    }
    
    // If no summary provided, go back to home
    if (!callSummary) {
      console.warn('⚠️ No summary provided - returning to home');
      setWaitingForSummary(false);
      setCallEnded(false);
      setSummary(null);
      setToken('');
      setRoomName('');
      return;
    }
    
    // Check if it's a very short call (less than 5 seconds)
    if (callSummary.duration_seconds && callSummary.duration_seconds < 5) {
      console.warn('⚠️ Very short call - returning to home');
      setWaitingForSummary(false);
      setCallEnded(false);
      setSummary(null);
      setToken('');
      setRoomName('');
      return;
    }
    
    // Check if summary text is empty (if it exists)
    if (callSummary.text !== undefined && callSummary.text.trim() === '') {
      console.warn('⚠️ Empty summary text - returning to home');
      setWaitingForSummary(false);
      setCallEnded(false);
      setSummary(null);
      setToken('');
      setRoomName('');
      return;
    }
    
    // Valid summary exists - show it
    console.log('✅ Valid summary - displaying');
    setSummary(callSummary);
    setWaitingForSummary(false);
    setCallEnded(true);
    setToken('');
    setRoomName('');
  };
  
  const handleDisconnect = () => {
    setWaitingForSummary(true);
    
    const timeout = setTimeout(() => {
      handleCallEnd();
    }, 10000); // Increased from 10s to 30s
    
    summaryTimeoutRef[0] = timeout;
  };

  const resetCall = () => {
    setCallEnded(false);
    setSummary(null);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="bg-slate-900/90 backdrop-blur-sm border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">SuperBryn</h1>
                <p className="text-xs text-slate-400">Voice Appointment System</p>
              </div>
            </div>
            {token && !callEnded && (
              <div className="flex items-center space-x-2 bg-green-900/30 px-3 py-1.5 rounded-lg border border-green-700/50">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-green-400">Connected</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {!callEnded && !waitingForSummary ? (
          token ? (
            <LiveKitRoom
              token={token}
              serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL!}
              connect={true}
              audio={true}
              video={false}
              onDisconnected={handleDisconnect}
              className="h-full"
            >
              <VoiceCallUI onCallEnd={handleCallEnd} roomName={roomName} />
              <RoomAudioRenderer />
            </LiveKitRoom>
          ) : (
            <div className="flex flex-col items-center justify-center min-h-[600px]">
              <div className="max-w-2xl w-full bg-slate-800/90 rounded-2xl shadow-2xl border border-slate-700 p-12 text-center">
                {/* Welcome Screen */}
                <div className="mb-8">
                  <div className="w-20 h-20 bg-blue-600 rounded-xl mx-auto flex items-center justify-center mb-6 shadow-2xl">
                    <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <h2 className="text-3xl font-bold text-white mb-3">Welcome to SuperBryn</h2>
                  <p className="text-lg text-slate-400">Professional voice appointment system</p>
                </div>

                <div className="space-y-2 mb-8 text-left bg-slate-900/50 rounded-xl p-6 border border-slate-700">
                  <h3 className="font-semibold text-slate-300 mb-3 text-center">What I Can Do</h3>
                  <ul className="space-y-2">
                    {[
                      '📅 Book appointments',
                      '🔍 Check bookings',
                      '✏️ Modify schedule',
                      '❌ Cancel appointments',
                      '⏰ View available slots',
                    ].map((item, i) => (
                      <li key={i} className="flex items-center text-slate-300 p-2 rounded-lg hover:bg-slate-800/50 transition-colors">
                        <span className="text-lg mr-3">{item.split(' ')[0]}</span>
                        <span>{item.substring(item.indexOf(' ') + 1)}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <button
                  onClick={startCall}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-xl font-semibold text-lg transition-all duration-200 shadow-lg hover:shadow-xl flex items-center justify-center space-x-2"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                  <span>Start Voice Call</span>
                </button>

                <p className="text-sm text-slate-400 mt-4">Click to begin your voice session</p>
              </div>
            </div>
          )
        ) : waitingForSummary ? (
          <div className="flex flex-col items-center justify-center min-h-[600px]">
            <div className="max-w-2xl w-full bg-slate-800/90 rounded-2xl shadow-2xl border border-slate-700 p-12 text-center">
              <div className="mb-8">
                <div className="w-20 h-20 bg-blue-600 rounded-xl mx-auto flex items-center justify-center mb-6 shadow-2xl animate-pulse">
                  <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h2 className="text-2xl font-bold text-white mb-3">Generating Summary...</h2>
                <p className="text-lg text-slate-400">Please wait while we prepare your conversation summary</p>
              </div>
              <div className="flex justify-center mb-6">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
              
              <button
                onClick={() => {
                  if (summaryTimeoutRef[0]) {
                    clearTimeout(summaryTimeoutRef[0]);
                    summaryTimeoutRef[0] = null;
                  }
                  setWaitingForSummary(false);
                  setCallEnded(false);
                  setToken('');
                  setRoomName('');
                }}
                className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-all border border-slate-600"
              >
                Cancel & Return Home
              </button>
            </div>
          </div>
        ) : (
          <CallSummary summary={summary} onReset={resetCall} />
        )}
      </div>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-900/90 backdrop-blur-sm border-t border-slate-700 py-3">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs text-slate-400">
            Powered by LiveKit • Deepgram • Cartesia • OpenAI
          </p>
        </div>
      </footer>
    </main>
  );
}
