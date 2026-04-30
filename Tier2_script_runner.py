# Russian websites
#import RU ERM
#import RU LVH
# EU Levenhuks
import BG_LVH_tier2 as bg_lvh
import EU_LVH_tier2 as eu_lvh
import HU_LVH_tier2 as hu_lvh
import PL_LVH_tier2 as pl_lvh
import CZ_ERM_tier2 as cz_erm
import HU_ERM_tier2 as hu_erm
import IT_ERM_tier2 as it_erm
import PL_ERM_tier2 as pl_erm
import random

script_modules = {
    'levenhuk': {
        'BG_LVH': bg_lvh,
        'EU_LVH': eu_lvh,
        'HU_LVH': hu_lvh,
        'PL_LVH': pl_lvh
    },
    'ermenrich': {
        'CZ_ERM': cz_erm,
        'HU_ERM': hu_erm,
        'IT_ERM': it_erm,
        'PL_ERM': pl_erm
    }
}

script_modules = {
    'ermenrich': {
        'CZ_ERM': cz_erm
    }
}

# Max orders per brand (with buffer for IT's variability)
num_orders_per_brand = {
    'levenhuk': 6,    # BG-1, EU-2, HU-1, PL-2
    'ermenrich': 8    # CZ-2, HU-1, IT-3(max), PL-2
}

# Collect all emails upfront (2 per brand since max is 8, and 8/5 → 2)
all_emails = {}
for brand, max_orders in num_orders_per_brand.items():
    emails_needed = (max_orders + 4) // 5  # Ceiling division
    brand_emails = []
    print(f"\n--- {brand.upper()} ---")
    for i in range(emails_needed):
        email = input(f"Enter email {i+1} for {brand}: ")
        brand_emails.append(email)
    all_emails[brand] = brand_emails
    print(all_emails)

test_phone = "+79444444444"

# Run each brand separately
for brand, modules in script_modules.items():
    emails = all_emails[brand]
    order_counter = 0  # Count orders made so far in this brand
    email_index = 0
    
    for script_name, module in modules.items():
        # Pass ALL remaining emails to the script, plus the starting index
        current_email = emails[email_index]
        remaining_emails = emails[email_index:]  # The email pool from this point
        
        main_function = getattr(module, f"main_{script_name.lower()}")
        
        print(f"\n{'='*60}")
        print(f"Running {script_name} with email: {current_email}")
        print(f"Backup emails available: {len(remaining_emails)-1}")
        print(f"{'='*60}")
        
        orders_made, email_index = main_function(current_email, test_phone, remaining_emails, order_counter)
        order_counter += orders_made
        
        # Check if we need to switch email BEFORE the next script
        if order_counter >= 5 and email_index + 1 < len(emails):
            email_index += 1
            print(f"Switching to next email: {emails[email_index]}")
