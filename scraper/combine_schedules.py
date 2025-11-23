#!/usr/bin/env python3
"""
Combine all course schedule CSVs into one master file and check room availability.
"""

import pandas as pd
import glob
import os
from datetime import datetime

def combine_all_schedules(input_dir: str, output_file: str):
    """Combine all CSV files from input directory into one master CSV."""

    # Get all CSV files
    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
    print(f"Found {len(csv_files)} CSV files to combine")

    # Read and combine all CSVs
    all_data = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            all_data.append(df)
            print(f"  Loaded {len(df)} courses from {os.path.basename(csv_file)}")
        except Exception as e:
            print(f"  ERROR reading {csv_file}: {e}")

    # Combine all dataframes
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"\nTotal courses: {len(combined_df)}")

        # Sort by course code for easier reading
        combined_df = combined_df.sort_values(['Course', 'Section'])

        # Save to output file
        combined_df.to_csv(output_file, index=False)
        print(f"Saved combined schedule to: {output_file}")

        return combined_df
    else:
        print("ERROR: No data to combine!")
        return None

def check_room_availability(df: pd.DataFrame, rooms: list, day: str, time: str):
    """Check if specified rooms are available at a given day/time."""

    print(f"\n{'='*80}")
    print(f"CHECKING ROOM AVAILABILITY FOR TUESDAY 8:30 AM")
    print(f"{'='*80}\n")

    results = {}

    for room in rooms:
        print(f"\nRoom: {room}")
        print(f"-" * 80)

        # Filter for this room
        room_classes = df[df['Location'].str.contains(room, na=False, case=False)]

        # Filter for Tuesday classes (Days contains 'T')
        # Need to be careful: T is Tuesday, R is Thursday
        # So we check if 'T' is in Days but handle TR, TF, etc.
        tuesday_classes = room_classes[room_classes['Days'].str.contains('T', na=False)]

        # Filter for 8:30 AM classes
        morning_classes = tuesday_classes[tuesday_classes['Times'].str.contains('8:30 AM', na=False)]

        if len(morning_classes) == 0:
            print(f"✓ AVAILABLE - No classes scheduled in {room} on Tuesdays at 8:30 AM")
            results[room] = {
                'available': True,
                'conflicting_classes': []
            }
        else:
            print(f"✗ OCCUPIED - {len(morning_classes)} class(es) scheduled:")
            for idx, row in morning_classes.iterrows():
                print(f"  - {row['Course']}-{row['Section']}: {row['Title']}")
                print(f"    Instructor: {row['Instructor']}")
                print(f"    Days: {row['Days']}, Times: {row['Times']}")
                print(f"    Enrollment: {row['Now']}/{row['Max']}")
                print()

            results[room] = {
                'available': False,
                'conflicting_classes': morning_classes.to_dict('records')
            }

        # Also show all Tuesday classes in this room for context
        if len(tuesday_classes) > 0:
            print(f"\nAll Tuesday classes in {room}:")
            for idx, row in tuesday_classes.iterrows():
                print(f"  - {row['Times']}: {row['Course']}-{row['Section']} ({row['Instructor']})")

    return results

def find_steve_kane_class(df: pd.DataFrame):
    """Find Steve Kane's Tuesday 8:30 AM class in Kupf 211."""

    print(f"\n{'='*80}")
    print(f"SEARCHING FOR STEVE KANE'S CLASS")
    print(f"{'='*80}\n")

    # Search for Steve Kane as instructor
    kane_classes = df[df['Instructor'].str.contains('Kane', na=False, case=False)]

    if len(kane_classes) > 0:
        print(f"Found {len(kane_classes)} class(es) with Kane as instructor:")
        for idx, row in kane_classes.iterrows():
            print(f"  - {row['Course']}-{row['Section']}: {row['Title']}")
            print(f"    Days: {row['Days']}, Times: {row['Times']}")
            print(f"    Location: {row['Location']}")
            print(f"    Enrollment: {row['Now']}/{row['Max']}")
            print()
        return kane_classes
    else:
        print("No classes found with 'Kane' as instructor.")
        print("Searching for classes in KUPF 211 on Tuesday at 8:30 AM...")

        kupf211_classes = df[
            (df['Location'].str.contains('KUPF 211', na=False, case=False)) &
            (df['Days'].str.contains('T', na=False)) &
            (df['Times'].str.contains('8:30 AM', na=False))
        ]

        if len(kupf211_classes) > 0:
            print(f"\nFound {len(kupf211_classes)} class(es) in KUPF 211 on Tuesday at 8:30 AM:")
            for idx, row in kupf211_classes.iterrows():
                print(f"  - {row['Course']}-{row['Section']}: {row['Title']}")
                print(f"    Instructor: {row['Instructor']}")
                print(f"    Enrollment: {row['Now']}/{row['Max']}")
                print()
            return kupf211_classes
        else:
            print("No classes found in KUPF 211 on Tuesday at 8:30 AM either.")
            return None

def main():
    input_dir = "data/temp_scrape"
    output_file = "Spring_2026_Complete_Schedule.csv"

    print("="*80)
    print("NJIT SPRING 2026 COURSE SCHEDULE ANALYZER")
    print("="*80)
    print()

    # Combine all schedules
    df = combine_all_schedules(input_dir, output_file)

    if df is not None:
        # Find Steve Kane's class
        find_steve_kane_class(df)

        # Check availability of requested rooms
        rooms_to_check = ['CKB 303', 'GITC 1400']
        availability = check_room_availability(df, rooms_to_check, 'T', '8:30 AM')

        # Generate summary report
        print(f"\n{'='*80}")
        print("SUMMARY FOR PROFESSOR STEVE KANE")
        print(f"{'='*80}\n")
        print("Request: Find alternative rooms to KUPF 211 for Tuesday 8:30 AM class")
        print()
        print("Results:")
        for room, info in availability.items():
            status = "✓ AVAILABLE" if info['available'] else "✗ OCCUPIED"
            print(f"  {room}: {status}")

        print(f"\nComplete schedule saved to: {output_file}")
        print(f"Total courses in Spring 2026: {len(df)}")
        print()

if __name__ == "__main__":
    main()
