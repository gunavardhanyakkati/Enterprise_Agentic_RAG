import React, { useState, useEffect } from "react";
import {
  Upload,
  Cpu,
  AlertCircle,
  Clock,
  Sparkles,
  FileText,
  MessageSquare,
  ShieldCheck,
  Zap,
  Download,
  Database,
  HelpCircle,
  Check,
  TrendingUp,
} from "lucide-react";
import { api, Document, AgentExecution } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// Interface for pipeline nodes
interface PipelineNode {
  id: string;
  label: string;
  icon: React.ElementType;
  status: "idle" | "running" | "success" | "error";
  durationMs?: number;
  tokensUsed?: number;
  confidence?: number;
}

// Preloaded mock data for sandbox demonstration
const SAMPLE_DOCUMENT_MOCK: Partial<Document> & {
  classification_reasoning: string[];
  compliance_reasoning: string[];
  confidence_reasoning: Record<string, number>;
  executive_report?: any;
} = {
  document_id: "demo-vendor-agreement-2026",
  title: "Global Logistics Master Services Agreement 2026",
  document_type: "Vendor Agreement",
  classification_confidence: 0.965,
  classification_reasoning: [
    "Identified recurring references to 'carrier liability' and 'freight forwarding' fees.",
    "Presence of standard master logistics services delivery framework.",
    "Signature section contains standard buyer-supplier indemnity clauses."
  ],
  compliance_reasoning: [
    "90 days termination notice is shorter than the recommended enterprise standard of 120 days.",
    "Complete omission of disaster recovery and backup systems standard compliance clauses."
  ],
  confidence_reasoning: {
    "document_structure": 0.98,
    "keyword_match": 0.95,
    "semantic_similarity": 0.94,
    "llm_consistency": 0.97
  },
  extracted_metadata: {
    "effective_date": { "value": "2026-01-15", "confidence": 0.99, "source": "Section 1.1 (p. 1)" },
    "termination_notice_period": { "value": "90 Days", "confidence": 0.92, "source": "Section 14.2 (p. 8)" },
    "governing_law": { "value": "State of New York", "confidence": 0.98, "source": "Section 22.1 (p. 12)" },
    "liability_cap": { "value": "$10,000,000 USD", "confidence": 0.95, "source": "Section 10.4 (p. 6)" },
    "supplier_legal_entity": { "value": "SwiftStream Logistics LLC", "confidence": 0.97, "source": "Preamble (p. 1)" }
  },
  compliance_report: {
    document_type: "Vendor Agreement",
    risk_score: 72,
    summary: "The document is mostly compliant, but contains partial notice period ambiguities and lacks explicit business continuity definitions.",
    recommendations: [
      "Explicitly detail backup supplier transition plans in Section 15.",
      "Align the notice period in Section 14.2 with corporate standard (120 Days)."
    ],
    checks: [
      { "clause": "Governing Law Specified", "status": "present", "evidence": "Governed by and construed in accordance with the laws of the State of New York." },
      { "clause": "Liability Caps Defined", "status": "present", "evidence": "Total cumulative liability shall not exceed Ten Million Dollars ($10,000,000 USD)." },
      { "clause": "Termination Notice Period", "status": "partial", "evidence": "Either party may terminate this agreement upon ninety (90) days written notice." },
      { "clause": "Business Continuity & Disaster Recovery", "status": "missing", "evidence": "No explicit business continuity or backup SLAs found." }
    ],
    reasoning: [
      "90 days termination notice is shorter than the recommended enterprise standard of 120 days.",
      "Complete omission of disaster recovery and backup systems standard compliance clauses."
    ]
  },
  summary: "This Master Services Agreement governs the transportation, warehousing, and fulfillment services provided by SwiftStream Logistics LLC to the Company. It establishes pricing sheets, performance SLAs, standard liability limits capped at $10M, and governing jurisdiction in New York. Term is 3 years with automatic renewals.",
  agent_executions: [
    { "agent": "ClassificationAgent", "execution_time_ms": 780, "confidence": 0.97, "tokens_used": 1420, "status": "success", "timestamp": "2026-06-27T17:10:01Z", "trace_id": "tr-class-7802" },
    { "agent": "MetadataAgent", "execution_time_ms": 1450, "confidence": 0.96, "tokens_used": 2890, "status": "success", "timestamp": "2026-06-27T17:10:02Z", "trace_id": "tr-meta-1493" },
    { "agent": "RetrieverAgent", "execution_time_ms": 320, "confidence": 0.88, "tokens_used": 540, "status": "success", "timestamp": "2026-06-27T17:10:03Z", "trace_id": "tr-ret-9402" },
    { "agent": "ComplianceAgent", "execution_time_ms": 2100, "confidence": 0.72, "tokens_used": 3410, "status": "success", "timestamp": "2026-06-27T17:10:05Z", "trace_id": "tr-comp-2211" },
    { "agent": "SummarizationAgent", "execution_time_ms": 1820, "confidence": 0.92, "tokens_used": 2980, "status": "success", "timestamp": "2026-06-27T17:10:07Z", "trace_id": "tr-sum-5502" }
  ],
  agent_execution_metadata: {
    "total_latency_ms": 6470,
    "total_tokens": 11240,
    "avg_confidence": 0.89,
    "success_rate": 1.0
  },
  executive_report: {
    "document_name": "Global Logistics Master Services Agreement 2026",
    "document_type": "Vendor Agreement",
    "confidence": 0.965,
    "summary": "This Master Services Agreement governs the transportation, warehousing, and fulfillment services provided by SwiftStream Logistics LLC. It establishes liability limits capped at $10M and governing jurisdiction in New York.",
    "compliance_score": 72,
    "risks": [
      "90-day notice of termination exposes company to supply chain service disruption during peak season.",
      "Omission of Force Majeure and Business Continuity clauses creates significant service delivery risk."
    ],
    "key_clauses": [
      "Section 10.4: Liability is capped at $10,000,000 USD cumulative.",
      "Section 22.1: Governing law is set in New York, with mandatory arbitration."
    ],
    "ai_insights": [
      "Moving to SwiftStream Logistics could reduce shipping transit times by 8%, but lacks regulatory indemnities.",
      "Contract aligns with industry standards for liability limits but has weak SLA credit policies."
    ],
    "recommendations": [
      "Negotiate notice period to 120 days.",
      "Add standard SLA remediation and back-up provider provisions before final signature."
    ]
  }
};

export function InterviewDemoPage() {
  const [toastMessage, setToastMessage] = useState<{ title: string; description: string; variant?: string } | null>(null);
  const toast = ({ title, description, variant }: { title: string; description: string; variant?: string }) => {
    setToastMessage({ title, description, variant });
    setTimeout(() => setToastMessage(null), 4000);
  };
  const [selectedDoc, setSelectedDoc] = useState<any>(SAMPLE_DOCUMENT_MOCK);
  const [activeNode, setActiveNode] = useState<string>("ClassificationAgent");
  
  // Pipeline Node States
  const [nodes, setNodes] = useState<PipelineNode[]>([
    { id: "Upload", label: "Upload & Parse", icon: Upload, status: "success", durationMs: 420 },
    { id: "ClassificationAgent", label: "Classification", icon: Cpu, status: "success", durationMs: 780, confidence: 0.97 },
    { id: "MetadataAgent", label: "Metadata", icon: FileText, status: "success", durationMs: 1450, confidence: 0.96 },
    { id: "RetrieverAgent", label: "Semantic Search", icon: Database, status: "success", durationMs: 320, confidence: 0.88 },
    { id: "ComplianceAgent", label: "Compliance Review", icon: ShieldCheck, status: "success", durationMs: 2100, confidence: 0.72 },
    { id: "SummarizationAgent", label: "Summarization", icon: Sparkles, status: "success", durationMs: 1820, confidence: 0.92 },
    { id: "QuestionAnsweringAgent", label: "Interactive QA", icon: MessageSquare, status: "idle" },
  ]);

  // QA State
  const [query, setQuery] = useState("");
  const [qaAnswer, setQaAnswer] = useState<any>(null);
  const [qaLoading, setQaLoading] = useState(false);

  // Executive Report States
  const [execReport, setExecReport] = useState<any>(SAMPLE_DOCUMENT_MOCK.executive_report);
  const [reportLoading, setReportLoading] = useState(false);
  const [isReportCached, setIsReportCached] = useState(true);

  // Upload/Live pipeline states
  const [file, setFile] = useState<File | null>(null);
  const [isLiveRunning, setIsLiveRunning] = useState(false);
  const [documentsList, setDocumentsList] = useState<Document[]>([]);

  useEffect(() => {
    // Load documents list to enable selecting a real document
    api.listDocuments()
      .then(res => setDocumentsList(res))
      .catch(err => console.error("Error listing documents:", err));
  }, []);

  // Handle document selection (either mock sandbox or real documents)
  const handleSelectDocument = async (docId: string) => {
    if (docId === "demo-vendor-agreement-2026") {
      setSelectedDoc(SAMPLE_DOCUMENT_MOCK);
      setExecReport(SAMPLE_DOCUMENT_MOCK.executive_report);
      setIsReportCached(true);
      setQaAnswer(null);
      // Reset nodes to success
      setNodes(prev => prev.map(n => {
        if (n.id === "QuestionAnsweringAgent") return { ...n, status: "idle" };
        const originalExec = SAMPLE_DOCUMENT_MOCK.agent_executions?.find(e => e.agent === n.id);
        return {
          ...n,
          status: "success",
          durationMs: originalExec?.execution_time_ms || n.durationMs,
          confidence: originalExec?.confidence || n.confidence
        };
      }));
      toast({
        title: "Loaded Sandbox Demo Mode",
        description: "Viewing interactive pre-processed mock document.",
      });
      return;
    }

    try {
      toast({ title: "Loading document data...", description: "Retrieving processing logs and analytics." });
      const fullDoc = await api.getDocument(docId);
      setSelectedDoc(fullDoc);
      setExecReport(null);
      setIsReportCached(false);
      setQaAnswer(null);

      // Reconstruct nodes from document agent executions
      const updatedNodes = nodes.map(n => {
        if (n.id === "Upload") return { ...n, status: "success" as const };
        if (n.id === "QuestionAnsweringAgent") return { ...n, status: "idle" as const };
        
        const exec = fullDoc.agent_executions?.find(e => e.agent === n.id);
        if (exec) {
          return {
            ...n,
            status: exec.status as "success" | "error",
            durationMs: exec.execution_time_ms,
            confidence: exec.confidence || undefined
          };
        }
        return { ...n, status: "idle" as const };
      });
      setNodes(updatedNodes);
      toast({ title: "Document loaded", description: `Active: ${fullDoc.title}` });
    } catch (err: any) {
      toast({ title: "Error loading document", description: err.message, variant: "destructive" });
    }
  };

  // Run the Live Pipeline step-by-step with visual feedback
  const runLivePipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    try {
      setIsLiveRunning(true);
      setQaAnswer(null);
      setExecReport(null);
      setIsReportCached(false);

      // Reset all nodes to idle
      setNodes(prev => prev.map(n => ({ ...n, status: "idle", durationMs: undefined, confidence: undefined })));

      // Step 1: Uploading
      setNodes(prev => prev.map(n => n.id === "Upload" ? { ...n, status: "running" } : n));
      const formData = new FormData();
      formData.append("file", file);
      const uploadedDoc = await api.uploadDocument(formData);
      
      setNodes(prev => prev.map(n => n.id === "Upload" ? { ...n, status: "success", durationMs: 450 } : n));
      setSelectedDoc(uploadedDoc);

      // Step 2: Running agents workflow sequentially
      const agentList = ["ClassificationAgent", "MetadataAgent", "RetrieverAgent", "ComplianceAgent", "SummarizationAgent"];
      
      for (const agentName of agentList) {
        setNodes(prev => prev.map(n => n.id === agentName ? { ...n, status: "running" } : n));
        
        // Wait 800ms for realistic UI step transition animation
        await new Promise(r => setTimeout(r, 800));
      }

      // Final run API triggers LangGraph pipeline in FastAPI
      const runResult = await api.runAgents(uploadedDoc.document_id);
      
      // Update nodes with actual response numbers
      const finalNodes = nodes.map(n => {
        if (n.id === "Upload") return { ...n, status: "success" as const };
        if (n.id === "QuestionAnsweringAgent") return { ...n, status: "idle" as const };
        const exec = runResult.agent_executions?.find(e => e.agent === n.id);
        return {
          ...n,
          status: (exec?.status || "success") as "success" | "error",
          durationMs: exec?.execution_time_ms,
          confidence: exec?.confidence || undefined
        };
      });
      setNodes(finalNodes);
      
      // Refresh active document from backend
      const refreshedDoc = await api.getDocument(uploadedDoc.id);
      setSelectedDoc(refreshedDoc);

      toast({
        title: "Pipeline Execution Complete",
        description: "LangGraph agent network executed successfully.",
      });
    } catch (err: any) {
      toast({
        title: "Pipeline Failed",
        description: err.message || "An error occurred during agent execution.",
        variant: "destructive",
      });
    } finally {
      setIsLiveRunning(false);
    }
  };

  // Generate executive report via Redis-cached endpoint
  const handleGenerateReport = async () => {
    if (!selectedDoc) return;
    try {
      setReportLoading(true);
      const report = await api.generateExecutiveReport(selectedDoc.document_id);
      setExecReport(report);
      setIsReportCached(true);
      toast({ title: "Executive Report Ready", description: "Report compiled and cached in Redis." });
    } catch (err: any) {
      toast({ title: "Generation Failed", description: err.message, variant: "destructive" });
    } finally {
      setReportLoading(false);
    }
  };

  // Handle Chat RAG query
  const handleAskQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !selectedDoc) return;

    try {
      setQaLoading(true);
      setNodes(prev => prev.map(n => n.id === "QuestionAnsweringAgent" ? { ...n, status: "running" } : n));
      
      const res = await api.chat(query, selectedDoc.document_id);
      setQaAnswer(res);
      
      setNodes(prev => prev.map(n => n.id === "QuestionAnsweringAgent" ? { ...n, status: "success", confidence: res.confidence } : n));
      
      // If mock mode, simulate latency
      if (selectedDoc.document_id === "demo-vendor-agreement-2026") {
        setNodes(prev => prev.map(n => n.id === "QuestionAnsweringAgent" ? { ...n, durationMs: 480 } : n));
      }
    } catch (err: any) {
      setNodes(prev => prev.map(n => n.id === "QuestionAnsweringAgent" ? { ...n, status: "error" } : n));
      toast({ title: "QA Failed", description: err.message, variant: "destructive" });
    } finally {
      setQaLoading(false);
    }
  };

  // Trigger PDF download with query auth token
  const downloadPdf = () => {
    if (!selectedDoc) return;
    const url = api.getReportPdfUrl(selectedDoc.document_id);
    window.open(url, "_blank");
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className={`fixed right-4 top-4 z-50 rounded-lg border p-4 shadow-lg transition-all ${
          toastMessage.variant === "destructive" ? "bg-red-50 text-red-900 border-red-200" : "bg-white text-slate-900 border-slate-200"
        }`}>
          <p className="font-bold text-sm">{toastMessage.title}</p>
          <p className="text-xs mt-1 text-slate-600">{toastMessage.description}</p>
        </div>
      )}
      {/* Top Banner */}
      <div className="rounded-lg bg-gradient-to-r from-blue-900 via-indigo-950 to-slate-900 p-6 text-white shadow-xl">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-indigo-500 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-white">
                Interview Sandbox
              </span>
              <span className="flex items-center gap-1 text-xs text-indigo-300">
                <Zap className="h-3 w-3" /> LangGraph + Gemini 1.5
              </span>
            </div>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight">Agentic AI Explainability Sandbox</h1>
            <p className="mt-2 text-slate-300 max-w-2xl">
              Inspect confidence breakdowns, real-time node latencies, custom prompt reasonings, and execution telemetry across the LangGraph multi-agent pipeline.
            </p>
          </div>
          
          <div className="flex flex-col gap-2 sm:flex-row">
            {/* Document Sandbox Selector */}
            <div className="flex flex-col">
              <label className="text-xs text-slate-300 mb-1 font-semibold">Demo Document Selector</label>
              <select
                className="rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                onChange={(e) => handleSelectDocument(e.target.value)}
                value={selectedDoc?.document_id || ""}
              >
                <option value="demo-vendor-agreement-2026">
                  ★ [SANDBOX PRE-LOADED] Master Services Agreement
                </option>
                {documentsList.map((d) => (
                  <option key={d.id} value={d.document_id}>
                    {d.title}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Left - Pipeline Flow, Right - Node Details */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Pipeline Controls & Flow Chart */}
        <div className="space-y-6 lg:col-span-1">
          {/* Custom Upload Form */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-bold">Process New Document</CardTitle>
              <CardDescription>Upload a custom file to run the live LangGraph agent execution.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={runLivePipeline} className="space-y-4">
                <div className="rounded-lg border border-dashed border-border p-4 text-center hover:bg-slate-50 transition">
                  <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    accept=".pdf,.txt,.docx"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer space-y-2 block">
                    <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
                    <span className="text-sm font-semibold block text-indigo-600 hover:text-indigo-700">
                      {file ? file.name : "Select File"}
                    </span>
                    <span className="text-xs text-muted-foreground block">PDF, DOCX or TXT (Max 10MB)</span>
                  </label>
                </div>
                <Button
                  type="submit"
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
                  disabled={!file || isLiveRunning}
                >
                  {isLiveRunning ? "Executing Agent Graph..." : "Run Agent Network"}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Vertical Pipeline Progress Visualizer */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-bold">LangGraph Live Node Trajectory</CardTitle>
              <CardDescription>Click any node to inspect explainability dashboards.</CardDescription>
            </CardHeader>
            <CardContent className="relative">
              <div className="relative pl-6 space-y-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-200">
                {nodes.map((node) => {
                  const NodeIcon = node.icon;
                  const isActive = activeNode === node.id;
                  let colorClass = "bg-slate-100 text-slate-400 border-slate-300";
                  
                  if (node.status === "running") {
                    colorClass = "bg-blue-50 text-blue-600 border-blue-500 ring-4 ring-blue-100 animate-pulse";
                  } else if (node.status === "success") {
                    colorClass = "bg-emerald-50 text-emerald-600 border-emerald-500";
                  } else if (node.status === "error") {
                    colorClass = "bg-red-50 text-red-600 border-red-500";
                  }

                  return (
                    <div
                      key={node.id}
                      onClick={() => setActiveNode(node.id)}
                      className={`relative flex items-center justify-between rounded-lg border p-3 cursor-pointer transition ${
                        isActive ? "border-indigo-600 bg-indigo-50/50 shadow-sm" : "border-transparent hover:bg-slate-50"
                      }`}
                    >
                      {/* Connection bullet point */}
                      <span className={`absolute -left-6 top-1/2 -translate-y-1/2 h-3.5 w-3.5 rounded-full border-2 bg-white transition ${
                        node.status === "success" ? "border-emerald-500" : node.status === "running" ? "border-blue-500" : "border-slate-300"
                      }`} />

                      <div className="flex items-center gap-3">
                        <div className={`flex h-10 w-10 items-center justify-center rounded-lg border-2 ${colorClass}`}>
                          <NodeIcon className="h-5 w-5" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold">{node.label}</p>
                          <p className="text-xs text-muted-foreground">
                            {node.status === "running" ? "Analyzing content..." : node.status === "success" ? "Completed" : "Pending"}
                          </p>
                        </div>
                      </div>

                      {/* Status Badges */}
                      <div className="text-right">
                        {node.durationMs && (
                          <span className="text-[10px] text-muted-foreground flex items-center gap-1 justify-end">
                            <Clock className="h-3 w-3" /> {node.durationMs}ms
                          </span>
                        )}
                        {node.confidence !== undefined && (
                          <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                            node.confidence > 0.85 ? "bg-emerald-100 text-emerald-800" : "bg-yellow-100 text-yellow-800"
                          }`}>
                            {intPercent(node.confidence)}% conf
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Explainability Engine Inspection Panel */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="min-h-[500px]">
            <CardHeader className="border-b">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg font-bold flex items-center gap-2">
                    <span>Explainability Dashboard</span>
                    <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs text-indigo-700">
                      {activeNode}
                    </span>
                  </CardTitle>
                  <CardDescription>
                    Real-time data inspector for active multi-agent execution node.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              {/* Classification Node View */}
              {activeNode === "ClassificationAgent" && (
                <div className="space-y-6">
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="rounded-lg border bg-slate-50 p-4">
                      <p className="text-xs text-muted-foreground font-semibold">Classified Category</p>
                      <p className="mt-1 text-lg font-extrabold text-slate-800">{selectedDoc?.document_type || "Unclassified"}</p>
                    </div>

                    <div className="rounded-lg border bg-slate-50 p-4">
                      <p className="text-xs text-muted-foreground font-semibold">Unified Confidence</p>
                      <p className="mt-1 text-lg font-extrabold text-emerald-600">
                        {intPercent(selectedDoc?.classification_confidence)}%
                      </p>
                    </div>

                    <div className="rounded-lg border bg-slate-50 p-4">
                      <p className="text-xs text-muted-foreground font-semibold">Latency Profile</p>
                      <p className="mt-1 text-lg font-extrabold text-slate-800">
                        {selectedDoc?.agent_executions?.find((e: any) => e.agent === "ClassificationAgent")?.execution_time_ms || 780} ms
                      </p>
                    </div>
                  </div>

                  {/* Confidence Breakdown Gauge */}
                  <div className="rounded-lg border p-4 space-y-4">
                    <h3 className="text-sm font-semibold flex items-center gap-1.5">
                      <TrendingUp className="h-4 w-4 text-indigo-600" />
                      Calibrated Confidence Breakdown
                    </h3>
                    <div className="grid gap-4 sm:grid-cols-2">
                      {Object.entries(selectedDoc?.confidence_reasoning || {}).map(([key, val]: [string, any]) => (
                        <div key={key} className="space-y-1">
                          <div className="flex justify-between text-xs font-medium">
                            <span className="capitalize">{key.replace("_", " ")}</span>
                            <span>{intPercent(val)}%</span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-slate-100">
                            <div
                              className="h-2 rounded-full bg-indigo-500"
                              style={{ width: `${val * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Classification Reasoning */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold">Why this classification?</h3>
                    <ul className="space-y-2">
                      {(selectedDoc?.classification_reasoning || []).map((reason: string, i: number) => (
                        <li key={i} className="flex gap-2 text-sm text-slate-700">
                          <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                          <span>{reason}</span>
                        </li>
                      ))}
                      {(!selectedDoc?.classification_reasoning || selectedDoc?.classification_reasoning.length === 0) && (
                        <p className="text-xs text-muted-foreground italic">No reasoning output saved for this document.</p>
                      )}
                    </ul>
                  </div>
                </div>
              )}

              {/* Metadata Node View */}
              {activeNode === "MetadataAgent" && (
                <div className="space-y-6">
                  <h3 className="text-sm font-semibold">Extracted Metadata Cards</h3>
                  <div className="grid gap-4 sm:grid-cols-2">
                    {Object.entries(selectedDoc?.extracted_metadata || {}).map(([key, fieldData]: [string, any]) => {
                      const isObj = fieldData && typeof fieldData === "object" && "value" in fieldData;
                      const value = isObj ? fieldData.value : fieldData;
                      const confidence = isObj ? fieldData.confidence : 0.85;
                      const source = isObj ? fieldData.source : "Automatic extraction";

                      return (
                        <div key={key} className="rounded-lg border p-4 hover:border-slate-300 transition space-y-2">
                          <div className="flex items-center justify-between border-b pb-1.5">
                            <span className="text-xs font-bold text-slate-700 capitalize">
                              {key.replace(/_/g, " ")}
                            </span>
                            <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                              confidence > 0.90 ? "bg-emerald-100 text-emerald-800" : "bg-yellow-100 text-yellow-800"
                            }`}>
                              {intPercent(confidence)}% confidence
                            </span>
                          </div>
                          <p className="text-sm font-semibold text-slate-900">{value || "Null / Not found"}</p>
                          {source && (
                            <p className="text-[10px] text-muted-foreground italic flex items-center gap-1">
                              <FileText className="h-3 w-3" /> Location: {source}
                            </p>
                          )}
                        </div>
                      );
                    })}
                    {!selectedDoc?.extracted_metadata && (
                      <p className="text-xs text-muted-foreground italic">No metadata extracted.</p>
                    )}
                  </div>
                </div>
              )}

              {/* Retrieval Node View */}
              {activeNode === "RetrieverAgent" && (
                <div className="space-y-6">
                  <div className="rounded-lg bg-slate-50 border p-4 space-y-2">
                    <h3 className="text-sm font-bold text-slate-800">Hybrid Search Details</h3>
                    <p className="text-xs text-slate-600">
                      The Retriever agent executed a unified dual-vector and keyword search against the OpenSearch server cluster to load the most relevant document chunks.
                    </p>
                  </div>

                  <h3 className="text-sm font-semibold">Retrieved Document Chunks</h3>
                  <div className="space-y-3">
                    {/* Simulated retrieval hits for sandbox demo */}
                    {selectedDoc?.document_id === "demo-vendor-agreement-2026" ? (
                      <>
                        <div className="rounded-lg border p-3 space-y-2 bg-slate-50">
                          <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                            <span className="font-semibold text-slate-800">Section 14.2 (Notice Periods)</span>
                            <span className="bg-indigo-100 text-indigo-800 px-1.5 py-0.5 rounded font-mono">Score: 0.912</span>
                          </div>
                          <p className="text-xs text-slate-700 italic">
                            "...Either party may terminate this agreement upon ninety (90) days written notice to the other party. Notice must be sent certified mail with return receipt requested..."
                          </p>
                        </div>
                        <div className="rounded-lg border p-3 space-y-2 bg-slate-50">
                          <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                            <span className="font-semibold text-slate-800">Section 10.4 (Limitation of Liability)</span>
                            <span className="bg-indigo-100 text-indigo-800 px-1.5 py-0.5 rounded font-mono">Score: 0.884</span>
                          </div>
                          <p className="text-xs text-slate-700 italic">
                            "...IN NO EVENT SHALL EITHER PARTY'S CUMULATIVE LIABILITY UNDER THIS AGREEMENT EXCEED TEN MILLION DOLLARS ($10,000,000 USD) IN THE AGGREGATE..."
                          </p>
                        </div>
                      </>
                    ) : (
                      <p className="text-xs text-muted-foreground italic text-center py-6">
                        Live search retrieval chunks will be loaded on demand during RAG QA searches.
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Compliance Node View */}
              {activeNode === "ComplianceAgent" && (
                <div className="space-y-6">
                  {/* Gauge and Summary Header */}
                  <div className="flex flex-col sm:flex-row gap-6 items-center justify-between rounded-lg border bg-slate-50 p-4">
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground font-semibold">Compliance Rating</p>
                      <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-extrabold ${
                          (selectedDoc?.compliance_report?.risk_score || 0) > 80 ? "text-emerald-600" : "text-amber-500"
                        }`}>
                          {selectedDoc?.compliance_report?.risk_score || 0}
                        </span>
                        <span className="text-sm text-muted-foreground">/ 100 Risk Score</span>
                      </div>
                      <p className="text-xs text-slate-600 mt-2 max-w-md">
                        {selectedDoc?.compliance_report?.summary}
                      </p>
                    </div>

                    {/* Radial SVG Gauge */}
                    <div className="relative h-20 w-20 shrink-0">
                      <svg className="h-full w-full -rotate-90">
                        <circle cx="40" cy="40" r="34" className="stroke-slate-200 fill-none" strokeWidth="6" />
                        <circle
                          cx="40"
                          cy="40"
                          r="34"
                          className="stroke-amber-500 fill-none"
                          strokeWidth="6"
                          strokeDasharray={2 * Math.PI * 34}
                          strokeDashoffset={2 * Math.PI * 34 * (1 - (selectedDoc?.compliance_report?.risk_score || 0) / 100)}
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center text-xs font-extrabold text-slate-700">
                        {selectedDoc?.compliance_report?.risk_score || 0}%
                      </div>
                    </div>
                  </div>

                  {/* Compliance Checks List */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold">Clause Checklists</h3>
                    <div className="space-y-2">
                      {(selectedDoc?.compliance_report?.checks || []).map((check: any, idx: number) => (
                        <div key={idx} className="rounded-lg border p-3 text-xs space-y-1.5">
                          <div className="flex items-center justify-between font-bold">
                            <span>{check.clause}</span>
                            <span className={`rounded px-1.5 py-0.5 capitalize text-[10px] ${
                              check.status === "present"
                                ? "bg-emerald-100 text-emerald-800"
                                : check.status === "partial"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-red-100 text-red-800"
                            }`}>
                              {check.status}
                            </span>
                          </div>
                          {check.evidence && (
                            <p className="text-[11px] text-slate-600 italic">Evidence: &ldquo;{check.evidence}&rdquo;</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Compliance Reasoning */}
                  <div className="space-y-3 border-t pt-4">
                    <h3 className="text-sm font-semibold flex items-center gap-1.5">
                      <HelpCircle className="h-4 w-4 text-amber-500" /> Why this risk score?
                    </h3>
                    <ul className="space-y-2">
                      {(selectedDoc?.compliance_reasoning || selectedDoc?.compliance_report?.reasoning || []).map((reason: string, i: number) => (
                        <li key={i} className="flex gap-2 text-xs text-slate-700">
                          <AlertCircle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Summary & Executive Report View */}
              {activeNode === "SummarizationAgent" && (
                <div className="space-y-6">
                  {/* Executive Summary */}
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold">Summarization Agent Output</h3>
                    <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 border rounded-lg p-4 italic">
                      &ldquo;{selectedDoc?.summary || "No summary generated for this document."}&rdquo;
                    </p>
                  </div>

                  {/* Executive Report Generation (Redis Cached) */}
                  <div className="border-t pt-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-sm font-bold text-slate-800">Executive Briefing & Actionable Report</h3>
                        <p className="text-xs text-muted-foreground">Generated on-demand and cached temporarily in Redis.</p>
                      </div>
                      
                      <Button
                        size="sm"
                        onClick={handleGenerateReport}
                        disabled={reportLoading}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white"
                      >
                        {reportLoading ? "Querying AI..." : execReport ? "Re-generate Report" : "Generate Report"}
                      </Button>
                    </div>

                    {execReport && (
                      <div className="space-y-4 rounded-lg border p-4 bg-white shadow-sm">
                        <div className="flex items-center justify-between border-b pb-2">
                          <span className="text-xs font-bold text-slate-800">AI Executive Advisory Report</span>
                          <span className={`text-[10px] rounded px-1.5 py-0.5 ${
                            isReportCached ? "bg-emerald-100 text-emerald-800 font-semibold" : "bg-slate-100 text-slate-600"
                          }`}>
                            {isReportCached ? "✓ Loaded from Redis Cache" : "Live generated"}
                          </span>
                        </div>

                        <div className="grid gap-4 sm:grid-cols-2 text-xs">
                          <div className="space-y-1.5">
                            <p className="font-bold text-red-600">Critical Risks</p>
                            <ul className="list-disc pl-4 space-y-1 text-slate-700">
                              {execReport.risks?.map((r: string, i: number) => <li key={i}>{r}</li>)}
                            </ul>
                          </div>

                          <div className="space-y-1.5">
                            <p className="font-bold text-blue-800">Significant Provisions</p>
                            <ul className="list-disc pl-4 space-y-1 text-slate-700">
                              {execReport.key_clauses?.map((c: string, i: number) => <li key={i}>{c}</li>)}
                            </ul>
                          </div>

                          <div className="space-y-1.5">
                            <p className="font-bold text-slate-800">Strategic AI Insights</p>
                            <ul className="list-disc pl-4 space-y-1 text-slate-700">
                              {execReport.ai_insights?.map((ins: string, i: number) => <li key={i}>{ins}</li>)}
                            </ul>
                          </div>

                          <div className="space-y-1.5">
                            <p className="font-bold text-indigo-900">Leadership Recommendations</p>
                            <ul className="list-disc pl-4 space-y-1 text-slate-700">
                              {execReport.recommendations?.map((rec: string, i: number) => <li key={i}>{rec}</li>)}
                            </ul>
                          </div>
                        </div>

                        {/* PDF Streamer Button */}
                        <div className="border-t pt-3 flex justify-end">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={downloadPdf}
                            className="flex items-center gap-1 text-indigo-700 border-indigo-200 hover:bg-indigo-50"
                          >
                            <Download className="h-3.5 w-3.5" /> Download Executive PDF Report
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* QA Node View */}
              {activeNode === "QuestionAnsweringAgent" && (
                <div className="space-y-6">
                  <div className="rounded-lg bg-slate-50 border p-4 space-y-2">
                    <h3 className="text-sm font-bold text-slate-800">RAG Semantic Question Answering</h3>
                    <p className="text-xs text-slate-600">
                      Submit contextual questions about the active document. The agent utilizes hybrid search to retrieve context blocks, then streams answers with structured source citations.
                    </p>
                  </div>

                  {/* Chat Box Form */}
                  <form onSubmit={handleAskQuestion} className="flex gap-2">
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Ask about liability, notice periods, SLAs..."
                      className="flex-1 rounded border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      disabled={qaLoading}
                    />
                    <Button type="submit" disabled={qaLoading || !query.trim()} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                      {qaLoading ? "Searching..." : "Ask Agent"}
                    </Button>
                  </form>

                  {/* Answer Presentation */}
                  {qaAnswer && (
                    <div className="rounded-lg border p-4 bg-indigo-50/20 space-y-3 text-xs">
                      <div className="flex items-center justify-between border-b pb-1.5">
                        <span className="font-bold text-indigo-900">RAG Agent Answer</span>
                        <span className="bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded">
                          Confidence: {intPercent(qaAnswer.confidence)}%
                        </span>
                      </div>
                      
                      <p className="text-sm text-slate-800 leading-relaxed font-medium">
                        {qaAnswer.answer}
                      </p>

                      {/* Source Citations */}
                      {qaAnswer.sources && qaAnswer.sources.length > 0 && (
                        <div className="space-y-1.5 pt-2 border-t">
                          <p className="font-bold text-slate-700">Source Citations & Reference Chunks:</p>
                          <div className="grid gap-2 sm:grid-cols-2">
                            {qaAnswer.sources.map((src: any, i: number) => (
                              <div key={i} className="rounded border bg-white p-2 text-[10px] space-y-1">
                                <div className="flex justify-between font-semibold">
                                  <span>{src.section || "General Content"}</span>
                                  <span className="text-indigo-600">Relevance: {src.score?.toFixed(3) || "0.850"}</span>
                                </div>
                                <p className="text-slate-500 italic">Chunk reference id: {src.chunk_id?.substring(0, 8) || "ch-mock"}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Observable Workflow Timeline & Trace Telemetry */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-bold">Observable Agent Execution Telemetry</CardTitle>
          <CardDescription>Corpus-wide pipeline executions. Click trace ID to view complete callback graph.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b bg-slate-50 text-slate-500 font-semibold">
                  <th className="py-2.5 px-4">Agent Name</th>
                  <th className="py-2.5 px-4">Timestamp (UTC)</th>
                  <th className="py-2.5 px-4">Latency (ms)</th>
                  <th className="py-2.5 px-4">Token Cost</th>
                  <th className="py-2.5 px-4">Confidence</th>
                  <th className="py-2.5 px-4">Trace Status</th>
                  <th className="py-2.5 px-4">Langfuse Link</th>
                </tr>
              </thead>
              <tbody>
                {(selectedDoc?.agent_executions || []).map((exec: AgentExecution, idx: number) => (
                  <tr key={idx} className="border-b hover:bg-slate-50/50">
                    <td className="py-2.5 px-4 font-bold text-slate-800">{exec.agent}</td>
                    <td className="py-2.5 px-4 text-muted-foreground">{exec.timestamp ? new Date(exec.timestamp).toLocaleString() : "2026-06-27, 17:10"}</td>
                    <td className="py-2.5 px-4 font-mono font-bold text-slate-800">{exec.execution_time_ms} ms</td>
                    <td className="py-2.5 px-4 text-muted-foreground">{exec.tokens_used || "N/A"} tokens</td>
                    <td className="py-2.5 px-4">
                      {exec.confidence !== null && exec.confidence !== undefined ? (
                        <span className={`rounded-full px-2 py-0.5 font-bold ${
                          exec.confidence > 0.85 ? "bg-emerald-100 text-emerald-800" : "bg-yellow-100 text-yellow-800"
                        }`}>
                          {intPercent(exec.confidence)}%
                        </span>
                      ) : "-"}
                    </td>
                    <td className="py-2.5 px-4">
                      <span className={`rounded px-1.5 py-0.5 capitalize font-semibold ${
                        exec.status === "success" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
                      }`}>
                        {exec.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-4">
                      {exec.trace_id ? (
                        <a
                          href={`http://localhost:3000/traces/${exec.trace_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-indigo-600 hover:underline inline-flex items-center gap-1 font-semibold"
                        >
                          Trace-{exec.trace_id.substring(0, 6)} ↗
                        </a>
                      ) : (
                        <span className="text-muted-foreground">No active trace</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Utility to convert confidence fraction to integer percentage
function intPercent(num: number | undefined | null): number {
  if (num === undefined || num === null) return 0;
  return Math.round(num * 100);
}
