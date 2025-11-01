"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bell, FileText, Layers, Settings, ShieldCheck, Users } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarSeparator,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";

function NavItem({ href, label, Icon }: { href: string; label: string; Icon: React.ComponentType<React.SVGProps<SVGSVGElement>> }) {
  const pathname = usePathname();
  const active = pathname === href || pathname?.startsWith(href + "/");
  return (
    <SidebarMenuItem>
      <Link
        href={href}
        data-active={active}
        className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-zinc-700 outline-hidden hover:bg-zinc-100 data-[active=true]:bg-primary/10 data-[active=true]:text-primary dark:text-zinc-300 dark:hover:bg-zinc-800"
      >
        <Icon className="h-4 w-4" />
        <span>{label}</span>
      </Link>
    </SidebarMenuItem>
  );
}

export default function SidebarAppNav() {
  return (
    <Sidebar>
      <SidebarHeader>
        <div className="px-1 text-sm font-semibold">Platform</div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Overview</SidebarGroupLabel>
          <SidebarMenu>
            <NavItem href="/dashboard" label="Dashboard" Icon={Activity} />
          </SidebarMenu>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Operations</SidebarGroupLabel>
          <SidebarMenu>
            <NavItem href="/alerts" label="Alerts" Icon={Bell} />
            <NavItem href="#" label="Rules" Icon={ShieldCheck} />
            <NavItem href="#" label="Documents" Icon={FileText} />
            <NavItem href="#" label="Entities" Icon={Users} />
          </SidebarMenu>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Admin</SidebarGroupLabel>
          <SidebarMenu>
            <NavItem href="#" label="Integrations" Icon={Layers} />
            <NavItem href="#" label="Settings" Icon={Settings} />
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarSeparator />
      <SidebarFooter>
        <div className="px-1 text-xs text-muted-foreground">v0.1.0</div>
      </SidebarFooter>
    </Sidebar>
  );
}
