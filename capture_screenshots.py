#!/usr/bin/env python3
"""
Capture screenshots of CardioXNet application for README documentation
"""
import asyncio
from playwright.async_api import async_playwright
import time

async def capture_screenshots():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("📸 Capturing screenshots...")
        
        # 1. Home Page - Gene Input
        print("1. Capturing Home Page...")
        await page.goto('http://localhost:3000', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Fill in sample genes
        gene_input = await page.query_selector('textarea')
        if gene_input:
            await gene_input.fill('TTN\nMYH7\nMYBPC3\nTNNT2\nLMNA')
        
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/01-home-input.png', full_page=True)
        print("   ✓ Saved: 01-home-input.png")
        
        # 2. Progress Page
        print("2. Capturing Progress Page...")
        await page.goto('http://localhost:3000/progress/analysis_20251209_114841', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='docs/screenshots/02-progress.png', full_page=False)
        print("   ✓ Saved: 02-progress.png")
        
        # 3. Results Page - Overview
        print("3. Capturing Results Page...")
        await page.goto('http://localhost:3000/results/analysis_20251209_114841', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='docs/screenshots/03-results-overview.png', full_page=False)
        print("   ✓ Saved: 03-results-overview.png")
        
        # 4. Results Page - Seed Genes and Key Genes
        print("4. Capturing Seed and Key Genes...")
        await page.evaluate('window.scrollTo(0, 400)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/04-key-genes.png', full_page=False)
        print("   ✓ Saved: 04-key-genes.png")
        
        # 5. Results Page - Pathways Table
        print("5. Capturing Pathways Table...")
        await page.evaluate('window.scrollTo(0, 1200)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/05-pathways-table.png', full_page=False)
        print("   ✓ Saved: 05-pathways-table.png")
        
        # 6. Details Page
        print("6. Capturing Details Page...")
        await page.goto('http://localhost:3000/detail/analysis_20251209_114841/KEGG:05414', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='docs/screenshots/06-details-page.png', full_page=False)
        print("   ✓ Saved: 06-details-page.png")
        
        # 7. Details Page - Pathway Lineage
        print("7. Capturing Pathway Lineage...")
        await page.evaluate('window.scrollTo(0, 600)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/07-pathway-lineage.png', full_page=False)
        print("   ✓ Saved: 07-pathway-lineage.png")
        
        # 8. Details Page - Literature Evidence
        print("8. Capturing Literature Evidence...")
        await page.evaluate('window.scrollTo(0, 1800)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/08-literature-evidence.png', full_page=False)
        print("   ✓ Saved: 08-literature-evidence.png")
        
        await browser.close()
        print("\n✅ All screenshots captured successfully!")

if __name__ == '__main__':
    asyncio.run(capture_screenshots())
