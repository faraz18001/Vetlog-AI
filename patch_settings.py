import sys

filepath = 'frontend/src/components/SettingsModal.jsx'
with open(filepath, 'r') as f:
    content = f.read()

# Add import
content = content.replace(
    'import "./SettingsModal.css";',
    'import "./SettingsModal.css";\nimport CustomSelect from "./CustomSelect";'
)

# Replace provider select
provider_select_old = """                    <select
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
                    </select>"""

provider_select_new = """                    <CustomSelect
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
                      options={providers.length === 0 ? [{value: 'ollama', label: 'Ollama'}] : providers.map(p => ({
                        value: p.id,
                        label: p.name + (configuredProviders.indexOf(p.id) !== -1 ? " \u2713" : "")
                      }))}
                    />"""

content = content.replace(provider_select_old, provider_select_new)

# Replace model select
model_select_old = """                        <select
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
                        </select>"""

model_select_new = """                        <div style={{ flex: 1, minWidth: 0 }}>
                          <CustomSelect
                            id="model"
                            value={model}
                            onChange={function (e) { setModel(e.target.value); }}
                            placeholder="-- Select a model --"
                            options={modelOptions}
                          />
                        </div>"""

content = content.replace(model_select_old, model_select_new)

with open(filepath, 'w') as f:
    f.write(content)

print("SettingsModal.jsx patched!")
