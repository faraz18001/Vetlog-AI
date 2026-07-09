import { useState, useCallback, useEffect } from "react";

const AUTH_KEY = "vetlog_auth";

function loadAuth() {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveAuth(data) {
  if (data) {
    localStorage.setItem(AUTH_KEY, JSON.stringify(data));
    return;
  }
  localStorage.removeItem(AUTH_KEY);
}

export function useAuth() {
  const [user, setUser] = useState(loadAuth);
  const [authError, setAuthError] = useState("");

  const login = useCallback(async (username, password) => {
    setAuthError("");
    try {
      const res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const text = await res.text();
        setAuthError("Invalid username or password");
        return false;
      }
      const data = await res.json();
      saveAuth(data);
      setUser(data);
      return true;
    } catch (err) {
      setAuthError("Could not connect to the server.");
      return false;
    }
  }, []);

  const register = useCallback(async (username, displayName, password) => {
    setAuthError("");
    try {
      const res = await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, display_name: displayName, password }),
      });
      if (!res.ok) {
        const text = await res.text();
        if (res.status === 400) {
          setAuthError("Username already taken");
        } else {
          setAuthError("Registration failed. Please try again.");
        }
        return false;
      }
      const data = await res.json();
      saveAuth(data);
      setUser(data);
      return true;
    } catch (err) {
      setAuthError("Could not connect to the server.");
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    saveAuth(null);
    setUser(null);
  }, []);

  return { user, login, register, logout, authError, setAuthError };
}
