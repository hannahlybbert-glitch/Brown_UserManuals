# Author: Hannah Lybbert
# Created: 01/28/2026
# Updated: 01/29/2026
# Purpose: Clean county population estimates file (Git Issue #12)

import pandas as pd
import os

# Set working directory
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# Input file path
input_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "raw", "co-est2024-pop.xlsx")

# Output file path
output_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "co_est2022_pop_clean.csv")

# Read the Excel file, skipping the first 4 header rows
# Rows 0-3 contain metadata and column headers
df = pd.read_excel(input_file, header=None, skiprows=4)

# Keep only the first 3145 rows (excludes the last 6 rows which are notes)
# Row 3148 in original file = row 3144 after skipping (0-indexed)
df = df.iloc[:3145]

# Keep only columns 0 (geographic area) and 4 (2022 population)
df = df.iloc[:, [0, 4]]

# Assign column names
df.columns = ['geographic_area', '2022_pop']

# Remove leading dots from geographic_area
df['geographic_area'] = df['geographic_area'].str.lstrip('.')

# State name to abbreviation mapping
state_abbrev = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'
}

# Filter to only keep rows that contain a comma (excludes "United States" and any other non-sub-geographic rows)
df = df[df['geographic_area'].str.contains(',', na=False)]

# Split geographic_area into county and state
# If "County," "Parish," "Borough," or "Municipality," is in the name, extract text before it
# Otherwise, extract everything before the "," (handles cities, census areas, etc.)
def extract_county(geo_area):
    if ' County,' in geo_area:
        return geo_area.split(' County,')[0]
    elif ' Parish,' in geo_area:
        return geo_area.split(' Parish,')[0]
    elif ' Borough,' in geo_area:
        return geo_area.split(' Borough,')[0]
    elif ' Municipality,' in geo_area:
        return geo_area.split(' Municipality,')[0]
    else:
        return geo_area.split(',')[0].strip()

df['county_name'] = df['geographic_area'].apply(extract_county)

# Extract state name (text after ", ")
df['state_name'] = df['geographic_area'].str.split(', ').str[1]

# Map state name to abbreviation
df['state'] = df['state_name'].map(state_abbrev)

# Keep only the desired columns (county_name is the original cleaned name)
df = df[['county_name', 'state', '2022_pop']]

# Save the cleaned file
df.to_csv(output_file, index=False)

print(f"Cleaned file saved to: {output_file}")
print(f"Number of rows: {len(df)}")
print(f"Number of columns: {len(df.columns)}")
print("\nFirst few rows:")
print(df.head())
print("\nLast few rows:")
print(df.tail())
