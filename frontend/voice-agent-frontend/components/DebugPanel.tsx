'use client';

import { useState } from 'react';
import { useRoomContext, useParticipants, useTracks, useLocalParticipant } from '@livekit/components-react';
import { Track } from 'livekit-client';

export default function DebugPanel() {
    const [isOpen, setIsOpen] = useState(false);
    const room = useRoomContext();
    const participants = useParticipants();
    const { localParticipant } = useLocalParticipant();
    const allTracks = useTracks([
        Track.Source.Camera,
        Track.Source.Microphone,
        Track.Source.ScreenShare,
        Track.Source.ScreenShareAudio,
        Track.Source.Unknown
    ]);

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg hover:bg-gray-700 z-50"
            >
                🐛 Debug
            </button>
        );
    }

    return (
        <div className="fixed bottom-4 right-4 bg-gray-900 text-white p-4 rounded-lg shadow-2xl max-w-md max-h-96 overflow-auto z-50">
            <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-lg">LiveKit Debug Panel</h3>
                <button
                    onClick={() => setIsOpen(false)}
                    className="text-gray-400 hover:text-white"
                >
                    ✕
                </button>
            </div>

            <div className="space-y-4 text-xs">
                {/* Room Info */}
                <div>
                    <h4 className="font-semibold text-yellow-400 mb-1">Room</h4>
                    <div className="bg-gray-800 p-2 rounded">
                        <div>Name: {room.name}</div>
                        <div>State: {room.state}</div>
                        <div>Participants: {participants.length}</div>
                    </div>
                </div>

                {/* Participants */}
                <div>
                    <h4 className="font-semibold text-green-400 mb-1">Participants ({participants.length})</h4>
                    <div className="space-y-2">
                        {participants.map((p) => (
                            <div key={p.identity} className="bg-gray-800 p-2 rounded">
                                <div className="font-medium text-blue-400">
                                    {p.identity}
                                    {p.identity === localParticipant?.identity && ' (You)'}
                                </div>
                                <div>Name: {p.name || 'N/A'}</div>
                                <div>Kind: {p.kind}</div>
                                <div>Is Local: {p.isLocal ? 'Yes' : 'No'}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Tracks */}
                <div>
                    <h4 className="font-semibold text-purple-400 mb-1">Tracks ({allTracks.length})</h4>
                    <div className="space-y-2">
                        {allTracks.map((t, i) => (
                            <div key={i} className="bg-gray-800 p-2 rounded">
                                <div className="font-medium text-orange-400">
                                    {t.source} - {t.participant.identity}
                                </div>
                                <div>Participant: {t.participant.name}</div>
                                <div>Kind: {t.publication.kind}</div>
                                <div>Subscribed: {t.publication.isSubscribed ? 'Yes' : 'No'}</div>
                                <div>Enabled: {t.publication.isEnabled ? 'Yes' : 'No'}</div>
                                <div>Muted: {t.publication.isMuted ? 'Yes' : 'No'}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

