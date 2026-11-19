from playwright.sync_api import sync_playwright
import pandas as pd
import time
import re

category = "electronic-devices"
target_count = 200
products_list = []

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    page = context.new_page()

    url = f"https://www.digikala.com/search/category-{category}/?sort=7"
    print(f"Opening {url}...")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    try:
        page.wait_for_selector("a[href*='/product/dkp-']", timeout=15000)
    except Exception:
        print("No products loaded.")

    no_new_data_rounds = 0

    while len(products_list) < target_count:
        cards = page.locator("a[href*='/product/dkp-']").all()
        before_count = len(products_list)

        for card in cards:
            if len(products_list) >= target_count:
                break

            href = card.get_attribute("href") or ""
            match = re.search(r"dkp-(\d+)", href)
            if not match:
                continue
            prod_id = match.group(1)

            if any(x["کد محصول"] == prod_id for x in products_list):
                continue

            text_lines = [line.strip() for line in card.inner_text().split("\n") if line.strip()]
            if not text_lines:
                continue

            title = max(text_lines, key=len)
            prices = []
            discount_percent = "0%"
            tags = []

            for line in text_lines:
                clean_en = line.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
                if "%" in clean_en or "٪" in line:
                    discount_percent = clean_en
                elif line != title and not clean_en.replace(",", "").replace("٬", "").isdigit():
                    tags.append(line)

                clean_num = clean_en.replace(",", "").replace("٬", "")
                if clean_num.isdigit() and int(clean_num) > 1000:
                    prices.append(int(clean_num))

            selling_price = min(prices) if prices else 0
            original_price = max(prices) if prices else 0

            products_list.append({
                "رتبه": len(products_list) + 1,
                "کد محصول": prod_id,
                "عنوان محصول": title,
                "قیمت فروش (تومان)": selling_price,
                "قیمت اصلی (تومان)": original_price,
                "درصد تخفیف": discount_percent,
                "جزئیات و برچسب کارت": " | ".join(tags),
                "لینک": f"https://www.digikala.com/product/dkp-{prod_id}/"
            })

        print(f"Collected so far: {len(products_list)} / {target_count}")

        if len(products_list) >= target_count:
            break

        if len(products_list) == before_count:
            no_new_data_rounds += 1
            if no_new_data_rounds >= 5:
                print("Reached end of list or page stopped loading more items.")
                break
        else:
            no_new_data_rounds = 0

        page.mouse.wheel(0, 2500)
        time.sleep(2.5)

    browser.close()

df = pd.DataFrame(products_list)
df.to_csv(f"top_{target_count}_{category}.csv", index=False, encoding="utf-8-sig")
print(f"Done. Total {len(df)} products saved.")