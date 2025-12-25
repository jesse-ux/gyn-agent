// apps/web/app/chat/page.tsx
"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";

// 引用弹窗组件
function SourceTooltip({
    source,
    children,
}: {
    source: SourceItem;
    children: React.ReactNode;
}) {
    const [show, setShow] = useState(false);

    return (
        <div
            style={{ position: "relative", display: "inline-block" }}
            onMouseEnter={() => setShow(true)}
            onMouseLeave={() => setShow(false)}
            onClick={() => setShow(!show)}
        >
            {children}
            {show && (
                <div
                    style={{
                        position: "absolute",
                        bottom: "100%",
                        left: 0,
                        marginBottom: 8,
                        padding: 12,
                        background: "white",
                        border: "1px solid rgba(0,0,0,0.15)",
                        borderRadius: 8,
                        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                        zIndex: 100,
                        minWidth: 280,
                        fontSize: 13,
                    }}
                >
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>
                        《{source.source ?? "未知来源"}》 第 {source.page ?? "?"} 页
                    </div>
                    {source.excerpt && (
                        <div style={{ opacity: 0.75, marginTop: 6, lineHeight: 1.5 }}>
                            {source.excerpt}…
                        </div>
                    )}
                    {source.distance !== undefined && (
                        <div style={{ fontSize: 11, opacity: 0.5, marginTop: 6 }}>
                            相似度: {(1 - source.distance).toFixed(3)}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

type SourceItem = {
    rank: number;
    source?: string;
    page?: number;
    chunk?: number;
    distance?: number;
    excerpt?: string;
};

type QAResp = {
    request_id: string;
    answer: string;
    sources: SourceItem[];
    latency_ms: number;
};

export default function ChatPage() {
    const [question, setQuestion] = useState("");
    const [loading, setLoading] = useState(false);
    const [streamLoading, setStreamLoading] = useState(false);
    const [data, setData] = useState<QAResp | null>(null);
    const [streamData, setStreamData] = useState("");
    const [streamSources, setStreamSources] = useState<SourceItem[]>([]);
    const [showStreamSources, setShowStreamSources] = useState(false);
    const [streamRequestId, setStreamRequestId] = useState<string>("");
    const [error, setError] = useState<string | null>(null);

    async function onAsk() {
        const q = question.trim();
        if (!q) return;

        setLoading(true);
        setError(null);
        setData(null);

        try {
            const resp = await fetch("/api/qa", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: q, top_k: 6 }),
            });

            if (!resp.ok) {
                const t = await resp.text();
                throw new Error(t || `HTTP ${resp.status}`);
            }

            const json = (await resp.json()) as QAResp;
            setData(json);
        } catch (e: any) {
            setError(e?.message || "Unknown error");
        } finally {
            setLoading(false);
        }
    }

    async function onStreamAsk() {
        const q = question.trim();
        if (!q) return;

        setStreamLoading(true);
        setError(null);
        setStreamData("");
        setStreamSources([]);
        setShowStreamSources(false);
        setStreamRequestId("");
        setData(null);

        try {
            const resp = await fetch("/api/qa/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: q, top_k: 6 }),
            });

            if (!resp.ok) {
                const t = await resp.text();
                throw new Error(t || `HTTP ${resp.status}`);
            }

            const reader = resp.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) {
                throw new Error("No response body");
            }

            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || ""; // 保留未完成的行

                for (const line of lines) {
                    if (!line.trim()) continue;

                    // 解析 SSE 事件
                    let eventLine = line;
                    let eventData = "";

                    // 检查是否有 event: 行
                    if (line.startsWith("event: ")) {
                        continue; // 下一行应该是 data:
                    }

                    // 解析 data: 行
                    if (line.startsWith("data: ")) {
                        const jsonStr = line.slice(6);
                        try {
                            const event = JSON.parse(jsonStr);

                            switch (event.type) {
                                case "sources":
                                    setStreamRequestId(event.request_id || "");
                                    setStreamSources(event.sources || []);
                                    break;

                                case "chunk":
                                    if (event.content) {
                                        setStreamData((prev) => prev + event.content);
                                    }
                                    break;

                                case "done":
                                    setStreamRequestId(event.request_id || "");
                                    setStreamLoading(false);
                                    setShowStreamSources(true); // 答案完成后显示参考来源
                                    console.log(`Stream completed in ${event.latency_ms}ms`);
                                    break;

                                case "error":
                                    throw new Error(event.message || "Stream error");

                                default:
                                    console.warn("Unknown event type:", event.type);
                            }
                        } catch (parseError) {
                            console.error("Failed to parse SSE JSON:", jsonStr, parseError);
                        }
                    }
                }
            }
        } catch (e: any) {
            setError(e?.message || "Unknown error");
        } finally {
            setStreamLoading(false);
        }
    }

    return (
        <main style={{ maxWidth: 900, margin: "40px auto", padding: 16 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600 }}>妇科知识库 QA（本地）</h1>

            <p style={{ opacity: 0.7, marginTop: 8 }}>
                免责声明：本工具仅用于科普信息整理，不提供诊断或处方建议；如有紧急情况请及时就医。
            </p>

            <div style={{ marginTop: 16 }}>
                <textarea
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="输入你的问题，例如：宫颈癌的预防方法有哪些？"
                    rows={4}
                    style={{
                        width: "100%",
                        padding: 12,
                        borderRadius: 10,
                        border: "1px solid rgba(0,0,0,0.15)",
                        fontSize: 14,
                    }}
                />
                <div style={{ marginTop: 10, display: "flex", gap: 10 }}>
                    <button
                        onClick={onAsk}
                        disabled={loading || streamLoading}
                        style={{
                            padding: "10px 14px",
                            borderRadius: 10,
                            border: "1px solid rgba(0,0,0,0.15)",
                            cursor: loading || streamLoading ? "not-allowed" : "pointer",
                        }}
                    >
                        {loading ? "生成中..." : "提问（普通）"}
                    </button>

                    <button
                        onClick={onStreamAsk}
                        disabled={loading || streamLoading}
                        style={{
                            padding: "10px 14px",
                            borderRadius: 10,
                            border: "1px solid rgba(0,0,0,0.15)",
                            backgroundColor: streamLoading ? "rgba(0,120,255,0.1)" : "transparent",
                            cursor: loading || streamLoading ? "not-allowed" : "pointer",
                        }}
                    >
                        {streamLoading ? "流式生成中..." : "提问（流式）"}
                    </button>

                    <button
                        onClick={() => {
                            setQuestion("");
                            setData(null);
                            setStreamData("");
                            setStreamSources([]);
                            setShowStreamSources(false);
                            setStreamRequestId("");
                            setError(null);
                        }}
                        disabled={loading || streamLoading}
                        style={{
                            padding: "10px 14px",
                            borderRadius: 10,
                            border: "1px solid rgba(0,0,0,0.15)",
                            cursor: loading || streamLoading ? "not-allowed" : "pointer",
                        }}
                    >
                        清空
                    </button>
                </div>
            </div>

            {error && (
                <pre
                    style={{
                        marginTop: 16,
                        padding: 12,
                        borderRadius: 10,
                        background: "rgba(255,0,0,0.06)",
                        whiteSpace: "pre-wrap",
                    }}
                >
                    {error}
                </pre>
            )}

            {streamData && (
                <section
                    style={{
                        marginTop: 18,
                        padding: 14,
                        borderRadius: 12,
                        border: "1px solid rgba(0,120,255,0.3)",
                        background: "rgba(0,120,255,0.02)",
                    }}
                >
                    <div style={{ fontSize: 12, opacity: 0.7, color: "#0078ff", display: "flex", justifyContent: "space-between" }}>
                        <span>{streamLoading ? "⏳ 流式生成中..." : "✅ 流式输出完成"}</span>
                        {streamRequestId && <span>request_id={streamRequestId}</span>}
                    </div>

                    <div style={{ marginTop: 10, lineHeight: 1.7 }}>
                        <ReactMarkdown>{streamData}</ReactMarkdown>
                    </div>
                </section>
            )}

            {showStreamSources && streamSources.length > 0 && (
                <div style={{ marginTop: 14, padding: 12, borderRadius: 10, background: "rgba(0,120,255,0.05)" }}>
                    <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 8, color: "#0078ff" }}>
                        参考来源（悬停或点击查看详情）
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        {streamSources.map((s) => (
                            <SourceTooltip key={`${s.rank}-${s.source}-${s.page}`} source={s}>
                                <div
                                    style={{
                                        display: "inline-flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        width: 28,
                                        height: 28,
                                        borderRadius: "50%",
                                        background: "#0078ff",
                                        color: "white",
                                        fontSize: 12,
                                        fontWeight: 600,
                                        cursor: "pointer",
                                        transition: "transform 0.2s",
                                    }}
                                    onMouseEnter={(e) =>
                                        (e.currentTarget.style.transform = "scale(1.1)")
                                    }
                                    onMouseLeave={(e) =>
                                        (e.currentTarget.style.transform = "scale(1)")
                                    }
                                >
                                    {s.rank}
                                </div>
                            </SourceTooltip>
                        ))}
                    </div>
                </div>
            )}

            {data && (
                <section
                    style={{
                        marginTop: 18,
                        padding: 14,
                        borderRadius: 12,
                        border: "1px solid rgba(0,0,0,0.12)",
                    }}
                >
                    <div style={{ fontSize: 12, opacity: 0.7 }}>
                        request_id={data.request_id} · latency={data.latency_ms}ms
                    </div>

                    <div style={{ marginTop: 10, lineHeight: 1.7 }}>
                        <ReactMarkdown>{data.answer}</ReactMarkdown>
                    </div>
                </section>
            )}

            {data?.sources?.length ? (
                <div style={{ marginTop: 14, padding: 12, borderRadius: 10, background: "rgba(0,0,0,0.03)" }}>
                    <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 8 }}>参考来源（悬停或点击查看详情）</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        {data.sources.map((s) => (
                            <SourceTooltip key={`${s.rank}-${s.source}-${s.page}`} source={s}>
                                <div
                                    style={{
                                        display: "inline-flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        width: 28,
                                        height: 28,
                                        borderRadius: "50%",
                                        background: "#333",
                                        color: "white",
                                        fontSize: 12,
                                        fontWeight: 600,
                                        cursor: "pointer",
                                        transition: "transform 0.2s",
                                    }}
                                    onMouseEnter={(e) =>
                                        (e.currentTarget.style.transform = "scale(1.1)")
                                    }
                                    onMouseLeave={(e) =>
                                        (e.currentTarget.style.transform = "scale(1)")
                                    }
                                >
                                    {s.rank}
                                </div>
                            </SourceTooltip>
                        ))}
                    </div>
                </div>
            ) : null}
        </main>
    );
}
