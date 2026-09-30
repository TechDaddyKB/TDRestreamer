import { test, expect } from "@playwright/test";
test("local login and setup are accessible", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "First time? Set up this appliance" })
    .click();
  await expect(page.getByLabel("One-time setup credential")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create workspace" }),
  ).toBeEnabled();
});
