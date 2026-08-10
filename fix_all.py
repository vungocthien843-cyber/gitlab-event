import os
import ftfy

def fix_directory(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        text = f.read()
                    
                    fixed_text = ftfy.fix_text(text)
                    
                    if text != fixed_text:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(fixed_text)
                        print(f"Fixed {filepath}")
                except Exception as e:
                    print(f"Failed to fix {filepath}: {e}")

fix_directory('src')
fix_directory('scripts')
fix_directory('tests')
print("All files processed!")
