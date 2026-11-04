import { Suspense } from "react";

export const instant = false;
import { ProspectsView } from "@/components/prospects/view";
import { PageFallback } from "@/components/fallback";

export default function ProspectsPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <ProspectsView />
    </Suspense>
  );
}
