'use client';


import { useEffect, useRef, useState } from 'react';
import { useTracks, useLocalParticipant, useParticipants } from '@livekit/components-react';
import { Track } from 'livekit-client';

export default function AvatarDisplay() {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [hasVideo, setHasVideo] = useState(false);
    const { localParticipant } = useLocalParticipant();
    const participants = useParticipants();
    const [isVideoReady, setIsVideoReady] = useState(false);
    
    // Get ALL video tracks (Camera source) - don't filter yet
    const videoTracks = useTracks([Track.Source.Camera]);

    useEffect(() => {
        // Find the agent's video track
        const agentVideoTrack = videoTracks.find(
            (trackRef) => 
                trackRef.participant.identity === 'agent_avatar' ||
                trackRef.participant.identity === 'bey-avatar-agent' ||
                (trackRef.participant.identity !== localParticipant?.identity && 
                 trackRef.source === Track.Source.Camera)
        );

        if (!agentVideoTrack) {
            setHasVideo(false);
            return;
        }

        const track = agentVideoTrack.publication.track;
        const videoElement = videoRef.current;

        if (!track || !videoElement) {
            setHasVideo(false);
            return;
        }

        track.attach(videoElement);
        setHasVideo(true);

        if (!isVideoReady) {
            setIsVideoReady(true);
        }

        return () => {
            track.detach(videoElement);
        };
    }, [
        videoTracks.length,
        videoTracks[0]?.publication.trackSid, 
        localParticipant?.identity,
        isVideoReady
    ]); 

    return (
        <div className="relative w-full aspect-video bg-gradient-to-br from-indigo-100 to-purple-100 rounded-xl overflow-hidden">
            <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover ${hasVideo ? 'block' : 'hidden'}`}
            />
            
            {!hasVideo && (
                <div className="w-full h-full flex items-center justify-center">
                    <div className="relative">
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-32 h-32 bg-indigo-400 rounded-full animate-pulse opacity-20"></div>
                        </div>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-24 h-24 bg-purple-400 rounded-full animate-pulse opacity-30 animation-delay-150"></div>
                        </div>

                        <div className="relative w-20 h-20 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-full flex items-center justify-center shadow-xl">
                            <svg
                                className="w-10 h-10 text-white"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                                />
                            </svg>
                        </div>

                        <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 flex space-x-1">
                            {[...Array(5)].map((_, i) => (
                                <div
                                    key={i}
                                    className="w-1 bg-indigo-600 rounded-full animate-wave"
                                    style={{
                                        height: '20px',
                                        animationDelay: `${i * 0.1}s`,
                                    }}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            )}

            <div className="absolute bottom-4 left-4 flex items-center space-x-2 bg-black bg-opacity-50 px-3 py-2 rounded-full">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-white text-sm font-medium">Active</span>
            </div>
        </div>
    );
}
