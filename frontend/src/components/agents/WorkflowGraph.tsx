import {
  Brain,
  FileSearch,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Tags,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { AgentExecution } from "@/lib/api";
import {
  DEFAULT_WORKFLOW_NODES,
  formatConfidence,
  formatTokens,
  getExecutionMap,
  getNodeStatus,
  type NodeStatus,
  type WorkflowNodeDef,
} from "@/lib/workflow";

const NODE_ICONS: Record<string, typeof Tags> = {
  classify: Tags,
  metadata: Sparkles,
  retrieve: FileSearch,
  compliance: ShieldCheck,
  summarize: Brain,
  qa: MessageSquare,
};

const STATUS_STYLES: Record<NodeStatus, { ring: string; bg: string; text: string }> = {
  success: { ring: "ring-emerald-500/50", bg: "bg-emerald-600/15", text: "text-emerald-300" },
  error: { ring: "ring-red-500/50", bg: "bg-red-600/15", text: "text-red-300" },
  pending: { ring: "ring-border", bg: "bg-muted/30", text: "text-muted-foreground" },
  on_demand: { ring: "ring-amber-500/40", bg: "bg-amber-600/10", text: "text-amber-200" },
};

interface WorkflowGraphProps {
  nodes?: WorkflowNodeDef[];
  executions: AgentExecution[];
  selectedNodeId?: string;
  onSelectNode?: (nodeId: string) => void;
}

export function WorkflowGraph({
  nodes = DEFAULT_WORKFLOW_NODES,
  executions,
  selectedNodeId,
  onSelectNode,
}: WorkflowGraphProps) {
  const executionMap = getExecutionMap(executions);

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-[920px] items-start gap-2">
        {nodes.map((node, index) => {
          const status = getNodeStatus(node, executions);
          const styles = STATUS_STYLES[status];
          const exec = executionMap.get(node.agent);
          const Icon = NODE_ICONS[node.id] || Tags;
          const selected = selectedNodeId === node.id;

          return (
            <div key={node.id} className="flex flex-1 items-center">
              <button
                type="button"
                onClick={() => onSelectNode?.(node.id)}
                className={`group w-full rounded-xl border border-border p-4 text-left transition-all hover:border-primary/40 ${
                  selected ? "border-primary ring-2 ring-primary/30" : ""
                } ${styles.bg}`}
              >
                <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-full ring-2 ${styles.ring}`}>
                  <Icon className={`h-5 w-5 ${styles.text}`} />
                </div>
                <p className="text-sm font-semibold">{node.label}</p>
                <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{node.description}</p>
                <div className="mt-3 flex flex-wrap gap-1">
                  <Badge
                    variant={
                      status === "success"
                        ? "success"
                        : status === "error"
                          ? "destructive"
                          : status === "on_demand"
                            ? "warning"
                            : "secondary"
                    }
                  >
                    {status === "on_demand" ? "on demand" : status}
                  </Badge>
                </div>
                {exec && (
                  <div className="mt-3 grid grid-cols-3 gap-1 text-[10px] text-muted-foreground">
                    <div>
                      <p className="uppercase tracking-wide">Time</p>
                      <p className="font-medium text-foreground">{exec.execution_time_ms}ms</p>
                    </div>
                    <div>
                      <p className="uppercase tracking-wide">Conf.</p>
                      <p className="font-medium text-foreground">{formatConfidence(exec.confidence)}</p>
                    </div>
                    <div>
                      <p className="uppercase tracking-wide">Tokens</p>
                      <p className="font-medium text-foreground">{formatTokens(exec.tokens_used)}</p>
                    </div>
                  </div>
                )}
              </button>
              {index < nodes.length - 1 && (
                <div className="mx-1 flex shrink-0 flex-col items-center">
                  <div className="h-0.5 w-6 bg-border" />
                  <div className="text-muted-foreground">→</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface AgentExecutionDetailsProps {
  nodes?: WorkflowNodeDef[];
  executions: AgentExecution[];
  selectedNodeId?: string;
}

export function AgentExecutionDetails({
  nodes = DEFAULT_WORKFLOW_NODES,
  executions,
  selectedNodeId,
}: AgentExecutionDetailsProps) {
  const executionMap = getExecutionMap(executions);
  const visibleNodes = selectedNodeId ? nodes.filter((n) => n.id === selectedNodeId) : nodes;

  return (
    <div className="space-y-3">
      {visibleNodes.map((node) => {
        const exec = executionMap.get(node.agent);
        const status = getNodeStatus(node, executions);

        return (
          <div key={node.id} className="rounded-lg border border-border p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium">{node.label}</p>
              <Badge
                variant={
                  status === "success"
                    ? "success"
                    : status === "error"
                      ? "destructive"
                      : status === "on_demand"
                        ? "warning"
                        : "secondary"
                }
              >
                {status === "on_demand" ? "on demand" : status}
              </Badge>
            </div>
            {exec ? (
              <div className="mt-3 grid gap-3 md:grid-cols-4">
                <Metric label="Execution time" value={`${exec.execution_time_ms} ms`} />
                <Metric label="Confidence" value={formatConfidence(exec.confidence)} />
                <Metric label="Tokens used" value={formatTokens(exec.tokens_used)} />
                <Metric label="Agent" value={exec.agent} />
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">
                {node.on_demand
                  ? "Run via Chat or POST /api/v1/agents/run with a question."
                  : "Not executed yet for this document."}
              </p>
            )}
            {exec?.detail && <p className="mt-2 text-sm text-muted-foreground">{exec.detail}</p>}
          </div>
        );
      })}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted/30 p-3">
      <p className="text-xs uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium">{value}</p>
    </div>
  );
}
