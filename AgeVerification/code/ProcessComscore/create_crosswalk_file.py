# Author: Hannah Lybbert
# Created: 01/21/2026
# Purpose: Creating crosswalk file (top_web_ID and building lookup file)

'''
Input: raw/Lookups/traffic_category_map/comscore_category_map_[YYYYMM].txt
Output: "data/ProcessComscore/intermediate/[month_id]/crosswalk.parquet" (columns: pattern_id, top_web_id)

  How to use in command line: python create_crosswalk_file.py YYYYMM
        Ex: python create_crosswalk_file.py 202201
'''


# Imports
import pandas as pd
import numpy as np
import os
import sys

# Local testing only - comment out when running from terminal
# os.chdir(r"C:\Users\hlybbert\OneDrive - The University of Chicago\Documents\AgeVerification")


# ----- LOAD DATA ----- #
# Get YYYYMM from command line argument
if len(sys.argv) != 2:
    print("Usage: python create_crosswalk_file.py YYYYMM")
    print("Example: python create_crosswalk_file.py 202201")
    sys.exit(1)

yyyymm = sys.argv[1]

# Construct input path using YYYYMM (try .gz first, then .txt)
input_path_gz = f'raw/Lookups/traffic_category_map/comscore_category_map_{yyyymm}.txt.gz'
input_path_txt = f'raw/Lookups/traffic_category_map/comscore_category_map_{yyyymm}.txt'

if os.path.exists(input_path_gz):
    input_path = input_path_gz
    compression = 'gzip'
elif os.path.exists(input_path_txt):
    input_path = input_path_txt
    compression = None
else:
    print(f"ERROR: Category map file not found for {yyyymm}")
    print(f"  Tried: {input_path_gz}")
    print(f"  Tried: {input_path_txt}")
    sys.exit(1)

# Reconstruct dataframe from txt file
df = pd.read_csv(input_path, sep='\t', header=None,
                 names=['month_id', 'pattern_id', 'web_id', 'web_name', 'level_name', 'level_id',
             'parent_id', 'subcategory', 'category', 'Magazine', 'Streaming_Video', 'Blog',
             'Streaming_Audio', 'Cable_Broadcast_TV', 'Radio', 'Newspaper'],
                 compression=compression)


# Extract month_id from the data (should be consistent across all rows)
month_id = df['month_id'].iloc[0]

# Construct output path using month_id
output_dir = f"data/ProcessComscore/intermediate/{month_id}"
output_path = f"{output_dir}/crosswalk.parquet"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)


# ----- CREATE top_web_id ----- #
    # must traverse up the hierarchy chain until we reach the root parent_id == 1

# 1. Create a lookup dictionary: web_id --> parent_id
parent_lookup = df[['web_id', 'parent_id']].drop_duplicates().set_index('web_id')['parent_id'].to_dict()

def find_root_web_id(web_id):
    # Traverse up the parent chain until we find the root (parent_id == 1)
    visited = set() # prevent infinite loops
    current_id = web_id

    while current_id in parent_lookup and current_id not in visited:
        parent = parent_lookup[current_id]
        if parent == 1:
            return current_id # this is the root
        visited.add(current_id)
        current_id = parent
    return current_id # Return current if we can't traverse further

# 2. Apply to create top_web_id in crosswalk dataframe
crosswalk = df[['pattern_id', 'web_id']].copy()
crosswalk['top_web_id'] = crosswalk['web_id'].apply(find_root_web_id)
crosswalk = crosswalk[['pattern_id', 'top_web_id']].drop_duplicates(subset='pattern_id')

# Ensure consistent string types for merge keys
crosswalk['pattern_id'] = crosswalk['pattern_id'].astype(str)
crosswalk['top_web_id'] = crosswalk['top_web_id'].astype(str)

# ----- OUTPUT - CROSSWALK FILE ----- #
crosswalk.to_parquet(output_path, index=False, engine='pyarrow')

print(f"Processing month: {yyyymm} (month_id: {month_id})")
print(f"Crosswalk file created with {len(crosswalk)} unique pattern ids.")
print(f"Unique top_web_ids in crosswalk: {crosswalk['top_web_id'].nunique()}")
print(f"Output saved to: {output_path}")

