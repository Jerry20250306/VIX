import csv
import sys

def parse_product_id(prod_id):
    prod_id = prod_id.strip()
    if len(prod_id) != 10:
        return {"Error": "Length not 10", "Original": prod_id}
    
    pp = prod_id[0:2]
    t = prod_id[2]
    aaaaa = prod_id[3:8]
    cc = prod_id[8:10]
    
    # 2. Strike
    try:
        strike = int(aaaaa)
    except ValueError:
        return {"Error": "Invalid Strike", "Original": prod_id}
        
    # 3. Month/Year & Call/Put
    month_code = cc[0]
    year_digit = cc[1]
    
    call_months = "ABCDEFGHIJKL"
    put_months = "MNOPQRSTUVWX"
    
    cp = None
    month = None
    
    if month_code in call_months:
        cp = "Call"
        month = call_months.index(month_code) + 1
    elif month_code in put_months:
        cp = "Put"
        month = put_months.index(month_code) + 1
    else:
        return {"Error": "Invalid Month Code", "Original": prod_id}
        
    return {
        "Original": prod_id,
        "Product": pp,
        "Type": t,
        "Strike": strike,
        "CP": cp,
        "Month": month,
        "YearDigit": year_digit
    }

def main():
    file_path = "c:/Users/jerry1016/.gemini/antigravity/VIX/資料來源/J002-11300041_20251231/temp/J002-11300041_20251231_TXOA6.csv"
    try:
        unique_ids = set()
        print(f"Reading file: {file_path}")
        print("Parsing first 20 unique IDs...\n")
        print(f"{'Original':<12} | {'Prod':<4} | {'Type':<4} | {'Strike':<6} | {'CP':<4} | {'M':<2} | {'Y':<1}")
        print("-" * 60)

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader) # skip header
            # Find index of svel_i081_prod_id
            try:
                col_idx = headers.index('svel_i081_prod_id')
            except ValueError:
                # Fallback if header is different or using tabs? 
                # The view_file showed standard CSV-like structure but maybe tab separated?
                # Actually view_file showed tabs or spaces. Let's try splitting line if csv fail.
                pass
            
            count = 0
            for row in reader:
                if not row: continue
                # Handle potential tab separation if csv reader failed to split correctly
                if len(row) == 1:
                     row = row[0].split('\t')
                
                # Manual index 1 based on view_file info: 
                # svel_i081_yymmdd	svel_i081_prod_id ...
                # 0: date, 1: prod_id
                if len(row) > 1:
                    pid = row[1]
                    if pid not in unique_ids:
                        unique_ids.add(pid)
                        res = parse_product_id(pid)
                        
                        if "Error" in res:
                            print(f"{res['Original']:<12} | Error: {res['Error']}")
                        else:
                            print(f"{res['Original']:<12} | {res['Product']:<4} | {res['Type']:<4} | {res['Strike']:<6} | {res['CP']:<4} | {res['Month']:<2} | {res['YearDigit']:<1}")
                        
                        count += 1
                        if count >= 20: 
                            break
                            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
