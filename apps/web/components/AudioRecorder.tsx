"use client";
import { useState, useRef } from "react";

interface AudioRecorderProps {
    onTranscribe: (text: string) => void;
    disabled?: boolean;
}

export default function AudioRecorder({ onTranscribe, disabled }: AudioRecorderProps) {
    const [isRecording, setIsRecording] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream);
            chunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (e) => {
                if (e.data.size > 0) chunksRef.current.push(e.data);
            };

            mediaRecorderRef.current.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: "audio/webm" });
                await handleUpload(blob);
                stream.getTracks().forEach((track) => track.stop()); // 释放麦克风
            };

            mediaRecorderRef.current.start();
            setIsRecording(true);
        } catch (err) {
            console.error("麦克风权限错误:", err);
            alert("无法访问麦克风，请检查浏览器权限。");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const handleUpload = async (audioBlob: Blob) => {
        setIsUploading(true);
        const formData = new FormData();
        // 这里的 filename 后缀很重要，Python 后端会检查
        formData.append("file", audioBlob, "voice_input.webm");

        try {
            // 调用 Next.js 的转发接口
            const res = await fetch("/api/transcribe", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) throw new Error("转录请求失败");

            const data = await res.json();
            if (data.text) {
                onTranscribe(data.text);
            }
        } catch (error) {
            console.error("语音识别错误:", error);
            alert("语音转文字失败，请重试");
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={disabled || isUploading}
            style={{
                padding: "8px 12px",
                borderRadius: "50%",
                border: "none",
                backgroundColor: isRecording ? "#ff4d4f" : "#f0f0f0",
                color: isRecording ? "white" : "#333",
                cursor: disabled || isUploading ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 40,
                height: 40,
                transition: "all 0.2s",
                boxShadow: isRecording ? "0 0 8px rgba(255, 77, 79, 0.6)" : "none",
            }}
            title={isRecording ? "点击停止" : "点击说话"}
        >
            {isUploading ? "..." : isRecording ? "⏹" : "🎤"}
        </button>
    );
}