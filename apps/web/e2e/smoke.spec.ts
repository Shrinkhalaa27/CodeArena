import { expect, test } from "@playwright/test";

// register -> open problem -> submit -> see a verdict
test("register, open a problem, submit and see a verdict", async ({ page }) => {
  const id = Date.now().toString(36);
  await page.goto("/register");
  await page.getByLabel("Email").fill(`e2e_${id}@example.com`);
  await page.getByLabel("Handle").fill(`e2e_${id}`);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByRole("button", { name: "Sign up" }).click();
  await page.waitForURL("**/problems");

  await page.getByRole("link", { name: "A Plus B" }).click();
  await expect(page.getByRole("heading", { name: "A Plus B" })).toBeVisible();
  await expect(page.getByTestId("editor")).toBeVisible();

  await page.getByTestId("submit").click();
  const verdict = page.getByTestId("verdict");
  await expect(verdict).toBeVisible();
  // Any FINAL verdict proves the queue -> worker -> persistence -> UI loop works.
  await expect(verdict).not.toHaveAttribute("data-verdict", /^(QUEUED|RUNNING|COMPILING)$/, { timeout: 30_000 });
});
