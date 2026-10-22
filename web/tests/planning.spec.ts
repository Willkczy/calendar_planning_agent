import { test, expect } from "@playwright/test";

test("edit, compare, approve and reload the same saved plan", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "完成個人作品集", exact: true })
    .click();
  await page.getByRole("button", { name: "拆解我的目標", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "先把步驟，調整成你的樣子。" }),
  ).toBeVisible();
  await page.getByLabel("任務 4 估計分鐘", { exact: true }).fill("60");
  await expect(page.getByText("有未儲存的修改", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "儲存並建立方案", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "選一個適合你的節奏。" }),
  ).toBeVisible();
  await page
    .locator(".candidate-card")
    .filter({
      has: page.getByRole("heading", { name: "配合精力", exact: true }),
    })
    .click();
  await page.getByRole("button", { name: "查看新增摘要", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("4 小時 30 分");
  await page
    .getByRole("button", { name: "確認新增至示範日曆", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "已新增 6 個事件", exact: true }),
  ).toBeVisible();
  const savedUrl = page.url();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "已新增 6 個事件", exact: true }),
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
    .getByRole("button", { name: "學會 Python 基礎", exact: true })
    .click();
  await page.getByRole("button", { name: "拆解我的目標", exact: true }).click();
  await page
    .getByRole("button", { name: "儲存並建立方案", exact: true })
    .click();
  await page.getByRole("button", { name: "調整任務", exact: true }).click();
  await page.getByLabel("任務 1 估計分鐘", { exact: true }).fill("20");
  await expect(
    page.getByRole("button", { name: "查看新增摘要", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "儲存並建立方案", exact: true })
    .click();
  await page.getByRole("button", { name: "不採用", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "沒有新增任何日曆事件", exact: true }),
  ).toBeVisible();
  const id = new URL(page.url()).searchParams.get("plan");
  const plan = await (await request.get(`/api/plans/${id}`)).json();
  expect(plan.write_results).toEqual([]);
  expect(plan.status).toBe("rejected");
});
