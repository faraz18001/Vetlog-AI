import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, RefreshCw } from "lucide-react";
import "./SettingsModal.css";

function authHeader(user) {
  if (!user || !user.token) return {};
  return { Authorization: "Bearer " + user.token };
}

function maskKey(key) {
  if (!key || key.length <= 8) return "****";
  return key.slice(0, 4) + "****" + key.slice(-4);
}

export default function SettingsModal({ isOpen, onClose, user }) {
  var [providers, setProviders] = useState([]);
  var [provider, setProvider] = useState("ollama");
  var [models, setModels] = useState([]);
  var [model, setModel] = useState("");
  var [apiKey, setApiKey] = useState("");
  var [savedKeyHint, setSavedKeyHint] = useState("");
  var [draftKeys, setDraftKeys] = useState({});
  var [draftModels, setDraftModels] = useState({});

  var [isLoading, setIsLoading] = useState(false);
  var [isFetchingModels, setIsFetchingModels] = useState(false);
  var [isSaving, setIsSaving] = useState(false);
  var [error, setError] = useState(null);
  var [modelError, setModelError] = useState(null);

  var headers = authHeader(user);
  var [configuredProviders, setConfiguredProviders] = useState([]);

  function fetchProviders() {
    return fetch("/api/user/config/providers")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        setProviders(data.providers || []);
      })
      .catch(function () {
        setError("Failed to load providers list.");
      });
  }

  function fetchSettings(prov) {
    var url = "/api/user/settings";
    if (prov) {
      url = url + "?provider=" + encodeURIComponent(prov);
    }
    return fetch(url, { headers: headers })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var p = data.provider || "ollama";
        var mdl = data.model || "";
        var hint = data.api_key_masked || "";
        setProvider(p);
        setModel(mdl);
        setSavedKeyHint(hint);
        setConfiguredProviders(data.configured_providers || []);
        // Auto-fetch models if we have a key saved or it's Ollama
        if (p === "ollama" || hint) {
          fetchModelsForProvider(p);
        }
      })
      .catch(function () {
        // fallback — user has no saved settings, use defaults
      });
  }

  function fetchModelsForProvider(prov, key) {
    if (!prov) return;
    setIsFetchingModels(true);
    setModelError(null);

    var url = "/api/user/models?provider=" + encodeURIComponent(prov);
    if (key) {
      url = url + "&api_key=" + encodeURIComponent(key);
    }
    console.log("Fetching models:", provider, "key_length:", key ? key.length : 0);
    fetch(url, { headers: headers })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var fetched = data.models || [];
        setModels(fetched);
        if (fetched.length === 0) {
          setModelError(data.error || "No models returned. You can type one manually.");
        }
      })
      .catch(function () {
        setModels([]);
        setModelError("Could not fetch models. Type one manually.");
      })
      .finally(function () {
        setIsFetchingModels(false);
      });
  }

  var initialLoadDone = useRef(false);

  useEffect(function () {
    if (!isOpen) return;
    setIsLoading(true);
    setError(null);
    initialLoadDone.current = false;

    Promise.all([fetchProviders(), fetchSettings()])
      .catch(function () { })
      .finally(function () {
        setIsLoading(false);
        initialLoadDone.current = true;
      });
  }, [isOpen]);

  // When provider changes (after initial load), load saved settings for that provider from DB
  useEffect(function () {
    if (!isOpen || !initialLoadDone.current) return;
    setModels([]);
    setModelError(null);
    fetchSettings(provider);
  }, [provider]);



  function handleApiKeyKeyDown(e) {
    if (e.key === "Enter" || e.key === "NumpadEnter") {
      e.preventDefault();
      var val = e.target.value;
      if (val) {
        fetchModelsForProvider(provider, val);
      }
    }
  }

  function handleSave(e) {
    e.preventDefault();
    setIsSaving(true);
    setError(null);

    var body = { provider: provider, model: model, api_key: apiKey };
    fetch("/api/user/settings", {
      method: "PUT",
      headers: Object.assign({ "Content-Type": "application/json" }, headers),
      body: JSON.stringify(body),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Server returned " + res.status);
        return res.json();
      })
      .then(function (data) {
        setSavedKeyHint(data.api_key_masked || "");
        setConfiguredProviders(data.configured_providers || []);
        setApiKey("");
        onClose();
      })
      .catch(function (err) {
        setError("Failed to save settings.");
        console.error(err);
      })
      .finally(function () {
        setIsSaving(false);
      });
  }

  // Build model dropdown options
  var modelOptions = [];
  if (model && models.indexOf(model) === -1) {
    modelOptions.push({ value: model, label: model + " (current)" });
  }
  for (var i = 0; i < models.length; i++) {
    modelOptions.push({ value: models[i], label: models[i] });
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

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
                      onChange={function (e) {
                        var newProv = e.target.value;
                        var oldProv = provider;
                        // Save drafts for the provider we're leaving
                        if (oldProv !== newProv) {
                          var updatedDraftKeys = {};
                          for (var k in draftKeys) updatedDraftKeys[k] = draftKeys[k];
                          updatedDraftKeys[oldProv] = apiKey;
                          var updatedDraftModels = {};
                          for (var m in draftModels) updatedDraftModels[m] = draftModels[m];
                          updatedDraftModels[oldProv] = model;
                          setDraftKeys(updatedDraftKeys);
                          setDraftModels(updatedDraftModels);
                          // Restore drafts for the provider we're switching to
                          setApiKey(updatedDraftKeys[newProv] || "");
                          setModel(updatedDraftModels[newProv] || "");
                        }
                        setProvider(newProv);
                        setModels([]);
                      }}
                      className="form-input"
                    >
                      {providers.length === 0 && (
                        <option value="ollama">Ollama</option>
                      )}
                      {providers.map(function (p) {
                        var isConfigured = configuredProviders.indexOf(p.id) !== -1;
                        return (
                          <option key={p.id} value={p.id}>
                            {p.name}{isConfigured ? " \u2713" : ""}
                          </option>
                        );
                      })}
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="model">Model Name</label>
                    <div className="model-input-row">
                      {isFetchingModels ? (
                        <div className="form-input" style={{ opacity: 0.5 }}>
                          Loading models...
                        </div>
                      ) : models.length > 0 ? (
                        <select
                          id="model"
                          value={model}
                          onChange={function (e) { setModel(e.target.value); }}
                          className="form-input"
                          required
                        >
                          {model === "" && (
                            <option value="">-- Select a model --</option>
                          )}
                          {modelOptions.map(function (opt) {
                            return (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            );
                          })}
                        </select>
                      ) : (
                        <input
                          type="text"
                          id="model"
                          value={model}
                          onChange={function (e) { setModel(e.target.value); }}
                          className="form-input"
                          placeholder="e.g. gpt-oss:20b-cloud"
                          required
                        />
                      )}
                      <button
                        type="button"
                        className="btn-icon"
                        onClick={function () { fetchModelsForProvider(provider, apiKey || undefined); }}
                        title="Refresh models list"
                        disabled={isFetchingModels}
                      >
                        <RefreshCw size={16} strokeWidth={2.5} className={isFetchingModels ? "spin" : ""} />
                      </button>
                    </div>
                    {modelError && <p className="form-hint form-hint--warn">{modelError}</p>}
                  </div>

                  <div className="form-group">
                    <label htmlFor="apikey">API Key</label>
                    <input
                      type="password"
                      id="apikey"
                      value={apiKey}
                      onChange={function (e) { setApiKey(e.target.value); }}
                      onKeyDown={handleApiKeyKeyDown}
                      className="form-input"
                      placeholder={savedKeyHint || "Enter your API key"}
                    />
                    {savedKeyHint && (
                      <p className="form-hint">
                        Current key: {savedKeyHint}. Leave blank to keep it.
                      </p>
                    )}
                    {provider !== "ollama" && !isFetchingModels && models.length === 0 && (
                      <p className="form-hint">
                        Enter your API key and press Enter to load available models.
                      </p>
                    )}
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
