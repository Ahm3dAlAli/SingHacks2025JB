import type { ReactNode } from "react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import SidebarAppNav from "@/components/SidebarAppNav";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider>
      <SidebarAppNav />
      <SidebarInset>
        <div className="flex items-center gap-2 border-b px-6 py-3">
          <SidebarTrigger />
        </div>
        <div className="px-6 py-6">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}

