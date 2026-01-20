'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    useLocalParticipant,
    useRoomContext,
    useDataChannel,
    useTracks,
} from '@livekit/components-react';
import { Track } from 'livekit-client';
import AvatarDisplay from './AvatarDisplay';
import ToolCallDisplay from './ToolCallDisplay';
import DebugPanel from './DebugPanel';
import { ToolCall } from '@/app/types';

interface VoiceCallUIProps {
    onCallEnd: (summary?: any) => void;
    roomName: string;
}

export default function VoiceCallUI({ onCallEnd, roomName }: VoiceCallUIProps) {
    const room = useRoomContext();
    const { localParticipant } = useLocalParticipant();
    const [isMuted, setIsMuted] = useState(false);
    const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
    const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
    const [callDuration, setCallDuration] = useState(0);
    
    const [costData, setCostData] = useState<any>(null);
    
    const [lastSummary, setLastSummary] = useState<any>(null);
    const [isDisconnecting, setIsDisconnecting] = useState(false);

    // Track call duration
    useEffect(() => {
        const interval = setInterval(() => {
            setCallDuration((prev) => prev + 1);
        }, 1000);

        return () => clearInterval(interval);
    }, []);

    // Listen for data messages from agent
    const handleDataReceived = useCallback((msg: any) => {
        try {
            const decoder = new TextDecoder();
            const message = JSON.parse(decoder.decode(msg.payload));

            console.log('Received message from agent:', message);

            if (message.type === 'tool_call') {
                // Add new tool call to the list
                setToolCalls((prev) => [...prev, message.data]);
                
                // Check if this is an end_conversation tool call with summary
                if (message.data?.name === 'end_conversation' && message.data?.result?.summary) {
                    console.log('📋 Summary received via tool_call:', message.data.result.summary);
                    const summary = message.data.result.summary;
                    setLastSummary(summary);
                    setIsDisconnecting(false);
                    
                    // Show summary and disconnect
                    onCallEnd(summary);
                    setTimeout(() => {
                        room.disconnect();
                    }, 500);
                }
            } else if (message.type === 'cost_update') {
                // Update real-time cost data
                setCostData(message.data);
            } else if (message.type === 'end_call') {
                // Backend is ending the call - show summary and disconnect
              
                // Store summary for use on disconnect
                setLastSummary(message.summary);
                setIsDisconnecting(false); // Clear loading state
                
                // Show summary to user FIRST before disconnecting
                if (message.summary) {
                    // Call onCallEnd first to set the summary state
                    onCallEnd(message.summary);
                    
                    // Then disconnect after a small delay to ensure state is set
                    setTimeout(() => {
                        console.log('🔌 Disconnecting from room...');
                        room.disconnect();
                    }, 500); // Small delay to ensure state update completes
                } else {
                    console.error('❌ No summary in end_call message!');
                    // Still disconnect even without summary
                    setTimeout(() => {
                        room.disconnect();
                        onCallEnd();
                    }, 500);
                }
            } else if (message.type === 'call_summary' || message.type === 'summary') {
                // Legacy summary formats or final summary
                console.log('📋 Received legacy/final summary:', message.data);
                setLastSummary(message.data);
                setIsDisconnecting(false); // Clear loading state
                onCallEnd(message.data);
            }
        } catch (error) {
            console.error('Error parsing data message:', error);
        }
    }, [onCallEnd, room]);

    useDataChannel(handleDataReceived);

    const audioTracks = useTracks([Track.Source.Microphone]);

    useEffect(() => {
        const agentTrack = audioTracks.find(
            (t: any) => t.participant.identity !== localParticipant.identity
        );

        if (agentTrack) {
            setIsAgentSpeaking(true);
            const timeout = setTimeout(() => setIsAgentSpeaking(false), 2000);
            return () => clearTimeout(timeout);
        }
    }, [audioTracks, localParticipant.identity]);

    const toggleMute = async () => {
        if (localParticipant) {
            const newMutedState = !isMuted;
            await localParticipant.setMicrophoneEnabled(!newMutedState);
            setIsMuted(newMutedState);
        }
    };

    const endCall = async () => {
        try {
            console.log('🔚 User ending call - requesting summary from backend...');
            
            setIsDisconnecting(true);
            
            const message = {
                type: 'end_call_request',
                timestamp: new Date().toISOString()
            };
            
            const encoder = new TextEncoder();
            await localParticipant.publishData(encoder.encode(JSON.stringify(message)), {
                reliable: true
            });

        } catch (error) {
            console.error('Error requesting summary:', error);
            room.disconnect();
            onCallEnd();
        }
    };

    const formatDuration = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="min-h-[600px] flex flex-col">
            {isDisconnecting && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center">
                    <div className="backdrop-blur-xl bg-white/10 rounded-3xl shadow-2xl border border-white/20 p-10 max-w-md mx-4">
                        <div className="text-center">
                            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 via-pink-500 to-indigo-500 rounded-full mx-auto flex items-center justify-center mb-6 animate-pulse shadow-2xl shadow-purple-500/50">
                                <svg className="w-10 h-10 text-white animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-3">Generating Summary...</h3>
                            <p className="text-purple-200 mb-6">Preparing your call summary</p>
                            <div className="flex justify-center space-x-3">
                                <div className="w-3 h-3 bg-purple-400 rounded-full animate-bounce shadow-lg shadow-purple-400/50" style={{ animationDelay: '0ms' }}></div>
                                <div className="w-3 h-3 bg-pink-400 rounded-full animate-bounce shadow-lg shadow-pink-400/50" style={{ animationDelay: '150ms' }}></div>
                                <div className="w-3 h-3 bg-indigo-400 rounded-full animate-bounce shadow-lg shadow-indigo-400/50" style={{ animationDelay: '300ms' }}></div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
            
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 flex flex-col">
                    <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700 p-8 flex-1">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h3 className="text-2xl font-bold text-white">
                                    SuperBryn Voice
                                </h3>
                                <p className="text-sm text-slate-400 mt-1">Voice Assistant Active</p>
                            </div>
                            <div className="flex items-center space-x-3 bg-slate-900/50 px-4 py-2 rounded-lg border border-slate-700">
                                <div
                                    className={`w-2 h-2 rounded-full ${isAgentSpeaking ? 'bg-green-500 animate-pulse' : 'bg-slate-500'
                                        }`}
                                />
                                <span className="text-sm text-slate-300 font-medium">
                                    {isAgentSpeaking ? 'Speaking' : 'Listening'}
                                </span>
                            </div>
                        </div>

                        <AvatarDisplay />

                        <div className="mt-8 flex items-center justify-center space-x-6">
                            <button
                                onClick={toggleMute}
                                className={`p-5 rounded-full transition-all duration-300 transform hover:scale-110 shadow-lg ${isMuted
                                    ? 'bg-red-500/90 hover:bg-red-600 shadow-red-500/50'
                                    : 'bg-white/20 hover:bg-white/30 backdrop-blur-sm border border-white/30 shadow-purple-500/30'
                                    }`}
                                title={isMuted ? 'Unmute' : 'Mute'}
                            >
                                <svg
                                    className={`w-6 h-6 ${isMuted ? 'text-white' : 'text-purple-100'}`}
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    {isMuted ? (
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"
                                        />
                                    ) : (
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                                        />
                                    )}
                                </svg>
                            </button>

                            <button
                                onClick={endCall}
                                className="px-10 py-5 bg-gradient-to-r from-red-500 to-pink-500 hover:from-red-600 hover:to-pink-600 text-white rounded-full font-bold transition-all duration-300 flex items-center space-x-3 shadow-2xl shadow-red-500/50 hover:shadow-red-500/70 transform hover:scale-105"
                            >
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z"
                                    />
                                </svg>
                                <span>End Call</span>
                            </button>

                            <div className="px-5 py-3 backdrop-blur-sm bg-white/20 rounded-full border border-white/30">
                                <span className="text-base font-bold text-purple-100">
                                    {formatDuration(callDuration)}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
                                
                <div className="lg:col-span-1">
                    <div className="backdrop-blur-xl bg-white/10 rounded-3xl shadow-2xl border border-white/20 p-6 h-full flex flex-col">
                        <div className="mb-6 p-5 bg-gradient-to-r from-green-400/20 to-emerald-400/20 rounded-2xl border border-green-400/30 backdrop-blur-sm">
                            <div className="flex items-center justify-between mb-3">
                                <h4 className="text-sm font-bold text-green-300 flex items-center">
                                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    Call Cost
                                </h4>
                                <span className="px-2 py-1 text-xs font-medium bg-green-400/30 text-green-200 rounded-full">Live</span>
                            </div>
                            <div className="text-3xl font-bold text-green-300 mb-3">
                                ${costData?.total_usd?.toFixed(4) || '0.0000'}
                            </div>
                            {costData && (
                                <div className="space-y-2 text-xs text-green-200">
                                    <div className="flex justify-between p-2 bg-white/5 rounded-lg">
                                        <span>STT:</span>
                                        <span className="font-bold">${costData.breakdown?.stt_cost?.toFixed(4) || '0.0000'}</span>
                                    </div>
                                    <div className="flex justify-between p-2 bg-white/5 rounded-lg">
                                        <span>TTS:</span>
                                        <span className="font-bold">${costData.breakdown?.tts_cost?.toFixed(4) || '0.0000'}</span>
                                    </div>
                                    <div className="flex justify-between p-2 bg-white/5 rounded-lg">
                                        <span>LLM:</span>
                                        <span className="font-bold">
                                            ${((costData.breakdown?.llm_input_cost || 0) + (costData.breakdown?.llm_output_cost || 0)).toFixed(4)}
                                        </span>
                                    </div>
                                    <div className="flex justify-between p-2 bg-white/5 rounded-lg">
                                        <span>Connection:</span>
                                        <span className="font-bold">${costData.breakdown?.connection_cost?.toFixed(4) || '0.0000'}</span>
                                    </div>
                                    {costData.breakdown?.avatar_cost > 0 && (
                                        <div className="flex justify-between p-2 bg-white/5 rounded-lg">
                                            <span>Avatar:</span>
                                            <span className="font-bold">${costData.breakdown?.avatar_cost?.toFixed(4)}</span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <h3 className="text-lg font-bold text-purple-200 mb-4 flex items-center">
                            <svg
                                className="w-5 h-5 mr-2 text-purple-400"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                                />
                            </svg>
                            Activity Log
                        </h3>
                        <div className="flex-1 overflow-auto">
                            <ToolCallDisplay toolCalls={toolCalls} />
                        </div>
                    </div>
                </div>
            </div>

            <div className="mt-4 text-center text-sm text-purple-300/70">
                Room: {roomName}
            </div>

            {process.env.NODE_ENV === 'development' && <DebugPanel />}
        </div>
    );
}