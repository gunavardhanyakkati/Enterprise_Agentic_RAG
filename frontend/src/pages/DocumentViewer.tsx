import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bot, FileText, ShieldCheck } from "lucide-react";
import { AgentExecutionDetails, WorkflowGraph } from "@/components/agents/WorkflowGraph";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Document } from "@/lib/api";
import { sortExecutionsByWorkflow } from "@/lib/workflow";

export function DocumentViewerPage() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<Document | null>(null);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [reportData, setReportData] = useState<any>(null);

  useEffect(() => {
    if (!id) return;
    api
      .getDocument(id)
      .then(setDoc)
      .catch((err) => setError(err.message));
  }, [id]);

  async function rerunAgents() {
    if (!id) return;
    setRunning(true);
    try {
      await api.runAgents(id);
      const updated = await api.getDocument(id);
      setDoc(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent run failed");
    } finally {
      setRunning(false);
    }
  }

  if (error) return <p className="text-red-400">{error}</p>;
  if (!doc) return <p className="text-muted-foreground">Loading document...</p>;

  const metadata = doc.extracted_metadata || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">{doc.title}</h1>
          <p className="text-muted-foreground">
            {doc.document_type} · {doc.department} · {doc.access_level}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to={`/chat?doc=${doc.document_id}`}>
            <Button variant="outline">Ask Question</Button>
          </Link>
          <Button onClick={rerunAgents} disabled={running}>
            <Bot className="h-4 w-4" />
            {running ? "Running..." : "Re-run Agents"}
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Badge variant={doc.content_processed ? "success" : "warning"}>
          {doc.content_processed ? "Indexed" : "Processing"}
        </Badge>
        {doc.classification_confidence != null && (
          <Badge variant="secondary">Classification {Math.round(doc.classification_confidence * 100)}%</Badge>
        )}
      </div>

      {doc.summary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{doc.summary}</p>
            
            {doc.classification_reasoning && doc.classification_reasoning.length > 0 && (
              <div className="rounded bg-slate-50 border p-3">
                <p className="text-xs font-semibold text-slate-700">Classification Reasoning:</p>
                <ul className="list-disc pl-4 mt-1 text-xs space-y-1 text-slate-600">
                  {doc.classification_reasoning.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Executive Report Advisory Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-indigo-600" />
                Executive Briefing
              </CardTitle>
              <CardDescription>Strategic action insights and cached compliance audit briefing.</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  try {
                    const report = await api.generateExecutiveReport(doc.document_id);
                    setReportData(report);
                  } catch (err: any) {
                    setError(err.message);
                  }
                }}
              >
                Compile Advisory
              </Button>
              {reportData && (
                <Button
                  size="sm"
                  onClick={() => {
                    const url = api.getReportPdfUrl(doc.document_id);
                    window.open(url, "_blank");
                  }}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  Download PDF Report
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        {reportData && (
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2 text-xs">
              <div className="space-y-1.5">
                <p className="font-bold text-red-600">Identified Exposure & Risks</p>
                <ul className="list-disc pl-4 space-y-1 text-slate-600">
                  {reportData.risks?.map((r: string, i: number) => <li key={i}>{r}</li>)}
                </ul>
              </div>
              <div className="space-y-1.5">
                <p className="font-bold text-blue-800">Critical Provisions</p>
                <ul className="list-disc pl-4 space-y-1 text-slate-600">
                  {reportData.key_clauses?.map((c: string, i: number) => <li key={i}>{c}</li>)}
                </ul>
              </div>
              <div className="space-y-1.5">
                <p className="font-bold text-slate-800">AI Tactical Insights</p>
                <ul className="list-disc pl-4 space-y-1 text-slate-600">
                  {reportData.ai_insights?.map((ins: string, i: number) => <li key={i}>{ins}</li>)}
                </ul>
              </div>
              <div className="space-y-1.5">
                <p className="font-bold text-indigo-900">Leadership Recommendations</p>
                <ul className="list-disc pl-4 space-y-1 text-slate-600">
                  {reportData.recommendations?.map((rec: string, i: number) => <li key={i}>{rec}</li>)}
                </ul>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {Object.keys(metadata).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Extracted Metadata</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-3 md:grid-cols-2">
              {Object.entries(metadata).map(([key, value]) => {
                const valObj = value as any;
                const isObj = valObj && typeof valObj === "object" && "value" in valObj;
                const displayVal = isObj ? String(valObj.value) : String(value);
                const confidence = isObj ? valObj.confidence : null;
                const source = isObj ? valObj.source : null;

                return (
                  <div key={key} className="rounded-md border border-border p-3">
                    <div className="flex justify-between items-center">
                      <dt className="text-xs uppercase text-muted-foreground">{key.replace(/_/g, " ")}</dt>
                      {confidence !== null && (
                        <span className="text-[10px] rounded px-1.5 bg-indigo-50 text-indigo-700 font-bold">
                          {Math.round(confidence * 100)}% conf
                        </span>
                      )}
                    </div>
                    <dd className="mt-1 text-sm font-semibold">{displayVal}</dd>
                    {source && (
                      <p className="text-[10px] mt-1.5 italic text-muted-foreground">Location: {source}</p>
                    )}
                  </div>
                );
              })}
            </dl>
          </CardContent>
        </Card>
      )}

      {doc.compliance_report && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              Compliance Report
            </CardTitle>
            <CardDescription>
              Risk score: {Math.round(doc.compliance_report.risk_score)}% · {doc.compliance_report.summary}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              {doc.compliance_report.checks.map((check, i) => (
                <div key={i} className="flex items-start justify-between gap-4 rounded-md border border-border p-3">
                  <div>
                    <p className="font-medium">{check.clause}</p>
                    <p className="text-sm text-muted-foreground">{check.evidence}</p>
                  </div>
                  <Badge
                    variant={
                      check.status === "present" ? "success" : check.status === "partial" ? "warning" : "destructive"
                    }
                  >
                    {check.status}
                  </Badge>
                </div>
              ))}
            </div>
            
            {doc.compliance_reasoning && doc.compliance_reasoning.length > 0 && (
              <div className="rounded bg-slate-50 border p-3">
                <p className="text-xs font-semibold text-amber-800">Compliance Reasonings:</p>
                <ul className="list-disc pl-4 mt-1 text-xs space-y-1 text-slate-600">
                  {doc.compliance_reasoning.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}

            {doc.compliance_report.recommendations.length > 0 && (
              <div>
                <p className="mb-2 font-medium">Recommendations</p>
                <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                  {doc.compliance_report.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {doc.agent_executions && doc.agent_executions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Agent Workflow</CardTitle>
            <CardDescription>LangGraph enterprise pipeline execution metrics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <WorkflowGraph executions={sortExecutionsByWorkflow(doc.agent_executions)} />
            <AgentExecutionDetails executions={sortExecutionsByWorkflow(doc.agent_executions)} />
          </CardContent>
        </Card>
      )}

      {doc.raw_text && (
        <Card>
          <CardHeader>
            <CardTitle>Raw Text Preview</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-muted/30 p-4 text-xs">
              {doc.raw_text.slice(0, 8000)}
              {doc.raw_text.length > 8000 && "\n\n... truncated ..."}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
