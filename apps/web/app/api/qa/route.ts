// apps/web/app/api/qa/route.ts
export async function POST(req: Request) {
    const body = await req.json();

    const apiBase = process.env.RAG_API_BASE || "http://127.0.0.1:8000";
    const resp = await fetch(`${apiBase}/v1/qa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    const text = await resp.text();
    return new Response(text, {
        status: resp.status,
        headers: { "Content-Type": "application/json" },
    });
}
