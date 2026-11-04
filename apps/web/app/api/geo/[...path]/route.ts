import { NextRequest } from "next/server";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

async function proxy(request: NextRequest, path: string[]) {
  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  if (authorization) headers.set("authorization", authorization);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();

  try {
    const base = API_URL.trim() || "http://127.0.0.1:8000";
    const target = new URL(`/api/v1/${path.join("/")}`, base);
    target.search = request.nextUrl.search;
    const response = await fetch(target, {
      method: request.method,
      headers,
      body: body || undefined,
      cache: "no-store",
    });
    const text = await response.text();
    return new Response(text, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json(
      { detail: "L'API Meridian est injoignable. Démarrez-la avec make api." },
      { status: 503 },
    );
  }
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(request, path);
}
