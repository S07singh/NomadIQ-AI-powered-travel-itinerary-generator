import { auth } from "@/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const { pathname } = req.nextUrl;

  // Public routes that don't require auth
  const publicRoutes = ["/", "/login", "/signup"];
  const isPublicRoute = publicRoutes.includes(pathname);
  const isAuthRoute = pathname.startsWith("/api/auth");
  const isApiRoute = pathname.startsWith("/api/");

  // Allow auth API routes
  if (isAuthRoute) return NextResponse.next();

  // Allow signup API
  if (pathname === "/api/signup") return NextResponse.next();

  // Redirect logged-in users away from login/signup
  if (isLoggedIn && (pathname === "/login" || pathname === "/signup")) {
    return NextResponse.redirect(new URL("/plans", req.nextUrl));
  }

  // Allow public routes
  if (isPublicRoute) return NextResponse.next();

  // Allow API routes (backend proxy)
  if (isApiRoute) return NextResponse.next();

  // Protect everything else
  if (!isLoggedIn) {
    return NextResponse.redirect(new URL("/login", req.nextUrl));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
