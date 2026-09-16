/**
 * useLanguageSelection — validates pair per PRD §15, derives canStart.
 */
import { useMemo, useState, useCallback } from "react";

export function useLanguageSelection(supportedLanguages = []) {
  const [sourceLanguage, setSourceLanguage] = useState("");
  const [targetLanguage, setTargetLanguage] = useState("");

  const validationError = useMemo(() => {
    if (!sourceLanguage || !targetLanguage) return "Select source and target language";
    if (sourceLanguage === targetLanguage) return "Source and target must be different";
    // supportedLanguages comes from /api/v1/capabilities; if populated, enforce
    if (supportedLanguages.length > 0) {
      if (!supportedLanguages.includes(sourceLanguage)) return `Source language not supported: ${sourceLanguage}`;
      if (!supportedLanguages.includes(targetLanguage)) return `Target language not supported: ${targetLanguage}`;
    }
    return null;
  }, [sourceLanguage, targetLanguage, supportedLanguages]);

  const setSource = useCallback((v) => setSourceLanguage(v), []);
  const setTarget = useCallback((v) => setTargetLanguage(v), []);

  const canStart = validationError === null;

  return {
    sourceLanguage,
    targetLanguage,
    setSource,
    setTarget,
    setSourceLanguage: setSource,
    setTargetLanguage: setTarget,
    validationError,
    canStart,
  };
}
