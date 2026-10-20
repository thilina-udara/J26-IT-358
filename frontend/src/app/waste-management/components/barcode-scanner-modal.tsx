"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Camera,
  CameraOff,
  CheckCircle2,
  AlertCircle,
  X,
  Keyboard,
  QrCode,
  Scan,
  Sparkles,
  ArrowRight,
  RefreshCw,
} from "lucide-react";

interface BarcodeScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBarcodeValidated: (barcode: string) => void;
  existingBarcodes?: string[];
  apiBaseUrl?: string;
  authToken?: string | null;
}

export function BarcodeScannerModal({
  isOpen,
  onClose,
  onBarcodeValidated,
  existingBarcodes = [],
  apiBaseUrl = "http://localhost:8003",
  authToken = null,
}: BarcodeScannerModalProps) {
  const [activeTab, setActiveTab] = useState<"camera" | "manual">("manual");
  const [barcodeInput, setBarcodeInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [availableBarcodes, setAvailableBarcodes] = useState<string[]>([]);
  const [loadingBarcodes, setLoadingBarcodes] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const scanIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch available pre-issued barcodes from Component 3 backend
  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    setBarcodeInput("");

    async function fetchAvailable() {
      setLoadingBarcodes(true);
      try {
        const headers: Record<string, string> = { Accept: "application/json" };
        if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

        const res = await fetch(`${apiBaseUrl}/api/transport/barcode/available`, {
          headers,
          cache: "no-store",
        });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.barcodes)) {
            const filtered = data.barcodes.filter((b: string) => !existingBarcodes.includes(b));
            setAvailableBarcodes(filtered);
          }
        }
      } catch {
        // Local fallback series
        const fallback = Array.from({ length: 15 }, (_, i) => {
          const num = String(i + 1).padStart(6, "0");
          return `BC-${num}`;
        }).filter((b) => !existingBarcodes.includes(b));
        setAvailableBarcodes(fallback);
      } finally {
        setLoadingBarcodes(false);
      }
    }

    fetchAvailable();
  }, [isOpen, apiBaseUrl, authToken, existingBarcodes]);

  // Handle Camera Lifecycle
  useEffect(() => {
    if (!isOpen || activeTab !== "camera") {
      stopCamera();
      return;
    }

    startCamera();

    return () => {
      stopCamera();
    };
  }, [isOpen, activeTab]);

  function stopCamera() {
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
      scanIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }

  async function startCamera() {
    setCameraError(null);
    try {
      if (!navigator?.mediaDevices?.getUserMedia) {
        throw new Error("Camera API is not supported in this browser environment.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      // BarcodeDetector API detection if available
      if ("BarcodeDetector" in window) {
        try {
          const detector = new (window as any).BarcodeDetector({
            formats: ["code_128", "code_39", "ean_13", "qr_code"],
          });

          scanIntervalRef.current = setInterval(async () => {
            if (videoRef.current && videoRef.current.readyState === videoRef.current.HAVE_ENOUGH_DATA) {
              try {
                const barcodes = await detector.detect(videoRef.current);
                if (barcodes.length > 0) {
                  const detected = barcodes[0].rawValue;
                  if (detected) {
                    stopCamera();
                    handleValidate(detected);
                  }
                }
              } catch {
                // Ignore frame detection errors
              }
            }
          }, 350);
        } catch {
          // Ignore
        }
      }
    } catch (err: any) {
      setCameraError(
        err?.message || "Could not access camera. Please check permissions or select from available stickers below."
      );
      setActiveTab("manual");
    }
  }

  // Barcode Validation Handler
  async function handleValidate(codeToValidate?: string) {
    const code = (codeToValidate || barcodeInput).trim().toUpperCase();
    setError(null);

    if (!code) {
      setError("Please enter or scan a barcode number.");
      return;
    }

    if (existingBarcodes.includes(code)) {
      setError(`Barcode "${code}" is already locked in your current transport list.`);
      return;
    }

    setLoading(true);
    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        Accept: "application/json",
      };
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

      const res = await fetch(`${apiBaseUrl}/api/transport/barcode/validate`, {
        method: "POST",
        headers,
        body: JSON.stringify({ barcode_no: code }),
      });

      const data = await res.json();

      if (!res.ok) {
        const msg = data.detail || "Validation failed. Please verify the barcode sticker.";
        setError(msg);
        return;
      }

      if (data.valid) {
        stopCamera();
        onBarcodeValidated(data.barcode_no);
        onClose();
      } else {
        setError(data.message || `Barcode sticker ${code} is not available.`);
      }
    } catch {
      setError("Could not reach the server to validate barcode. Please check connection.");
    } finally {
      setLoading(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(15, 23, 42, 0.65)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          stopCamera();
          onClose();
        }
      }}
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: "24px",
          width: "100%",
          maxWidth: "540px",
          boxShadow: "0 20px 40px -15px rgba(0,0,0,0.25)",
          overflow: "hidden",
          border: "1px solid #e2e8f0",
          animation: "modalSlideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #e2e8f0",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "12px",
                background: "#16a34a",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <QrCode size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: "17px", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                Scan Crate Barcode Sticker
              </h3>
              <p style={{ fontSize: "12.5px", color: "#64748b", margin: "2px 0 0 0" }}>
                Component 3: Transport Tracking & Spoilage Risk
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              stopCamera();
              onClose();
            }}
            style={{
              background: "#f1f5f9",
              border: "none",
              borderRadius: "10px",
              width: "36px",
              height: "36px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              color: "#64748b",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: "flex", borderBottom: "1px solid #e2e8f0", background: "#f8fafc" }}>
          <button
            type="button"
            onClick={() => setActiveTab("manual")}
            style={{
              flex: 1,
              padding: "12px 16px",
              border: "none",
              background: activeTab === "manual" ? "#ffffff" : "transparent",
              color: activeTab === "manual" ? "#16a34a" : "#64748b",
              fontWeight: activeTab === "manual" ? 700 : 500,
              fontSize: "13px",
              cursor: "pointer",
              borderBottom: activeTab === "manual" ? "2px solid #16a34a" : "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
          >
            <Keyboard size={16} />
            <span>Select / Manual Entry</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("camera")}
            style={{
              flex: 1,
              padding: "12px 16px",
              border: "none",
              background: activeTab === "camera" ? "#ffffff" : "transparent",
              color: activeTab === "camera" ? "#16a34a" : "#64748b",
              fontWeight: activeTab === "camera" ? 700 : 500,
              fontSize: "13px",
              cursor: "pointer",
              borderBottom: activeTab === "camera" ? "2px solid #16a34a" : "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
          >
            <Camera size={16} />
            <span>Live Camera Scan</span>
          </button>
        </div>

        {/* Body Content */}
        <div style={{ padding: "24px" }}>
          {error && (
            <div
              style={{
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "12px",
                padding: "12px 16px",
                marginBottom: "16px",
                display: "flex",
                alignItems: "center",
                gap: "10px",
                color: "#b91c1c",
                fontSize: "13px",
              }}
            >
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {activeTab === "camera" ? (
            <div>
              <div
                style={{
                  position: "relative",
                  width: "100%",
                  height: "260px",
                  background: "#0f172a",
                  borderRadius: "16px",
                  overflow: "hidden",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <video
                  ref={videoRef}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  playsInline
                  muted
                />
                <div
                  style={{
                    position: "absolute",
                    inset: "25px",
                    border: "2px dashed #22c55e",
                    borderRadius: "12px",
                    pointerEvents: "none",
                    boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.45)",
                  }}
                />
              </div>
              {cameraError && (
                <p style={{ fontSize: "12px", color: "#ef4444", marginTop: "10px", textAlign: "center" }}>
                  {cameraError}
                </p>
              )}
            </div>
          ) : (
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "12.5px",
                  fontWeight: 700,
                  color: "#334155",
                  marginBottom: "8px",
                }}
              >
                Enter Barcode Number:
              </label>
              <div style={{ display: "flex", gap: "8px", marginBottom: "18px" }}>
                <input
                  type="text"
                  placeholder="e.g. BC-000001"
                  value={barcodeInput}
                  onChange={(e) => setBarcodeInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleValidate();
                    }
                  }}
                  style={{
                    flex: 1,
                    padding: "11px 14px",
                    borderRadius: "12px",
                    border: "1.5px solid #cbd5e1",
                    fontSize: "14px",
                    fontFamily: "monospace",
                    fontWeight: 700,
                    outline: "none",
                  }}
                />
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleValidate()}
                  style={{
                    background: "linear-gradient(135deg, #16a34a 0%, #15803d 100%)",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: "12px",
                    padding: "11px 20px",
                    fontSize: "13.5px",
                    fontWeight: 700,
                    cursor: loading ? "wait" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  {loading ? <RefreshCw size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                  <span>Validate</span>
                </button>
              </div>

              {/* Available Stickers Chips */}
              <div
                style={{
                  background: "#f8fafc",
                  borderRadius: "16px",
                  padding: "16px",
                  border: "1px solid #e2e8f0",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>
                    Available Crate Barcode Stickers ({availableBarcodes.length})
                  </span>
                  <span style={{ fontSize: "11px", color: "#16a34a", fontWeight: 600 }}>Click to select</span>
                </div>

                {loadingBarcodes ? (
                  <p style={{ fontSize: "12px", color: "#94a3b8" }}>Loading available stickers...</p>
                ) : availableBarcodes.length === 0 ? (
                  <p style={{ fontSize: "12px", color: "#94a3b8" }}>No unassigned stickers available.</p>
                ) : (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", maxHeight: "150px", overflowY: "auto" }}>
                    {availableBarcodes.slice(0, 24).map((code) => (
                      <button
                        key={code}
                        type="button"
                        onClick={() => {
                          setBarcodeInput(code);
                          handleValidate(code);
                        }}
                        style={{
                          background: "#ffffff",
                          border: "1px solid #cbd5e1",
                          borderRadius: "8px",
                          padding: "6px 10px",
                          fontSize: "12px",
                          fontFamily: "monospace",
                          fontWeight: 700,
                          color: "#1e293b",
                          cursor: "pointer",
                          transition: "all 0.15s",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "#16a34a";
                          e.currentTarget.style.background = "#f0fdf4";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "#cbd5e1";
                          e.currentTarget.style.background = "#ffffff";
                        }}
                      >
                        {code}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
