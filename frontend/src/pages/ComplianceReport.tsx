import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/input";
import { api, type ComplianceReport, type Document } from "@/lib/api";

export function CompliancePage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listDocuments()
      .then((docs) => {
        setDocuments(docs);
        const withReport = docs.find((d) => d.compliance_report);
        if (withReport) {
          setSelectedId(withReport.document_id);
          setReport(withReport.compliance_report!);
        } else if (docs.length) {
          setSelectedId(docs[0].document_id);
        }
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const doc = documents.find((d) => d.document_id === selectedId);
    if (doc?.compliance_report) {
      setReport(doc.compliance_report);
    } else {
      setReport(null);
    }
  }, [selectedId, documents]);

  const riskLevel =
    !report ? "unknown" : report.risk_score >= 0.7 ? "high" : report.risk_score >= 0.4 ? "medium" : "low";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Compliance Reports</h1>
        <p className="text-muted-foreground">Review compliance analysis from the enterprise compliance agent</p>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">Document:</span>
        <Select value={selectedId} onChange={(e) => setSelectedId(e.target.value)} className="max-w-lg">
          {documents.map((doc) => (
            <option key={doc.document_id} value={doc.document_id}>
              {doc.title} ({doc.document_type})
            </option>
          ))}
        </Select>
        {selectedId && (
          <Link to={`/documents/${selectedId}`} className="text-sm text-primary hover:underline">
            View document
          </Link>
        )}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {!report && selectedId && (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            No compliance report for this document. Re-run agents from the document viewer.
          </CardContent>
        </Card>
      )}

      {report && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Risk Score</CardDescription>
                <CardTitle className="text-3xl">{Math.round(report.risk_score * 100)}%</CardTitle>
              </CardHeader>
              <CardContent>
                <Badge
                  variant={riskLevel === "high" ? "destructive" : riskLevel === "medium" ? "warning" : "success"}
                >
                  {riskLevel} risk
                </Badge>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Checks Passed</CardDescription>
                <CardTitle className="text-3xl">
                  {report.checks.filter((c) => c.status === "present").length}/{report.checks.length}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Document Type</CardDescription>
                <CardTitle className="text-xl">{report.document_type}</CardTitle>
              </CardHeader>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5" />
                Compliance Summary
              </CardTitle>
              <CardDescription>{report.summary}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {report.checks.map((check, i) => (
                <div key={i} className="flex items-start gap-3 rounded-lg border border-border p-4">
                  <AlertTriangle
                    className={`mt-0.5 h-4 w-4 shrink-0 ${
                      check.status === "present"
                        ? "text-emerald-400"
                        : check.status === "partial"
                          ? "text-amber-400"
                          : "text-red-400"
                    }`}
                  />
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{check.clause}</p>
                      <Badge
                        variant={
                          check.status === "present" ? "success" : check.status === "partial" ? "warning" : "destructive"
                        }
                      >
                        {check.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{check.evidence}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {report.recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-inside list-disc space-y-2 text-sm">
                  {report.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
