// apps/web/app/api/qa/stream/route.ts
export async function POST(req: Request) {
    const body = await req.json();

    const apiBase = process.env.RAG_API_BASE || "http://127.0.0.1:8000";
    const resp = await fetch(`${apiBase}/v1/qa/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!resp.ok) {
        const text = await resp.text();
        return new Response(text, {
            status: resp.status,
            headers: { "Content-Type": "application/json" },
        });
    }

    // 流式转发响应
    return new Response(resp.body, {
        status: resp.status,
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    });
}
