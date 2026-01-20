export interface ToolCall {
  id: string;
  name: string;
  args: any;
  result: any;
  timestamp: string;
}

export interface Summary {
  text: string;
  duration_seconds: number;
  tool_calls_count: number;
  cost_breakdown: CostBreakdown;
}

export interface CostBreakdown {
  breakdown: {
    stt_cost: number;
    tts_cost: number;
    llm_input_cost: number;
    llm_output_cost: number;
    tools_cost: number;
    total_cost: number;
  };
  usage_stats: {
    stt_minutes: number;
    tts_characters: number;
    llm_input_tokens: number;
    llm_output_tokens: number;
    tool_calls: number;
  };
  total_usd: number;
}

export interface Appointment {
  id: string;
  user_id: string;
  date: string;
  time: string;
  name: string;
  purpose: string;
  status: 'confirmed' | 'cancelled';
  created_at: string;
}

export interface User {
  id: string;
  contact_number: string;
  name?: string;
  created_at: string;
}