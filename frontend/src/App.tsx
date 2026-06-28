import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { useAuth } from "@/lib/auth";
import { AgentVisualizationPage } from "@/pages/AgentVisualization";
import { AnalyticsPage } from "@/pages/Analytics";
import { ChatPage } from "@/pages/Chat";
import { CompliancePage } from "@/pages/ComplianceReport";
import { DashboardPage } from "@/pages/Dashboard";
import { DocumentViewerPage } from "@/pages/DocumentViewer";
import { LoginPage } from "@/pages/Login";
import { SearchPage } from "@/pages/Search";
import { UploadPage } from "@/pages/Upload";
import { InterviewDemoPage } from "@/pages/InterviewDemo";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center">Loading...</div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="documents/:id" element={<DocumentViewerPage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="compliance" element={<CompliancePage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="agents" element={<AgentVisualizationPage />} />
        <Route path="interview-demo" element={<InterviewDemoPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
