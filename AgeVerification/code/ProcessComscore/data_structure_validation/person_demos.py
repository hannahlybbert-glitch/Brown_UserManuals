import pandas as pd
import os

os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Load the person demographic file with correct column names
df = pd.read_csv(
    'raw/desktop_demographics/US_comscore_person_demos_202201.txt',
    sep='\t',
    header=None,
    names=['person_id', 'machine_id', 'gender', 'age', 'children_present', 'hh_income',
            'hh_size', 'ethnicity_id', 'race_id', 'computer_location', 'country', 'region', 'time_zone_bias',
'month_id']
)

# Display first few rows
print("First few rows:")
print(df.head())
print(f"\nSample age values:")
print(df['age'].head(10))

# Convert age to numeric (in case it's stored as string)
df['age'] = pd.to_numeric(df['age'], errors='coerce')

# Sum the age
age_sum = df['age'].sum()
print(f"\nTotal age sum: {age_sum:,.0f}")
print(f"Average age: {df['age'].mean():.2f}")
print(f"Number of records: {len(df):,}")
print(f"Number of non-null ages: {df['age'].notna().sum():,}")

# Additional age statistics
print(f"\nAge statistics:")
print(df['age'].describe())