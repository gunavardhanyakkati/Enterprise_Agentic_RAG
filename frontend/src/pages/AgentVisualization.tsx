import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, CheckCircle2, Clock, Coins, Play, RefreshCw } from "lucide-react";
import { AgentExecutionDetails, WorkflowGraph } from "@/components/agents/WorkflowGraph";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { api, type Document } from "@/lib/api";
import {
  DEFAULT_WORKFLOW_EDGES,
  DEFAULT_WORKFLOW_NODES,
  sortExecutionsByWorkflow,
  type WorkflowEdgeDef,
  type WorkflowNodeDef,
} from "@/lib/workflow";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function AgentVisualizationPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string>();
  const [workflowNodes, setWorkflowNodes] = useState<WorkflowNodeDef[]>(DEFAULT_WORKFLOW_NODES);
  const [workflowEdges, setWorkflowEdges] = useState<WorkflowEdgeDef[]>(DEFAULT_WORKFLOW_EDGES);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api
      .getAgentWorkflow()
      .then((workflow) => {
        setWorkflowNodes(workflow.nodes);
        setWorkflowEdges(workflow.edges);
      })
      .catch(() => {});

    api
      .listDocuments()
      .then((docs) => {
        setDocuments(docs);
        const withAgents = docs.find((d) => d.agent_executions?.length);
        setSelectedId(withAgents?.document_id || docs[0]?.document_id || "");
      })
      .catch((err) => setError(err.message));
  }, []);

  const selectedDoc = documents.find((d) => d.document_id === selectedId);
  const executions = useMemo(
    () => sortExecutionsByWorkflow(selectedDoc?.agent_executions || [], workflowNodes),
    [selectedDoc, workflowNodes],
  );

  const totals = useMemo(() => {
    return executions.reduce(
      (acc, exec) => ({
        time: acc.time + exec.execution_time_ms,
        tokens: acc.tokens + (exec.tokens_used || 0),
        success: acc.success + (exec.status === "success" ? 1 : 0),
      }),
      { time: 0, tokens: 0, success: 0 },
    );
  }, [executions]);

  const chartData = executions.map((exec) => ({
    name: exec.agent.replace(/Agent$/, ""),
    time: exec.execution_time_ms,
    tokens: exec.tokens_used || 0,
    confidence: exec.confidence != null ? Math.round(exec.confidence * 100) : 0,
  }));

  async function rerunPipeline(withQuestion = false) {
    if (!selectedId) return;
    setRunning(true);
    setError("");
    try {
      await api.runAgents(
        selectedId,
        withQuestion ? "What are the key points and obligations in this document?" : undefined,
      );
      const updated = await api.getDocument(selectedId);
      setDocuments((prev) => prev.map((d) => (d.document_id === selectedId ? updated : d)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline run failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">LangGraph Workflow Visualization</h1>
          <p className="text-muted-foreground">
            Classification → Metadata → Retrieval → Compliance → Summary → QA
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => rerunPipeline(false)} disabled={running || !selectedId}>
            <RefreshCw className={`h-4 w-4 ${running ? "animate-spin" : ""}`} />
            Re-run Pipeline
          </Button>
          <Button onClick={() => rerunPipeline(true)} disabled={running || !selectedId}>
            <Play className="h-4 w-4" />
            Run with QA
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-muted-foreground">Document:</span>
        <Select value={selectedId} onChange={(e) => setSelectedId(e.target.value)} className="max-w-lg">
          {documents.map((doc) => (
            <option key={doc.document_id} value={doc.document_id}>
              {doc.title}
            </option>
          ))}
        </Select>
        {selectedDoc && (
          <Badge variant="secondary">{selectedDoc.document_type}</Badge>
        )}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Agent Graph
          </CardTitle>
          <CardDescription>
            Click a node to inspect execution time, confidence, and token usage
          </CardDescription>
        </CardHeader>
        <CardContent>
          <WorkflowGraph
            nodes={workflowNodes}
            executions={executions}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
          />
          <p className="mt-4 text-xs text-muted-foreground">
            Edges: {workflowEdges.map((e) => `${e.source}→${e.target}`).join(", ")}
          </p>
        </CardContent>
      </Card>

      {executions.length > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <Clock className="h-4 w-4" /> Total Time
              </CardDescription>
              <CardTitle className="text-3xl">{totals.time}ms</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <Coins className="h-4 w-4" /> Total Tokens
              </CardDescription>
              <CardTitle className="text-3xl">{totals.tokens}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" /> Success Rate
              </CardDescription>
              <CardTitle className="text-3xl">
                {Math.round((totals.success / executions.length) * 100)}%
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Per-Agent Metrics</CardTitle>
            <CardDescription>Execution time (ms) and token usage by agent</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="time" name="Time (ms)" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="tokens" name="Tokens" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Node Details</CardTitle>
          <CardDescription>
            {selectedNodeId ? "Selected node metrics" : "All workflow nodes"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AgentExecutionDetails
            nodes={workflowNodes}
            executions={executions}
            selectedNodeId={selectedNodeId}
          />
        </CardContent>
      </Card>

      {selectedId && (
        <Link to={`/documents/${selectedId}`} className="inline-block text-sm text-primary hover:underline">
          View full document details →
        </Link>
      )}
    </div>
  );
}
