'use client';

import ReactMarkdown from 'react-markdown';

interface CallSummaryProps {
    summary: {
        text: string;
        duration_seconds: number;
        tool_calls_count: number;
        cost_breakdown: {
            breakdown: {
                stt_cost: number;
                tts_cost: number;
                llm_input_cost: number;
                llm_output_cost: number;
                tools_cost: number;
                connection_cost: number;
                avatar_cost: number;
                total_cost: number;
            };
            usage_stats: {
                stt_minutes: number;
                tts_characters: number;
                llm_input_tokens: number;
                llm_output_tokens: number;
                tool_calls: number;
                connection_minutes: number;
                avatar_minutes: number;
            };
            total_usd: number;
        };
    } | null;
    onReset: () => void;
}

export default function CallSummary({ summary, onReset }: CallSummaryProps) {
    const formatDuration = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}m ${secs}s`;
    };

    if (!summary) {
        return (
            <div className="max-w-4xl mx-auto bg-slate-800/90 rounded-2xl shadow-2xl border border-slate-700 p-12 text-center">
                <h2 className="text-2xl font-bold text-white mb-4">Call Ended</h2>
                <p className="text-slate-400 mb-6">No summary available</p>
                <button
                    onClick={onReset}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                    Start New Call
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            {/* Header */}
            <div className="bg-slate-800/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700 p-8">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-3xl font-bold text-white">Call Summary</h2>
                        <p className="text-slate-400 mt-1">
                            Duration: {formatDuration(summary.duration_seconds)} • {summary.tool_calls_count} actions
                        </p>
                    </div>
                    <div className="w-16 h-16 bg-green-600/20 rounded-full flex items-center justify-center border border-green-600/30">
                        <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                </div>

                {/* Summary Text with Markdown */}
                <div className="bg-slate-900/50 rounded-lg p-6 mb-6 border border-slate-700">
                    <h3 className="font-semibold text-white mb-3 flex items-center">
                        <svg className="w-5 h-5 mr-2 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Conversation Summary
                    </h3>
                    <div className="text-slate-300 leading-relaxed">
                        <ReactMarkdown
                            components={{
                                h1: ({ node, ...props }) => <h1 className="text-2xl font-bold text-white mt-4 mb-2" {...props} />,
                                h2: ({ node, ...props }) => <h2 className="text-xl font-bold text-white mt-3 mb-2" {...props} />,
                                h3: ({ node, ...props }) => <h3 className="text-lg font-bold text-white mt-2 mb-1" {...props} />,
                                p: ({ node, ...props }) => <p className="text-slate-300 mb-2" {...props} />,
                                strong: ({ node, ...props }) => <strong className="text-white font-semibold" {...props} />,
                                ul: ({ node, ...props }) => <ul className="list-disc list-inside space-y-1 my-2" {...props} />,
                                li: ({ node, ...props }) => <li className="text-slate-300" {...props} />,
                            }}
                        >
                            {summary.text}
                        </ReactMarkdown>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div className="bg-blue-600/20 rounded-lg p-4 border border-blue-600/30">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-blue-400 font-medium">Duration</p>
                                <p className="text-2xl font-bold text-white">
                                    {formatDuration(summary.duration_seconds)}
                                </p>
                            </div>
                            <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                    </div>

                    <div className="bg-purple-600/20 rounded-lg p-4 border border-purple-600/30">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-purple-400 font-medium">Actions</p>
                                <p className="text-2xl font-bold text-white">{summary.tool_calls_count}</p>
                            </div>
                            <svg className="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                    </div>

                    <div className="bg-green-600/20 rounded-lg p-4 border border-green-600/30">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-green-400 font-medium">Status</p>
                                <p className="text-2xl font-bold text-white">Complete</p>
                            </div>
                            <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                    </div>
                </div>

                {/* Cost Breakdown */}
                {summary.cost_breakdown && (
                    <div className="bg-gradient-to-r from-amber-600/20 to-orange-600/20 rounded-lg p-6 border border-amber-600/30">
                        <h3 className="font-semibold text-white mb-4 flex items-center">
                            <svg className="w-5 h-5 mr-2 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Cost Breakdown
                        </h3>

                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
                            <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                                <p className="text-xs text-slate-400">Speech-to-Text</p>
                                <p className="text-lg font-bold text-white">
                                    ${summary.cost_breakdown.breakdown.stt_cost.toFixed(4)}
                                </p>
                                <p className="text-xs text-slate-400">
                                    {summary.cost_breakdown.usage_stats.stt_minutes.toFixed(2)} min
                                </p>
                            </div>

                            <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                                <p className="text-xs text-slate-400">Text-to-Speech</p>
                                <p className="text-lg font-bold text-white">
                                    ${summary.cost_breakdown.breakdown.tts_cost.toFixed(4)}
                                </p>
                                <p className="text-xs text-slate-400">
                                    {summary.cost_breakdown.usage_stats.tts_characters} chars
                                </p>
                            </div>

                            <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                                <p className="text-xs text-slate-400">LLM (Input)</p>
                                <p className="text-lg font-bold text-white">
                                    ${summary.cost_breakdown.breakdown.llm_input_cost.toFixed(4)}
                                </p>
                                <p className="text-xs text-slate-400">
                                    {summary.cost_breakdown.usage_stats.llm_input_tokens} tokens
                                </p>
                            </div>

                            <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                                <p className="text-xs text-slate-400">LLM (Output)</p>
                                <p className="text-lg font-bold text-white">
                                    ${summary.cost_breakdown.breakdown.llm_output_cost.toFixed(4)}
                                </p>
                                <p className="text-xs text-slate-400">
                                    {summary.cost_breakdown.usage_stats.llm_output_tokens} tokens
                                </p>
                            </div>

                            <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                                <p className="text-xs text-slate-400">Tool Calls</p>
                                <p className="text-lg font-bold text-white">
                                    ${summary.cost_breakdown.breakdown.tools_cost.toFixed(4)}
                                </p>
                                <p className="text-xs text-slate-400">
                                    {summary.cost_breakdown.usage_stats.tool_calls} calls
                                </p>
                            </div>

                            <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                                <p className="text-xs text-slate-400">Connection</p>
                                <p className="text-lg font-bold text-white">
                                    ${summary.cost_breakdown.breakdown.connection_cost.toFixed(4)}
                                </p>
                                <p className="text-xs text-slate-400">
                                    {summary.cost_breakdown.usage_stats.connection_minutes.toFixed(2)} min
                                </p>
                            </div>

                            {summary.cost_breakdown.breakdown.avatar_cost > 0 && (
                                <div className="bg-slate-900/50 rounded p-3 border border-slate-700">
                                    <p className="text-xs text-slate-400">Avatar Video</p>
                                    <p className="text-lg font-bold text-white">
                                        ${summary.cost_breakdown.breakdown.avatar_cost.toFixed(4)}
                                    </p>
                                    <p className="text-xs text-slate-400">
                                        {summary.cost_breakdown.usage_stats.avatar_minutes.toFixed(2)} min
                                    </p>
                                </div>
                            )}

                            <div className="bg-gradient-to-br from-amber-600 to-orange-600 rounded p-3 border-2 border-amber-500">
                                <p className="text-xs text-amber-100 font-medium">TOTAL COST</p>
                                <p className="text-2xl font-bold text-white">
                                    ${summary.cost_breakdown.total_usd.toFixed(4)}
                                </p>
                            </div>
                        </div>

                        <p className="text-xs text-slate-400 italic">
                            * Estimated costs based on current API pricing
                        </p>
                    </div>
                )}
            </div>

            {/* Actions */}
            <div className="flex justify-center">
                <button
                    onClick={onReset}
                    className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold transition-all shadow-lg hover:shadow-xl flex items-center space-x-2"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Start New Call</span>
                </button>
            </div>
        </div>
    );
}
