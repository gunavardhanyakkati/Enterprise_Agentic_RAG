import { FormEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bot, Send, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/input";
import { api, type ChatResponse, type Document } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  confidence?: number;
  sources?: ChatResponse["sources"];
}

export function ChatPage() {
  const [searchParams] = useSearchParams();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentId, setDocumentId] = useState(searchParams.get("doc") || "");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const response = await api.chat(question, documentId || undefined);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          confidence: response.confidence,
          sources: response.sources,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: err instanceof Error ? err.message : "Chat failed" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] flex-col gap-4">
      <div>
        <h1 className="text-3xl font-bold">Document Q&A Chat</h1>
        <p className="text-muted-foreground">Ask questions grounded in your indexed documents via the QA agent</p>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">Scope:</span>
        <Select value={documentId} onChange={(e) => setDocumentId(e.target.value)} className="max-w-md">
          <option value="">All documents</option>
          {documents.map((doc) => (
            <option key={doc.document_id} value={doc.document_id}>
              {doc.title}
            </option>
          ))}
        </Select>
      </div>

      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardHeader className="border-b border-border pb-4">
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Enterprise QA Agent
          </CardTitle>
          <CardDescription>Powered by Gemini with RAG retrieval</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col overflow-hidden p-0">
          <div className="flex-1 space-y-4 overflow-y-auto p-6">
            {messages.length === 0 && (
              <p className="text-center text-sm text-muted-foreground">
                Ask about policies, contracts, compliance requirements, or document content.
              </p>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
                {msg.role === "assistant" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/20">
                    <Bot className="h-4 w-4" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-3 ${
                    msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted/40"
                  }`}
                >
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                  {msg.confidence != null && (
                    <Badge variant="secondary" className="mt-2">
                      {Math.round(msg.confidence * 100)}% confidence
                    </Badge>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {msg.sources.map((src, j) => (
                        <p key={j} className="text-xs text-muted-foreground">
                          Source: {src.title || src.document_id} {src.section ? `· ${src.section}` : ""}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20">
                  <Bot className="h-4 w-4 animate-pulse" />
                </div>
                <div className="rounded-lg bg-muted/40 px-4 py-3 text-sm text-muted-foreground">Thinking...</div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border p-4">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              className="flex-1"
            />
            <Button type="submit" disabled={loading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
