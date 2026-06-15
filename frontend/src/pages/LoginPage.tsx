import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";

import { I } from "@/components/icons";
import { Button } from "@/components/ui";
import { useAuth } from "@/store/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password, tenantSlug.trim() || undefined);
      const from = (loc.state as { from?: string } | null)?.from || "/";
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detail || "Sign-in failed. Check your credentials and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: "1fr 1.1fr",
        background: "var(--mist)",
      }}
    >
      {/* Left — form */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          padding: "48px 64px",
          background: "var(--card)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 56 }}>
          <img
            src="/favicon-32x32.png"
            srcSet="/favicon-32x32.png 1x, /android-chrome-192x192.png 2x"
            alt="Bunchly"
            width={32}
            height={32}
            style={{ borderRadius: 9, display: "block", objectFit: "contain" }}
          />
          <span style={{ fontSize: 24, color: "var(--ink-3)" }}>Bunchly</span>
        </div>

        <form
          onSubmit={handleSubmit}
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            maxWidth: 380,
          }}
        >
          <span className="eyebrow">Sign in</span>
          <h1
            style={{
              fontSize: 44,
              color: "var(--ink-3)",
              margin: "8px 0 6px",
              letterSpacing: "-0.015em",
            }}
          >
            Welcome back.
          </h1>
          <p style={{ color: "var(--text-2)", fontSize: 15, marginBottom: 32 }}>
            Sign in to your bunch. People, processes and payroll all in one place.
          </p>

          {error && (
            <div
              style={{
                background: "var(--danger-soft)",
                color: "var(--danger)",
                padding: "10px 12px",
                borderRadius: 8,
                fontSize: 12.5,
                marginBottom: 14,
              }}
            >
              {error}
            </div>
          )}

          <div className="field" style={{ marginBottom: 14 }}>
            <label>Work email</label>
            <input
              className="input"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="field" style={{ marginBottom: 14 }}>
            <label>Password</label>
            <input
              className="input"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="field" style={{ marginBottom: 20 }}>
            <label>
              Organisation slug <span style={{ color: "var(--text-4)" }}>(optional)</span>
            </label>
            <input
              className="input"
              value={tenantSlug}
              placeholder="e.g. acme"
              onChange={(e) => setTenantSlug(e.target.value)}
            />
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            style={{ width: "100%", marginBottom: 12 }}
            disabled={submitting}
          >
            {submitting ? "Signing in…" : <>Sign in <I.arrow size={14} /></>}
          </Button>

          <div
            style={{
              marginTop: 32,
              paddingTop: 24,
              borderTop: "1px solid var(--hairline-2)",
              fontSize: 12.5,
              color: "var(--text-3)",
              textAlign: "center",
            }}
          >
            Don't have an account?{" "}
            <a href="/" style={{ color: "var(--action)", fontWeight: 500 }}>
              Talk to your HR admin
            </a>
          </div>
        </form>

        <div style={{ fontSize: 11, color: "var(--text-4)", display: "flex", gap: 16 }}>
          <span>© Bunchly 2026</span>
          <a>Privacy</a>
          <a>Terms</a>
          <a>Security</a>
        </div>
      </div>

      {/* Right — decoration */}
      <div
        style={{
          background:
            "linear-gradient(135deg, #141E2C 0%, #1B2737 70%, var(--action-deep) 100%)",
          padding: "48px 64px",
          display: "flex",
          flexDirection: "column",
          color: "#fff",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "-10%",
            right: "-10%",
            width: 320,
            height: 320,
            borderRadius: "50%",
            background: "radial-gradient(circle, var(--yellow) 0%, transparent 70%)",
            opacity: 0.3,
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "-15%",
            left: "-10%",
            width: 360,
            height: 360,
            borderRadius: "50%",
            background: "radial-gradient(circle, var(--bunchly) 0%, transparent 70%)",
            opacity: 0.4,
          }}
        />

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            maxWidth: 520,
            position: "relative",
            zIndex: 1,
          }}
        >
          <span className="eyebrow" style={{ color: "var(--yellow)" }}>
            Built on Bunchly
          </span>
          <h2
            style={{
              fontSize: 48,
              lineHeight: 1.05,
              margin: "12px 0 16px",
              letterSpacing: "-0.015em",
            }}
          >
            Bring Your Bunch Together
          </h2>
          <p style={{ color: "rgba(255,255,255,0.7)", fontSize: 15, lineHeight: 1.55 }}>
            People, payroll and processes beautifully connected in one place.
          </p>
        </div>

        <div
          style={{
            position: "relative",
            zIndex: 1,
            display: "flex",
            gap: 24,
            fontSize: 12,
            color: "rgba(255,255,255,0.5)",
          }}
        >
          <span style={{ marginLeft: "auto" }}>SOC 2 · ISO 27001 · POPIA</span>
        </div>
      </div>
    </div>
  );
}
