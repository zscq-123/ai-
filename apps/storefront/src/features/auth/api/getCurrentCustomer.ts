import "server-only";
import { cookies } from "next/headers";
import type { AuthenticatedCustomer } from "../model/customer";

const commerceApiBaseUrl = process.env.COMMERCE_API_BASE_URL ?? "http://127.0.0.1:8080";

export async function getCurrentCustomer(): Promise<AuthenticatedCustomer | null> {
  const session = (await cookies()).get("nova_session");
  if (!session) return null;

  try {
    const response = await fetch(`${commerceApiBaseUrl}/api/public/auth/me`, {
      headers: { Cookie: `${session.name}=${session.value}` },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as AuthenticatedCustomer;
  } catch {
    return null;
  }
}
