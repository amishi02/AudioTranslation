/**
 * P3-TEST-001: LanguageSelector validation.
 * Requires Vitest + @testing-library/react (Phase 10 full test harness).
 * Documents contract for Phase 3: identical pair blocked, unsupported blocked.
 *
 * Run when test harness added: npm test
 */
import React from "react"; // eslint-disable-line no-unused-vars
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LanguageSelector from "../components/LanguageSelector.jsx";

describe("LanguageSelector", () => {
  it("shows validation error when source === target", () => {
    render(
      <LanguageSelector
        sourceLanguage="en"
        targetLanguage="en"
        onSourceChange={() => {}}
        onTargetChange={() => {}}
        supportedLanguages={["en", "hi"]}
      />
    );
    expect(screen.getByTestId("validation-error")).toBeInTheDocument();
  });

  it("renders without error for valid pair", () => {
    render(
      <LanguageSelector
        sourceLanguage="en"
        targetLanguage="hi"
        onSourceChange={() => {}}
        onTargetChange={() => {}}
        supportedLanguages={["en", "hi"]}
      />
    );
    expect(screen.queryByTestId("validation-error")).not.toBeInTheDocument();
  });
});
