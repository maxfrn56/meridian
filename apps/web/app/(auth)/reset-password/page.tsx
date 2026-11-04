import { Suspense } from "react";
import { ResetPassword } from "@/components/auth/recovery";

export const instant = false;

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPassword />
    </Suspense>
  );
}
