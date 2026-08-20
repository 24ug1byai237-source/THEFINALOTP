import React, { useState } from "react";
import {
  ShieldCheck,
  Mail,
  Lock,
  ArrowRight,
  UserCheck,
  Stethoscope,
  Landmark,
  Zap,
  User,
  Phone,
  CheckCircle2,
} from "lucide-react";
import type { UserRole } from "../../types";
import { useAuth, DEMO_CREDENTIALS } from "../../context/AuthContext";
import { useTranslation } from "../../context/LocaleContext";
import { translateData } from "../../i18n/dataTranslations";
import { LanguageSelector } from "../common/LanguageSelector";

export const LoginPage: React.FC = () => {
  const { loginWithCredentials, registerByRole, allFarms, setActiveFarm } = useAuth();
  const { t, locale } = useTranslation();

  // Role Selection (Farmer | Veterinarian | Government Officer)
  const [activeRole, setActiveRole] = useState<UserRole>("farmer");
  
  // Auth Mode (Sign In | Create Account)
  const [mode, setMode] = useState<"signin" | "create">("signin");

  // Form states
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [districtId, setDistrictId] = useState("district-ranchi");
  const [selectedFarmId, setSelectedFarmId] = useState("FARM-JH-2026-0487");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleRoleChange = (role: UserRole) => {
    setActiveRole(role);
    setError("");
    setSuccessMsg("");
  };

  const handleModeChange = (newMode: "signin" | "create") => {
    setMode(newMode);
    setError("");
    setSuccessMsg("");
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    if (activeRole === "farmer") {
      const found = allFarms.find((f) => f.id === selectedFarmId);
      if (found) {
        setActiveFarm(found);
        localStorage.setItem("selected_farm_id", found.id);
      }
    }

    if (mode === "signin") {
      if (!email.trim() || !password.trim()) {
        setError("Please enter your email and password.");
        return;
      }
      setLoading(true);
      try {
        await loginWithCredentials(email.trim(), password);
      } catch (err: any) {
        setError(err?.message || "Invalid credentials. Please try again.");
      } finally {
        setLoading(false);
      }
    } else {
      if (!fullName.trim() || !email.trim() || !password.trim()) {
        setError("Full Name, Email, and Password are required to create an account.");
        return;
      }
      setLoading(true);
      try {
        await registerByRole({
          fullName: fullName.trim(),
          email: email.trim(),
          password,
          role: activeRole,
          phone: phone.trim() || undefined,
          districtId,
        });
        setSuccessMsg(`Account created successfully as ${activeRole.toUpperCase()}! Redirecting...`);
      } catch (err: any) {
        setError(err?.message || "Failed to create account. Email may already be registered.");
      } finally {
        setLoading(false);
      }
    }
  };

  const handleQuickDemo = async (role: UserRole) => {
    setLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      if (role === "farmer") {
        const found = allFarms.find((f) => f.id === selectedFarmId);
        if (found) {
          setActiveFarm(found);
          localStorage.setItem("selected_farm_id", found.id);
        }
      }
      const creds = DEMO_CREDENTIALS[role];
      await loginWithCredentials(creds.email, creds.password);
    } catch (err: any) {
      setError(err?.message || "Demo login failed. Please ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const roleTitle =
    activeRole === "farmer"
      ? t("role.farmer")
      : activeRole === "veterinarian"
      ? t("role.veterinarian")
      : t("role.officer");

  return (
    <div className="login-container">
      <div className="login-card" style={{ position: "relative" }}>
        {/* Top-right Language Selector */}
        <div style={{ position: "absolute", top: "16px", right: "16px", zIndex: 10 }}>
          <LanguageSelector compact />
        </div>

        {/* Header Branding */}
        <div className="login-header">
          <div className="login-brand-icon">
            <ShieldCheck size={38} color="#10B981" />
          </div>
          <h1 className="login-title">{t("app.name")}</h1>
          <p className="login-subtitle">{t("app.tagline")}</p>
        </div>

        {/* 1. ROLE SELECTION — BEFORE LOGIN */}
        <div className="role-selection-box">
          <span className="role-selection-label">{t("auth.chooseRole")}</span>
          <div className="login-role-tabs">
            <button
              type="button"
              className={`login-tab ${activeRole === "farmer" ? "active" : ""}`}
              onClick={() => handleRoleChange("farmer")}
            >
              <UserCheck size={18} />
              <span>{t("role.farmer")}</span>
            </button>
            <button
              type="button"
              className={`login-tab ${activeRole === "veterinarian" ? "active" : ""}`}
              onClick={() => handleRoleChange("veterinarian")}
            >
              <Stethoscope size={18} />
              <span>{t("role.veterinarian")}</span>
            </button>
            <button
              type="button"
              className={`login-tab ${activeRole === "officer" ? "active" : ""}`}
              onClick={() => handleRoleChange("officer")}
            >
              <Landmark size={18} />
              <span>{t("role.officer")}</span>
            </button>
          </div>
        </div>

        {/* Mode Selector: Create Account vs Sign In */}
        <div className="auth-mode-toggle">
          <button
            type="button"
            className={`mode-btn ${mode === "signin" ? "active" : ""}`}
            onClick={() => handleModeChange("signin")}
          >
            {t("auth.signIn")}
          </button>
          <button
            type="button"
            className={`mode-btn ${mode === "create" ? "active" : ""}`}
            onClick={() => handleModeChange("create")}
          >
            {t("auth.createAccount")}
          </button>
        </div>

        {error && <div className="login-error-alert" role="alert">{error}</div>}
        {successMsg && (
          <div className="login-success-alert" style={{ background: "#DCFCE7", color: "#15803D", padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
            <CheckCircle2 size={18} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleFormSubmit} className="login-form">
          {mode === "create" && (
            <div className="form-group">
              <label className="form-label">{t("auth.fullName")}</label>
              <div className="input-with-icon">
                <User size={18} className="input-icon" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder={
                    activeRole === "farmer"
                      ? "e.g. Ramesh Singh"
                      : activeRole === "veterinarian"
                      ? "e.g. Dr. Priya Sharma"
                      : "e.g. Officer Suresh Verma"
                  }
                  className="form-input"
                  required
                />
              </div>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">{t("auth.email")}</label>
            <div className="input-with-icon">
              <Mail size={18} className="input-icon" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="form-input"
                autoComplete="email"
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">{t("auth.password")}</label>
            <div className="input-with-icon">
              <Lock size={18} className="input-icon" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="form-input"
                autoComplete="current-password"
                required
              />
            </div>
          </div>

          {activeRole === "farmer" && (
            <div className="form-group">
              <label className="form-label">{t("auth.selectFarm")}</label>
              <div className="input-with-icon">
                <UserCheck size={18} className="input-icon" />
                <select
                  value={selectedFarmId}
                  onChange={(e) => setSelectedFarmId(e.target.value)}
                  className="form-input"
                  style={{
                    background: "#1E293B",
                    color: "#FFFFFF",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    paddingLeft: "42px",
                    height: "46px",
                    fontSize: "14px",
                    width: "100%",
                    cursor: "pointer",
                  }}
                >
                  {allFarms.map((farm) => (
                    <option key={farm.id} value={farm.id} style={{ background: "#0F172A", color: "#FFFFFF" }}>
                      {translateData(farm.name, locale)} — {translateData(farm.location, locale)} ({farm.farmType.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {mode === "create" && (
            <>
              <div className="form-group">
                <label className="form-label">{t("auth.phone")}</label>
                <div className="input-with-icon">
                  <Phone size={18} className="input-icon" />
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+91 9876543210"
                    className="form-input"
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">{t("auth.districtScope")}</label>
                <select
                  value={districtId}
                  onChange={(e) => setDistrictId(e.target.value)}
                  className="form-input"
                  style={{ background: "#1E293B", color: "#FFFFFF" }}
                >
                  <option value="district-ranchi">Ranchi, Jharkhand</option>
                  <option value="district-ramgarh">Ramgarh, Jharkhand</option>
                  <option value="district-bengaluru-rural">Bengaluru Rural, Karnataka</option>
                  <option value="district-guntur">Guntur, Andhra Pradesh</option>
                </select>
              </div>
            </>
          )}

          <button type="submit" className="login-btn-primary" disabled={loading}>
            {loading
              ? mode === "create" ? "Creating Account..." : "Authenticating..."
              : mode === "create"
              ? `Create ${roleTitle} Account`
              : `Sign In as ${roleTitle}`}
            <ArrowRight size={18} />
          </button>
        </form>

        {/* Quick Demo Section */}
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
            Each demo button authenticates via the database. Portal access is strictly determined by the server-assigned role.
          </p>
        </div>
      </div>
    </div>
  );
};
