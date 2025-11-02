import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// This is a proxy endpoint that forwards requests to the backend service
export async function GET(request: NextRequest) {
  try {
    // Get query parameters from the request
    const { searchParams } = new URL(request.url);
    const params = new URLSearchParams();
    
    // Forward all query parameters to the backend
    searchParams.forEach((value, key) => {
      params.append(key, value);
    });
  
    // Build the backend URL with query parameters
    const backendUrl = `http://tae-service:8002/api/v1/rules?${params.toString()}`;
    
    // Make request to the backend
    const response = await fetch(backendUrl, {
      headers: {
        'Accept': 'application/json',
      },
      // Add cache control headers to prevent caching
      next: { revalidate: 0 },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: error.detail || 'Failed to fetch rules' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching rules:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export const dynamic = 'force-dynamic'; // Ensure the route is handled at runtime
