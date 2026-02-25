f = r'c:\Users\jerry1016\.gemini\antigravity\VIX\Viewer\templates\index.html'
content = open(f, encoding='utf-8').read()

old = '<div id="alert-tab-next" style="display: none;">\n                    <div class="table-container">'
new = '<div id="alert-tab-next" style="display: none;">\n                    <div class="table-container" style="max-height: 70vh; overflow-y: auto;">'

if old in content:
    content = content.replace(old, new, 1)
    open(f, 'w', encoding='utf-8').write(content)
    print('OK: replaced Next tab table-container')
else:
    print('NOT FOUND - checking actual content...')
    idx = content.find('alert-tab-next')
    print(repr(content[idx:idx+200]))
