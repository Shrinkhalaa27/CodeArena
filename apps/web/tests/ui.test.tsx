import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Heatmap, RatingChart } from "@/components/charts";
import { EmptyState, ErrorState, RichText, VerdictBadge } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { isFinal, timeUntil } from "@/lib/format";

describe("VerdictBadge", () => {
  it.each([
    ["ACCEPTED", "Accepted"], ["WRONG_ANSWER", "Wrong Answer"], ["TIME_LIMIT_EXCEEDED", "Time Limit Exceeded"],
    ["COMPILATION_ERROR", "Compilation Error"], ["RUNTIME_ERROR", "Runtime Error"], ["INTERNAL_ERROR", "Judge Error"],
  ])("renders %s", (status, label) => {
    render(<VerdictBadge status={status} />);
    expect(screen.getByTestId("verdict")).toHaveTextContent(label);
    expect(screen.getByTestId("verdict")).toHaveAttribute("data-verdict", status);
  });
  it("shows a live indicator only while pending", () => {
    const { container, rerender } = render(<VerdictBadge status="RUNNING" />);
    expect(container.querySelector(".animate-pulse")).not.toBeNull();
    rerender(<VerdictBadge status="ACCEPTED" />);
    expect(container.querySelector(".animate-pulse")).toBeNull();
  });
  it("classifies final states", () => {
    expect(isFinal("QUEUED")).toBe(false);
    expect(isFinal("RUNNING")).toBe(false);
    expect(isFinal("WRONG_ANSWER")).toBe(true);
  });
});

describe("states", () => {
  it("ErrorState exposes the request id and a retry action", () => {
    render(<ErrorState error={new ApiError(500, "X", "Boom", "req-1")} retry={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Boom");
    expect(screen.getByText(/req-1/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
  it("EmptyState shows hint", () => {
    render(<EmptyState title="Nothing" hint="Add some" />);
    expect(screen.getByText("Add some")).toBeInTheDocument();
  });
});

describe("timeUntil", () => {
  const now = Date.parse("2026-01-01T00:00:00Z");
  it("formats hours and days, never negative", () => {
    expect(timeUntil("2026-01-01T01:02:03Z", now)).toBe("01:02:03");
    expect(timeUntil("2026-01-03T02:30:00Z", now)).toBe("2d 2h 30m");
    expect(timeUntil("2025-12-31T00:00:00Z", now)).toBe("00:00:00");
  });
});

describe("charts", () => {
  it("RatingChart has an accessible label and an empty state", () => {
    const { rerender } = render(<RatingChart points={[{ rating: 1200, label: "a" }, { rating: 1300, label: "b" }]} />);
    expect(screen.getByRole("img")).toHaveAttribute("aria-label", expect.stringContaining("1200 to 1300"));
    rerender(<RatingChart points={[]} />);
    expect(screen.getByText(/appears after/i)).toBeInTheDocument();
  });
  it("Heatmap summarises totals", () => {
    const today = new Date().toISOString().slice(0, 10);
    render(<Heatmap activity={{ [today]: 3 }} />);
    expect(screen.getByRole("img")).toHaveAttribute("aria-label", expect.stringContaining("3 submissions"));
  });
});

describe("RichText", () => {
  it("renders bold and code as elements and never injects HTML", () => {
    const { container } = render(<RichText text={"Sum **a** and `b` <img src=x onerror=alert(1)>"} />);
    expect(container.querySelector("strong")?.textContent).toBe("a");
    expect(container.querySelector("code")?.textContent).toBe("b");
    expect(container.querySelector("img")).toBeNull();
  });
});
