# Russian websites
import RU_ERM_tier2 as ru_erm
import RU_LVH_tier2 as ru_lvh


script_modules = {
    'ru_websites': {
        'RU_LVH': ru_lvh
    }
}


# Max orders per brand (with buffer for IT's variability)
num_orders_per_brand = {
    'ru_websites': 3    # RU - 3 
}

# Collect all emails upfront (2 per brand since max is 8, and 8/5 > 1)
all_emails = {}
for brand, max_orders in num_orders_per_brand.items():
    emails_needed = (max_orders + 4) // 5  # Ceiling division
    brand_emails = []
    print(f"\n--- {brand.upper()} ---")
    for i in range(emails_needed):
        email = input(f"Enter email {i+1} for {brand}: ")
        brand_emails.append(email)
    all_emails[brand] = brand_emails

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

        print(test_phone)
        orders_made, new_email_index = main_function(current_email, test_phone, remaining_emails, order_counter)
        order_counter += orders_made
        
        # Update email_index from what the script tells us
        email_index += new_email_index  # Add the relative index change
        
        print(f"Orders so far for {brand}: {order_counter}, Email index: {email_index}")


#File "C:\Users\astavrova\Desktop\Алена (врем.)\1 - GitHub\Tier_2\RU_LVH_tier2.py", line 1628, in run_test_plan
    #print(f'COMBO {c}: {order.selected_delivery['local_name']} + {order.selected_payment['local_name']}')
#TypeError: 'NoneType' object is not subscriptable