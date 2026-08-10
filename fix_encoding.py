import os

with open('src/services/github_events.py', 'r', encoding='utf-8') as f:
    corrupted_text = f.read()

if corrupted_text.startswith('\ufeff'):
    corrupted_text = corrupted_text[1:]

original_text = corrupted_text.encode('cp1252').decode('utf-8')

with open('github_events_fixed.py', 'w', encoding='utf-8') as f:
    f.write(original_text)
print("Fixed successfully!")
