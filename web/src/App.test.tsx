import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
afterEach(() => vi.unstubAllGlobals());
describe("authentication", () => {
  it("explains unavailable capabilities and requires bootstrap fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ error: { message: "Sign in" } }),
      }),
    );
    render(<App />);
    await screen.findByRole("heading", { name: "Welcome back" });
    await userEvent.click(
      screen.getByRole("button", { name: "First time? Set up this appliance" }),
    );
    expect(screen.getByLabelText("One-time setup credential")).toHaveAttribute(
      "type",
      "password",
    );
    expect(screen.getByLabelText("Password")).toHaveAttribute(
      "minlength",
      "12",
    );
    expect(
      screen.getByText(/Discord and Google login are not implemented/),
    ).toBeVisible();
  });
  it("does not offer mutation controls to viewers", async () => {
    vi.stubGlobal(
      "EventSource",
      class {
        addEventListener() {}
        close() {}
      },
    );
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => ({
        ok: true,
        json: async () =>
          url.endsWith("/auth/me")
            ? { role: "viewer", user_id: "u", tenant_id: "t" }
            : url.endsWith("/capabilities")
              ? { publishing: false }
              : { items: [] },
      })),
    );
    render(<App />);
    await screen.findByRole("heading", { name: "Your streaming workspace" });
    await userEvent.click(screen.getByRole("button", { name: /Sessions/ }));
    expect(
      screen.queryByRole("button", { name: "Create session" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/No media is processed/)).toBeVisible();
  });
});
