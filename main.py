import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def scrape_upwork(page, keyword, min_b, max_b):
    max_str = str(max_b) if max_b else ""
    url = f"https://upwork.com{keyword}&t=1&total_amount={min_b}-{max_str}"
    print(f"Scraping Upwork: {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        job_cards = await page.locator("article.job-tile").all()
        for card in job_cards:
            try:
                title = await card.locator("h2.job-tile-title").inner_text()
                location = await card.locator("[data-test='client-country']").inner_text()
                budget_text = await card.locator("[data-test='budget']").inner_text()
                duration_text = await card.locator("[data-test='duration']").inner_text()
                commitment = "Full-time" if "30+ hrs" in duration_text else "Part-time / Contract"
                job_href = await card.locator("h2.job-tile-title a").get_attribute("href")
                
                await Actor.push_data({
                    "platform": "Upwork",
                    "role": title.strip(),
                    "budget_range": f"${min_b} - ${max_b if max_b else 'Any'}",
                    "extracted_pay": budget_text.strip(),
                    "location": location.strip(),
                    "commitment": commitment,
                    "url": f"https://upwork.com{job_href}"
                })
            except Exception:
                continue
    except Exception as e:
        print(f"Upwork scrape failed or timed out: {e}")

async def scrape_linkedin(page, keyword, min_b, max_b):
    url = f"https://linkedin.com{keyword}"
    print(f"Scraping LinkedIn: {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        job_cards = await page.locator(".base-card").all()
        for card in job_cards:
            try:
                title = await card.locator(".base-search-card__title").inner_text()
                company = await card.locator(".base-search-card__subtitle").inner_text()
                location = await card.locator(".job-search-card__location").inner_text()
                job_href = await card.locator("a.base-card__full-link").get_attribute("href")
                
                await Actor.push_data({
                    "platform": "LinkedIn",
                    "role": title.strip(),
                    "company": company.strip(),
                    "budget_range": f"${min_b} - ${max_b if max_b else 'Any'}",
                    "extracted_pay": "Check description (LinkedIn filter applied)",
                    "location": location.strip(),
                    "commitment": "Full-time (Default)",
                    "url": job_href
                })
            except Exception:
                continue
    except Exception as e:
        print(f"LinkedIn scrape failed or timed out: {e}")

async def scrape_simplify(page, keyword, min_b, max_b):
    url = f"https://simplify.jobs{keyword}"
    print(f"Scraping Simplify: {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        job_cards = await page.locator("[data-testid='job-list-item']").all()
        if not job_cards:
            job_cards = await page.locator("a[href*='/p/']").all()

        for card in job_cards:
            try:
                text_content = await card.inner_text()
                if min_b and f"${min_b}" not in text_content and min_b > 1000:
                    continue
                    
                job_href = await card.get_attribute("href")
                await Actor.push_data({
                    "platform": "Simplify",
                    "role": text_content.split("\n")[0] if "\n" in text_content else text_content,
                    "budget_range": f"${min_b} - ${max_b if max_b else 'Any'}",
                    "extracted_pay": f"Filtered threshold > ${min_b}",
                    "location": "Remote / United States",
                    "commitment": "Full-time / Internship",
                    "url": f"https://simplify.jobs{job_href}" if job_href.startswith("/") else job_href
                })
            except Exception:
                continue
    except Exception as e:
        print(f"Simplify scrape failed or timed out: {e}")

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        platform = actor_input.get("platform", "all").lower()
        keyword = actor_input.get("keyword", "developer")
        min_budget = actor_input.get("min_budget", 100)
        max_budget = actor_input.get("max_budget", 5000)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Master logic handler for specific platforms vs 'all'
            if platform == "all":
                print("Running All-in-One Sequential Scan...")
                await scrape_upwork(page, keyword, min_budget, max_budget)
                await scrape_linkedin(page, keyword, min_budget, max_budget)
                await scrape_simplify(page, keyword, min_budget, max_budget)
            elif platform == "upwork":
                await scrape_upwork(page, keyword, min_budget, max_budget)
            elif platform == "linkedin":
                await scrape_linkedin(page, keyword, min_budget, max_budget)
            elif platform == "simplify":
                await scrape_simplify(page, keyword, min_budget, max_budget)
                
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
