import { describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import type { SessionPerformer } from "@/types/SessionPerformer";
import { pickDefaultSinger, useDefaultSinger } from "./useDefaultSinger";

const performer = (id: number, name: string): SessionPerformer => ({
  id,
  name,
  seat: id,
  is_active: true,
});

const roster = [
  performer(1, "Host"),
  performer(2, "Sarah"),
  performer(3, "Patrick"),
];

const turnOf = (performerId: number | null, performerName: string | null) => ({
  performerId,
  performerName,
});

describe("pickDefaultSinger", () => {
  it("starts on whoever's turn it is", () => {
    expect(pickDefaultSinger(roster, turnOf(2, "Sarah"))).toBe("Sarah");
  });

  it("falls back to the first seat when nobody is up", () => {
    expect(pickDefaultSinger(roster, turnOf(null, null))).toBe("Host");
    expect(pickDefaultSinger(roster, undefined)).toBe("Host");
  });

  it("falls back to the first seat when the turn's performer isn't offered", () => {
    // A queued turn whose performer has left the rotation: the roster only
    // lists active seats, so there is no button for them.
    expect(pickDefaultSinger(roster, turnOf(9, "Gone"))).toBe("Host");
  });

  it("matches a legacy row's name when the turn has no performer id", () => {
    expect(pickDefaultSinger(roster, turnOf(null, "Patrick"))).toBe("Patrick");
    expect(pickDefaultSinger(roster, turnOf(null, "Stranger"))).toBe("Host");
  });

  it("is empty with no roster, even when someone is up", () => {
    expect(pickDefaultSinger([], turnOf(2, "Sarah"))).toBe("");
  });
});

describe("useDefaultSinger", () => {
  type Props = {
    roster: SessionPerformer[];
    turn: ReturnType<typeof turnOf> | undefined;
  };
  const render = (initialProps: Props) =>
    renderHook(({ roster, turn }: Props) => useDefaultSinger(roster, turn), {
      initialProps,
    });

  it("starts on the turn's performer", () => {
    const { result } = render({ roster, turn: turnOf(3, "Patrick") });
    expect(result.current[0]).toBe("Patrick");
  });

  it("starts on the first seat with no turn", () => {
    const { result } = render({ roster, turn: undefined });
    expect(result.current[0]).toBe("Host");
  });

  it("follows a turn that arrives after mount", () => {
    const { result, rerender } = render({ roster, turn: undefined });
    expect(result.current[0]).toBe("Host");

    rerender({ roster, turn: turnOf(2, "Sarah") });
    expect(result.current[0]).toBe("Sarah");
  });

  it("follows a roster that arrives after mount", () => {
    const { result, rerender } = render({
      roster: [],
      turn: turnOf(2, "Sarah"),
    });
    expect(result.current[0]).toBe("");

    rerender({ roster, turn: turnOf(2, "Sarah") });
    expect(result.current[0]).toBe("Sarah");
  });

  it("keeps a deliberate pick when the turn moves on", () => {
    const { result, rerender } = render({ roster, turn: turnOf(2, "Sarah") });
    act(() => result.current[1]("Patrick"));
    expect(result.current[0]).toBe("Patrick");

    rerender({ roster, turn: turnOf(1, "Host") });
    expect(result.current[0]).toBe("Patrick");
  });

  it("keeps an emptied pick for the free-text field", () => {
    // "Someone else…" clears the name; a later turn must not refill it.
    const { result, rerender } = render({ roster, turn: turnOf(2, "Sarah") });
    act(() => result.current[1](""));

    rerender({ roster, turn: turnOf(3, "Patrick") });
    expect(result.current[0]).toBe("");
  });
});
