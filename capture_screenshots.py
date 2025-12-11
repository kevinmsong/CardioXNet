#!/usr/bin/env python3
"""
Capture screenshots of CardioXNet application for README documentation
Uses the actual seed genes from analysis_20251209_114841: PIK3R1, ITGB1, SRC
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
        
        print("📸 Capturing screenshots with correct seed genes: PIK3R1, ITGB1, SRC")
        
        # 1. Home Page - Gene Input
        print("1. Capturing Home Page with correct genes...")
        await page.goto('http://localhost:3000', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Fill in the ACTUAL seed genes from the analysis
        gene_input = await page.query_selector('textarea')
        if gene_input:
            await gene_input.fill('PIK3R1\nITGB1\nSRC')
        
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
        
        # 5. Results Page - Important Genes
        print("5. Capturing Important Genes...")
        await page.evaluate('window.scrollTo(0, 1000)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/05-important-genes.png', full_page=False)
        print("   ✓ Saved: 05-important-genes.png")
        
        # 6. Results Page - Pathways Table
        print("6. Capturing Pathways Table...")
        await page.evaluate('window.scrollTo(0, 1800)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/06-pathways-table.png', full_page=False)
        print("   ✓ Saved: 06-pathways-table.png")
        
        # 7. Details Page
        print("7. Capturing Details Page...")
        await page.goto('http://localhost:3000/detail/analysis_20251209_114841/KEGG:05414', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='docs/screenshots/07-details-page.png', full_page=False)
        print("   ✓ Saved: 07-details-page.png")
        
        # 8. Details Page - Pathway Genes and Literature
        print("8. Capturing Pathway Genes and Literature...")
        await page.evaluate('window.scrollTo(0, 1200)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/08-pathway-genes-literature.png', full_page=False)
        print("   ✓ Saved: 08-pathway-genes-literature.png")
        
        await browser.close()
        print("\n✅ All screenshots captured successfully with correct seed genes!")
        print("   Seed genes used: PIK3R1, ITGB1, SRC")

if __name__ == '__main__':
    asyncio.run(capture_screenshots())
