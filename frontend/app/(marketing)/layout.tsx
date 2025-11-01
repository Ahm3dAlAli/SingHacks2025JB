import type { ReactNode } from "react";
import Header from "@/components/Header";

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Header />
      {children}
    </>
  );
}
