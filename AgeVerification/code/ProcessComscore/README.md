# Comscore Data Processing Pipeline

This directory contains tools for processing Comscore web browsing data.

## Available Scripts

### Session Data Cleaner (`ScratchCleanMain.py`)

General-purpose class for cleaning and filtering Comscore session data.

**Features:**
- Reads compressed session files (.txt.gz)
- Applies proper column names and data types
- Filters to websites of interest (optional)
- Removes invalid rows (negative durations, missing IDs)
- Can process single files or batch process directories

**Usage:**
```python
from pathlib import Path
from ScratchCleanMain import ComscoreSessionCleaner

# Create cleaner (no filtering)
cleaner = ComscoreSessionCleaner(
    websites_of_interest=None,  # or provide list of pattern_ids
    output_dir=Path('data/cleaned_sessions')
)

# Process a single file
df = cleaner.clean_single_file(Path('raw/desktop_day_session/file.txt.gz'))

# Or process entire directory
cleaner.process_directory(
    input_dir=Path('raw/desktop_day_session'),
    pattern='*.txt.gz'
)
```

### Crosswalk Creation (`analysis/00_create_crosswalk_files.py`)

Creates crosswalk files mapping pattern_id to top_web_id for consistent entity tracking across time periods.

**Why needed:**
- Pattern IDs can change over time for the same website
- Top web ID provides stable tracking across months
- Essential for longitudinal analysis

**Usage:**
```bash
python analysis/00_create_crosswalk_files.py \
  --category_map_dir raw/Lookups/traffic_category_map \
  --output_dir data/crosswalks
```

**Outputs:**
- `pattern_id_to_top_web_id_{month}.csv` - Month-specific mappings
- `top_web_id_master_lookup.csv` - Master lookup with website names and categories

## Data Structure

### Session Data Files

Tab-delimited files with the following columns:
- `machine_id` - Unique machine identifier
- `person_id` - Unique person identifier
- `session_id` - Unique session identifier
- `date_id` - Date identifier (requires lookup)
- `session_start_ss2k` - Session start time (seconds since 2000)
- `page_count` - Number of pages viewed
- `duration_seconds` - Session duration in seconds
- `website_pattern_id` - Website identifier (requires lookup)
- `referrer_pattern_id` - Referring website identifier

### Lookup Tables

**Time Lookup:**
- Maps `date_id` to calendar dates
- Located in: `raw/Lookups/time_lookup/`

**Traffic Category Map:**
- Maps `pattern_id` to website names and categories
- Located in: `raw/Lookups/traffic_category_map/`
- **Important:** Pattern IDs can change over time, so join on both pattern_id AND month

**Demographics:**
- Person and household characteristics
- Located in: `raw/desktop_machine_demos/`
- Available at machine_id and person_id level

## Important Considerations

### Pattern ID Stability
Pattern IDs can change meaning over time. When merging website information, join on **both** pattern_id AND the time period (month).

Use the crosswalk files in `data/crosswalks/` to track websites consistently across time.

### Memory Management
Session data files are large. For processing:
- Use chunked reading with pandas (`chunksize` parameter)
- Process files one at a time when possible
- Consider Parquet format for intermediate outputs

### Person ID vs Machine ID
- Multiple people can share a machine
- Demographics available for both person_id and machine_id
- Choose based on your research question

## Customizing for Your Research

This is a starter pipeline. To adapt for your specific research:

1. **Identify websites of interest:**
   - Search category map files for relevant pattern_ids
   - Create custom filtering logic in the session cleaner

2. **Define your analysis unit:**
   - Person-day, person-week, or person-month
   - Session-level or aggregated

3. **Add merges as needed:**
   - Time lookups for calendar dates
   - Demographics for person characteristics
   - Website info for categorization

4. **Create analysis datasets:**
   - Aggregate sessions to your chosen unit
   - Apply quality filters
   - Generate summary statistics

## Useful Commands

```bash
# Check data size
du -sh raw/desktop_day_session/

# Count rows in compressed file
gunzip -c raw/desktop_day_session/file.txt.gz | wc -l

# Preview compressed file
gunzip -c raw/desktop_day_session/file.txt.gz | head -20

# Search for pattern_id in category map
gunzip -c raw/Lookups/traffic_category_map/file.txt.gz | grep "pattern_id"
```

## Dependencies

- Python 3.11+
- pandas
- numpy
- pathlib (standard library)
- logging (standard library)
