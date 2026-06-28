import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Line,
  LineChart,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Document } from "@/lib/api";
import { Button } from "@/components/ui/button";

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"];

export function AnalyticsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [agentAnalytics, setAgentAnalytics] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "operations">("overview");
  const [error, setError] = useState("");

  useEffect(() => {
    api.listDocuments()
      .then(setDocuments)
      .catch((err) => setError(err.message));
      
    api.getAgentAnalytics()
      .then(setAgentAnalytics)
      .catch((err) => console.error("Error loading agent analytics:", err));
  }, []);

  const byType = useMemo(() => {
    const counts: Record<string, number> = {};
    documents.forEach((d) => {
      counts[d.document_type] = (counts[d.document_type] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [documents]);

  const byDepartment = useMemo(() => {
    const counts: Record<string, number> = {};
    documents.forEach((d) => {
      counts[d.department] = (counts[d.department] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [documents]);

  const agentStats = useMemo(() => {
    const stats: Record<string, { count: number; totalMs: number; totalTokens: number }> = {};
    documents.forEach((doc) => {
      doc.agent_executions?.forEach((exec) => {
        if (!stats[exec.agent]) stats[exec.agent] = { count: 0, totalMs: 0, totalTokens: 0 };
        stats[exec.agent].count += 1;
        stats[exec.agent].totalMs += exec.execution_time_ms;
        stats[exec.agent].totalTokens += exec.tokens_used || 0;
      });
    });
    return Object.entries(stats).map(([agent, data]) => ({
      agent: agent.replace(/_/g, " "),
      avgMs: Math.round(data.totalMs / data.count),
      tokens: data.totalTokens,
      runs: data.count,
    }));
  }, [documents]);

  const avgConfidence =
    documents.filter((d) => d.classification_confidence != null).length > 0
      ? documents.reduce((sum, d) => sum + (d.classification_confidence || 0), 0) /
        documents.filter((d) => d.classification_confidence != null).length
      : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Analytics & Operations</h1>
          <p className="text-muted-foreground">Document intelligence and multi-agent performance telemetry</p>
        </div>
        
        <div className="flex rounded-lg bg-muted p-1 border">
          <Button
            size="sm"
            variant={activeTab === "overview" ? "secondary" : "ghost"}
            onClick={() => setActiveTab("overview")}
            className="rounded-md"
          >
            Corpus Overview
          </Button>
          <Button
            size="sm"
            variant={activeTab === "operations" ? "secondary" : "ghost"}
            onClick={() => setActiveTab("operations")}
            className="rounded-md"
          >
            Agent Operations
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {activeTab === "overview" ? (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total Documents</CardDescription>
                <CardTitle className="text-3xl">{documents.length}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Indexed</CardDescription>
                <CardTitle className="text-3xl">{documents.filter((d) => d.content_processed).length}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Avg Classification Confidence</CardDescription>
                <CardTitle className="text-3xl">{Math.round(avgConfidence * 100)}%</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Compliance Reports</CardDescription>
                <CardTitle className="text-3xl">{documents.filter((d) => d.compliance_report).length}</CardTitle>
              </CardHeader>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Documents by Type</CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                {byType.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No data yet</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={byType} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                        {byType.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Documents by Department</CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                {byDepartment.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No data yet</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={byDepartment}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                      <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>

          {agentStats.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Agent Executions</CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={agentStats}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="agent" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <YAxis yAxisId="left" orientation="left" stroke="#6366f1" />
                    <YAxis yAxisId="right" orientation="right" stroke="#22c55e" />
                    <Tooltip />
                    <Bar yAxisId="left" dataKey="avgMs" fill="#6366f1" name="Avg Duration (ms)" radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="right" dataKey="tokens" fill="#22c55e" name="Total Tokens" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-5">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total Agent Runs</CardDescription>
                <CardTitle className="text-3xl text-indigo-600 font-extrabold">
                  {agentAnalytics?.total_runs || 0}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total Tokens</CardDescription>
                <CardTitle className="text-2xl font-extrabold text-slate-800">
                  {agentAnalytics?.total_tokens?.toLocaleString() || 0}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Estimated Cost</CardDescription>
                <CardTitle className="text-2xl font-extrabold text-emerald-600">
                  ${agentAnalytics?.estimated_cost?.toFixed(4) || "0.0000"}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Avg Latency (SLA)</CardDescription>
                <CardTitle className="text-2xl font-extrabold text-slate-800">
                  {agentAnalytics?.average_latency_ms || 0} ms
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Success Rate</CardDescription>
                <CardTitle className="text-2xl font-extrabold text-indigo-700">
                  {agentAnalytics ? `${Math.round(agentAnalytics.success_rate * 100)}%` : "100%"}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Token Cost Load Timeline (7 Days)</CardTitle>
                <CardDescription>Corpus token load processed daily over the past week</CardDescription>
              </CardHeader>
              <CardContent className="h-72">
                {agentAnalytics?.timeline && (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={agentAnalytics.timeline}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                      <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="tokens" stroke="#6366f1" strokeWidth={2.5} activeDot={{ r: 8 }} />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Agent Average Duration Performance</CardTitle>
                <CardDescription>Comparison of execution latencies across agents</CardDescription>
              </CardHeader>
              <CardContent className="h-72">
                {agentAnalytics?.agent_performance && (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={agentAnalytics.agent_performance}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="agent" tick={{ fill: "#94a3b8", fontSize: 9 }} />
                      <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="avg_latency_ms" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Agent Performance Metrics</CardTitle>
              <CardDescription>Detailed statistics per individual agent module</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b bg-slate-50 text-slate-500 font-semibold">
                      <th className="py-2.5 px-4">Agent Module</th>
                      <th className="py-2.5 px-4">Total Invocations</th>
                      <th className="py-2.5 px-4">Avg Duration (ms)</th>
                      <th className="py-2.5 px-4">Total Tokens</th>
                      <th className="py-2.5 px-4">Avg Confidence</th>
                      <th className="py-2.5 px-4">SLA Success Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(agentAnalytics?.agent_performance || []).map((perf: any, idx: number) => (
                      <tr key={idx} className="border-b hover:bg-slate-50/50">
                        <td className="py-2.5 px-4 font-bold text-slate-800">{perf.agent}</td>
                        <td className="py-2.5 px-4 font-semibold">{perf.runs} runs</td>
                        <td className="py-2.5 px-4 font-mono font-bold text-slate-800">{perf.avg_latency_ms} ms</td>
                        <td className="py-2.5 px-4 text-muted-foreground">{perf.total_tokens.toLocaleString()} tokens</td>
                        <td className="py-2.5 px-4">
                          {perf.avg_confidence != null ? `${Math.round(perf.avg_confidence * 100)}%` : "-"}
                        </td>
                        <td className="py-2.5 px-4">
                          <span className={`rounded px-1.5 py-0.5 font-bold ${
                            perf.success_rate > 0.95 ? "bg-emerald-100 text-emerald-800" : "bg-yellow-100 text-yellow-800"
                          }`}>
                            {Math.round(perf.success_rate * 100)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
