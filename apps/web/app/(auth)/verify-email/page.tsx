import { Suspense } from "react";
import { VerifyEmail } from "@/components/auth/recovery";

export const instant = false;

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmail />
    </Suspense>
  );
}
