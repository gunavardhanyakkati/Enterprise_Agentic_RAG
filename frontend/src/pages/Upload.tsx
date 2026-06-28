import { FormEvent, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
import { api } from "@/lib/api";

export function UploadPage() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("Engineering");
  const [documentType, setDocumentType] = useState("Technical Document");
  const [accessLevel, setAccessLevel] = useState("internal");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Please select a file");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title || file.name);
    formData.append("description", "");
    formData.append("department", department);
    formData.append("document_type", documentType);
    formData.append("access_level", accessLevel);

    for (const [key, value] of formData.entries()) {
      console.log(`FormData Entry: ${key} =`, value);
    }

    setLoading(true);
    setError("");
    try {
      const doc = await api.uploadDocument(formData);
      navigate(`/documents/${doc.document_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && fileRef.current) {
      const dt = new DataTransfer();
      dt.items.add(file);
      fileRef.current.files = dt.files;
      if (!title) setTitle(file.name.replace(/\.[^.]+$/, ""));
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Upload Document</h1>
        <p className="text-muted-foreground">
          Upload PDF, DOCX, or TXT. The pipeline will parse, chunk, embed, and run enterprise agents.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New Document</CardTitle>
          <CardDescription>Supported formats: PDF, DOCX, TXT</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div
              className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 transition-colors ${
                dragOver ? "border-primary bg-primary/5" : "border-border"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <UploadCloud className="mb-3 h-10 w-10 text-muted-foreground" />
              <p className="mb-2 text-sm text-muted-foreground">Drag and drop or click to browse</p>
              <Input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" className="max-w-xs" />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="title">Title</Label>
                <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Document title" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="department">Department</Label>
                <Input id="department" value={department} onChange={(e) => setDepartment(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="type">Document Type</Label>
                <Select id="type" value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
                  <option>Employment Contract</option>
                  <option>Invoice</option>
                  <option>Resume</option>
                  <option>Email</option>
                  <option>HR Policy</option>
                  <option>Technical Document</option>
                  <option>Legal Agreement</option>
                  <option>Purchase Order</option>
                  <option>Employee Handbook</option>
                  <option>Compliance Document</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="access">Access Level</Label>
                <Select id="access" value={accessLevel} onChange={(e) => setAccessLevel(e.target.value)}>
                  <option value="public">Public</option>
                  <option value="internal">Internal</option>
                  <option value="confidential">Confidential</option>
                  <option value="restricted">Restricted</option>
                </Select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="secondary">Parse</Badge>
              <Badge variant="secondary">Chunk</Badge>
              <Badge variant="secondary">Embed</Badge>
              <Badge variant="secondary">Index</Badge>
              <Badge variant="success">Gemini Agents</Badge>
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Processing..." : "Upload & Analyze"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
