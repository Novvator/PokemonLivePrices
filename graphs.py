# Generates scripts for the base_url search one by one
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import matplotlib.pyplot as plt

# Setup Selenium WebDriver (e.g., using Chrome)
def setup_driver():
    options = Options()
    options.headless = True  # Run headless (without opening a browser window)
    # driver_service = Service("path/to/chromedriver")  # Provide path to your chromedriver
    driver = webdriver.Chrome(options=options)
    return driver

# Step 1: Scrape Product Images and IDs using Selenium with wait
def scrape_product_images_and_ids(driver, page_url):
    driver.get(page_url)
    
    # Wait for the products to be rendered on the page (i.e., wait for the images to load)
    WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='lazy-image__wrapper']//img")))
    
    # Once the elements are loaded, we can scrape the product data
    product_elements = driver.find_elements(By.XPATH, "//div[@class='lazy-image__wrapper']//img")
    
    products = []
    for product in product_elements:
        src = product.get_attribute("src")
        if "/product/" in src:
            product_id = src.split("/product/")[1].split("_")[0]
            # products[product_id] = src deleted this to create list of IDs
            products.append(product_id)

    return products


# Function to fetch price data for each product ID
def fetch_price_data(product_id):
    api_url = f"https://infinite-api.tcgplayer.com/price/history/{product_id}/detailed?range=quarter"
    headers = {"Accept": "application/json"}  # Add necessary headers if required
    response = requests.get(api_url, headers=headers)
    
    # Check if the response is valid and contains the required data
    if response.status_code == 200:
        data = response.json()
        prices = []
        dates = []
        
        # Extract data from 'buckets'
        if "result" in data and data["result"]:
            buckets = data["result"][0].get("buckets", [])
            for bucket in buckets:
                prices.append(float(bucket["marketPrice"]))
                dates.append(datetime.strptime(bucket["bucketStartDate"], "%Y-%m-%d"))
        else:
            print(f"Unexpected response structure or no data available for product {product_id}.")
        return dates, prices
    else:
        print(f"Error fetching data for product {product_id}: {response.status_code}")
        return [], []

# Function to fetch the product image
def fetch_product_image(product_id):
    image_url = f"https://tcgplayer-cdn.tcgplayer.com/product/{product_id}_in_200x200.jpg"  # Construct image URL
    try:
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        return Image.open(BytesIO(image_response.content))
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image for product {product_id}: {e}")
        return None

# Function to generate the graph for a product
def generate_graph(product_id, product_image, dates, prices):
    if not dates or not prices:
        print(f"No price data available for product {product_id}. Skipping graph generation.")
        return

    # Create the graph
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot the prices
    line, = ax.plot(dates, prices, marker='o', label="Market Price")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    fig.autofmt_xdate()

    ax.set_title(f"Market Price Over Time for Product {product_id}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(True)
    ax.legend()

    # Add the product image
    if product_image:
        left, bottom, width, height = 0.1, 0.6, 0.2, 0.2  # Adjust the placement of the image
        img_ax = fig.add_axes([left, bottom, width, height], anchor='NE', zorder=1)
        img_ax.imshow(product_image)
        img_ax.axis("off")  # Hide axes for the image

    # Add hover functionality
    annot = ax.annotate(
        "", xy=(0, 0), xytext=(15, 15),
        textcoords="offset points", bbox=dict(boxstyle="round", fc="w"),
        arrowprops=dict(arrowstyle="->")
    )
    annot.set_visible(False)

    def update_annot(ind):
        """Update the annotation with the hovered point's data."""
        x, y = line.get_data()
        annot.xy = (x[ind["ind"][0]], y[ind["ind"][0]])
        text = f"Date: {x[ind['ind'][0]].strftime('%Y-%m-%d')}\nPrice: ${y[ind['ind'][0]]:.2f}"
        annot.set_text(text)

    def on_hover(event):
        """Handle hover events over the plot."""
        vis = annot.get_visible()
        if event.inaxes == ax:
            contains, ind = line.contains(event)
            if contains:
                update_annot(ind)
                annot.set_visible(True)
                fig.canvas.draw_idle()
            else:
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_hover)

    # Save and display the graph
    plt.tight_layout()
    plt.savefig(f"product_{product_id}_market_price_graph.png")
    plt.show()

# Main function to process multiple products
def main():
    base_url = "https://www.tcgplayer.com/search/pokemon/product?productLineName=pokemon&Language=English&q=etb&view=grid&page="
    pages_to_scrape = 1  # Adjust this to scrape more pages
    all_products = {}

    driver = setup_driver()

    for page in range(1, pages_to_scrape + 1):
        url = base_url + str(page)
        products = scrape_product_images_and_ids(driver, url)
        # all_products.update(products)
    product_ids = products  # Replace with actual product IDs
    for product_id in product_ids:
        print(f"Processing product ID {product_id}")
        
        # Fetch price data for the product
        dates, prices = fetch_price_data(product_id)

        # Fetch product image
        product_image = fetch_product_image(product_id)

        # Generate and display the graph
        generate_graph(product_id, product_image, dates, prices)

if __name__ == "__main__":
    main()
