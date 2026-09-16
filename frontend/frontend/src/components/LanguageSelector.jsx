import React from "react"; // eslint-disable-line no-unused-vars
import { LANGUAGES } from "../utils/constants.js";

export default function LanguageSelector({
  sourceLanguage,
  targetLanguage,
  onSourceChange,
  onTargetChange,
  supportedLanguages = [],
  disabled = false,
}) {
  // Use supportedLanguages from capabilities if provided, else fallback to LANGUAGES
  const options =
    supportedLanguages.length > 0
      ? supportedLanguages.map((code) => {
          const found = LANGUAGES.find((l) => l.code === code);
          return found || { code, label: code };
        })
      : LANGUAGES;

  const showError = sourceLanguage && targetLanguage && sourceLanguage === targetLanguage;

  return (
    <div className="language-selector" data-testid="language-selector">
      <div className="lang-field">
        <label htmlFor="source-language">Source Language</label>
        <select
          id="source-language"
          data-testid="source-lang"
          value={sourceLanguage}
          onChange={(e) => onSourceChange(e.target.value)}
          disabled={disabled}
        >
          <option value="">Select source</option>
          {options.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      <div className="lang-field">
        <label htmlFor="target-language">Target Language</label>
        <select
          id="target-language"
          data-testid="target-lang"
          value={targetLanguage}
          onChange={(e) => onTargetChange(e.target.value)}
          disabled={disabled}
        >
          <option value="">Select target</option>
          {options.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      {showError && (
        <p className="validation-error" role="alert" data-testid="validation-error">
          Source and target must be different
        </p>
      )}
    </div>
  );
}
