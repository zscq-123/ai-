import { createHmac } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

type SupportRequest = {
  message?: unknown;
  merchantId?: unknown;
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(request: NextRequest) {
  let body: SupportRequest;
  try {
    body = await request.json() as SupportRequest;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  const message = typeof body.message === "string" ? body.message.trim() : "";
  const merchantId = typeof body.merchantId === "string" ? body.merchantId : undefined;
  if (!message || message.length > 2_000) {
    return NextResponse.json({ detail: "Message must contain 1-2000 characters" }, { status: 400 });
  }
  if (merchantId && !UUID_PATTERN.test(merchantId)) {
    return NextResponse.json({ detail: "Invalid merchant id" }, { status: 400 });
  }

  const upstreamHeaders: Record<string, string> = { "Content-Type": "application/json" };
  if (merchantId) {
    const secret = process.env.AI_TRUSTED_CONTEXT_SECRET;
    if (!secret) {
      return NextResponse.json({ detail: "Support context is not configured" }, { status: 503 });
    }
    upstreamHeaders["X-Nova-Merchant-Id"] = merchantId;
    upstreamHeaders["X-Nova-Context-Signature"] = createHmac("sha256", secret)
      .update(`\n${merchantId}`)
      .digest("hex");
  }

  const aiServiceUrl = process.env.AI_SERVICE_URL ?? "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${aiServiceUrl}/v1/support/chat`, {
      method: "POST",
      headers: upstreamHeaders,
      body: JSON.stringify({ message }),
      cache: "no-store",
    });
    const responseBody = await response.text();
    return new NextResponse(responseBody, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "AI support service unavailable" }, { status: 502 });
  }
}
