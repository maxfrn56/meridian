import { Suspense } from "react";

export const instant = false;
import { BillingView } from "@/components/billing/view";
import { PageFallback } from "@/components/fallback";

export default function BillingPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <BillingView />
    </Suspense>
  );
}
