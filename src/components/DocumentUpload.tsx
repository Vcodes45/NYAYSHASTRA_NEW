import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Progress } from './ui/progress';

interface UploadedDocument {
  id: string;
  name: string;
  size: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  summary?: DocumentSummary;
  error?: string;
}

interface DocumentSummary {
  caseSummary: string[];
  keyArguments: string[];
  verdict: string;
  citedSections: Array<{ act: string; section: string }>;
  parties?: string;
  courtName?: string;
  date?: string;
  complainant?: string;
  accused?: string;
  caseType?: string;
}

interface DocumentUploadProps {
  language: 'en' | 'hi';
  onDocumentProcessed?: (summary: DocumentSummary) => void;
}

export const DocumentUpload = ({ language, onDocumentProcessed }: DocumentUploadProps) => {
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      processFiles(files);
    }
  }, []);

  const processFiles = (files: File[]) => {
    files.forEach((file) => {
      if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
        const doc: UploadedDocument = {
          id: Math.random().toString(36).substr(2, 9),
          name: file.name,
          size: file.size,
          status: 'uploading',
          progress: 0,
        };
        
        setDocuments((prev) => [...prev, doc]);

        // Use real API for upload and processing
        simulateProcessing(doc.id, file);
      }
    });
  };

  const simulateProcessing = async (docId: string, file: File) => {
    try {
      // Use real API for upload
      const formData = new FormData();
      formData.append('file', file);
      
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const data = await response.json();
      const serverDocId = data.document_id;
      
      // Update to processing state
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === docId ? { ...d, status: 'processing', progress: 100 } : d
        )
      );
      
      // Poll for status
      const pollStatus = async () => {
        try {
          const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
          const statusResponse = await fetch(`${apiUrl}/api/documents/status/${serverDocId}`);
          if (!statusResponse.ok) {
            throw new Error('Status check failed');
          }
          
          const statusData = await statusResponse.json();
          
          if (statusData.status === 'completed' && statusData.summary) {
            const summary: DocumentSummary = {
              caseSummary: statusData.summary.case_summary || [],
              keyArguments: statusData.summary.key_arguments || [],
              verdict: statusData.summary.verdict || 'Processing completed',
              citedSections: (statusData.summary.cited_sections || []).map((s: any) => ({
                act: s.act || 'IPC',
                section: s.section || ''
              })),
              parties: statusData.summary.parties,
              courtName: statusData.summary.court_name,
              date: statusData.summary.date,
              complainant: statusData.summary.complainant,
              accused: statusData.summary.accused,
              caseType: statusData.summary.case_type,
            };
            
            setDocuments((prev) =>
              prev.map((d) =>
                d.id === docId ? { ...d, status: 'completed', summary } : d
              )
            )
            
            onDocumentProcessed?.(summary);
          } else if (statusData.status === 'error') {
            throw new Error(statusData.error_message || 'Processing failed');
          } else {
            // Still processing, poll again
            setTimeout(() => pollStatus(), 2000);
          }
        } catch (pollError: any) {
          console.error('Polling error:', pollError);
          setDocuments((prev) =>
            prev.map((d) =>
              d.id === docId ? { ...d, status: 'error', error: pollError.message } : d
            )
          );
        }
      };
      
      pollStatus();
    } catch (error: any) {
      console.error('Document processing error:', error);
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === docId ? { ...d, status: 'error', error: error.message } : d
        )
      );
    }
  };

  const removeDocument = (docId: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== docId));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="glass-strong rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary" />
          {language === 'en' ? 'Document Summarization' : 'दस्तावेज़ सारांश'}
        </h3>
        <p className="text-xs text-muted-foreground mt-1">
          {language === 'en' 
            ? 'Upload court orders, judgments, or legal documents for AI analysis'
            : 'AI विश्लेषण के लिए अदालती आदेश, निर्णय या कानूनी दस्तावेज़ अपलोड करें'}
        </p>
      </div>

      {/* Upload Area */}
      <div className="p-4">
        <motion.div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          animate={{
            scale: isDragging ? 1.02 : 1,
            borderColor: isDragging ? 'hsl(var(--primary))' : 'hsl(var(--border))',
          }}
          className={`relative rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
            isDragging ? 'bg-primary/5' : 'bg-muted/20'
          }`}
        >
          <input
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFileSelect}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          <Upload className={`h-10 w-10 mx-auto mb-3 ${isDragging ? 'text-primary' : 'text-muted-foreground'}`} />
          <p className="text-sm text-foreground font-medium">
            {language === 'en' ? 'Drop PDF files here or click to browse' : 'PDF फ़ाइलें यहाँ छोड़ें या ब्राउज़ करने के लिए क्लिक करें'}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {language === 'en' ? 'Supports court orders, judgments, FIRs, and legal notices' : 'अदालती आदेश, निर्णय, FIR और कानूनी नोटिस का समर्थन करता है'}
          </p>
        </motion.div>
      </div>

      {/* Document List */}
      <AnimatePresence>
        {documents.length > 0 && (
          <div className="border-t border-border p-4 space-y-3">
            {documents.map((doc) => (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="rounded-xl border border-border bg-card/50 overflow-hidden"
              >
                {/* Document Header */}
                <div className="flex items-center gap-3 p-3">
                  <div className={`p-2 rounded-lg ${
                    doc.status === 'completed' ? 'bg-accent/20' : 
                    doc.status === 'error' ? 'bg-destructive/20' : 
                    'bg-primary/20'
                  }`}>
                    {doc.status === 'uploading' && <Loader2 className="h-4 w-4 text-primary animate-spin" />}
                    {doc.status === 'processing' && <Loader2 className="h-4 w-4 text-primary animate-spin" />}
                    {doc.status === 'completed' && <CheckCircle className="h-4 w-4 text-accent" />}
                    {doc.status === 'error' && <AlertCircle className="h-4 w-4 text-destructive" />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{doc.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(doc.size)} • 
                      {doc.status === 'uploading' && (language === 'en' ? ' Uploading...' : ' अपलोड हो रहा है...')}
                      {doc.status === 'processing' && (language === 'en' ? ' AI Processing...' : ' AI प्रसंस्करण...')}
                      {doc.status === 'completed' && (language === 'en' ? ' Analysis Complete' : ' विश्लेषण पूर्ण')}
                      {doc.status === 'error' && (
                        <span>
                          {language === 'en' ? ' Error' : ' त्रुटि'}
                          {doc.error && `: ${doc.error}`}
                        </span>
                      )}
                    </p>
                  </div>

                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 shrink-0"
                    onClick={() => removeDocument(doc.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {/* Progress Bar */}
                {(doc.status === 'uploading' || doc.status === 'processing') && (
                  <div className="px-3 pb-3">
                    <Progress value={doc.status === 'processing' ? 100 : doc.progress} className="h-1" />
                  </div>
                )}

                {/* Summary */}
                {doc.status === 'completed' && doc.summary && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="border-t border-border p-5 space-y-5"
                  >
                    {/* Case Type Badge */}
                    {doc.summary.caseType && (
                      <div className="flex justify-center">
                        <span className="inline-flex items-center gap-2 bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-700 px-4 py-2 rounded-full text-sm font-semibold border border-amber-500/30">
                          <span>⚖️</span>
                          {doc.summary.caseType}
                        </span>
                      </div>
                    )}

                    {/* Parties - Complainant vs Accused */}
                    {(doc.summary.complainant || doc.summary.accused) && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gradient-to-r from-green-500/10 via-transparent to-red-500/10 rounded-xl border border-border/50">
                        {doc.summary.complainant && (
                          <div className="flex items-start gap-3 p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                            <span className="text-2xl">👤</span>
                            <div>
                              <p className="text-xs uppercase font-bold text-green-600 mb-1">
                                {language === 'en' ? 'Complainant / Petitioner' : 'शिकायतकर्ता'}
                              </p>
                              <p className="text-sm font-medium text-foreground">{doc.summary.complainant}</p>
                            </div>
                          </div>
                        )}
                        {doc.summary.accused && (
                          <div className="flex items-start gap-3 p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                            <span className="text-2xl">👤</span>
                            <div>
                              <p className="text-xs uppercase font-bold text-red-600 mb-1">
                                {language === 'en' ? 'Accused / Respondent' : 'आरोपी / प्रतिवादी'}
                              </p>
                              <p className="text-sm font-medium text-foreground">{doc.summary.accused}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Court, Date & Parties Header */}
                    <div className="flex flex-wrap gap-3 pb-4 border-b border-border/50">
                      {doc.summary.courtName && (
                        <div className="flex items-center gap-2 bg-secondary/20 px-4 py-2 rounded-lg">
                          <span className="text-lg">🏛️</span>
                          <span className="text-sm font-medium text-secondary">{doc.summary.courtName}</span>
                        </div>
                      )}
                      {doc.summary.date && (
                        <div className="flex items-center gap-2 bg-muted px-4 py-2 rounded-lg">
                          <span className="text-lg">📅</span>
                          <span className="text-sm font-medium text-muted-foreground">{doc.summary.date}</span>
                        </div>
                      )}
                      {doc.summary.parties && (
                        <div className="flex items-center gap-2 bg-blue-500/10 px-4 py-2 rounded-lg">
                          <span className="text-lg">👥</span>
                          <span className="text-sm font-medium text-blue-600">{doc.summary.parties}</span>
                        </div>
                      )}
                    </div>

                    {/* Case Summary Box - Main highlight */}
                    {doc.summary.caseSummary && doc.summary.caseSummary.length > 0 && (
                      <div className="rounded-xl bg-gradient-to-br from-primary/10 via-primary/5 to-transparent border border-primary/20 p-5">
                        <div className="flex items-center gap-2 mb-4">
                          <span className="text-xl">📋</span>
                          <h4 className="text-base font-bold text-foreground">
                            {language === 'en' ? 'What Happened in This Case' : 'इस केस में क्या हुआ'}
                          </h4>
                        </div>
                        <ul className="space-y-3">
                          {doc.summary.caseSummary.map((point, idx) => (
                            <li key={idx} className="flex items-start gap-3">
                              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 text-primary text-sm font-bold flex items-center justify-center">
                                {idx + 1}
                              </span>
                              <span className="text-sm text-foreground leading-relaxed">{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Key Arguments Section */}
                    {doc.summary.keyArguments && doc.summary.keyArguments.length > 0 && (
                      <div className="rounded-xl bg-muted/50 border border-border p-5">
                        <div className="flex items-center gap-2 mb-4">
                          <span className="text-xl">⚖️</span>
                          <h4 className="text-base font-bold text-foreground">
                            {language === 'en' ? 'Key Arguments' : 'मुख्य तर्क'}
                          </h4>
                        </div>
                        <ul className="space-y-3">
                          {doc.summary.keyArguments.map((arg, idx) => (
                            <li key={idx} className="flex items-start gap-3">
                              <span className="flex-shrink-0 text-primary text-lg">•</span>
                              <span className="text-sm text-muted-foreground leading-relaxed">{arg}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Verdict Section */}
                    <div className="rounded-xl bg-accent/15 border border-accent/30 p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-xl">🔨</span>
                        <h4 className="text-base font-bold text-accent">
                          {language === 'en' ? 'Verdict / Decision' : 'निर्णय'}
                        </h4>
                      </div>
                      <p className="text-sm text-foreground leading-relaxed">{doc.summary.verdict}</p>
                    </div>

                    {/* Cited Sections */}
                    {doc.summary.citedSections && doc.summary.citedSections.length > 0 && (
                      <div className="rounded-xl bg-muted/30 border border-border p-5">
                        <div className="flex items-center gap-2 mb-4">
                          <span className="text-xl">📜</span>
                          <h4 className="text-base font-bold text-foreground">
                            {language === 'en' ? 'Cited Legal Sections' : 'उद्धृत कानूनी धाराएं'}
                          </h4>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {doc.summary.citedSections.map((section, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center gap-1.5 text-sm font-medium bg-primary/20 text-primary px-4 py-2 rounded-lg border border-primary/30"
                            >
                              <span className="text-base">§</span>
                              {section.act} {section.section}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
