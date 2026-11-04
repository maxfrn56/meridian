import { Suspense } from "react";

export const instant = false;
import { TrackingView } from "@/components/tracking/view";
import { PageFallback } from "@/components/fallback";

export default function TrackingPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <TrackingView />
    </Suspense>
  );
}
