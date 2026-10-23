import { test, expect } from "@playwright/test";

test("edit, compare, approve and reload the same saved plan", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Build a portfolio", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Break down my goal", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Make the plan your own." }),
  ).toBeVisible();
  await page
    .getByLabel("Task 4 estimate (minutes)", { exact: true })
    .fill("60");
  await expect(
    page.getByText("Unsaved changes", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Save and build schedules", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Find a rhythm that fits." }),
  ).toBeVisible();
  await page
    .locator(".candidate-card")
    .filter({
      has: page.getByRole("heading", { name: "Match energy", exact: true }),
    })
    .click();
  await page
    .getByRole("button", { name: "Review events", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("4 hr 30 min");
  await page
    .getByRole("button", { name: "Add to demo calendar", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "6 events added", exact: true }),
  ).toBeVisible();
  const savedUrl = page.url();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "6 events added", exact: true }),
  ).toBeVisible();
  expect(page.url()).toBe(savedUrl);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBeTruthy();
});

test("return to editing invalidates approval, then reject without writes", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Learn Python basics", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Break down my goal", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Save and build schedules", exact: true })
    .click();
  await page.getByRole("button", { name: "Edit tasks", exact: true }).click();
  await page
    .getByLabel("Task 1 estimate (minutes)", { exact: true })
    .fill("20");
  await expect(
    page.getByRole("button", { name: "Review events", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Save and build schedules", exact: true })
    .click();
  await page.getByRole("button", { name: "Reject plan", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "No calendar events were added",
      exact: true,
    }),
  ).toBeVisible();
  const id = new URL(page.url()).searchParams.get("plan");
  const plan = await (await request.get(`/api/plans/${id}`)).json();
  expect(plan.write_results).toEqual([]);
  expect(plan.status).toBe("rejected");
});
