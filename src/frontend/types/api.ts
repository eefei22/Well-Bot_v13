export interface ChatTurnRequest {
  text: string;
  user_id: string;
  conversation_id: string;
  session_id: string;
  trace_id: string;
}

export interface CardEnvelope {
  status: "ok" | "error";
  type: "card" | "error_card";
  title: string;
  body: string;
  meta: {
    kind: string;
  };
  persisted_ids?: {
    primary_id: string | null;
    extra: string[];
  };
  diagnostics?: {
    tool: string;
    duration_ms: number;
  };
  error_code?: string | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: Date;
  card?: CardEnvelope;
}

export interface TranscriptEvent {
  type: "partial" | "final";
  text: string;
  confidence?: number;
}

export interface SessionMetadata {
  user_id: string;
  conversation_id: string;
  session_id: string;
  trace_id: string;
}
