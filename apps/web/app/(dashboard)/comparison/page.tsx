import { Suspense } from "react";

export const instant = false;
import { ComparisonView } from "@/components/comparison/view";
import { PageFallback } from "@/components/fallback";

export default function ComparisonPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <ComparisonView />
    </Suspense>
  );
}
