"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Activity, Bell, CreditCard, Layers, Settings, ShieldCheck, Users, Newspaper, FileText } from "lucide-react";
import { useRole, saveRole } from "@/lib/use-role";
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



function NavItem({ href, label, Icon, after }: { href: string; label: string; Icon: React.ComponentType<React.SVGProps<SVGSVGElement>>; after?: React.ReactNode }) {
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
        <span className="flex items-center gap-2">
          {label}
          {after}
        </span>
      </Link>
    </SidebarMenuItem>
  );
}

export default function SidebarAppNav() {
  const { role } = useRole();
  function RegUpdatesBadge() {
    const [count, setCount] = useState<number>(0);
    useEffect(() => {
      let mounted = true;
      async function load() {
        try {
          const res = await fetch("/api/rules/suggestions?status=needs_review");
          if (!res.ok) return;
          const data = await res.json();
          if (mounted) setCount(Array.isArray(data.items) ? data.items.length : 0);
        } catch {}
      }
      load();
      const t = setInterval(load, 15000);
      return () => { mounted = false; clearInterval(t); };
    }, []);
    if (!count) return null;
    return <span className="rounded-full bg-amber-500 px-1.5 py-0.5 text-[10px] text-white">{count}</span>;
  }
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
            <NavItem href="/rules" label="Rules" Icon={ShieldCheck} />
            <NavItem href="/transactions" label="Transactions" Icon={CreditCard} />
            <NavItem href="/regulatory-updates" label="Regulatory Updates" Icon={Newspaper} after={<RegUpdatesBadge />} />
            <NavItem href="/kyc" label="KYC" Icon={Users} />
            <NavItem href="/documentation-review" label="Documentation" Icon={FileText} />
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
        <div className="px-1 text-xs text-muted-foreground flex items-center justify-between gap-2 w-full">
          <div className="flex items-center gap-2">
            <span>Role</span>
            <select
              value={role}
              onChange={(e) => saveRole(e.target.value as any)}
              className="rounded border bg-white p-1 dark:border-zinc-700 dark:bg-zinc-950"
            >
              <option value="relationship_manager">Relationship Manager</option>
              <option value="compliance_manager">Compliance Manager</option>
              <option value="legal">Legal</option>
            </select>
          </div>
          <span>v0.1.0</span>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
