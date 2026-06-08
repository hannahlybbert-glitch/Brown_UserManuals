import pandas as pd
import os

os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Load the demographic file with correct column names
df = pd.read_csv(
    'raw/desktop_demographics/US_comscore_machine_demos_202201.txt',
    sep='\t',
    header=None,
    names=['machine_id', 'country', 'region', 'time_zone_bias', 'computer_location',
            'hoh_age', 'hh_income', 'children_present', 'hh_size', 'month_id']
)



# Display first few rows
print("First few rows:")
print(df.head())

# Extract the first number from the age range (e.g., "45-54" -> 45)
df['hoh_age_numeric'] = df['hoh_age'].astype(str).str.split('-').str[0]
df['hoh_age_numeric'] = pd.to_numeric(df['hoh_age_numeric'], errors='coerce')

# Sum the age
age_sum = df['hoh_age_numeric'].sum()
print(f"\nTotal age sum: {age_sum:,.0f}")
print(f"Average age: {df['hoh_age_numeric'].mean():.2f}")
print(f"Number of records: {len(df):,}")

# Additional age statistics
print(f"\nAge statistics:")
print(df['hoh_age_numeric'].describe())