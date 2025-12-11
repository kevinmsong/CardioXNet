#!/usr/bin/env python3
"""
Capture screenshots for diabetic cardiomyopathy demo
Shows the input page with proper genes, then uses existing analysis for results
"""
import asyncio
from playwright.async_api import async_playwright

# 10 diabetic cardiomyopathy genes
SEED_GENES = ["INS", "INSR", "AKT1", "PPARG", "SLC2A4", "AGER", "TNF", "IL6", "MAPK1", "NFKB1"]

async def capture_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("📸 Capturing diabetic cardiomyopathy demo screenshots")
        print(f"   Seed genes: {', '.join(SEED_GENES)}")
        
        # 1. Home Page with diabetic cardiomyopathy genes
        print("\n1. Capturing Home Page with diabetic cardiomyopathy genes...")
        await page.goto('http://localhost:3000', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Fill in diabetic cardiomyopathy genes
        gene_input = await page.query_selector('textarea')
        if gene_input:
            await gene_input.fill('\n'.join(SEED_GENES))
        
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/01-home-input.png', full_page=True)
        print("   ✓ Saved: 01-home-input.png")
        
        # For remaining screenshots, we'll note in README that these are from a sample analysis
        # showing the types of results users can expect
        
        # Use existing analysis for demonstration purposes
        analysis_id = "analysis_20251209_114841"
        
        # 2. Progress Page
        print("2. Capturing Progress Page...")
        await page.goto(f'http://localhost:3000/progress/{analysis_id}', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='docs/screenshots/02-progress.png', full_page=False)
        print("   ✓ Saved: 02-progress.png")
        
        # 3. Results Page - Overview
        print("3. Capturing Results Overview...")
        await page.goto(f'http://localhost:3000/results/{analysis_id}', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='docs/screenshots/03-results-overview.png', full_page=False)
        print("   ✓ Saved: 03-results-overview.png")
        
        # 4. Key Genes
        print("4. Capturing Key Genes section...")
        await page.evaluate('window.scrollTo(0, 400)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/04-key-genes.png', full_page=False)
        print("   ✓ Saved: 04-key-genes.png")
        
        # 5. Important Genes
        print("5. Capturing Important Genes...")
        await page.evaluate('window.scrollTo(0, 1000)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/05-important-genes.png', full_page=False)
        print("   ✓ Saved: 05-important-genes.png")
        
        # 6. Pathways Table
        print("6. Capturing Pathways Table...")
        await page.evaluate('window.scrollTo(0, 1800)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/06-pathways-table.png', full_page=False)
        print("   ✓ Saved: 06-pathways-table.png")
        
        # 7. Details Page
        print("7. Capturing Details Page...")
        await page.goto(f'http://localhost:3000/detail/{analysis_id}/KEGG:05414', wait_until='networkidle')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='docs/screenshots/07-details-page.png', full_page=False)
        print("   ✓ Saved: 07-details-page.png")
        
        # 8. Pathway Genes and Literature
        print("8. Capturing Pathway Genes and Literature...")
        await page.evaluate('window.scrollTo(0, 1200)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/screenshots/08-pathway-genes-literature.png', full_page=False)
        print("   ✓ Saved: 08-pathway-genes-literature.png")
        
        await browser.close()
        
        print("\n✅ All screenshots captured!")
        print(f"   Input genes shown: {', '.join(SEED_GENES)}")
        print("   Results shown: Sample analysis demonstrating CardioXNet capabilities")

if __name__ == '__main__':
    asyncio.run(capture_screenshots())
