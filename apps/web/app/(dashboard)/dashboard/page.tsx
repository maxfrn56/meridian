import { Suspense } from "react";

export const instant = false;
import { DashboardView } from "@/components/dashboard/view";
import { PageFallback } from "@/components/fallback";

export default function DashboardPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <DashboardView />
    </Suspense>
  );
}
