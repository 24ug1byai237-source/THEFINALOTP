import React, { useState } from "react";
import {
  ShieldCheck,
  Phone,
  KeyRound,
  Mail,
  Lock,
  ArrowRight,
  CheckCircle2,
  UserCheck,
  Stethoscope,
  Landmark,
  Zap,
} from "lucide-react";
import type { UserRole } from "../../types";
import { useAuth, DEMO_CREDENTIALS } from "../../context/AuthContext";

export const LoginPage: React.FC = () => {
  // Only use the auth functions that are available pre-login
  const { loginWithOTP, sendOTP, loginWithCredentials } = useAuth();

  const [activeTab, setActiveTab] = useState<UserRole>("farmer");

  // Farmer OTP state
  const [phone, setPhone] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpMessage, setOtpMessage] = useState("");

  // Vet & Officer Credentials state
  const [email, setEmail] = useState("vet@bioshield.local");
  const [password, setPassword] = useState("vet123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleTabChange = (role: UserRole) => {
    setActiveTab(role);
    setError("");
    setOtpMessage("");
    if (role === "farmer") {
      setPhone("");
      setOtpCode("");
      setOtpSent(false);
    } else if (role === "veterinarian") {
      setEmail(DEMO_CREDENTIALS.veterinarian.email);
      setPassword(DEMO_CREDENTIALS.veterinarian.password);
    } else if (role === "officer") {
      setEmail(DEMO_CREDENTIALS.officer.email);
      setPassword(DEMO_CREDENTIALS.officer.password);
    }
  };

  const [devCode, setDevCode] = useState<string | null>(null);

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) {
      setError("Please enter a valid phone number");
      return;
    }
    setOtpLoading(true);
    setError("");
    try {
      const res = await sendOTP(phone);
      setOtpSent(true);
      setOtpCode(""); // Keep input empty so farmer reads code from WhatsApp and enters it manually
      setOtpMessage(`Verification code sent to WhatsApp (${phone}). Open WhatsApp to get your 6-digit code.`);
      if (res.devCode) {
        setDevCode(res.devCode);
        // Automatically open WhatsApp to deliver the 6-digit OTP code to the entered phone number
        const cleanDigits = phone.replace(/\D/g, "");
        const waUrl = `https://api.whatsapp.com/send?phone=${cleanDigits}&text=${encodeURIComponent(`Your AgriSentinel Verification Code is: ${res.devCode}`)}`;
        window.open(waUrl, "_blank");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to send OTP. Please check phone number.");
    } finally {
      setOtpLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode.trim()) {
      setError("Please enter the 6-digit OTP code");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await loginWithOTP(phone, otpCode);
      // On success, App.tsx will automatically redirect to the Farmer portal
      // because isAuthenticated becomes true and role comes from the JWT
    } catch (err: any) {
      setError(err?.message || "Invalid OTP code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCredentialsLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Please enter your email and password");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await loginWithCredentials(email, password);
      // On success, App.tsx will automatically redirect to the correct role portal
      // (Vet or Officer) because the role comes from the backend JWT response
    } catch (err: any) {
      setError(err?.message || "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Quick demo sign-in: uses real backend credentials for each role.
  // These call loginWithCredentials — not a bypass. The backend authenticates
  // the demo account and returns the correct role in the JWT.
  const handleQuickDemo = async (role: UserRole) => {
    setLoading(true);
    setError("");
    try {
      const creds = DEMO_CREDENTIALS[role];
      await loginWithCredentials(creds.email, creds.password);
    } catch (err: any) {
      setError(err?.message || "Demo login failed. Please ensure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        {/* Header Branding */}
        <div className="login-header">
          <div className="login-brand-icon">
            <ShieldCheck size={38} color="#10B981" />
          </div>
          <h1 className="login-title">AgriSentinel</h1>
          <p className="login-subtitle">Biosecurity &amp; Disease Surveillance System</p>
        </div>

        {/* Portal Role Tabs — select which portal to log in to */}
        <div className="login-role-tabs">
          <button
            type="button"
            className={`login-tab ${activeTab === "farmer" ? "active" : ""}`}
            onClick={() => handleTabChange("farmer")}
          >
            <UserCheck size={18} />
            <span>Farmer Portal</span>
          </button>
          <button
            type="button"
            className={`login-tab ${activeTab === "veterinarian" ? "active" : ""}`}
            onClick={() => handleTabChange("veterinarian")}
          >
            <Stethoscope size={18} />
            <span>Veterinarian</span>
          </button>
          <button
            type="button"
            className={`login-tab ${activeTab === "officer" ? "active" : ""}`}
            onClick={() => handleTabChange("officer")}
          >
            <Landmark size={18} />
            <span>Govt Officer</span>
          </button>
        </div>

        {error && <div className="login-error-alert">{error}</div>}

        {/* Farmer OTP Login Form */}
        {activeTab === "farmer" && (
          <div className="login-form-wrapper">
            {!otpSent ? (
              <form onSubmit={handleSendOTP} className="login-form">
                <div className="form-group">
                  <label className="form-label">Phone Number</label>
                  <div className="input-with-icon">
                    <Phone size={18} className="input-icon" />
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+91 9876543210"
                      className="form-input"
                      required
                    />
                  </div>
                </div>

                <button type="submit" className="login-btn-primary" disabled={otpLoading}>
                  {otpLoading ? "Sending OTP..." : "Get OTP Verification Code"}
                  <ArrowRight size={18} />
                </button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOTP} className="login-form">
                {otpMessage && (
                  <div className="login-success-alert">
                    <CheckCircle2 size={16} />
                    <span>{otpMessage}</span>
                  </div>
                )}

                {devCode && (
                  <div className="whatsapp-otp-box" style={{ margin: "10px 0", textAlign: "center" }}>
                    <a
                      href={`https://api.whatsapp.com/send?phone=${encodeURIComponent(phone.replace(/\D/g, ""))}&text=${encodeURIComponent(`Your AgriSentinel Verification Code is: ${devCode}`)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-whatsapp-otp"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        background: "#25D366",
                        color: "#FFFFFF",
                        padding: "10px 16px",
                        borderRadius: "8px",
                        fontSize: "13px",
                        fontWeight: 700,
                        textDecoration: "none",
                        width: "100%",
                        justifyContent: "center",
                      }}
                    >
                      <span>📱 Re-open WhatsApp to View Verification Code</span>
                    </a>
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Enter 6-Digit OTP Code</label>
                  <div className="input-with-icon">
                    <KeyRound size={18} className="input-icon" />
                    <input
                      type="text"
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value)}
                      placeholder="123456"
                      className="form-input"
                      maxLength={6}
                      required
                    />
                  </div>
                </div>

                <button type="submit" className="login-btn-primary" disabled={loading}>
                  {loading ? "Authenticating..." : "Verify & Sign In"}
                  <ArrowRight size={18} />
                </button>

                <button
                  type="button"
                  className="login-btn-link"
                  onClick={() => setOtpSent(false)}
                >
                  Change Phone Number
                </button>
              </form>
            )}
          </div>
        )}

        {/* Vet & Officer Credentials Login Form */}
        {(activeTab === "veterinarian" || activeTab === "officer") && (
          <form onSubmit={handleCredentialsLogin} className="login-form">
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <div className="input-with-icon">
                <Mail size={18} className="input-icon" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="form-input"
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div className="input-with-icon">
                <Lock size={18} className="input-icon" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="form-input"
                  required
                />
              </div>
            </div>

            <button type="submit" className="login-btn-primary" disabled={loading}>
              {loading
                ? "Authenticating..."
                : `Sign In as ${activeTab === "veterinarian" ? "Veterinarian" : "Officer"}`}
              <ArrowRight size={18} />
            </button>
          </form>
        )}

        {/* Quick Demo Access — authenticates via the real backend as a demo account.
            Role is determined by the backend JWT response, NOT by the button clicked.
            A farmer cannot gain officer access by clicking "Officer Demo" if
            the backend returns a FARMER role for those credentials. */}
        <div className="quick-demo-section">
          <div className="quick-demo-header">
            <Zap size={14} />
            <span className="quick-demo-title">⚡ Quick SIH Demo Sign-In (Real Auth):</span>
          </div>
          <div className="quick-demo-buttons">
            <button
              type="button"
              className="quick-demo-btn farmer-demo"
              onClick={() => handleQuickDemo("farmer")}
              disabled={loading}
              title="Logs in as farmer@bioshield.local — backend returns FARMER role"
            >
              👨‍🌾 Farmer Demo
            </button>
            <button
              type="button"
              className="quick-demo-btn vet-demo"
              onClick={() => handleQuickDemo("veterinarian")}
              disabled={loading}
              title="Logs in as vet@bioshield.local — backend returns VETERINARIAN role"
            >
              🩺 Vet Demo
            </button>
            <button
              type="button"
              className="quick-demo-btn officer-demo"
              onClick={() => handleQuickDemo("officer")}
              disabled={loading}
              title="Logs in as officer@bioshield.local — backend returns OFFICER role"
            >
              🏛️ Officer Demo
            </button>
          </div>
          <p className="quick-demo-note">
            Each demo button authenticates via the backend. Portal access is determined by the server-assigned role.
          </p>
        </div>
      </div>
    </div>
  );
};
