# Russian websites
#import RU ERM
#import RU LVH
# EU Levenhuks
# import BG_LVH_tier_2 as bg_lvh
# import EU_LVH_tier_2 as eu_lvh
import HU_LVH_tier2 as hu_lvh
# import PL_LVH_tier_2 as pl_lvh
# EU Ermenrichs
# import CZ_ERM_tier_2 as cz_erm
# import HU_ERM_tier_2 as hu_erm
# import IT_ERM_tier_2 as it_erm
# import PL_ERM_tier_2 as pl_erm

import random

script_modules = {
     'HU_LVH': hu_lvh
    }


# Initialize test data
test_email = input("Enter email: ")
# test_email_2 = input("Enter second email: ")
test_phone = "+79444444444"

print(f"\n{'='*60}")
print(f"Running HU script with email: {test_email}")
print(f"{'='*60}")
hu_lvh.main_hu(test_email, test_phone)
   
