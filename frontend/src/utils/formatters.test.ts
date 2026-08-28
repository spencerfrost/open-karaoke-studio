import { parseDurationToSeconds } from "./formatters";

describe("parseDurationToSeconds", () => {
  it("parses mm:ss", () => {
    expect(parseDurationToSeconds("4:11")).toBe(251);
  });

  it("parses h:mm:ss", () => {
    expect(parseDurationToSeconds("1:02:03")).toBe(3723);
  });

  it("parses a bare seconds string", () => {
    expect(parseDurationToSeconds("251")).toBe(251);
  });

  it("returns 0 for unparseable input", () => {
    expect(parseDurationToSeconds("4:1x")).toBe(0);
  });

  it("returns 0 for an empty string", () => {
    expect(parseDurationToSeconds("")).toBe(0);
  });
});
