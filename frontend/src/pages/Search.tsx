import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Filter, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type SearchHit } from "@/lib/api";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  // Advanced Relational Filters
  const [docType, setDocType] = useState("");
  const [dept, setDept] = useState("");
  const [access, setAccess] = useState("");
  const [noticeDays, setNoticeDays] = useState("");
  const [liability, setLiability] = useState("");

  const resetFilters = () => {
    setDocType("");
    setDept("");
    setAccess("");
    setNoticeDays("");
    setLiability("");
  };

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setSearched(true);
    try {
      const filters: Record<string, any> = {};
      if (docType) filters.document_type = docType;
      if (dept) filters.department = dept;
      if (access) filters.access_level = access;
      if (noticeDays) filters.notice_period_days = parseInt(noticeDays);
      if (liability) filters.min_liability_cap = parseFloat(liability);

      const result = await api.search(query.trim(), filters);
      setHits(result.hits);
      setTotal(result.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Enterprise Hybrid Search</h1>
        <p className="text-muted-foreground">Semantic search + relational metadata filters across document vaults</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Filters Sidebar */}
        <Card className="lg:col-span-1 h-fit">
          <CardHeader className="pb-3 border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-bold flex items-center gap-1.5">
                <Filter className="h-4 w-4 text-indigo-600" />
                Advanced Filters
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={resetFilters}
                className="h-7 px-2 text-xs text-muted-foreground hover:text-indigo-600"
              >
                Reset
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-4 space-y-4 text-xs">
            {/* Category Filter */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Classification Type</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full rounded border bg-background p-2 text-xs focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Categories</option>
                <option value="Vendor Agreement">Vendor Agreement</option>
                <option value="Financial Report">Financial Report</option>
                <option value="Employee Policy">Employee Policy</option>
                <option value="Technical Document">Technical Document</option>
              </select>
            </div>

            {/* Department Filter */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Department</label>
              <select
                value={dept}
                onChange={(e) => setDept(e.target.value)}
                className="w-full rounded border bg-background p-2 text-xs focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Departments</option>
                <option value="Legal">Legal</option>
                <option value="Finance">Finance</option>
                <option value="HR">HR</option>
                <option value="Engineering">Engineering</option>
                <option value="Operations">Operations</option>
              </select>
            </div>

            {/* Security Access Level */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Access Control Level</label>
              <select
                value={access}
                onChange={(e) => setAccess(e.target.value)}
                className="w-full rounded border bg-background p-2 text-xs focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Access Levels</option>
                <option value="public">Public</option>
                <option value="internal">Internal</option>
                <option value="confidential">Confidential</option>
                <option value="restricted">Restricted</option>
              </select>
            </div>

            {/* Notice Period Filter */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Notice Period (Days)</label>
              <Input
                type="number"
                value={noticeDays}
                onChange={(e) => setNoticeDays(e.target.value)}
                placeholder="e.g. 90"
                className="h-8 text-xs"
              />
            </div>

            {/* Liability Cap Filter */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Min Liability Cap ($)</label>
              <Input
                type="number"
                value={liability}
                onChange={(e) => setLiability(e.target.value)}
                placeholder="e.g. 5000000"
                className="h-8 text-xs"
              />
            </div>
          </CardContent>
        </Card>

        {/* Search Results Display Area */}
        <div className="lg:col-span-3 space-y-6">
          <Card>
            <CardContent className="pt-6">
              <form onSubmit={handleSearch} className="flex gap-3">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask a question or search keywords across metadata and policy vaults..."
                  className="flex-1"
                />
                <Button type="submit" disabled={loading} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">
                  <Search className="h-4 w-4 mr-1" />
                  {loading ? "Searching..." : "Search"}
                </Button>
              </form>
            </CardContent>
          </Card>

          {error && <p className="text-sm text-red-400">{error}</p>}

          {searched && (
            <Card>
              <CardHeader>
                <CardTitle>Vault Search Results</CardTitle>
                <CardDescription>{total} matches found for &quot;{query}&quot;</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {hits.length === 0 && <p className="text-sm text-muted-foreground py-6 text-center">No matching document chunks found.</p>}
                {hits.map((hit, i) => {
                  const complianceScore = hit.compliance_report?.risk_score;
                  const isLowCompliance = complianceScore !== undefined && complianceScore < 80;

                  return (
                    <div key={i} className="rounded-lg border border-border p-4 bg-slate-50/50 hover:bg-slate-50 transition space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
                        <div className="flex items-center gap-2">
                          <p className="font-bold text-slate-800">{hit.title}</p>
                          {hit.document_type && (
                            <Badge variant="secondary">{hit.document_type}</Badge>
                          )}
                          {hit.access_level && (
                            <Badge variant="secondary" className="capitalize text-[10px]">{hit.access_level}</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className="bg-indigo-600 text-white font-mono">Score {hit.score.toFixed(3)}</Badge>
                          {hit.section_name && <Badge variant="secondary" className="bg-white">{hit.section_name}</Badge>}
                        </div>
                      </div>
                      
                      <p className="text-xs text-slate-700 leading-relaxed italic">
                        &ldquo;{hit.chunk_text || hit.abstract}&rdquo;
                      </p>

                      <div className="flex items-center justify-between pt-1 border-t text-[11px]">
                        {isLowCompliance ? (
                          <span className="flex items-center gap-1 text-red-600 font-semibold">
                            <ShieldAlert className="h-3.5 w-3.5" /> High Risk Profile (Compliance Score: {complianceScore}%)
                          </span>
                        ) : (
                          <span className="text-muted-foreground">
                            Indexed: {hit.created_at ? new Date(hit.created_at).toLocaleDateString() : "June 2026"}
                          </span>
                        )}

                        {hit.arxiv_id && (
                          <Link
                            to={`/documents/${hit.arxiv_id}`}
                            className="text-indigo-600 font-semibold hover:underline inline-flex items-center"
                          >
                            Open Intelligence File ➔
                          </Link>
                        )}
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
