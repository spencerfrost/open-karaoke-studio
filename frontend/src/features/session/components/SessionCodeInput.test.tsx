import { describe, expect, it } from "vitest";
import { useState } from "react";
import { render, screen, userEvent } from "@/test/utils";
import { SessionCodeInput } from "./SessionCodeInput";

const Harness = () => {
  const [code, setCode] = useState("");
  return (
    <>
      <label htmlFor="code">Code</label>
      <SessionCodeInput id="code" value={code} onChange={setCode} />
      <output>{code}</output>
    </>
  );
};

const typedCode = () => screen.getByRole("status");

describe("SessionCodeInput", () => {
  it("uppercases letters and ignores anything else", async () => {
    render(<Harness />);
    await userEvent.type(screen.getByLabelText("Code"), "a1b-cd");

    expect(typedCode()).toHaveTextContent("ABCD");
  });

  it("cleans up a pasted code", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByLabelText("Code"));
    await userEvent.paste("wx-yz");

    expect(typedCode()).toHaveTextContent("WXYZ");
  });

  it("stops at four letters", async () => {
    render(<Harness />);
    await userEvent.type(screen.getByLabelText("Code"), "abcdef");

    expect(typedCode()).toHaveTextContent(/^ABCD$/);
  });
});
