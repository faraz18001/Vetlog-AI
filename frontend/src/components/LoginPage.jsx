import { useState } from "react";
import { Cat, Loader } from "lucide-react";
import "./LoginPage.css";

export default function LoginPage({ onLogin, onRegister, authError, setAuthError }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function switchMode(newMode) {
    setMode(newMode);
    setAuthError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    if (mode === "register" && !displayName.trim()) return;

    setIsSubmitting(true);
    setAuthError("");

    var success = false;
    if (mode === "login") {
      success = await onLogin(username.trim(), password);
    } else {
      success = await onRegister(username.trim(), displayName.trim(), password);
    }

    if (!success) {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="grain-overlay" aria-hidden="true" />

      <div className="login-card">
        <div className="login-brand">
          <span className="login-brand-icon">
            <Cat size={36} strokeWidth={2.25} />
          </span>
          <h1 className="login-brand-name">Vetlog AI</h1>
          <p className="login-brand-tagline">Your clinic assistant</p>
        </div>

        <div className="login-tabs">
          <button
            className={"login-tab" + (mode === "login" ? " active" : "")}
            onClick={() => switchMode("login")}
          >
            Sign In
          </button>
          <button
            className={"login-tab" + (mode === "register" ? " active" : "")}
            onClick={() => switchMode("register")}
          >
            Register
          </button>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-field">
            <label htmlFor="login-username">Username</label>
            <input
              id="login-username"
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              disabled={isSubmitting}
            />
          </div>

          {mode === "register" && (
            <div className="login-field">
              <label htmlFor="login-display">Display Name</label>
              <input
                id="login-display"
                type="text"
                placeholder="How should we call you?"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                autoComplete="name"
                disabled={isSubmitting}
              />
            </div>
          )}

          <div className="login-field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              disabled={isSubmitting}
            />
          </div>

          {authError && (
            <div className="login-error">{authError}</div>
          )}

          <button className="login-btn" type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <span className="login-btn-loading">
                <Loader size={16} className="spin" />
                {mode === "login" ? "Signing in..." : "Creating account..."}
              </span>
            ) : (
              mode === "login" ? "Sign In" : "Create Account"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
