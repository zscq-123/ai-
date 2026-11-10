import { createHmac } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

type SupportRequest = {
  message?: unknown;
  merchantId?: unknown;
  productId?: unknown;
  skuId?: unknown;
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
  const productId = typeof body.productId === "string" ? body.productId : undefined;
  const skuId = typeof body.skuId === "string" ? body.skuId : undefined;
  if (!message || message.length > 2_000) {
    return NextResponse.json({ detail: "Message must contain 1-2000 characters" }, { status: 400 });
  }
  for (const [label, value] of [["merchant", merchantId], ["product", productId], ["SKU", skuId]] as const) {
    if (value && !UUID_PATTERN.test(value)) {
      return NextResponse.json({ detail: `Invalid ${label} id` }, { status: 400 });
    }
  }

  const upstreamHeaders: Record<string, string> = { "Content-Type": "application/json" };
  const customerId = await currentCustomerId(request);
  if (customerId || merchantId || productId || skuId) {
    const secret = process.env.AI_TRUSTED_CONTEXT_SECRET;
    if (!secret) {
      return NextResponse.json({ detail: "Support context is not configured" }, { status: 503 });
    }
    if (customerId) upstreamHeaders["X-Nova-Customer-Id"] = customerId;
    if (merchantId) upstreamHeaders["X-Nova-Merchant-Id"] = merchantId;
    if (productId) upstreamHeaders["X-Nova-Product-Id"] = productId;
    if (skuId) upstreamHeaders["X-Nova-Sku-Id"] = skuId;
    upstreamHeaders["X-Nova-Context-Signature"] = createHmac("sha256", secret)
      .update(`${customerId ?? ""}\n${merchantId ?? ""}\n${productId ?? ""}\n${skuId ?? ""}`)
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

async function currentCustomerId(request: NextRequest): Promise<string | undefined> {
  const session = request.cookies.get("nova_session");
  if (!session) return undefined;
  const commerceApiUrl = process.env.COMMERCE_API_BASE_URL ?? "http://127.0.0.1:8080";
  try {
    const response = await fetch(`${commerceApiUrl}/api/public/auth/me`, {
      headers: { Cookie: `${session.name}=${session.value}` },
      cache: "no-store",
    });
    if (!response.ok) return undefined;
    const payload = await response.json() as { id?: unknown };
    return typeof payload.id === "string" && UUID_PATTERN.test(payload.id) ? payload.id : undefined;
  } catch {
    return undefined;
  }
}
