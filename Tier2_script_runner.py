# Russian websites
#import RU ERM
#import RU LVH
# EU Levenhuks
import BG_LVH_tier2 as bg_lvh
import EU_LVH_tier2 as eu_lvh
import HU_LVH_tier2 as hu_lvh
import PL_LVH_tier2 as pl_lvh
# EU Ermenrichs
import CZ_ERM_tier2 as cz_erm
import HU_ERM_tier2 as hu_erm
import IT_ERM_tier2 as it_erm
import PL_ERM_tier2 as pl_erm

import random

script_modules = {
    'BG_LVH': bg_lvh,
    'EU_LVH': eu_lvh,
    'HU_LVH': hu_lvh,
    'PL_LVH': pl_lvh, 
    'CZ_ERM': cz_erm,
    'HU_ERM': hu_erm,
    'IT_ERM': it_erm,
    'PL_ERM': pl_erm
    }

script_modules = {
    'IT_ERM': it_erm
    }

MAX_ORDERS_PER_BRAND = {
    'Levenhuk': 6,  # BG - 1, EU - 2, HU - 1, PL - 2 
    'Ermenrich': 7 # CZ - 2, HU - 1, IT - 2, PL - 2
}

def collect_emails(max_orders):
    # Ask for all needed emails upfront
    emails_needed = (max_orders + 4) // 5  # Ceiling division
    emails = []
    
    for i in range(emails_needed):
        email = input(f"Enter email {i+1}: ")
        emails.append(email)
    return emails

brand = 'Ermenrich'  # Make this automatic later ###
max_orders = MAX_ORDERS_PER_BRAND[brand]
emails = collect_emails(max_orders)

# Initialize test data
test_phone = "+79444444444"
order_counter = 0
email_index = 0

for script in script_modules:
    module = script_modules[script]
    main_function = getattr(module, f"main_{script.lower()}")
    current_email = emails[email_index]
    
    print(f"\n{'='*60}")
    print(f"Running {script} with email: {current_email}")
    print(f"{'='*60}")

    # Run the script and get how many orders it made
    orders_made = main_function(current_email, test_phone)
    order_counter += orders_made

    # Check if next script needs a different email
    if order_counter >= 5:
        email_index = order_counter // 5
        if email_index >= len(emails):
            # Safety: ask for another email if we somehow exceeded predictions
            new_email = input(f"Unexpected! Need additional email (orders so far: {order_counter}): ")
            emails.append(new_email)
   
