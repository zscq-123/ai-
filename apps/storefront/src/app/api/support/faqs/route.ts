import { NextRequest, NextResponse } from "next/server";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(request: NextRequest) {
  const merchantId = request.nextUrl.searchParams.get("merchantId");
  if (merchantId && !UUID_PATTERN.test(merchantId)) {
    return NextResponse.json({ detail: "Invalid merchant id" }, { status: 400 });
  }

  const commerceApiBaseUrl = process.env.COMMERCE_API_BASE_URL ?? "http://127.0.0.1:8080";
  const url = new URL("/api/public/support/faqs", commerceApiBaseUrl);
  if (merchantId) url.searchParams.set("merchantId", merchantId);

  try {
    const upstream = await fetch(url, { cache: "no-store" });
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "FAQ service unavailable" }, { status: 502 });
  }
}
