import { NextRequest, NextResponse } from "next/server";

const commerceApiBaseUrl = process.env.COMMERCE_API_BASE_URL ?? "http://127.0.0.1:8080";
const allowedActions = new Set(["register", "login", "logout"]);

export async function POST(request: NextRequest, context: RouteContext<"/api/auth/[action]">) {
  const { action } = await context.params;
  if (!allowedActions.has(action)) {
    return NextResponse.json({ message: "不支持的账号操作" }, { status: 404 });
  }

  const headers = new Headers();
  const cookie = request.headers.get("cookie");
  const contentType = request.headers.get("content-type");
  if (cookie) headers.set("cookie", cookie);
  if (contentType) headers.set("content-type", contentType);

  try {
    const body = action === "logout" ? undefined : await request.text();
    const upstream = await fetch(`${commerceApiBaseUrl}/api/public/auth/${action}`, {
      method: "POST",
      headers,
      body,
      cache: "no-store",
    });
    const response = new NextResponse(upstream.status === 204 ? null : await upstream.text(), {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
    });
    const setCookie = upstream.headers.get("set-cookie");
    if (setCookie) response.headers.set("set-cookie", setCookie);
    return response;
  } catch {
    return NextResponse.json({ message: "账号服务暂时不可用，请稍后重试" }, { status: 503 });
  }
}
