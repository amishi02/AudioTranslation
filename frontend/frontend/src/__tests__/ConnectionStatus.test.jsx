/**
 * P3-TEST-002: ConnectionStatus per-state rendering.
 * Requires Vitest (Phase 10).
 */
import React from "react"; // eslint-disable-line no-unused-vars
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ConnectionStatus from "../components/ConnectionStatus.jsx";
import { CONNECTION_STATES } from "../utils/constants.js";

describe("ConnectionStatus", () => {
  const cases = [
    [CONNECTION_STATES.IDLE, "Select languages"],
    [CONNECTION_STATES.CONNECTING, "Connecting"],
    [CONNECTION_STATES.LISTENING, "Listening"],
    [CONNECTION_STATES.ERROR, "Error"],
  ];
  cases.forEach(([status, text]) => {
    it(`renders ${status}`, () => {
      render(<ConnectionStatus status={status} />);
      expect(screen.getByTestId("connection-status")).toHaveAttribute("data-status", status);
      expect(screen.getByText(new RegExp(text))).toBeInTheDocument();
    });
  });
});
