import py7zr
import sys

file_path = r"C:\Users\marco\Downloads\TSE\data\raw_logs\ac\o00407-0100700090001.logjez"

try:
    with py7zr.SevenZipFile(file_path, mode='r') as z:
        print(f"Files in archive: {z.getnames()}")
        all_files = z.getnames()
        target = next((f for f in all_files if f.endswith('.dat') or 'log' in f.lower()), None)
        
        if target:
            import shutil
            import os
            
            tmp_dir = "tmp_extract"
            if os.path.exists(tmp_dir): shutil.rmtree(tmp_dir)
            
            z.extract(path=tmp_dir, targets=[target])
            
            extracted_path = os.path.join(tmp_dir, target)
            print(f"Extracted to: {extracted_path}")
            
            with open(extracted_path, 'rb') as f:
                content = f.read()
                
            # Try decoding
            try:
                text = content.decode('utf-8')
            except:
                text = content.decode('latin1')
            
            print("--- HEAD ---")
            print('\n'.join(text.splitlines()[:20]))
            print("--- END ---")
            
            # Cleanup
            # shutil.rmtree(tmp_dir)
        else:
            print("No suitable log file found inside archive.")
except Exception as e:
    print(f"Error: {e}")
