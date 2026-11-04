import { Suspense } from "react";

export const instant = false;
import { SettingsView } from "@/components/settings/view";
import { PageFallback } from "@/components/fallback";

export default function SettingsPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <SettingsView />
    </Suspense>
  );
}
