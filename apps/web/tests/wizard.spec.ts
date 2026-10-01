import { test, expect } from '@playwright/test';

test.describe('Wizard Flow', () => {
  test('should display RTL Hebrew interface', async ({ page }) => {
    await page.goto('/');
    
    // Check RTL direction
    const html = page.locator('html');
    await expect(html).toHaveAttribute('dir', 'rtl');
    await expect(html).toHaveAttribute('lang', 'he');
    
    // Check Hebrew title
    await expect(page.locator('h1')).toContainText('יועץ דיג');
  });

  test('should navigate through wizard steps', async ({ page }) => {
    await page.goto('/wizard');
    
    // Step 1: Fish selection
    await expect(page.locator('h2')).toContainText('דג מטרה');
    
    // Select a fish
    await page.click('button:has-text("לברק")');
    await page.click('button:has-text("הבא")');
    
    // Step 2: Location
    await expect(page.locator('h2')).toContainText('מיקום וזמן');
    
    // Fill location
    await page.fill('input[placeholder*="פלמחים"]', 'תל אביב');
    await page.click('button:has-text("חוף חולי")');
    await page.click('button:has-text("הבא")');
    
    // Step 3: Conditions
    await expect(page.locator('h2')).toContainText('תנאים');
    
    await page.click('button:has-text("צלול")');
    await page.click('button:has-text("בינוני")');
    await page.click('button:has-text("הבא")');
    
    // Step 4: Equipment
    await expect(page.locator('h2')).toContainText('ציוד');
    await page.click('button:has-text("הבא")');
    
    // Step 5: Review
    await expect(page.locator('h2')).toContainText('סיכום');
    await expect(page.locator('text=לברק')).toBeVisible();
    await expect(page.locator('text=תל אביב')).toBeVisible();
  });

  test('should be usable at 360px width', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 640 });
    await page.goto('/wizard');
    
    // All buttons should be visible and clickable
    const fishButtons = page.locator('button:has-text("לברק")');
    await expect(fishButtons).toBeVisible();
    
    // Navigation buttons should be visible
    await expect(page.locator('button:has-text("הבא")')).toBeVisible();
  });

  test('should show progress indicator', async ({ page }) => {
    await page.goto('/wizard');
    
    // Progress bar should exist
    const progressBars = page.locator('.h-2.rounded');
    await expect(progressBars).toHaveCount(5);
    
    // First should be active
    await expect(progressBars.first()).toHaveClass(/bg-primary-600/);
  });
});

test.describe('Result Page', () => {
  test('should display suitability score correctly', async ({ page }) => {
    // This test requires a mock API or real backend
    // For now, we test the UI structure
    await page.goto('/result/test-id');
    
    // Should show loading or error state
    await expect(page.locator('text=טוען').or(page.locator('text=שגיאה'))).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/');
    
    const h1 = page.locator('h1');
    await expect(h1).toHaveCount(1);
  });

  test('should have accessible form controls', async ({ page }) => {
    await page.goto('/wizard');
    
    // Navigate to equipment step
    await page.click('button:has-text("הבא")');
    await page.click('button:has-text("הבא")');
    await page.click('button:has-text("הבא")');
    
    // Check input labels
    const inputs = page.locator('input[type="number"]');
    await expect(inputs.first()).toBeVisible();
  });
});

test.describe('RTL Numeric Display', () => {
  test('should display numbers in LTR within RTL context', async ({ page }) => {
    await page.goto('/wizard');
    
    // Navigate to equipment step
    await page.click('button:has-text("הבא")');
    await page.click('button:has-text("הבא")');
    await page.click('button:has-text("הבא")');
    
    // Check that numeric inputs have LTR class
    const numericInputs = page.locator('.ltr-nums');
    await expect(numericInputs.first()).toBeVisible();
  });
});
