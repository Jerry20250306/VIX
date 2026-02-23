
import pandas as pd
import sys

def main():
    file_path = r'資料來源/20251201/NearPROD_20251201.tsv'
    print(f"Reading {file_path}...")
    try:
        df = pd.read_csv(file_path, sep='\t', dtype=str)
        print("Columns:", df.columns.tolist())
        
        if 'c.min_outlier' in df.columns:
            print("\nUnique values in c.min_outlier:")
            print(df['c.min_outlier'].unique())
            print(df['c.min_outlier'].value_counts())
            
        if 'p.min_outlier' in df.columns:
            print("\nUnique values in p.min_outlier:")
            print(df['p.min_outlier'].unique())
            print(df['p.min_outlier'].value_counts())

        # Find row where c.min_outlier is valid (not '-' and not 'V') AND sysIDs are same
        target_rows = df[
            (df['c.min_outlier'] != '-') & 
            (df['c.min_outlier'] != 'V') & 
            (df['c.min_outlier'].notna()) & 
            (df['c.min_sysID'] == df['c.last_sysID'])
        ]
        
        if not target_rows.empty:
            print(f"\nFound {len(target_rows)} rows where Min_Outlier is VALID (not V) BUT SysIDs are same.")
            row = target_rows.iloc[0]
            print(f"\nRow for {row['time']}, {row['strike']}:")
            for col in df.columns:
                print(f"{col}: {row[col]}")
        else:
            print(f"\nNo rows found where Min_Outlier is VALID (not V) AND SysIDs are same.")
            print("Hypothesis supported: If Q_Min == Q_Last and Valid, Min_Outlier is '-'.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
