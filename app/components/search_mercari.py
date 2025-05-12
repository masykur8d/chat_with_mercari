from playwright.sync_api import sync_playwright


def search_mercari(keywords: str, sort_order: str = "score:desc") -> list:
    """
    Synchronous function to search for items on Mercari using Playwright with Firefox.
    Instead using chrome, we use Firefox to avoid detected as a bot.

    Args:
        keywords (str): The search keywords to use on Mercari.
        sort_order (str): The sorting option to use. Default is "score:desc" (recommended items).
                          Other options:
                          - "created_time:desc" (latest items)
                          - "price:asc" (lowest price)
                          - "price:desc" (highest price)
                          - "num_likes:desc" (most liked)

    Returns:
        list: A list of dictionaries containing item names, URLs, prices, descriptions, and additional details.
    """
    with sync_playwright() as playwright:
        # Launch the Firefox browser in non-headless mode
        browser = playwright.firefox.launch(headless=True)
        context = browser.new_context(locale="ja-JP")
        page = context.new_page()

        # Navigate to the Mercari Japan homepage
        page.goto("https://jp.mercari.com/")

        # Find the search bar and input the keywords
        page.get_by_role("textbox", name="検索キーワードを入力").click()
        page.get_by_role("textbox", name="検索キーワードを入力").fill(keywords)
        page.get_by_role("textbox", name="検索キーワードを入力").press("Enter")

        # Wait for the search results to load
        page.wait_for_selector("div#item-grid ul li[data-testid='item-cell'] img")

        # Apply the "On Sale" filter
        page.get_by_test_id("on-sale-condition-checkbox").check()
        page.wait_for_selector("div#item-grid ul li[data-testid='item-cell'] img")

        # Sort by the specified order
        page.get_by_label("並び替えおすすめ順新しい順価格の安い順価格の高い順いいね！順").select_option(sort_order)
        page.wait_for_selector("div#item-grid ul li[data-testid='item-cell'] img")

        # Extract the first 10 items' names and URLs
        items = []
        item_elements = page.query_selector_all("ul li[data-testid='item-cell']")[:5]
        for item in item_elements:
            # Extract the item name
            name_element = item.query_selector("span[data-testid='thumbnail-item-name']")
            name = name_element.inner_text() if name_element else "No name"

            # Extract the item URL
            link_element = item.query_selector("a[data-testid='thumbnail-link']")
            url = "https://jp.mercari.com" + link_element.get_attribute("href") if link_element else "No URL"

            # Open the item URL in a new tab and extract additional data
            item_data = {"name": name, "url": url}
            if url != "No URL":
                new_tab = context.new_page()
                new_tab.goto(url)

                try:
                    # Check if the item is from a shop (skip if "data-testid='mercari-shops-banner-icon'" is found)
                    shop_banner_element = new_tab.query_selector("div[data-testid='mercari-shops-banner-icon']")
                    if shop_banner_element:
                        print(f"Skipping shop item {name} ({url}) - Detected as Mercari Shops")
                        new_tab.close()
                        continue

                    # Wait for the parent container to be fully loaded
                    new_tab.wait_for_selector("div#item-info[data-testid='item-detail-container']", state="attached")

                    # Wait for the price element to load
                    print("Waiting for price element to load...")
                    new_tab.wait_for_selector("div[data-testid='price'] span:nth-child(2)", state="visible")
                    price_element = new_tab.query_selector("div[data-testid='price'] span:nth-child(2)") or \
                                    new_tab.query_selector("div[data-testid='product-price'] span:nth-child(2)")
                    item_data["price"] = price_element.inner_text() if price_element else "No price"

                    # Extract the description (handle multiple patterns)
                    print("Extracting description...")
                    description_element = new_tab.query_selector("pre[data-testid='description']")
                    item_data["description"] = description_element.inner_text() if description_element else "No description"

                    # Extract the picture URL
                    print("Extracting picture URL...")
                    picture_element = new_tab.query_selector("div[data-testid='carousel-item'] img")
                    item_data["picture"] = picture_element.get_attribute("src") if picture_element else "No picture"

                    # Extract additional details (handle multiple patterns)
                    print("Extracting additional details...")
                    category_element = new_tab.query_selector("div[data-testid='item-detail-category']") or \
                                       new_tab.query_selector("div[data-testid='product-detail-category']")
                    item_data["category"] = category_element.inner_text() if category_element else "No category"

                    size_element = new_tab.query_selector("span[data-testid='商品のサイズ']")
                    item_data["size"] = size_element.inner_text() if size_element else "No size"

                    condition_element = new_tab.query_selector("span[data-testid='商品の状態']")
                    item_data["condition"] = condition_element.inner_text() if condition_element else "No condition"

                    shipping_cost_element = new_tab.query_selector("span[data-testid='配送料の負担']")
                    item_data["shipping_cost"] = shipping_cost_element.inner_text() if shipping_cost_element else "No shipping cost"

                    shipping_method_element = new_tab.query_selector("span[data-testid='配送の方法']")
                    item_data["shipping_method"] = shipping_method_element.inner_text() if shipping_method_element else "No shipping method"

                    shipping_region_element = new_tab.query_selector("span[data-testid='発送元の地域']")
                    item_data["shipping_region"] = shipping_region_element.inner_text() if shipping_region_element else "No shipping region"

                    shipping_time_element = new_tab.query_selector("span[data-testid='発送までの日数']")
                    item_data["shipping_time"] = shipping_time_element.inner_text() if shipping_time_element else "No shipping time"

                    # Extract the number of likes
                    print("Extracting number of likes...")
                    like_element = new_tab.query_selector("div[data-testid='icon-heart-button'] span.merText.body__5616e150.inherit__5616e150")
                    item_data["likes"] = like_element.inner_text() if like_element else "No likes"

                    print(f"Extracted details: {item_data}")

                except Exception as e:
                    # Handle any errors during data extraction
                    item_data["price"] = "No price (Error)"
                    item_data["description"] = "No description (Error)"
                    item_data["picture"] = "No picture (Error)"
                    item_data["category"] = "No category (Error)"
                    item_data["size"] = "No size (Error)"
                    item_data["condition"] = "No condition (Error)"
                    item_data["shipping_cost"] = "No shipping cost (Error)"
                    item_data["shipping_method"] = "No shipping method (Error)"
                    item_data["shipping_region"] = "No shipping region (Error)"
                    item_data["shipping_time"] = "No shipping time (Error)"
                    item_data["likes"] = "No likes (Error)"

                # Close the tab after extracting the data
                new_tab.close()

            # Append the item details to the list
            items.append(item_data)

        # Close the browser
        context.close()
        browser.close()

        return items


# async def call_search_mercari(keywords: str, sort_order: str = "score:desc"):
#     """
#     Callable function for OpenAI tools to execute the Mercari search.

#     Args:
#         keywords (str): The search keywords to use on Mercari.
#         sort_order (str): The sorting option to use. Default is "score:desc" (recommended items).

#     Returns:
#         list: A list of dictionaries containing item names, URLs, prices, descriptions, and additional details.
#     """
#     # Run the synchronous search_mercari function in a thread
#     from asyncio import to_thread
#     items = await to_thread(search_mercari, keywords, sort_order)
#     return items


# # Example usage for testing:
# if __name__ == "__main__":
#     import asyncio

#     # Call the function with a sample keyword and sort order
#     results = asyncio.run(call_search_mercari("スノボウェア やすい", sort_order="created_time:desc"))

#     # Print the results in a readable format
#     print("Search Results:")
#     for idx, item in enumerate(results, start=1):
#         print(f"\nItem {idx}:")
#         print(f"  Name: {item['name']}")
#         print(f"  URL: {item['url']}")
#         print(f"  Price: {item['price']}")
#         print(f"  Description: {item['description']}")
#         print(f"  Picture: {item['picture']}")
#         print(f"  Category: {item['category']}")
#         print(f"  Size: {item['size']}")
#         print(f"  Condition: {item['condition']}")
#         print(f"  Shipping Cost: {item['shipping_cost']}")
#         print(f"  Shipping Method: {item['shipping_method']}")
#         print(f"  Shipping Region: {item['shipping_region']}")
#         print(f"  Shipping Time: {item['shipping_time']}")
#         print(f"  Likes: {item['likes']}")
