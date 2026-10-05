/**
 * NyayGuru AI Pro - Custom Hooks
 * React hooks for API integration and state management.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import * as api from "../services/api";
import {
  ChatMessage,
  ChatResponse,
  AgentStep,
  Statute,
  Citation,
  CaseLaw,
  IPCBNSMapping,
  DocumentStatus,
  transformStreamingResponse,
} from "../services/api";
import { useChatState } from "./useChatContext";

// ============== useChat Hook ==============

export interface UseChatOptions {
  language?: "en" | "hi";
  useStreaming?: boolean;
  onAgentUpdate?: (agent: string, status: string) => void;
}

export function useChat(options: UseChatOptions = {}) {
  const { language = "en", useStreaming = true, onAgentUpdate } = options;

  const {
    messages,
    setMessages,
    sessionId,
    setSessionId,
    currentStatutes,
    setCurrentStatutes,
    currentCitations,
    setCurrentCitations,
    currentCaseLaws,
    setCurrentCaseLaws,
    currentMappings,
    setCurrentMappings,
    clearChat: clearMessages,
  } = useChatState();

  const { getToken } = useAuth();
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [completedAgents, setCompletedAgents] = useState<string[]>([]);
  const [processingAgents, setProcessingAgents] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (content: string, domain?: string) => {
      if (!content.trim() || isProcessing) return;

      // Add user message
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: "user",
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsProcessing(true);
      setError(null);
      setCompletedAgents([]);
      setProcessingAgents([]);
      setActiveAgent(null);

      try {
        const token = (await getToken()) || undefined;

        if (useStreaming) {
          // Use streaming API
          let response: {
            content: string;
            contentHi?: string;
            citations: Citation[];
            statutes: Statute[];
            caseLaws: CaseLaw[];
            ipcBnsMappings: IPCBNSMapping[];
          } = {
            content: "",
            citations: [],
            statutes: [],
            caseLaws: [],
            ipcBnsMappings: [],
          };
          let detectedLang = "en";

          for await (const chunk of api.sendChatMessageStreaming(
            content,
            language,
            sessionId || undefined,
            token,
            domain,
          )) {
            switch (chunk.type) {
              case "start":
                setSessionId(chunk.data.session_id);
                break;

              case "agent_status":
                const agent = chunk.data.agent;
                const status = chunk.data.status;

                if (status === "processing") {
                  setActiveAgent(agent);
                  setProcessingAgents([agent]);
                  onAgentUpdate?.(agent, status);
                } else if (status === "completed") {
                  setCompletedAgents((prev) => [...prev, agent]);
                  setProcessingAgents([]);
                  onAgentUpdate?.(agent, status);
                }
                break;

              case "statutes":
                setCurrentStatutes(chunk.data.statutes || []);
                break;

              case "case_laws":
                setCurrentCaseLaws(chunk.data.case_laws || []);
                break;

              case "citations":
                setCurrentCitations(chunk.data.citations || []);
                break;

              case "response":
                // Transform raw backend response to camelCase
                response = transformStreamingResponse(chunk.data);
                detectedLang = chunk.data.detected_language || "en";
                break;

              case "complete":
                setActiveAgent(null);
                break;

              case "error":
                console.error("Server streamed an error:", chunk.data.message);
                // We'll still wait for the response chunk which will contain the fallback message
                break;
            }
          }

          // Add assistant message - use detected language to determine primary content
          const assistantMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            // If detected Hindi, show Hindi as primary content
            content:
              detectedLang === "hi" && response.contentHi
                ? response.contentHi
                : response.content || "",
            contentHindi: response.contentHi,
            citations: response.citations,
            statutes: response.statutes,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, assistantMessage]);
        } else {
          // Use regular API
          const response = await api.sendChatMessage(
            content,
            language,
            sessionId || undefined,
            token,
            domain,
          );


          setSessionId(response.sessionId);
          setCurrentStatutes(response.statutes);
          setCurrentCitations(response.citations);
          setCurrentCaseLaws(response.caseLaws);
          setCurrentMappings(response.ipcBnsMappings);

          // Simulate agent completion
          const agents = [
            "query",
            "statute",
            "case",
            "regulatory",
            "citation",
            "summary",
            "response",
          ];
          setCompletedAgents(agents);

          // Use detected language to determine primary content
          const detectedLang = response.detectedLanguage || "en";
          const assistantMessage: ChatMessage = {
            id: response.id,
            role: "assistant",
            // If detected Hindi, show Hindi as primary content
            content:
              detectedLang === "hi" && response.contentHi
                ? response.contentHi
                : response.content,
            contentHindi: response.contentHi,
            citations: response.citations,
            statutes: response.statutes,
            timestamp: new Date(response.timestamp),
          };
          setMessages((prev) => [...prev, assistantMessage]);
        }
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "An error occurred";
        setError(errorMessage);
        console.error("Chat error:", err);
      } finally {
        setIsProcessing(false);
        setActiveAgent(null);
        setProcessingAgents([]);
      }
    },
    [language, useStreaming, sessionId, isProcessing, onAgentUpdate],
  );

  const loadSession = useCallback(
    async (sId: string) => {
      setIsProcessing(true);
      setError(null);
      try {
        const token = (await getToken()) || undefined;
        const data = await api.getSessionMessages(sId, token);
        setMessages(data.messages);
        setSessionId(data.sessionId);
        return data;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to load session";
        setError(errorMessage);
      } finally {
        setIsProcessing(false);
      }
    },
    [getToken, setMessages, setSessionId],
  );

  return {
    messages,
    isProcessing,
    activeAgent,
    completedAgents,
    processingAgents,
    currentStatutes,
    currentCitations,
    currentCaseLaws,
    currentMappings,
    sessionId,
    error,
    sendMessage,
    clearMessages,
    loadSession,
  };
}

// ============== useDocumentUpload Hook ==============

export function useDocumentUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [documents, setDocuments] = useState<Map<string, DocumentStatus>>(
    new Map(),
  );
  const [error, setError] = useState<string | null>(null);

  const pollingIntervals = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const uploadDocument = useCallback(async (file: File) => {
    setIsUploading(true);
    setError(null);

    try {
      const result = await api.uploadDocument(file);

      // Add to documents map with initial status
      setDocuments((prev) => {
        const newMap = new Map(prev);
        newMap.set(result.documentId, {
          documentId: result.documentId,
          filename: result.filename,
          status: "pending",
          progress: 10,
        });
        return newMap;
      });

      // Start polling for status
      startPolling(result.documentId);

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Upload failed";
      setError(errorMessage);
      throw err;
    } finally {
      setIsUploading(false);
    }
  }, []);

  const startPolling = useCallback((documentId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await api.getDocumentStatus(documentId);

        setDocuments((prev) => {
          const newMap = new Map(prev);
          newMap.set(documentId, status);
          return newMap;
        });

        // Stop polling if completed or error
        if (status.status === "completed" || status.status === "error") {
          clearInterval(interval);
          pollingIntervals.current.delete(documentId);
        }
      } catch (err) {
        console.error("Status polling error:", err);
      }
    }, 1000);

    pollingIntervals.current.set(documentId, interval);
  }, []);

  const removeDocument = useCallback((documentId: string) => {
    // Clear polling
    const interval = pollingIntervals.current.get(documentId);
    if (interval) {
      clearInterval(interval);
      pollingIntervals.current.delete(documentId);
    }

    // Remove from state
    setDocuments((prev) => {
      const newMap = new Map(prev);
      newMap.delete(documentId);
      return newMap;
    });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      pollingIntervals.current.forEach((interval) => clearInterval(interval));
    };
  }, []);

  return {
    isUploading,
    documents: Array.from(documents.values()),
    error,
    uploadDocument,
    removeDocument,
  };
}

// ============== useStatutes Hook ==============

export function useStatutes() {
  const [statutes, setStatutes] = useState<Statute[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatutes = useCallback(
    async (actCode?: string, domain?: string) => {
      setLoading(true);
      setError(null);

      try {
        const data = await api.getStatutes(actCode, domain);
        setStatutes(data);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch statutes";
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const searchStatutes = useCallback(
    async (query: string, actCodes?: string[]) => {
      setLoading(true);
      setError(null);

      try {
        const { results } = await api.searchStatutes(query, actCodes);
        setStatutes(results);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Search failed";
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return {
    statutes,
    loading,
    error,
    fetchStatutes,
    searchStatutes,
  };
}

// ============== useIPCBNSComparison Hook ==============

export function useIPCBNSComparison() {
  const [comparisons, setComparisons] = useState<IPCBNSMapping[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchComparisons = useCallback(
    async (ipcSection?: string, bnsSection?: string) => {
      setLoading(true);
      setError(null);

      try {
        const { comparisons: data } = await api.getIPCBNSComparisons(
          ipcSection,
          bnsSection,
        );
        setComparisons(data);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch comparisons";
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return {
    comparisons,
    loading,
    error,
    fetchComparisons,
  };
}

// ============== useChatHistory Hook ==============

export function useChatHistory() {
  const [sessions, setSessions] = useState<api.ChatSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { getToken, isSignedIn } = useAuth();

  const fetchHistory = useCallback(
    async (limit: number = 20) => {
      // Don't fetch if not signed in
      if (!isSignedIn) {
        setSessions([]);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const token = (await getToken()) || undefined;
        if (!token) {
          setSessions([]);
          return;
        }
        const data = await api.getChatHistory(limit, token);
        setSessions(data.sessions);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch history";
        setError(errorMessage);
        // Return empty array if backend not available
        setSessions([]);
      } finally {
        setLoading(false);
      }
    },
    [getToken, isSignedIn],
  );

  const loadSession = useCallback(
    async (sessionId: string) => {
      try {
        const token = (await getToken()) || undefined;
        const data = await api.getSessionMessages(sessionId, token);
        return data;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to load session";
        setError(errorMessage);
        throw err;
      }
    },
    [getToken],
  );

  const deleteSession = useCallback(
    async (sessionId: string) => {
      try {
        const token = (await getToken()) || undefined;
        await api.deleteSession(sessionId, token);
        // Remove from local state
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        return true;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to delete session";
        setError(errorMessage);
        return false;
      }
    },
    [getToken],
  );

  // Fetch history on mount and when sign-in status changes
  useEffect(() => {
    if (isSignedIn) {
      fetchHistory();
    } else {
      setSessions([]);
    }
  }, [isSignedIn]);

  return {
    sessions,
    loading,
    error,
    fetchHistory,
    loadSession,
    deleteSession,
  };
}

export default {
  useChat,
  useDocumentUpload,
  useStatutes,
  useIPCBNSComparison,
  useChatHistory,
};
