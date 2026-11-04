import { Suspense } from "react";

export const instant = false;
import { AuditView } from "@/components/audit/view";
import { PageFallback } from "@/components/fallback";

export default function AuditPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <AuditView />
    </Suspense>
  );
}
