import os
import ftfy

with open('src/services/github_events.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix mojibake
fixed_text = ftfy.fix_text(text)

with open('github_events_ftfy.py', 'w', encoding='utf-8') as f:
    f.write(fixed_text)
print("FTFY finished!")
