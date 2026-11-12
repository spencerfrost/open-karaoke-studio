import { describe, expect, it } from "vitest";
import { phonePromptEnd, UNTIMED_PROMPT_SECONDS } from "./phonePromptWindow";

const lrc = ["[00:00.00]", "[00:12.50] First line", "[00:15.00] Second"].join(
  "\n",
);

describe("phonePromptEnd", () => {
  it("ends at the first sung line, skipping blank spacers", () => {
    expect(phonePromptEnd(lrc, 0)).toBe(12.5);
  });

  it("follows the lyrics offset: positive shows lines earlier", () => {
    expect(phonePromptEnd(lrc, 500)).toBe(12);
    expect(phonePromptEnd(lrc, -1000)).toBe(13.5);
  });

  it("never goes below the start of the song", () => {
    expect(phonePromptEnd(lrc, 20_000)).toBe(0);
  });

  it("uses a fixed stretch without timed lyrics", () => {
    expect(phonePromptEnd(null, 0)).toBe(UNTIMED_PROMPT_SECONDS);
    expect(phonePromptEnd("Plain words\nno timestamps", 0)).toBe(
      UNTIMED_PROMPT_SECONDS,
    );
  });
});
