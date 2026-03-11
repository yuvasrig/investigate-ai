import { useState, useRef } from "react";
import { Mic, MicOff, Loader2, CheckCircle } from "lucide-react";

const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

export interface VoiceIntent {
  ticker: string;
  amount: number;
  action: string;
  confidence: number;
  raw_text: string;
}

interface Props {
  onIntent: (intent: VoiceIntent, transcript: string) => void;
  disabled?: boolean;
}

export function VoiceInput({ onIntent, disabled = false }: Props) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");
  const [waveform, setWaveform] = useState<number[]>(Array(20).fill(0));

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const animFrameRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  const startRecording = async () => {
    setError("");
    setTranscript("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Waveform visualizer
      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      audioCtx.createMediaStreamSource(stream).connect(analyser);
      analyser.fftSize = 64;
      const dataArr = new Uint8Array(analyser.frequencyBinCount);

      const tick = () => {
        analyser.getByteFrequencyData(dataArr);
        setWaveform(Array.from(dataArr.slice(0, 20)));
        animFrameRef.current = requestAnimationFrame(tick);
      };
      animFrameRef.current = requestAnimationFrame(tick);

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      recorder.onstop = async () => {
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
        audioCtxRef.current?.close();
        setWaveform(Array(20).fill(0));
        stream.getTracks().forEach((t) => t.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await processAudio(audioBlob);
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      setError("Microphone access denied. Please allow microphone access or use text input below.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processAudio = async (audioBlob: Blob) => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");

      const res = await fetch(`${API_BASE}/api/voice/transcribe`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        // Fall back to text mode — transcription endpoint not available
        const err = await res.json().catch(() => ({ detail: "Transcription failed" }));
        throw new Error(err.detail || "Transcription unavailable");
      }

      const data = await res.json();
      setTranscript(data.transcript);
      if (data.intent?.ticker) {
        onIntent(data.intent, data.transcript);
      } else {
        setError("Couldn't detect a ticker/amount. Try: \"Analyze $5,000 in NVIDIA\"");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Processing failed");
    } finally {
      setIsProcessing(false);
    }
  };

  // Text-mode fallback
  const [textQuery, setTextQuery] = useState("");
  const handleTextSubmit = async () => {
    if (!textQuery.trim()) return;
    setIsProcessing(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/voice/parse-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: textQuery }),
      });
      const data = await res.json();
      const intent = data.intent;
      if (intent?.ticker) {
        setTranscript(textQuery);
        onIntent(intent, textQuery);
      } else {
        setError("Couldn't parse a ticker/amount. Try: \"I want to invest $5,000 in NVIDIA\"");
      }
    } catch {
      setError("Failed to parse text");
    } finally {
      setIsProcessing(false);
    }
  };

  const isDone = !isRecording && !isProcessing && transcript;

  return (
    <div className="flex flex-col items-center gap-5 w-full">
      {/* Mic button */}
      <div className="flex flex-col items-center gap-3">
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing || disabled}
          className={[
            "w-24 h-24 rounded-full flex items-center justify-center",
            "shadow-lg transition-all duration-200 focus:outline-none",
            isRecording
              ? "bg-red-500 hover:bg-red-600 animate-pulse ring-4 ring-red-300"
              : isDone
              ? "bg-green-500 hover:bg-green-600"
              : "bg-accent hover:bg-accent/90",
            (isProcessing || disabled) ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
          ].join(" ")}
          aria-label={isRecording ? "Stop recording" : "Start recording"}
        >
          {isProcessing ? (
            <Loader2 className="w-10 h-10 text-white animate-spin" />
          ) : isDone ? (
            <CheckCircle className="w-10 h-10 text-white" />
          ) : isRecording ? (
            <MicOff className="w-10 h-10 text-white" />
          ) : (
            <Mic className="w-10 h-10 text-white" />
          )}
        </button>

        <p className="text-sm text-muted-foreground">
          {isProcessing
            ? "Processing…"
            : isRecording
            ? "Tap to stop"
            : isDone
            ? "Got it!"
            : "Tap to speak"}
        </p>
      </div>

      {/* Waveform */}
      {isRecording && (
        <div className="flex items-end gap-0.5 h-10">
          {waveform.map((v, i) => (
            <div
              key={i}
              className="w-1.5 rounded-full bg-accent transition-all duration-75"
              style={{ height: `${Math.max(4, (v / 255) * 40)}px` }}
            />
          ))}
        </div>
      )}

      {/* Transcript display */}
      {transcript && (
        <div className="bg-secondary rounded-lg px-4 py-2 text-sm text-foreground max-w-sm text-center">
          "{transcript}"
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-xs text-red-500 text-center max-w-xs">{error}</p>
      )}

      {/* Text fallback */}
      <div className="flex items-center gap-2 w-full max-w-sm">
        <div className="flex-1 h-px bg-border" />
        <span className="text-xs text-muted-foreground">or type</span>
        <div className="flex-1 h-px bg-border" />
      </div>
      <div className="flex w-full max-w-sm gap-2">
        <input
          className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          placeholder='e.g. "Invest $5,000 in NVIDIA"'
          value={textQuery}
          onChange={(e) => setTextQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleTextSubmit()}
          disabled={isProcessing || disabled}
        />
        <button
          onClick={handleTextSubmit}
          disabled={!textQuery.trim() || isProcessing || disabled}
          className="rounded-lg bg-accent text-accent-foreground px-4 py-2 text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors"
        >
          Parse
        </button>
      </div>
    </div>
  );
}
