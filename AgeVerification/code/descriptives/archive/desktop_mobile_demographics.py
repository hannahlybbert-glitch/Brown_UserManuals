# Author: Hannah Lybbert
# Created: 01/27/2026
# Purpose: Demographic descriptives

# Import libraries
import pandas as pd
import os
import matplotlib.pyplot as plt

# Set working directory
os.chdir("C:/Users/hlybbert/OneDrive - The University of Chicago/Documents/AgeVerification")

# Reconstruct desktop demographics dataframe from txt file
desktop_demos = pd.read_csv(
    "raw/desktop_demographics/US_comscore_machine_demos_202201.txt",
    sep='\t',
    header=None,
    names=['machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
            'hoh_age', 'hh_income', 'children_present', 'hh_size', 'month_id']
)

# Reconstruct person demographics dataframe from txt file
person_demos = pd.read_csv(
    "raw/desktop_demographics/US_comscore_person_demos_202201.txt",
    sep='\t',
    header=None,
    names=['person_id', 'machine_id', 'gender', 'age', 'children_present',
            'hh_income', 'hh_size', 'ethnicity_id', 'race_id', 'computer_location',
            'country', 'region', 'time_zone_bias', 'month_id']
)

# Convert person_demos age from string to integer
person_demos['age'] = pd.to_numeric(person_demos['age'], errors='coerce')

# Reconstruct mobile demographics dataframe from txt file
mobile_demos = pd.read_csv(
    "raw/mobile_demographics/US_comscore_mobile_demos_202201.txt",
    sep='\t',
    header=None,
    names=['month_id', 'platform', 'machine_id', 'age', 'gender',
            'hh_income', 'hh_size', 'children_present', 'region']
)

### HANNAH COMMENT = looks like the mobile demos are not in the right roder, fix before runnign dmeographics 

# Check the actual number of columns in mobile_demos
print(f"Number of columns in mobile_demos: {mobile_demos.shape[1]}")
print(f"\nFirst row of mobile_demos:")
print(mobile_demos.iloc[0])


# # Create overlayed histogram
# plt.figure(figsize=(10, 6))
# plt.hist(person_demos['age'].dropna(), bins=50, alpha=0.5, label='Person Demographics (Desktop)',
# edgecolor='black')
# plt.hist(mobile_demos['age'].dropna(), bins=50, alpha=0.5, label='Mobile Demographics',
# edgecolor='black')
# plt.xlabel('Age')
# plt.ylabel('Density')
# plt.title('Age Distribution: Desktop Person Demographics vs Mobile Demographics')
# plt.legend()
# plt.grid(True, alpha=0.3)
# plt.show()


# # Check the unique values and data types for age in both dataframes
# print("Person demographics age:")
# print(f"Data type: {person_demos['age'].dtype}")
# print(f"First 20 unique values: {sorted(person_demos['age'].dropna().unique())[:20]}")
# print(f"\nSample values: {person_demos['age'].head(10).tolist()}")

# print("\n" + "="*50 + "\n")

# print("Mobile demographics age:")
# print(f"Data type: {mobile_demos['age'].dtype}")
# print(f"First 20 unique values: {sorted(mobile_demos['age'].dropna().unique())[:20]}")
# print(f"\nSample values: {mobile_demos['age'].head(10).tolist()}")