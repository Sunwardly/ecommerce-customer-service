import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    let data
    if (path === '/api/visitor/session') data = { sender_id: 'v_test_browser', demo_user_id: 'u1001' }
    else if (path === '/api/chat/history') data = { sender_id: 'v_test_browser', messages: [] }
    else if (path === '/api/chat') data = { sender_id: 'v_test_browser', message_id: 'reply', messages: [{ text: '测试客服回复' }] }
    else throw new Error(`Unexpected API call: ${path}`)
    await route.fulfill({ json: data })
  })
  await page.route('**/commerce/**', route => route.fulfill({ json: { data: { orders: [], products: [] } } }))
})

test('mobile keyboard-sized viewport keeps composer visible and avoids page scroll', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  const input = page.getByPlaceholder('请输入咨询内容...')
  await input.fill('你好')
  await page.setViewportSize({ width: 390, height: 430 })
  await expect(input).toBeVisible()
  // Viewport resize is applied by the app in requestAnimationFrame.
  await expect.poll(async () => {
    const bounds = await input.boundingBox()
    return bounds ? bounds.y + bounds.height : Infinity
  }).toBeLessThanOrEqual(430)
  expect(await page.evaluate(() => window.scrollY)).toBe(0)
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect(page.getByText('测试客服回复', { exact: true })).toBeVisible()
  await expect(page.getByText(/第.*轮/)).toHaveCount(0)
})

test('mobile object panel opens and can return to chat', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  const toggle = page.getByRole('button', { name: '订单 / 商品', exact: true })
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-expanded', 'true')
  await page.getByRole('button', { name: '返回聊天', exact: true }).click()
  await expect(toggle).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByPlaceholder('请输入咨询内容...')).toBeVisible()
})

test('desktop can send a text message and renders the local support image', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.goto('/')
  await page.getByPlaceholder('请输入咨询内容...').fill('你好')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect(page.getByText('测试客服回复', { exact: true })).toBeVisible()
  const avatar = page.locator('img[src="/images/support-avatar.svg"]').first()
  await expect(avatar).toBeVisible()
  expect(await avatar.evaluate(img => img.complete && img.naturalWidth > 0)).toBe(true)
})
