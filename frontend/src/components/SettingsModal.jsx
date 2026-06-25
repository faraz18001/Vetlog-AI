import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import "./SettingsModal.css";

const PROVIDERS = [
  { id: "ollama", label: "Ollama (Local / Cloud)" },
  { id: "gemini", label: "Google Gemini" },
  { id: "openai", label: "OpenAI" },
  { id: "groq", label: "Groq" },
  { id: "mistral", label: "Mistral" },
  { id: "cerebras", label: "Cerebras" },
  { id: "openrouter", label: "OpenRouter" },
];

export default function SettingsModal({ isOpen, onClose }) {
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch current config when the modal opens
  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      fetch("/api/config/llm")
        .then((res) => res.json())
        .then((data) => {
          setProvider(data.provider || "ollama");
          setModel(data.model || "");
          setApiKey(""); // Don't fetch/show the actual API key for security
          setError(null);
        })
        .catch((err) => {
          console.error("Failed to load LLM config:", err);
          setError("Failed to load settings.");
        })
        .finally(() => setIsLoading(false));
    }
  }, [isOpen]);

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setError(null);

    try {
      const res = await fetch("/api/config/llm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, model, api_key: apiKey }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      onClose(); // close on success
    } catch (err) {
      console.error("Failed to save config:", err);
      setError("Failed to save settings. Check console for details.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          
          {/* Modal Content */}
          <div className="modal-wrapper">
            <motion.div
              className="settings-modal"
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ type: "spring", bounce: 0, duration: 0.4 }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="settings-title"
            >
              <div className="modal-header">
                <h2 id="settings-title" className="modal-title">Settings</h2>
                <button 
                  className="modal-close-btn" 
                  onClick={onClose}
                  aria-label="Close settings"
                >
                  <X size={18} strokeWidth={2.5} />
                </button>
              </div>

              {isLoading ? (
                <div className="modal-body modal-body--loading">Loading configuration...</div>
              ) : (
                <form className="modal-body" onSubmit={handleSave}>
                  {error && <div className="modal-error">{error}</div>}
                  
                  <div className="form-group">
                    <label htmlFor="provider">LLM Provider</label>
                    <select
                      id="provider"
                      value={provider}
                      onChange={(e) => setProvider(e.target.value)}
                      className="form-input"
                    >
                      {PROVIDERS.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="model">Model Name</label>
                    <input
                      type="text"
                      id="model"
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="form-input"
                      placeholder="e.g. gpt-4o or gemini-2.5-flash-lite"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="apikey">API Key</label>
                    <input
                      type="password"
                      id="apikey"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="form-input"
                      placeholder="Leave blank to keep existing key"
                    />
                    <p className="form-hint">
                      Required if switching providers or setting up for the first time.
                    </p>
                  </div>

                  <div className="modal-footer">
                    <button 
                      type="button" 
                      className="btn-secondary" 
                      onClick={onClose}
                    >
                      Cancel
                    </button>
                    <button 
                      type="submit" 
                      className="btn-primary" 
                      disabled={isSaving}
                    >
                      {isSaving ? "Saving..." : "Save Changes"}
                    </button>
                  </div>
                </form>
              )}
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
