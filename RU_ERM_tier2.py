from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import random
import os
import traceback
import sys

# Initialize driver with None (to be changed later)
driver = None
wait = None
website_main = "https://ermenrich.com/"

# Create the optimized driver (loads fast, limits images)
def create_optimized_driver():
    # Use Options class to customize WebDriver
    options = Options()
    # Wait for DOM to be interactive (instead of all resources to downloaded)
    options.page_load_strategy = 'eager'
    
    # Block all images, background networking and extensions
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    options.add_argument('--disable-background-networking')
    options.add_argument('--disable-extensions')
    
    driver = webdriver.Chrome(options=options)
    
    # Longer timeout for initial load
    driver.set_page_load_timeout(60)
    
    return driver

def take_screenshot(name):
    # Create screenshot folder, name screenshot images
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")

    filename = f"screenshots/{name}_{int(time.time())}.png"
    driver.save_screenshot(filename)
    print(f"(Screenshot saved as: {filename})")
    return filename

# Step counter class to count step number automatically
class StepCounter:
    def __init__(self):
        self.step = 1
    
    def print_step(self, message):
        print(f"\n--- Step {self.step}: {message} ---")
        self.step += 1

# Container for general order data and functions
class ParentContext:
    def __init__(self):
        self.user_email = None
        self.user_phone = None

        self.sku = {
            'selected': None,
            'region': None,
            'price_class': None, # Just 1 price class here (price class 0)
            'price_class_type': 'flexible',  
            'unavailable': []   # Track unavailable SKUs
        }

        self.selected_delivery = None 

        self.selected_payment = None

        # Results summary
        self.summary = {
            'delivery_option': None,
            'payment_option': None,
            'basket_price': None,
            'order_result': None,
            'expected_fee': None,
            'order_fee': None}
    
    def get_sku_list(self, price_class):
        # Returns the SKU list for a specific price class
        return self.sku_lists['price_classes'][price_class]
    
    def get_all_skus(self):
        # Get all SKUs from both price classes
        all_skus = self.sku_lists['price_classes'][0] 
    
    def mark_sku_unavailable(self, sku):
        # Add a SKU to the unavailable list
        if sku not in self.sku['unavailable']:
            self.sku['unavailable'].append(sku)

    def get_default_delivery(self):
        for option in self.delivery_options:
            if option.get('is_default', False):
                return option
        # If no default marked, return first one
        return self.delivery_options[0] if self.delivery_options else None
    
    def get_delivery_option_by_name(self, local_name):
        for option in self.delivery_options:
            if option['local_name'] == local_name:
                return option
        return None

    def get_available_payment_options(self):
        if not self.selected_delivery:
            return self.payment_options.copy()
    
        delivery = self.selected_delivery
        compatible = delivery.get('compatible_with', {})
        allowed_payments = compatible.get('payment', [])
    
        # Also check region if set
        region = self.sku.get('region')
        allowed_regions = compatible.get('region', [])
    
        if region and allowed_regions and region not in allowed_regions:
            return []  # This delivery isn't available in this region
    
        available = [
            p for p in self.payment_options
            if p['en_name'] in allowed_payments
        ]
        return available

    def get_default_payment(self):
        available = self.get_available_payment_options()

        for option in available:
            if option.get('is_default', False):
                return option
            
        return available[0] if available else None

    def get_cash_payment(self):
        for option in self.payment_options:
            if option.get('is_cash', False):
                return option
        return None            
        
    def update_summary(self, **kwargs):
        self.summary.update(kwargs)

# Container for all order-related data
class OrderContextHU(ParentContext):
    def __init__(self):
        super().__init__()
    
        self.sku_lists = {
            'price_classes': {
                0: [83843, 84582, 84644, 84087, 82981,
                    83822,  82976, 83837, 84560, 85961]
            }
        }
     
        self.delivery_options = [
            # Moscow default = Доставка курьером, no action
            # St. Pete default = Самовывоз из магазина + confirm shop
            # Regions default = Доставка курьером СДЭК, no action

            {            
                'local_name': 'самовывоз (Санкт-Петербург)',
                'en_name': 'shop pickup (St. Petersburg)',
                'opt_id': 'ID_SHIPPING_METHOD_ID_6',
                'is_default': True,
                'compatible_with': {
                    'region': ['St. Petersburg'],
                    'payment': ['credit card', 'bank transfer', 'yandex split']
                }
                # Академическая - только предоплаченные заказы!
                },
            {
                'local_name': 'доставка курьером (сдэк)',
                'en_name': 'courier (SDEK)',
                'opt_id': 'ID_SHIPPING_METHOD_ID_8',
                'is_third_party': True,
                'compatible_with': {
                    'region': ['St. Petersburg', 'regions'],
                    # "Оплата при получении" = "cash on delivery"
                    # "Наличными курьеру" = "cash on delivery (courier)"
                    'payment': ['credit card', 'cash on delivery (courier)', 'bank transfer', 'yandex split']
                }
            },
            {
                'local_name': 'доставка курьером (Москва)',
                'en_name': 'courier (Moscow)',
                'opt_id': 'ID_SHIPPING_METHOD_ID_2',
                'is_default': True,
                'compatible_with': {
                    'region': ['Moscow'],
                    'payment': ['credit card', 'cash on delivery (courier)', 'bank transfer', 'yandex split']
                }
            },
            {
                'local_name': 'срочная доставка курьером (Москва)',
                'en_name': 'express courier (Moscow)',
                'opt_id': 'ID_SHIPPING_METHOD_ID_3',
                'compatible_with': {
                    'region': ['Moscow'],
                    'payment': ['credit card', 'cash on delivery (courier)', 'bank transfer', 'yandex split']
                }
            },
            {
                'local_name': 'самовывоз (Москва)',
                'en_name': 'shop pickup (Moscow)',
                'opt_id': 'ID_SHIPPING_METHOD_ID_5',
                'compatible_with': {
                    'region': ['Moscow'],
                    'payment': ['credit card', 'bank transfer', 'yandex split']
                }
                # Лубянка - только предоплаченные заказы!
            },
            {
                'local_name': 'самовывоз (сдэк)',
                'en_name': 'pickup (SDEK)',
                'opt_id': 'ID_SHIPPING_METHOD_ID_9',
                'is_third_party': True,
                'compatible_with': {
                    'region': ['regions'],
                    # "Оплата при получении" = "cash on delivery"
                    # "Наличными курьеру" = "cash on delivery (courier)"
                    'payment': ['credit card', 'cash on delivery', 'bank transfer', 'yandex split']
                }
            },
            {
                'local_name': 'ems',
                'en_name': 'ems',
                'opt_id': 'ID_SHIPPING_METHOD_ID_4',
                'is_third_party': True,
                'compatible_with': {
                    'region': ['regions'],
                    # "Оплата при получении" = "cash on delivery"
                    # "Наличными курьеру" = "cash on delivery (courier)"
                    # "Наложенный платеж" = "cash on delivery (ems)"
                    'payment': ['credit card', 'bank transfer', 'cash on delivery (ems)', 'yandex split']
                }
            },
        ]

        self.payment_options = [
            {
                'local_name': 'оплата онлайн (банковская карта)',
                'en_name': 'credit card',
                'opt_id': 'ID_PAY_SYSTEM_ID_11',
                'is_default': True,
                'is_third_party': True,
            },
            {
                'local_name': 'банковский перевод',
                'en_name': 'bank transfer',
                'opt_id': 'ID_PAY_SYSTEM_ID_2',
            },
            {
                'local_name': 'яндекс сплит',
                'en_name': 'yandex split',
                'opt_id': 'ID_PAY_SYSTEM_ID_15',
            },
            {   'local_name': 'наличными курьеру',
                'en_name': 'cash on delivery (courier)',
                'opt_id': 'ID_PAY_SYSTEM_ID_8',
            },
            {   'local_name': 'оплата при получении',
                'en_name': 'cash on delivery',
                'opt_id': 'ID_PAY_SYSTEM_ID_5',
            },
             {   'local_name': 'наложенный платеж',
                'en_name': 'cash on delivery (ems)',
                'opt_id': 'ID_PAY_SYSTEM_ID_9',
            }
        ]

        self.fees = {
            'shipping': {                
                'shop pickup (St. Petersburg)': {
                        'display': 'Бесплатная доставка',
                        'amount': 0
                    },

                'shop pickup (Moscow)': {
                    'display': 'Бесплатная доставка',
                    'amount': 0
                    },

                'courier (Moscow)': {
                    'display': '350 ₽',
                    'amount': 350
                    },

                'express courier (Moscow)': {
                    'display': '500 ₽',
                    'amount': 500
                    } 
            }
        }
    
    
    def get_expected_shipping_fee(self):
        if not self.selected_delivery:
            return None, None
        elif self.selected_delivery.get('is_third_party'):
            # Guard against calling before we're on the order page
            if driver is None:
                return None, None
            # Third party deliveries, will always have numbers
            try:
                fee_element = driver.find_element(By.ID, 'bx-cost-shipping').text
                fee_amount = extract_price(fee_element)
                return fee_element, fee_amount
            except:
                return None, None
        # Our deliveries, may have numbers or "Бесплатная доставка"
        else:
            delivery_name = self.selected_delivery['en_name']
            fee_data = self.fees['shipping'].get(delivery_name)
            return fee_data['display'], fee_data['amount'] if fee_data else (None, None)


# Choose random sku, return a string and int price class
def choose_sku(order):
    price_class = order.sku['price_class']
    sku_list = order.get_sku_list(price_class)
    available_skus = [
        str(sku) for sku in sku_list 
        if str(sku) not in order.sku['unavailable']
    ]
        
    if available_skus:
        selected_sku = random.choice(available_skus)
        order.sku['selected'] = selected_sku
            
        print(f"✓ Selected SKU: {selected_sku} (Price class: {price_class})")
        return selected_sku
    
    # If we get here, both classes have no available SKUs
    print("✗ WARNING: No available SKUs in either price class!")
    return None

def choose_address(order):
    # Define a list of shipping addresses
    shipping_addresses = {
    'Moscow': [
        # Maybe include zip code to check later?
        '109125 Москва Саратовская 19 строение 5', # Google/Dadata zips don't match, used Dadata
        '109028 Москва Яузский бульвар 15',
        '101000 Москва Чистопрудный бульвар 10 строение 2'
    ],
    'St. Petersburg': [
        '194017 СПб пр. Энгельса 66',
        '197101 СПб Большая Пушкарская 46 лит. А', # Google/Dadata zips don't match, used Dadata
        '191180 СПб наб. Реки Фонтанки 92'
    ],
    'regions': [
        '236004 Калининград, Аллея Смелых 25',
        '614051 Пермь Пономарева 56',
        '185031 Петрозаводск Кондопожская 8',
        '450080 Уфа Менделеева 191А',
        '364024 Грозный Лорсанова 28'# Google/Dadata zips don't match, used Dadata
    ] 
    }
    chosen_region = order.sku.get('region')
    region_lib = shipping_addresses[chosen_region]

    address = region_lib[random.choice()] 
    return(address) #returns a string

def extract_price(price_text):
    # Remove all characters except digits and the comma/dot
    # Only EU, US have dot (23.95 EU - no need to replace), the rest have comma
    clean_text = re.sub(r'[^\d]', '', price_text)
    try:
        return int(clean_text)
    except ValueError:
        return None
  
def close_cookie_popup():
    try:
        accept_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 
                "#cookie_notice_alert a.btn.btn-primary"))
        )
        accept_button.click()
        print("Cookie popup closed")
        time.sleep(1)
        return True    
     
    except Exception as e:
        print(f"✗ Error handling cookie popup: {str(e)}")
        return False

def search_for_sku(sku):
    # Find item by SKU search 
    try:
        print("Navigating to main page...")
        driver.get(website_main)
        time.sleep(3)
        
        close_cookie_popup()
        
        print("Opening search box...")
        search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".header__search")))
        search_box.click()
        time.sleep(1)
        
        print("Entering SKU...")
        search_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[data-iv-toggle='search']")))
        search_input.clear()
        search_input.send_keys(str(sku))
                
        print("Submitting search...")
        search_input.send_keys(Keys.ENTER)
        
        print("Waiting for results to load...")
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-card"))
            )
        except:
            time.sleep(5)

        # Find card SKU line, like "Product ID: 83836"
        card_sku_elem = driver.find_element(By.CSS_SELECTOR, ".product-card__article.swiper-no-swiping")
        card_sku = card_sku_elem.text[-5:]
        print(f"SKU on the product card is: {card_sku}")
        
        # Scroll to the element to take screenshot
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card_sku_elem)
        time.sleep(2)
        take_screenshot("search_results")

        if sku == card_sku:        
            print("Search completed successfully")
            return True
        else:
            print(f"✗ First found item doesn't match the search: looked for {sku}, first item is {card_sku}")
            return False
        
    except Exception as e:
        print(f"✗ Search failed: {str(e)}")
        take_screenshot("search_error")
        return False

def is_item_available(order):
    # Is only applied when sku != None
    sku = order.sku['selected']
    try:
        search_for_sku(sku)
        price_text = driver.find_element(By.CLASS_NAME, "product-card__price").text.lower()
        # Check language file for the translations: out of stock, discontinued, coming soon
        unavailable_indicators = ['нет в наличии', 'снят с производства', 'скоро в продаже']
        if any(indicator in price_text for indicator in unavailable_indicators):
            return False, price_text
        else:
            cart_button = driver.find_element(By.CSS_SELECTOR, "button[data-control-cart]")
            if cart_button.is_displayed():
                return True, "available"
            else:
                return False, "unclear"

    except Exception as e:
        return False, str(e)

def get_offer_id(sku):
    try:
        print(f"Finding offer ID for SKU: {sku}")
        
        # Find the product card container
        product_card = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".product-card.product-control.product-card_inited.product-control_inited")))
        
        # Get the offer ID from the data attributes
        offer_id = product_card.get_attribute('data-offer-id')
        
        if offer_id:
            print(f"✓ Found offer ID {offer_id}")
            return int(offer_id)      
        
    except Exception as e:
        print(f"✗ Failed to get offer ID: {str(e)}")
        take_screenshot("offer_id_error")
        return None
    
    except Exception as e:
        print(f"✗ Error finding offer ID: {str(e)}")
        return None

def add_to_cart_via_api(offer_id, quantity=1):
    # Simple API call - no UI updates attempted, relies on page refresh to update the cart
    try:
        print(f"Adding offer {offer_id} to cart via API...")
        
        script = f"""
            fetch('/rest/methods/user/basket/change', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{offerId: {offer_id}, quantity: {quantity}}})
            }})
            .then(response => response.json())
            .then(data => {{
                console.log('API response:', data);
                // Store success state for verification
                window.lastCartAdd = {{
                    success: true,
                    offerId: {offer_id},
                    timestamp: Date.now()
                }};
            }})
            .catch(error => {{
                console.error('API Error:', error);
                window.lastCartAdd = {{success: false, error: error.message}};
            }});
        """
        
        driver.execute_script(script)
        time.sleep(2) # Wait for API call

        # Verify it worked
        check_script = """
            return window.lastCartAdd || {success: false, error: 'No response'};
        """
        result = driver.execute_script(check_script)
        
        if result.get('success'):
            print(f"✓ API call successful for offer {offer_id}")
            return True
        else:
            print(f"✗ API call failed: {result.get('error')}")
            return False
                
    except Exception as e:
        print(f"Failed to add to cart via API: {str(e)}")
        take_screenshot("api_add_error")
        return False 

def navigate_to_cart_directly():
    # Navigate to the cart page directly by URL
    try:
        cart_url = website_main + "basket/"
        print(f"Navigating to cart URL: {cart_url}")
        
        driver.get(cart_url)
        time.sleep(3)
        
        # Check if we're on a cart page
        current_url = driver.current_url.lower()
        if "basket" in current_url:
            print("✓ Successfully navigated to cart page")
            return True
        else:
            print(f"✗ Not on cart page. Current URL: {driver.current_url}")
            return False
        
    except Exception as e:
        print(f"✗ Failed to navigate to cart: {str(e)}")
        take_screenshot("cart_navigation_error")
        return False

def check_cart_contents(sku, expected_quantity=1):
    # Verify our item is in the basket
    cart_items = driver.find_elements(By.CSS_SELECTOR, 
        "div[class*='cart-list__item'][id^='basket-basket_item_']")
    total_qty = 0
    found = False
    
    for cart_item in cart_items:  # cart_item is the whole DIV for a basket item
        if str(sku) in cart_item.text:
            found = True
            # Get quantity directly in element counter
            qty_input = cart_item.find_element(By.CLASS_NAME, "counter__input")
            qty = int(qty_input.get_attribute('value'))
            total_qty += qty
            print(f"✓ Found SKU {sku}, quantity: {qty}")
    
    if not found:
        print(f"✗ SKU {sku} not found")
        return False
    
    print(f"Total quantity: {total_qty}, Expected: {expected_quantity}")
    return total_qty == expected_quantity

def get_total_price_basket(order):
    # Extract the total price from the Cart price block
    try:
        price_text = driver.find_element(By.CLASS_NAME, 'cart-panel__result-price').text
        price = extract_price(price_text)
        if price is not None:
            order.summary['basket_price'] = price
            return price

        print("✗ Could not find total price on page")
        return None
        
    except Exception as e:
        print(f"✗ Error extracting price: {str(e)}")
        return None

def proceed_to_checkout():
    # Click the checkout button, verify Basket > Order page
    try:
        checkout_button = driver.find_element(By.CSS_SELECTOR, ".btn.btn-primary.text-uppercase.w-100.fs-18.fs-xxl-24")
        if checkout_button and checkout_button.is_displayed():
            print(f"Found checkout button")
                                
        if not checkout_button:
            raise Exception("✗ Could not find checkout button")
        
        print("Clicking checkout button...")
        checkout_button.click()
        
        # Wait for the order page to load
        print("Waiting for order page to load...")
        WebDriverWait(driver, 5).until(
            EC.url_contains("order")
        )
        
        # Verify we're on the order page
        current_url = driver.current_url.lower()
        if "order" in current_url:
            print(f"✓ Successfully navigated to order page: {driver.current_url}")
            return True
        else:
            print(f"✗ Not on order page. Current URL: {driver.current_url}")
            take_screenshot("not_on_order_page")
            return False
        
    except Exception as e:
        print(f"Failed to proceed to checkout: {str(e)}")
        take_screenshot("checkout_error")
        return False

def _select_pickup_location(order):
    # Handle ALL pickup types: Moscow shop, St. Pete shop, SDEK pickup points.
    # Picks a random location, avoiding pre-pay-only shops (text-danger warning).
    try:
        # Wait for the pickup list to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "delivery-map__list"))
        )
        time.sleep(0.5)
        
        # Get all pickup items
        all_items = driver.find_elements(By.CLASS_NAME, "delivery-map__item")
        
        if not all_items:
            print("✗ No pickup locations found")
            return False
        
        # Filter out pre-pay-only locations (they have text-danger warning)
        usable_items = []
        for item in all_items:
            danger_warnings = item.find_elements(By.CLASS_NAME, "text-danger")
            if not danger_warnings:
                usable_items.append(item)
        
        if not usable_items:
            print("✗ All locations are pre-pay only!")
            take_screenshot("all_prepay_only")
            return False
        
        print(f"Found {len(usable_items)} usable locations (filtered out {len(all_items) - len(usable_items)} pre-pay only)")
        
        # Pick a random location
        chosen = random.choice(usable_items)
        
        # Get the location name for logging
        title_elem = chosen.find_element(By.CLASS_NAME, "delivery-map__title")
        location_name = title_elem.text.split("\n")[0][:80]  # First line, truncated
        print(f"Selected: {location_name}")
        
        # Find and click the "Заберу здесь" button
        pickup_button = chosen.find_element(By.CSS_SELECTOR, "button[data-set-shop]")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pickup_button)
        time.sleep(0.3)
        pickup_button.click()
        time.sleep(1)
        
        print(f"✓ Pickup location confirmed")
        return True
        
    except Exception as e:
        print(f"✗ Failed to select pickup location: {str(e)}")
        traceback.print_exc()
        take_screenshot("pickup_selection_error")
        return False
    
def click_delivery_option(order):
    try:
        delivery = order.selected_delivery
        delivery_name = delivery['local_name']
        delivery_en = delivery['en_name']
        delivery_id = delivery['opt_id']
        
        # Step 1: Click the delivery radio/label (regardless of whether it's default)
        # This is safe — clicking an already-selected radio is a no-op
        try:
            delivery_label = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f"label[for='{delivery_id}']"))
            )
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", delivery_label
            )
            time.sleep(0.3)
            delivery_label.click()
            time.sleep(0.5)
            print(f"Selected delivery: {delivery_name}")
        except Exception as e:
            print(f"✗ Failed to click delivery: {str(e)}")
            return False
        
        # Step 2: Handle sub-actions based on delivery type
        if 'shop pickup' in delivery_en:
            return _select_shop_pickup_location(order)
        elif 'pickup (SDEK)' in delivery_en:
            return _select_sdek_pickup_point(order)
        # courier, express courier, EMS — no sub-action needed
        
        return True
        
    except Exception as e:
        print(f"✗ Error in delivery selection: {str(e)}")
        take_screenshot("delivery_option_error")
        return False

def click_payment_option(order):
    try:
        selected = order.selected_payment

        selected_name = selected['local_name']
        selected_id = selected['opt_id']

        # Get default payment from order context
        default = order.get_default_payment()
        default_name = default['local_name'] if default else None
        
        # Only interact with UI if not default
        if selected_name != default_name:
            try:
                # Find and click the payment option label
                payment_label = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 
                        f"label[for='{selected_id}']"))
                )
                print("Found payment label, attempting to click...")
                
                # Scroll to the label
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                    payment_label
                )
                time.sleep(0.5)
                payment_label.click()
                time.sleep(1)
                
                print(f"✓ Option clicked: {selected_name}")
                return True
                
            except Exception as e:
                print(f"✗ Failed to click payment option {selected_name}: {str(e)}")
                return False
        else:
            print(f"Using default payment option ({default_name}), no action needed")
            return True
            
    except Exception as e:
        print(f"✗ Error when clicking the payment option: {str(e)}")
        take_screenshot("payment_option_error")
        return False     
                                                                                                    
def fill_order_form(user_email, test_phone):
    try:
        ship_to = choose_address() #is a dictionary
        country_name = ship_to['country']
        city_name = ship_to['city']
        print(f"Chosen address in: {country_name}, {city_name}")
        
        # Wait for the form to be present
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "bx-input-order-EMAIL"))
        )        
        print("Form found, starting to fill fields...")
        
        # Contact information
        print("Filling contact information...")
        
        # Email field
        try:
            email_field = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "bx-input-order-EMAIL"))
            )
            email_field.clear()
            email_field.send_keys(user_email)
            print("Email field filled")
        except Exception as e:
            print(f"✗ Error with email field: {str(e)}")
            take_screenshot("email_field_error")
            return False
        
        # Phone field
        try:
            phone_field = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "bx-input-order-PHONE"))
            )
            phone_field.clear()
            phone_field.send_keys(test_phone)
            print("Phone field filled")
        except Exception as e:
            print(f"✗ Error with phone field: {str(e)}")
            take_screenshot("phone_field_error")
            return False
        
        # Name field
        try:
            name_field = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "bx-input-order-FIO_SHIP"))
            )
            name_field.clear()
            name_field.send_keys("Alena Auto Test")
            print("Name field filled")
        except Exception as e:
            print(f"✗ Error with name field: {str(e)}")
            take_screenshot("name_field_error")
            return False
        
        # Order comment
        try:
            comment_field = driver.find_element(By.ID, "bx-input-order-USER_DESCRIPTION")
            driver.execute_script('arguments[0].value = "Alena Auto Test\\nThis order was made by Alyona\'s helpful minions";', comment_field)
            print("Comment field filled")
        
        except Exception as e:
            print(f"✗ Error with comment field: {str(e)}")
            take_screenshot("comment_field_error")
        
        # Shipping address
        print("Filling shipping address...")
        
        # Country field (a dropdown with typeahead)
        try:
            country_field = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "bx-input-order-COUNTRY_SHIPPING-ts-control"))
            )
            country_field.click()
            time.sleep(0.5)
            country_field.clear()
            country_field.send_keys(country_name)
            time.sleep(1)
            country_field.send_keys(Keys.ENTER)
            time.sleep(1)
            print("Country selected")
            
        except Exception as e:
            print(f"✗ Error with country field: {str(e)}")
            take_screenshot("country_field_error")
            return False
        
        # City field 
        try:
            # Wait for the whole order form container to be fully rendered
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "CART-SIDEBAR-TARGET"))
            )
            time.sleep(1)  # Small buffer for JS layout calculations
    
            # Now wait for city field specifically, with retry
            city_field = None
            for attempt in range(3):
                try:
                    city_field = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "bx-input-order-CITY_SHIP"))
                    )
            
                    # Scroll into view
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", 
                        city_field
                    )
                    time.sleep(0.3)
            
                    city_field.click()
                    break  # Success!
            
                except Exception as click_error:
                    print(f"Attempt {attempt + 1}/3 failed: {str(click_error)[:100]}")
                    time.sleep(2)
    
            if city_field is None:
                raise Exception("Failed to click city field after 3 attempts")
    
            city_field.clear()
            city_field.send_keys(city_name)
            print("City field filled")
    
            city_field.send_keys(Keys.TAB)
            time.sleep(0.5)
    
        except Exception as e:
            print(f"✗ Error with city field: {str(e)}")
            take_screenshot("city_field_error")
            return False
        
        # Address field
        try:
            address_field = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "bx-input-order-ADDRESS_SHIP"))
            )
            
            # Click to ensure focus
            address_field.click()
            time.sleep(0.5)
            
            address_field.clear()
            address_field.send_keys(ship_to['address'])
            print("Address field filled")
            
            # Press Tab to move to next field
            address_field.send_keys(Keys.TAB)
            time.sleep(0.5)
            
        except Exception as e:
            print(f"✗ Error with address field: {str(e)}")
            take_screenshot("address_field_error")
            return False
        
        # Postal code field
        try:
            postal_code_field = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "bx-input-order-ZIP_SHIP"))
            )
            
            # Click to ensure focus
            postal_code_field.click()
            time.sleep(0.5)
            
            postal_code_field.clear()
            postal_code_field.send_keys(ship_to['postal_code'])
            print("Postal code field filled")
            
        except Exception as e:
            print(f"✗ Error with postal code field: {str(e)}")
            take_screenshot("postal_code_field_error")
            return False
        
        # Billing address is the same as shipping (default tick remains)
        print("Billing address remains same as shipping (default)")
        
        print("✓ Order form filled successfully")
        return True 
        
    except Exception as e:
        print(f"Error filling order form: {str(e)}")
        take_screenshot("order_form_error")
        return False

def verify_order_fee(order):
    try:
        print("Verifying order fees...")
        time.sleep(2)

        # Get actual fee from page
        fee_element = wait.until(
            EC.presence_of_element_located((By.ID, "bx-cost-shipping"))
        )    
        actual_fee_text = fee_element.text
        print(f"Actual fee on page: '{actual_fee_text}'")

        expected_display, expected_amount = order.get_expected_shipping_fee()
        order.summary['expected_fee'] = expected_display

        if actual_fee_text == 'Ingyenes kiszállítás':
            actual_fee = 0
        else:
            actual_fee = extract_price(actual_fee_text)
        
        if actual_fee == expected_amount:
            print(f"✓ Fee verified: {actual_fee} Ft")
            return True, actual_fee
        else:
            print(f"✗ Fee mismatch: Expected '{expected_display}', got '{actual_fee}'")
            return False, actual_fee
                
    except Exception as e:
        print(f"✗ Error verifying order fees: {str(e)}")
        take_screenshot("fee_verification_error")
        return False, "Error"

def place_order():
    # Finalize the order by clicking the checkout button on the order form
    try:
        print("Placing final order...")
        
        take_screenshot("before_final_order")
        
        # Find and click the checkout button
        checkout_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "submit"))
        )
        print(f"Found checkout button")
        
        # Scroll to button
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkout_button)
        time.sleep(1)
        checkout_button.click()
        return True
        
    except Exception as e:
        print(f"✗ Error in final order submission: {str(e)}")
        take_screenshot("final_order_error")
        return False
    
def get_order_number():
    # Get the order number from the URL of the confirmation page
    # URL is like: https://levenhuk.com/order/?ORDER_ID=T-B2C-US-41574
    try:
        current_url = driver.current_url
        if "ORDER_ID=" in current_url:
            # Slicing different number of characters for test ("T-") and regular orders
            # Will need to edit if > 99,999 orders
            if "T-" in current_url:
                order_num = current_url[-13:]
            else:
                order_num = current_url[-11:]
            print(f"✓ Order confirmed! Order number: {order_num}")
            return order_num
                
        else:
            print(f"✗ Order number is not in current url")
            return False
        
    except Exception as e:
        print(f"✗ Error in final order submission: {str(e)}")
        take_screenshot("final_order_error")
        return False

def generate_test_plan(order):
    # Pick a region randomly and filter deliveries by it
    # Or include region as a dimension in your generate_test_plan
    third_party_deliveries = [
        d for d in order.delivery_options
        if d.get('is_third_party', False)
    ]

    third_party_payments = [
        p for p in order.payment_options
        if p.get('is_third_party', False)
    ]

    plan = []
    uncovered_payments = set(p['en_name'] for p in third_party_payments)

    # Pass 1: coverage-optimized (greedy by delivery)
    for delivery in third_party_deliveries:
        order.selected_delivery = delivery
        compatible_payments = order.get_available_payment_options()
        chosen_payment = None

        # Case 1: We have third-party payments to cover
        if third_party_payments:
            compatible_third_party = [
                p for p in compatible_payments 
                if p['en_name'] in uncovered_payments
            ]

            if compatible_third_party:
                chosen_payment = random.choice(compatible_third_party)
                uncovered_payments.discard(chosen_payment['en_name'])
            else:
                # All payments covered, fallback to any compatible third-party
                compatible_third_party = [
                    p for p in compatible_payments 
                    if p in third_party_payments
                ]
                if compatible_third_party:
                    chosen_payment = random.choice(compatible_third_party)
    
        # Case 2: Only third-party deliveries exist, no third-party payments
        elif third_party_deliveries:
            if compatible_payments:
                chosen_payment = random.choice(compatible_payments)
        
        if chosen_payment:
            price_class = determine_price_class(chosen_payment)
            plan.append({
                'delivery': delivery,
                'payment': chosen_payment,
                'price_class': price_class
            })
    
    # Pass 2: handle any remaining uncovered payments
    # (when there are more payments than deliveries can cover in one pass)
    if uncovered_payments:
        print(f"Payments still uncovered: {uncovered_payments}")
        
        for payment_name in uncovered_payments:
            # Find the payment object
            payment = next(p for p in third_party_payments if p['en_name'] == payment_name)
            
            # Find a compatible third-party delivery
            compatible_deliveries = [
                d for d in third_party_deliveries
                if d['local_name'] in payment.get('compatible_with', {}).get('delivery', [])
            ]
            
            if compatible_deliveries:
                delivery = random.choice(compatible_deliveries)
                price_class = determine_price_class(payment)
                plan.append({
                    'delivery': delivery,
                    'payment': payment,
                    'price_class': price_class
                })
            else:
                print(f"✗ Warning: No compatible delivery for {payment_name}")
    
    print(f'Generated test plan with {len(plan)} combo(s)')
    return plan

def execute_single_order(order):
    global driver, wait
    user_email = order.user_email
    test_phone = order.user_phone
    
    try:
        # Initialize step counter
        step_counter = StepCounter()
        print("---------------LOGS FOR NERDS---------------")
        
        print(f'Chosen delivery: {order.selected_delivery['local_name']}')
        print(f'Chosen payment: {order.selected_payment['local_name']}')

        print("\nLaunching browser...")
        driver = create_optimized_driver()
        driver.maximize_window()
        wait = WebDriverWait(driver, 20)

        while True:
            # Only choose the skus that are NOT in unavailable_items
            my_sku = choose_sku(order)
            total_skus = order.get_all_skus()
            if my_sku != None:
                print(f"Chosen SKU: {str(my_sku)}")

                step_counter.print_step("Searching for SKU")
                # Avaialability check already includes search_for_sku
                available, status = is_item_available(order)
    
                if available:
                    print(f"✓ SKU {my_sku} is available")
                    break
                # If item is NOT available:
                else:
                    if len(order.sku['unavailable']) < len(total_skus): 
                        print(f"✗ SKU {my_sku} not available: {status}")
                        order.sku['unavailable'].append(str(my_sku))
                        time.sleep(1)  # Small delay before retry

            # If choose_sku() returns None, meaning all items are unavailable
            else:
                print("✗ All items are UNAVAILABLE")
                print("Closing the browser")
                driver.quit()
                sys.exit()
                #return?

        order.sku['selected'] = my_sku
        
        step_counter.print_step("Getting offer ID")
        offer_id = get_offer_id(my_sku)

        if offer_id:
            step_counter.print_step("Adding to cart")
                
            if add_to_cart_via_api(offer_id, 1):
                print("Refreshing page to synchronize UI")
                driver.refresh()
                time.sleep(1)
                step_counter.print_step("Navigating to cart")

                if navigate_to_cart_directly():
                    step_counter.print_step("Checking cart contents")
                    if check_cart_contents(my_sku):
                        step_counter.print_step("Getting cart total price")
                        basket_price = get_total_price_basket(order)

                        if basket_price is not None:
                            print(f"Cart total price: {basket_price}")
                                
                            step_counter.print_step("Proceeding to checkout")
                            take_screenshot("basket_before_checkout")
                                
                            if proceed_to_checkout():
                                step_counter.print_step("Filling order form")                                
                                fill_form_success = fill_order_form(user_email, test_phone)
                                
                                if fill_form_success:
                                    step_counter.print_step("Clicking delivery option")
                                    delivery_success = click_delivery_option(order)
                                    if delivery_success:
                                        order.summary['delivery_option'] = order.selected_delivery['local_name']
                                    
                                    step_counter.print_step("Clicking payment option")
                                    payment_success = click_payment_option(order)
                                    if payment_success:
                                        order.summary['payment_option'] = order.selected_payment['local_name']
                                  
                                    time.sleep(2)
                                    step_counter.print_step("Verifying delivery and payment fees...")
                                    fee_success, fee_display = verify_order_fee(order)
                                    if fee_success:
                                        order.summary['order_fee'] = fee_display
                                            
                                    step_counter.print_step("Placing order")
                                    order_result = place_order()

                                    if order_result:
                                        print("✓ Order successfully placed!")
                                        time.sleep(3)
                                        step_counter.print_step("Getting the order number")
                                        test_order_num = get_order_number()

                                    else:
                                        print("✗ Failed to place order")                                                                                 
                                else:
                                    print("✗ Failed to fill order form") 
                            else:
                                print("\n✗ Failed to proceed to checkout")
                        else:
                            print("\n✗ Could not extract price from cart page")
                    else:
                        print("\n✗ Item was added but not found in cart")
                else:
                    print("\n✗ Failed to navigate to cart")
            else:
                print("\n✗ Failed to add item to cart via API")
        else:
            print("\n✗ Could not find offer ID for the product")
        
        print("\nProcess completed. Browser will close in 10 seconds.")

        print("----------ORDER INFO----------")
        if order_result:
            print(f"Order number: {test_order_num}") # Will return False in case of error
        else:
            print("Order number: order wasn't placed")
        print(f"Chosen SKU: {order.sku['selected']}")
        print(f"Item price: {order.summary['basket_price']} Ft")
        print(f"Delivery option: {order.summary['delivery_option']}")
        print(f"Payment option: {order.summary['payment_option']}")


        # Shipping fees match check
        if fee_success:
            print(f"Order fee (shipping + payment): ✓ As expected, {order.summary['order_fee']} Ft")
        else:
            print(f"✗ Shipping fees don't match: expected {order.summary['expected_fee']}, got {order.summary['order_fee']}")
        
        print("----------END----------")
        time.sleep(10)
        
    except Exception as e:
        print(f"\n✗ Script failed with error: {str(e)}")
        take_screenshot("main_script_error")          
   
    finally:
        driver.quit()

def run_test_plan(order, emails, order_counter):
    plan = generate_test_plan(order)
    c = 1
    email_switches = 0
    local_counter = order_counter  # Continuation of brand-wide count
   
    for combo in plan:
        # Check if we need to switch email mid-script
        if local_counter > 0 and local_counter % 5 == 0:
            email_switches += 1
            if email_switches < len(emails):
                order.user_email = emails[email_switches]
                print(f"Switched to email: {order.user_email}")
            else:
                print("✗ Out of emails! Cannot place more orders.")
                break

        order.selected_delivery = combo['delivery']
        order.selected_payment = combo['payment']
        order.sku['price_class'] = combo['price_class']

        print(f'COMBO {c}: {order.selected_delivery['local_name']} + {order.selected_payment['local_name']} + Price class {order.sku['price_class']}')
        execute_single_order(order)
        c += 1
        local_counter += 1
    
    orders_made = c - 1  # Actual orders placed
    # Return how many emails were used (0-indexed)
    return orders_made, email_switches

def main_hu_erm(email, phone, emails=None, order_counter=0):
    global driver, wait
    
    if emails is None:
        emails = [email]  # Backward compatibility
    
    order = OrderContextHU()
    order.user_email = email
    order.user_phone = phone
    
    orders_made, email_index = run_test_plan(order, emails, order_counter)
    return orders_made, email_index

if __name__ == "__main__":
    main_hu_erm()

