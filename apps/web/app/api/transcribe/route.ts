import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();

        // 你的 Python 后端地址
        const apiBase = process.env.RAG_API_BASE || "http://127.0.0.1:8000";

        const backendRes = await fetch(`${apiBase}/v1/transcribe`, {
            method: "POST",
            body: formData,
            // 注意：fetch 会自动设置 multipart/form-data 的 boundary，不要手动设置 Content-Type
        });

        if (!backendRes.ok) {
            return NextResponse.json(
                { error: "Backend transcription failed" },
                { status: backendRes.status }
            );
        }

        const data = await backendRes.json();
        return NextResponse.json(data);
    } catch (error: any) {
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}