'use client';

import { ToolCall } from '@/app/types';
import { useEffect, useRef } from 'react';

interface ToolCallDisplayProps {
    toolCalls: ToolCall[];
}

export default function ToolCallDisplay({ toolCalls }: ToolCallDisplayProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Auto-scroll to bottom when new tool call arrives
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [toolCalls]);

    const getToolIcon = (toolName: string): string => {
        const icons: Record<string, string> = {
            identify_user: '👤',
            fetch_slots: '📅',
            book_appointment: '✅',
            retrieve_appointments: '🔍',
            cancel_appointment: '❌',
            modify_appointment: '✏️',
            end_conversation: '👋',
        };
        return icons[toolName] || '🔧';
    };

    const getToolColor = (toolName: string): string => {
        const colors: Record<string, string> = {
            identify_user: 'border-blue-500 bg-blue-50',
            fetch_slots: 'border-purple-500 bg-purple-50',
            book_appointment: 'border-green-500 bg-green-50',
            retrieve_appointments: 'border-yellow-500 bg-yellow-50',
            cancel_appointment: 'border-red-500 bg-red-50',
            modify_appointment: 'border-orange-500 bg-orange-50',
            end_conversation: 'border-gray-500 bg-gray-50',
        };
        return colors[toolName] || 'border-gray-500 bg-gray-50';
    };

    const formatToolName = (toolName: string): string => {
        return toolName
            .split('_')
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    };

    const formatTime = (timestamp: string): string => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    };

    return (
        <div
            ref={scrollRef}
            className="space-y-3 overflow-y-auto max-h-[500px] pr-2 custom-scrollbar"
        >
            {toolCalls.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                    <svg
                        className="w-12 h-12 mx-auto mb-3 opacity-50"
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
                    <p className="text-sm">No activity yet</p>
                    <p className="text-xs mt-1">Tool calls will appear here</p>
                </div>
            ) : (
                toolCalls.map((call, index) => (
                    <div
                        key={call.id || index}
                        className={`border-l-4 rounded-lg p-4 shadow-sm transition-all duration-300 animate-slide-in ${getToolColor(
                            call.name
                        )}`}
                        style={{ animationDelay: `${index * 0.05}s` }}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center space-x-2">
                                <span className="text-2xl">{getToolIcon(call.name)}</span>
                                <span className="font-semibold text-gray-800 text-sm">
                                    {formatToolName(call.name)}
                                </span>
                            </div>
                            <span className="text-xs text-gray-500">
                                {formatTime(call.timestamp)}
                            </span>
                        </div>

                        {/* Tool-specific content */}
                        <div className="text-sm text-gray-700 space-y-1">
                            {call.name === 'identify_user' && (
                                <div>
                                    <p className="text-xs text-gray-500 mb-1">Phone Number:</p>
                                    <p className="font-medium">{call.args?.phone_number}</p>
                                    {call.result?.success && (
                                        <p className="text-green-600 text-xs mt-1">✓ User identified</p>
                                    )}
                                </div>
                            )}

                            {call.name === 'fetch_slots' && (
                                <div>
                                    <p className="text-xs text-gray-500 mb-1">Date: {call.args?.date}</p>
                                    {call.result?.available_slots && (
                                        <div className="mt-2">
                                            <p className="text-xs text-gray-500 mb-1">
                                                Available slots ({call.result.total_slots}):
                                            </p>
                                            <div className="flex flex-wrap gap-1">
                                                {call.result.available_slots.map((slot: string) => (
                                                    <span
                                                        key={slot}
                                                        className="px-2 py-1 bg-white rounded text-xs font-medium border border-gray-200"
                                                    >
                                                        {slot}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {call.name === 'book_appointment' && (
                                <div>
                                    <div className="space-y-1">
                                        <p>
                                            <span className="text-xs text-gray-500">Name:</span>{' '}
                                            <span className="font-medium">{call.args?.name}</span>
                                        </p>
                                        <p>
                                            <span className="text-xs text-gray-500">Date:</span>{' '}
                                            <span className="font-medium">{call.args?.date}</span>
                                        </p>
                                        <p>
                                            <span className="text-xs text-gray-500">Time:</span>{' '}
                                            <span className="font-medium">{call.args?.time}</span>
                                        </p>
                                        <p>
                                            <span className="text-xs text-gray-500">Purpose:</span>{' '}
                                            <span className="font-medium">{call.args?.purpose}</span>
                                        </p>
                                    </div>
                                    {call.result?.success ? (
                                        <div className="mt-2 p-2 bg-green-100 border border-green-300 rounded text-xs">
                                            <p className="text-green-800 font-medium">✓ Appointment Booked!</p>
                                            <p className="text-green-700 text-xs">ID: {call.result.appointment_id?.slice(0, 8)}...</p>
                                        </div>
                                    ) : call.result?.error ? (
                                        <div className="mt-2 p-2 bg-red-100 border border-red-300 rounded text-xs">
                                            <p className="text-red-800">✗ {call.result.error}</p>
                                        </div>
                                    ) : null}
                                </div>
                            )}

                            {call.name === 'retrieve_appointments' && (
                                <div>
                                    {call.result?.appointments && call.result.appointments.length > 0 ? (
                                        <div className="space-y-2 mt-2">
                                            <p className="text-xs text-gray-500">
                                                Found {call.result.total} appointment(s):
                                            </p>
                                            {call.result.appointments.map((appt: any, i: number) => (
                                                <div
                                                    key={i}
                                                    className="p-2 bg-white rounded border border-gray-200 text-xs"
                                                >
                                                    <p className="font-medium">{appt.name}</p>
                                                    <p className="text-gray-600">
                                                        {appt.date} at {appt.time}
                                                    </p>
                                                    <p className="text-gray-500">{appt.purpose}</p>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-gray-500 text-xs">No appointments found</p>
                                    )}
                                </div>
                            )}

                            {call.name === 'cancel_appointment' && (
                                <div>
                                    <p className="text-xs text-gray-500 mb-1">
                                        Appointment ID: {call.args?.appointment_id?.slice(0, 8)}...
                                    </p>
                                    {call.result?.success && (
                                        <p className="text-red-600 text-xs mt-1">✓ Appointment cancelled</p>
                                    )}
                                </div>
                            )}

                            {call.name === 'modify_appointment' && (
                                <div>
                                    <p className="text-xs text-gray-500 mb-1">
                                        Rescheduled to: {call.args?.new_date} at {call.args?.new_time}
                                    </p>
                                    {call.result?.success && (
                                        <p className="text-orange-600 text-xs mt-1">✓ Appointment modified</p>
                                    )}
                                </div>
                            )}

                            {call.name === 'end_conversation' && (
                                <div>
                                    <p className="text-gray-600 text-xs">Conversation ended</p>
                                </div>
                            )}
                        </div>
                    </div>
                ))
            )}
        </div>
    );
}