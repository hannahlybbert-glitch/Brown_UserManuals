# Author: Hannah Lybbert
# Created: 01/28/2026
# Updated: 01/29/2026
# Purpose: Clean Nielsen ZIP to DMA file (Git Issue #12)

import pandas as pd
import os

# Set working directory - comment out for portability
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")

# Get the project root directory (3 levels up from this file)
file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# Input file path
input_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "raw", "Zip to DMA 2023.XLS")

# Output file path
output_file = os.path.join(project_root, "data", "ProcessAuxiliary", "DMA_County", "ZIP_to_DMA_clean.csv")

# Read the Excel file from the 'ZIP by DMA' sheet
# Skip the first 2 rows (report period info), then skip the header row (row with column names)
df = pd.read_excel(input_file, sheet_name='ZIP by DMA', skiprows=3)

# Drop the last 2 columns (they are empty/NaN)
df = df.iloc[:, :12]

# Assign column names
column_names = [
    'ZIP_code',
    'DMA_code',
    'DMA_name',
    'multi_county',
    'state_code',
    'county_code',
    'state',
    'county',
    'county_size',
    'territory',
    'DMA_rank',
    'metro'
]

df.columns = column_names

# Save the cleaned file
df.to_csv(output_file, index=False)

print(f"Cleaned file saved to: {output_file}")
print(f"Number of rows: {len(df)}")
print(f"Number of columns: {len(df.columns)}")
print("\nFirst few rows:")
print(df.head())
