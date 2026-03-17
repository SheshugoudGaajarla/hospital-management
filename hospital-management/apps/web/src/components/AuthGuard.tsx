"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { AppRole, getRole, getToken } from "@/src/lib/auth";

type AuthGuardProps = {
  children: ReactNode;
  allowedRoles?: AppRole[];
};

export function AuthGuard({ children, allowedRoles }: AuthGuardProps) {
  const router = useRouter();
  const [authState, setAuthState] = useState<"checking" | "allowed">("checking");

  useEffect(() => {
    const token = getToken();
    const role = getRole();

    if (!token || !role) {
      router.replace("/login");
      return;
    }

    if (allowedRoles && !allowedRoles.includes(role)) {
      router.replace("/no-access");
      return;
    }

    setAuthState("allowed");
  }, [allowedRoles, router]);

  if (authState === "checking") {
    return <div className="state-view">Checking authentication...</div>;
  }

  return <>{children}</>;
}
