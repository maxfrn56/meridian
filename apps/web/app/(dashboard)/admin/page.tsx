import { Suspense } from "react";

export const instant = false;
import { AdminView } from "@/components/admin/view";
import { PageFallback } from "@/components/fallback";

export default function AdminPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <AdminView />
    </Suspense>
  );
}
