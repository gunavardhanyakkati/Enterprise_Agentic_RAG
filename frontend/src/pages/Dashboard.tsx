import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type Document } from "@/lib/api";

export function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listDocuments()
      .then(setDocuments)
      .catch((err) => setError(err.message));
  }, []);

  const processed = documents.filter((d) => d.content_processed).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your enterprise document intelligence workspace</p>
      </div>

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
            <CardTitle className="text-3xl">{processed}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Categories</CardDescription>
            <CardTitle className="text-3xl">{new Set(documents.map((d) => d.document_type)).size}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>With Compliance</CardDescription>
            <CardTitle className="text-3xl">{documents.filter((d) => d.compliance_report).length}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Documents</CardTitle>
            <CardDescription>Latest uploads and intelligence results</CardDescription>
          </div>
          <Link
            to="/upload"
            className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Upload
          </Link>
        </CardHeader>
        <CardContent>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <div className="space-y-3">
            {documents.slice(0, 8).map((doc) => (
              <Link
                key={doc.document_id}
                to={`/documents/${doc.document_id}`}
                className="flex items-center justify-between rounded-lg border border-border p-4 hover:bg-accent/40"
              >
                <div>
                  <p className="font-medium">{doc.title}</p>
                  <p className="text-sm text-muted-foreground">{doc.department} · {doc.document_type}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={doc.content_processed ? "success" : "secondary"}>
                    {doc.content_processed ? "Indexed" : "Pending"}
                  </Badge>
                  {doc.classification_confidence != null && (
                    <Badge variant="secondary">{Math.round(doc.classification_confidence * 100)}%</Badge>
                  )}
                </div>
              </Link>
            ))}
            {documents.length === 0 && !error && (
              <p className="text-sm text-muted-foreground">No documents yet. Upload your first document.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
