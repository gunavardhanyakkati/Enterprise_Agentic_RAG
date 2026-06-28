import { NavLink, Outlet } from "react-router-dom";
import {
  BarChart3,
  Bot,
  Cpu,
  FileSearch,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/search", label: "Search", icon: FileSearch },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/compliance", label: "Compliance", icon: ShieldCheck },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/agents", label: "Agent Workflow", icon: Bot },
  { to: "/interview-demo", label: "Interview Sandbox", icon: Cpu },
];

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="border-b border-border bg-card lg:border-b-0 lg:border-r">
        <div className="flex h-16 items-center px-6">
          <div>
            <p className="text-sm font-semibold">Enterprise Doc Intelligence</p>
            <p className="text-xs text-muted-foreground">Agentic AI Platform</p>
          </div>
        </div>
        <nav className="space-y-1 px-3 py-4">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent hover:text-foreground"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-border p-4">
          <p className="text-sm font-medium">{user?.username}</p>
          <p className="text-xs text-muted-foreground">{user?.department}</p>
          <Button variant="ghost" size="sm" className="mt-3 w-full justify-start" onClick={logout}>
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </div>
      </aside>
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
