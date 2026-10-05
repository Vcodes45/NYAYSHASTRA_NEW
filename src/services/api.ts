/**
 * NyayGuru AI Pro - API Service
 * Handles all API communication with the backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Types
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  contentHindi?: string;
  citations?: Citation[];
  statutes?: Statute[];
  caseLaws?: CaseLaw[];
  ipcBnsMappings?: IPCBNSMapping[];
  agentPipeline?: AgentStep[];
  timestamp: Date;
}

export interface Citation {
  id: string;
  title: string;
  titleHi?: string;
  source:
    | "gazette"
    | "supreme_court"
    | "high_court"
    | "law_commission"
    | "indiankanoon";
  sourceName?: string;
  url: string;
  excerpt?: string;
  takeaway?: string;
  year?: number;
  court?: string;
  type?: string;
  isLandmark?: boolean;
  verified?: boolean;
}

export interface Statute {
  id: string | number;
  sectionNumber: string;
  actCode: string;
  actName: string;
  titleEn: string;
  titleHi?: string;
  contentEn: string;
  contentHi?: string;
  domain?: string;
  punishmentDescription?: string;
  isBailable?: boolean;
  isCognizable?: boolean;
}

export interface CaseLaw {
  id: string | number;
  caseNumber: string;
  caseName: string;
  caseNameHi?: string;
  court: string;
  courtName?: string;
  judgmentDate?: string;
  reportingYear?: number;
  summaryEn?: string;
  summaryHi?: string;
  isLandmark?: boolean;
  citationString?: string;
  sourceUrl?: string;
  keyHoldings?: string[];
  domain?: string;
}

export interface IPCBNSMapping {
  id: string;
  ipcSection: string;
  ipcTitle: string;
  ipcContent: string;
  bnsSection: string;
  bnsTitle: string;
  bnsContent: string;
  changes: Array<{ type: string; description: string }>;
  punishmentChange?: {
    old: string;
    new: string;
    increased: boolean;
  };
  mappingType?: string;
}

export interface AgentStep {
  agent: string;
  status: "pending" | "processing" | "completed" | "error";
  startedAt?: string;
  completedAt?: string;
  resultSummary?: string;
}

export interface AgentInfo {
  id: string;
  name: string;
  nameHi: string;
  description: string;
  descriptionHi?: string;
  color: string;
}

export interface ChatResponse {
  id: string;
  sessionId: string;
  role: string;
  content: string;
  contentHi?: string;
  citations: Citation[];
  statutes: Statute[];
  caseLaws: CaseLaw[];
  ipcBnsMappings: IPCBNSMapping[];
  agentPipeline: AgentStep[];
  detectedDomain?: string;
  detectedLanguage?: string;
  executionTimeSeconds?: number;
  timestamp: string;
}

export interface DocumentUploadResponse {
  documentId: string;
  filename: string;
  status: string;
  message: string;
}

export interface DocumentStatus {
  documentId: string;
  filename: string;
  status:
    | "pending"
    | "extracting"
    | "analyzing"
    | "summarizing"
    | "completed"
    | "error";
  progress: number;
  summary?: {
    keyArguments: string[];
    verdict?: string;
    citedSections: Array<{ act: string; section: string }>;
    parties?: string;
    courtName?: string;
    date?: string;
  };
  errorMessage?: string;
}

// API Functions

/**
 * Send a chat message and get a response
 */
export async function sendChatMessage(
  content: string,
  language: "en" | "hi" = "en",
  sessionId?: string,
  token?: string,
  domain?: string,
): Promise<ChatResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/api/chat/`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      content,
      language,
      session_id: sessionId,
      domain,
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  const data = await response.json();
  return transformChatResponse(data);
}

/**
 * Send a chat message with streaming updates
 */
export async function* sendChatMessageStreaming(
  content: string,
  language: "en" | "hi" = "en",
  sessionId?: string,
  token?: string,
  domain?: string,
): AsyncGenerator<{ type: string; data: any }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      content,
      language,
      session_id: sessionId,
      domain,
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          yield data;
        } catch (e) {
          console.error("Failed to parse SSE data:", e);
        }
      }
    }
  }
}

/**
 * Get all statutes
 */
export async function getStatutes(
  actCode?: string,
  domain?: string,
  limit: number = 20,
): Promise<Statute[]> {
  const params = new URLSearchParams();
  if (actCode) params.append("act_code", actCode);
  if (domain) params.append("domain", domain);
  params.append("limit", String(limit));

  const response = await fetch(`${API_BASE_URL}/api/statutes/?${params}`);
  if (!response.ok) throw new Error(`API error: ${response.statusText}`);

  const data = await response.json();
  return data.map(transformStatute);
}

/**
 * Search statutes
 */
export async function searchStatutes(
  query: string,
  actCodes?: string[],
  domain?: string,
  limit: number = 10,
): Promise<{ results: Statute[]; total: number }> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  if (actCodes) params.append("act_codes", actCodes.join(","));
  if (domain) params.append("domain", domain);

  const response = await fetch(`${API_BASE_URL}/api/statutes/search?${params}`);
  if (!response.ok) throw new Error(`API error: ${response.statusText}`);

  const data = await response.json();
  return {
    results: data.results.map(transformStatute),
    total: data.total,
  };
}

/**
 * Get a specific section
 */
export async function getSection(
  sectionNumber: string,
  actCode: string = "IPC",
): Promise<Statute> {
  const response = await fetch(
    `${API_BASE_URL}/api/statutes/section/${sectionNumber}?act_code=${actCode}`,
  );
  if (!response.ok) throw new Error(`API error: ${response.statusText}`);

  const data = await response.json();
  return transformStatute(data);
}

/**
 * Get IPC-BNS comparisons
 */
export async function getIPCBNSComparisons(
  ipcSection?: string,
  bnsSection?: string,
  searchQuery?: string,
): Promise<{ comparisons: IPCBNSMapping[]; total: number }> {
  const params = new URLSearchParams();
  if (ipcSection) params.append("ipc_section", ipcSection);
  if (bnsSection) params.append("bns_section", bnsSection);
  if (searchQuery) params.append("search_query", searchQuery);

  const response = await fetch(
    `${API_BASE_URL}/api/statutes/comparison?${params}`,
  );
  if (!response.ok) throw new Error(`API error: ${response.statusText}`);

  const data = await response.json();
  return {
    comparisons: data.comparisons.map(transformMapping),
    total: data.total,
  };
}

/**
 * Upload a document for analysis
 */
export async function uploadDocument(
  file: File,
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) throw new Error(`API error: ${response.statusText}`);

  const data = await response.json();
  return {
    documentId: data.document_id,
    filename: data.filename,
    status: data.status,
    message: data.message,
  };
}

/**
 * Get document status
 */
export async function getDocumentStatus(
  documentId: string,
): Promise<DocumentStatus> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/status/${documentId}`,
  );
  if (!response.ok) throw new Error(`API error: ${response.statusText}`);

  const data = await response.json();
  return {
    documentId: data.document_id,
    filename: data.filename,
    status: data.status,
    progress: data.progress,
    summary: data.summary
      ? {
          keyArguments: data.summary.key_arguments || [],
          verdict: data.summary.verdict,
          citedSections: data.summary.cited_sections || [],
          parties: data.summary.parties,
          courtName: data.summary.court_name,
          date: data.summary.date,
        }
      : undefined,
    errorMessage: data.error_message,
  };
}

/**
 * Get agent information
 */
export async function getAgents(): Promise<AgentInfo[]> {
  const response = await fetch(`${API_BASE_URL}/api/agents`);
  if (!response.ok) throw new Error(`API error: ${response.statusText}`);

  const data = await response.json();
  return data.agents.map((agent: any) => ({
    id: agent.id,
    name: agent.name,
    nameHi: agent.name_hi,
    description: agent.description,
    descriptionHi: agent.description_hi,
    color: agent.color,
  }));
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{
  status: string;
  version: string;
}> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) throw new Error(`API error: ${response.statusText}`);
  return response.json();
}

/**
 * Warm up the database by making a simple health check
 * This helps reduce cold start times for Neon PostgreSQL
 */
export async function warmUpDatabase(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/health`, { method: "GET" });
    // Also ping the statutes endpoint to warm up the DB connection
    await fetch(`${API_BASE_URL}/api/statutes/?limit=1`, { method: "GET" });
  } catch (e) {
    // Silently fail - this is just a warmup
    console.log("Database warmup in progress...");
  }
}

/**
 * Get dashboard stats summary
 */
export async function getDashboardStats(): Promise<{
  savedStatutes: number;
  casesAnalyzed: number;
  activeSessions: number;
}> {
  const response = await fetch(`${API_BASE_URL}/api/stats/summary`);
  if (!response.ok) throw new Error(`API error: ${response.statusText}`);
  return response.json();
}

// ============== Chat History API ==============

export interface ChatSession {
  id: string;
  title: string;
  date: string;
  messageCount: number;
  language?: string;
  domain?: string;
}

export interface ChatHistoryResponse {
  sessions: ChatSession[];
}

/**
 * Get chat history for the current user
 */
export async function getChatHistory(
  limit: number = 20,
  token?: string,
): Promise<ChatHistoryResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/chat/history?limit=${limit}`,
    {
      method: "GET",
      headers,
    },
  );

  if (response.status === 401) {
    // Auth not configured on backend — return empty rather than throwing
    return { sessions: [] };
  }

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get messages for a specific chat session
 */
export async function getSessionMessages(
  sessionId: string,
  token?: string,
): Promise<{ messages: ChatMessage[]; sessionId: string; domain: string }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/chat/history/${sessionId}`,
    {
      method: "GET",
      headers,
    },
  );

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  const data = await response.json();

  // Transform messages
  return {
    sessionId: data.sessionId,
    domain: data.domain || "all",
    messages: (data.messages || []).map((msg: any) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      contentHindi: msg.contentHindi,
      citations: msg.citations || [],
      timestamp: new Date(msg.timestamp),
    })),
  };
}

/**
 * Delete a chat session
 */
export async function deleteSession(
  sessionId: string,
  token?: string,
): Promise<{ success: boolean; message: string }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/chat/history/${sessionId}`,
    {
      method: "DELETE",
      headers,
    },
  );

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

// Transform functions (snake_case to camelCase)

function transformChatResponse(data: any): ChatResponse {
  return {
    id: data.id,
    sessionId: data.session_id,
    role: data.role,
    content: data.content,
    contentHi: data.content_hi,
    citations: (data.citations || []).map(transformCitation),
    statutes: (data.statutes || []).map(transformStatute),
    caseLaws: (data.case_laws || []).map(transformCaseLaw),
    ipcBnsMappings: (data.ipc_bns_mappings || []).map(transformMapping),
    agentPipeline: (data.agent_pipeline || []).map(transformAgentStep),
    detectedDomain: data.detected_domain,
    detectedLanguage: data.detected_language,
    executionTimeSeconds: data.execution_time_seconds,
    timestamp: data.timestamp,
  };
}

function transformCitation(data: any): Citation {
  return {
    id: data.id,
    title: data.title,
    titleHi: data.title_hi,
    source: data.source,
    sourceName: data.source_name,
    url: data.url,
    excerpt: data.excerpt,
    year: data.year,
    court: data.court,
    type: data.type,
    isLandmark: data.is_landmark,
    verified: data.verified,
  };
}

function transformStatute(data: any): Statute {
  return {
    id: data.id,
    sectionNumber: data.section_number,
    actCode: data.act_code,
    actName: data.act_name,
    titleEn: data.title_en,
    titleHi: data.title_hi,
    contentEn: data.content_en,
    contentHi: data.content_hi,
    domain: data.domain,
    punishmentDescription: data.punishment_description,
    isBailable: data.is_bailable,
    isCognizable: data.is_cognizable,
  };
}

function transformCaseLaw(data: any): CaseLaw {
  return {
    id: data.id,
    caseNumber: data.case_number,
    caseName: data.case_name,
    caseNameHi: data.case_name_hi,
    court: data.court,
    courtName: data.court_name,
    judgmentDate: data.judgment_date,
    reportingYear: data.reporting_year,
    summaryEn: data.summary_en,
    summaryHi: data.summary_hi,
    isLandmark: data.is_landmark,
    citationString: data.citation_string,
    sourceUrl: data.source_url,
    keyHoldings: data.key_holdings,
    domain: data.domain,
  };
}

function transformMapping(data: any): IPCBNSMapping {
  return {
    id: data.id,
    ipcSection: data.ipc_section,
    ipcTitle: data.ipc_title,
    ipcContent: data.ipc_content,
    bnsSection: data.bns_section,
    bnsTitle: data.bns_title,
    bnsContent: data.bns_content,
    changes: data.changes || [],
    punishmentChange: data.punishment_change,
    mappingType: data.mapping_type,
  };
}

function transformAgentStep(data: any): AgentStep {
  return {
    agent: data.agent,
    status: data.status,
    startedAt: data.started_at,
    completedAt: data.completed_at,
    resultSummary: data.result_summary,
  };
}

/**
 * Transform streaming response data from snake_case to camelCase
 * This is needed because streaming responses come in raw backend format
 */
export function transformStreamingResponse(data: any): {
  content: string;
  contentHi?: string;
  citations: Citation[];
  statutes: Statute[];
  caseLaws: CaseLaw[];
  ipcBnsMappings: IPCBNSMapping[];
} {
  return {
    content: data.content || "",
    contentHi: data.content_hi,
    citations: (data.citations || []).map(transformCitation),
    statutes: (data.statutes || []).map(transformStatute),
    caseLaws: (data.case_laws || []).map(transformCaseLaw),
    ipcBnsMappings: (data.ipc_bns_mappings || []).map(transformMapping),
  };
}

export default {
  sendChatMessage,
  sendChatMessageStreaming,
  getStatutes,
  searchStatutes,
  getSection,
  getIPCBNSComparisons,
  uploadDocument,
  getDocumentStatus,
  getAgents,
  healthCheck,
};
