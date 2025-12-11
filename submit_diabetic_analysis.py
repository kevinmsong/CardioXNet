#!/usr/bin/env python3
"""
Submit diabetic cardiomyopathy analysis via frontend and wait for completion
"""
import asyncio
from playwright.async_api import async_playwright
import time
import json

SEED_GENES = ["INS", "INSR", "AKT1", "PPARG", "SLC2A4", "AGER", "TNF", "IL6", "MAPK1", "NFKB1"]

async def submit_analysis():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("🚀 Submitting diabetic cardiomyopathy analysis...")
        print(f"   Genes: {', '.join(SEED_GENES)}")
        
        # Go to home page
        await page.goto('http://localhost:3000', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Fill in genes
        gene_input = await page.query_selector('textarea[placeholder*="gene" i], textarea')
        if gene_input:
            await gene_input.fill('\n'.join(SEED_GENES))
            print("   ✓ Genes entered")
        else:
            print("   ✗ Could not find gene input field")
            await browser.close()
            return None
        
        await page.wait_for_timeout(1000)
        
        # Find and click submit button
        submit_button = None
        possible_selectors = [
            'button:has-text("Start Analysis")',
            'button:has-text("Submit")',
            'button:has-text("Analyze")',
            'button[type="submit"]',
            'button:has-text("Run")'
        ]
        
        for selector in possible_selectors:
            try:
                submit_button = await page.query_selector(selector)
                if submit_button:
                    print(f"   ✓ Found button: {selector}")
                    break
            except:
                continue
        
        if not submit_button:
            print("   ✗ Could not find submit button")
            await browser.close()
            return None
        
        # Click submit
        await submit_button.click()
        print("   ✓ Clicked submit")
        await page.wait_for_timeout(3000)
        
        # Get analysis ID from URL
        current_url = page.url
        print(f"   Current URL: {current_url}")
        
        analysis_id = None
        if '/progress/' in current_url:
            analysis_id = current_url.split('/progress/')[1].split('?')[0].split('/')[0]
        elif '/results/' in current_url:
            analysis_id = current_url.split('/results/')[1].split('?')[0].split('/')[0]
        
        if analysis_id:
            print(f"   ✓ Analysis ID: {analysis_id}")
            
            # Save analysis ID
            with open('/tmp/diabetic_analysis_id.txt', 'w') as f:
                f.write(analysis_id)
            
            print(f"\n⏳ Waiting for analysis to complete...")
            print("   This may take 3-5 minutes...")
            
            # Wait for completion
            max_wait = 600  # 10 minutes
            elapsed = 0
            completed = False
            
            while elapsed < max_wait:
                try:
                    # Try to load results page
                    await page.goto(f'http://localhost:3000/results/{analysis_id}', 
                                  wait_until='networkidle', timeout=10000)
                    
                    # Check for pathways table
                    table = await page.query_selector('table')
                    if table:
                        # Check if table has rows
                        rows = await page.query_selector_all('tbody tr')
                        if len(rows) > 0:
                            print(f"\n   ✓ Analysis complete! ({elapsed}s)")
                            completed = True
                            break
                except Exception as e:
                    pass
                
                # Wait and check again
                await page.wait_for_timeout(10000)  # Wait 10 seconds
                elapsed += 10
                if elapsed % 30 == 0:  # Print every 30 seconds
                    print(f"   ... still waiting ({elapsed}s / {max_wait}s)")
            
            if completed:
                print(f"\n✅ Analysis {analysis_id} completed successfully!")
                await browser.close()
                return analysis_id
            else:
                print(f"\n⚠️  Analysis did not complete within {max_wait}s")
                await browser.close()
                return analysis_id  # Return anyway, might be usable
        else:
            print("   ✗ Could not extract analysis ID from URL")
            await browser.close()
            return None

if __name__ == '__main__':
    analysis_id = asyncio.run(submit_analysis())
    if analysis_id:
        print(f"\nAnalysis ID: {analysis_id}")
        print("You can now capture screenshots with this analysis ID")
    else:
        print("\nFailed to submit analysis")
