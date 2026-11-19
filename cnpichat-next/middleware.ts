import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // Proxy all /api/* requests to Django backend.
  // Middleware runs BEFORE Next.js built-in trailing-slash redirects,
  // so this prevents the 308 redirect loop.
  if (pathname.startsWith("/api/")) {
    // Normalize: ensure trailing slash for Django
    const backendPath = pathname.endsWith("/") ? pathname : `${pathname}/`;
    const url = `${BACKEND_URL}${backendPath}${search}`;

    return NextResponse.rewrite(url);
  }
}

export const config = {
  matcher: "/api/:path*",
};
