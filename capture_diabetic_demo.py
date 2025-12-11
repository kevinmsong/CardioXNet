#!/usr/bin/env python3
"""
Submit diabetic cardiomyopathy analysis and capture screenshots
"""
import asyncio
from playwright.async_api import async_playwright
import time

SEED_GENES = ["INS", "INSR", "AKT1", "PPARG", "SLC2A4", "AGER", "TNF", "IL6", "MAPK1", "NFKB1"]

async def submit_and_capture():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Non-headless to see what's happening
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("🚀 Starting diabetic cardiomyopathy analysis demo...")
        
        # 1. Go to home page and submit analysis
        print("\n1. Submitting analysis with 10 diabetic cardiomyopathy genes...")
        await page.goto('http://localhost:3000', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Fill in seed genes
        gene_input = await page.query_selector('textarea')
        if gene_input:
            await gene_input.fill('\n'.join(SEED_GENES))
            print(f"   ✓ Entered genes: {', '.join(SEED_GENES)}")
        
        await page.wait_for_timeout(1000)
        
        # Capture home page screenshot
        await page.screenshot(path='docs/screenshots/01-home-input.png', full_page=True)
        print("   ✓ Screenshot: 01-home-input.png")
        
        # Click submit button
        submit_button = await page.query_selector('button:has-text("Start Analysis")')
        if not submit_button:
            submit_button = await page.query_selector('button[type="submit"]')
        
        if submit_button:
            await submit_button.click()
            print("   ✓ Clicked submit button")
            await page.wait_for_timeout(3000)
            
            # Get analysis ID from URL
            current_url = page.url
            print(f"   Current URL: {current_url}")
            
            if '/progress/' in current_url:
                analysis_id = current_url.split('/progress/')[1].split('?')[0]
                print(f"   ✓ Analysis ID: {analysis_id}")
                
                # 2. Capture progress page
                print("\n2. Capturing progress page...")
                await page.wait_for_timeout(2000)
                await page.screenshot(path='docs/screenshots/02-progress.png', full_page=False)
                print("   ✓ Screenshot: 02-progress.png")
                
                # Wait for analysis to complete (check every 5 seconds, max 5 minutes)
                print("\n3. Waiting for analysis to complete...")
                max_wait = 300  # 5 minutes
                elapsed = 0
                while elapsed < max_wait:
                    # Check if we can navigate to results
                    try:
                        results_url = f'http://localhost:3000/results/{analysis_id}'
                        await page.goto(results_url, wait_until='networkidle', timeout=5000)
                        
                        # Check if results are loaded (look for pathways table)
                        table = await page.query_selector('table')
                        if table:
                            print(f"   ✓ Analysis complete after {elapsed} seconds!")
                            break
                    except:
                        pass
                    
                    # Go back to progress page
                    await page.goto(f'http://localhost:3000/progress/{analysis_id}', wait_until='networkidle')
                    await page.wait_for_timeout(5000)
                    elapsed += 5
                    print(f"   ... waiting ({elapsed}s / {max_wait}s)")
                
                if elapsed >= max_wait:
                    print("   ⚠️  Analysis taking too long, will use existing analysis for demo")
                    analysis_id = "analysis_20251209_114841"  # Fallback
                
                # Save analysis ID for screenshot script
                with open('/tmp/demo_analysis_id.txt', 'w') as f:
                    f.write(analysis_id)
                
                print(f"\n✅ Analysis ID saved: {analysis_id}")
                print("   You can now run the screenshot capture script")
                
            else:
                print("   ⚠️  Did not navigate to progress page")
        else:
            print("   ⚠️  Submit button not found")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(submit_and_capture())
