import { NextResponse } from "next/server";
import { getNightData } from "@/lib/data";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params;
    const data = getNightData(sessionId);
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Session not found" }, { status: 404 });
  }
}
