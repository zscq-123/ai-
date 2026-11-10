import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs/promises';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, '../独立站medical-sgcom/ikeas/frontend/package.json'));
const puppeteer = require('puppeteer-core');
const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
});
const output = path.join(root, 'data/integration-local');
const checks = [];
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1360, height: 900 });
  await page.goto('http://localhost:5173/login');
  const login = await page.evaluate(async () => {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'admin123' }),
    });
    const result = await response.json();
    if (!result.data?.token) return false;
    localStorage.setItem('oms-token', result.data.token);
    localStorage.setItem('oms-user', JSON.stringify(result.data.user));
    return true;
  });
  assert(login, 'Local OMS demo login failed');
  await page.goto('http://localhost:5173/support');
  await page.waitForSelector('textarea[aria-label="客服问题"]');
  const order = await page.evaluate(async () => {
    const response = await fetch('/api/v1/orders?page=1&size=1', {
      headers: { Authorization: `Bearer ${localStorage.getItem('oms-token')}` },
    });
    return (await response.json()).data?.records?.[0];
  });
  const orderNo = order?.orderNo;
  assert(orderNo, 'Local OMS needs an existing order for the read-only smoke');
  await page.type('input[aria-label="关联订单号"]', orderNo);
  await page.type('textarea[aria-label="客服问题"]', '这个订单当前什么状态？');
  const responsePromise = page.waitForResponse(r => r.url().includes('/support/chat') && r.request().method() === 'POST', { timeout: 45000 });
  await page.click('button[type="submit"]');
  const response = await responsePromise;
  const result = await response.json();
  assert.equal(response.status(), 200);
  assert.equal(typeof result.data.answer, 'string');
  const statuses = { 1: '待支付', 2: '已支付', 3: '已审核', 4: '已发货', 5: '已签收', 6: '已完成', 7: '已取消', 8: '售后处理中' };
  assert(result.data.answer.includes(statuses[order.status]), 'The reply must include the verified order state');
  assert(result.data.answer.includes(orderNo), 'The reply must identify the selected order');
  assert(result.data.citations.some(c => c.reference.startsWith('order://oms/')));
  await page.waitForFunction(answer => document.body.innerText.includes(answer), {}, result.data.answer);
  await page.screenshot({ path: path.join(output, 'oms-support.png'), fullPage: true });
  checks.push({ name: 'OMS browser authenticated order chat', status: 'passed', answer: result.data.answer });

  const shop = await browser.newPage();
  await shop.setViewport({ width: 390, height: 844 });
  await shop.goto('http://localhost:3000/zh/', { waitUntil: 'networkidle2' });
  await shop.waitForSelector('button[data-support-launcher]');
  await shop.click('button[data-support-launcher]');
  await shop.waitForSelector('input[maxlength="2000"]');
  await shop.type('input[maxlength="2000"]', '怎么联系你们？');
  const shopResponsePromise = shop.waitForResponse(r => r.url().includes('/chat/messages') && r.request().method() === 'POST', { timeout: 45000 });
  await shop.click('form button[type="submit"]');
  const shopResponse = await shopResponsePromise;
  const reply = await shopResponse.json();
  assert.equal(shopResponse.status(), 200);
  assert.equal(reply.degraded, false);
  assert(reply.citations.some(c => c.reference === 'faq://buzud/contact'));
  await shop.waitForFunction(answer => document.body.innerText.includes(answer), {}, reply.reply);
  await shop.screenshot({ path: path.join(output, 'buzud-support-mobile.png'), fullPage: false });
  checks.push({ name: 'BUZUD mobile browser FAQ chat', status: 'passed', answer: reply.reply });
  const denied = await shop.evaluate(async () => {
    const r = await fetch('http://localhost:8090/api/v1/chat/messages', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: '查一下订单', orderNo: 'NO-ACCESS' }),
    });
    return r.status;
  });
  assert.equal(denied, 401);
  checks.push({ name: 'BUZUD anonymous order denied', status: 'passed' });
  await fs.writeFile(path.join(output, 'browser-smoke.json'), JSON.stringify({ checkedAt: new Date().toISOString(), checks }, null, 2));
  console.log(JSON.stringify(checks, null, 2));
} finally {
  await browser.close();
}
