import { test, expect } from "@playwright/test";
test("local fixture can configure a session and retains safe capability boundaries", async ({
  page,
}) => {
  test.skip(
    process.env.TDR_E2E_FIXTURE !== "true",
    "Requires disposable integration database",
  );
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("owner");
  await page.getByLabel("Password", { exact: true }).fill("test-password-long");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Your streaming workspace" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../runtime/screenshots/overview.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: /Sessions/ }).click();
  await page.getByLabel("Session name").fill("Browser acceptance");
  await page.getByRole("button", { name: "Create session" }).click();
  const session = page
    .locator("article")
    .filter({ has: page.getByRole("heading", { name: "Browser acceptance" }) });
  await expect(session).toBeVisible();
  await session.getByRole("button", { name: "Set test mode" }).click();
  await expect(session).toContainText("testing");
  await expect(
    session.getByRole("button", { name: "Go Live unavailable" }),
  ).toBeDisabled();
  await session.getByRole("button", { name: "Stop", exact: true }).click();
  await expect(session).toContainText("ended");
  await page.getByRole("button", { name: /OBS inputs/ }).click();
  await page.getByLabel("Name", { exact: true }).fill("Browser input");
  await page.getByRole("button", { name: "Save input" }).click();
  await expect(page.getByText("Save this token now")).toBeVisible();
  await page.getByRole("button", { name: "I have saved it — dismiss" }).click();
  await expect(page.getByText("Save this token now")).not.toBeVisible();
  await page.getByRole("button", { name: /Compatibility/ }).click();
  await page.getByLabel("Output orientation").selectOption("vertical");
  await page.getByRole("button", { name: "Evaluate compatibility" }).click();
  await expect(
    page.getByRole("heading", { name: "unsupported", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Approve video conversion for this proposal").check();
  await page.getByRole("button", { name: "Evaluate compatibility" }).click();
  await expect(
    page.getByRole("heading", { name: "video conversion", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Color theme").selectOption("light");
  await page.screenshot({
    path: "../runtime/screenshots/planner-light.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: /API documentation/ }).click();
  await expect(
    page.getByRole("heading", { name: "REST API reference" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
});
