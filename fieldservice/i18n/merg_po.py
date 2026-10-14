#!/usr/bin/env python3
# merge_po.py
import re, sys, json

def unquote_po(value):
    parts = re.findall(r'"((?:\\.|[^"\\])*)"', value)
    return ''.join(part.encode().decode('unicode_escape') for part in parts)

def parse_po(path):
    entries = {}
    current_msgid = None
    current_msgstr = None
    collecting = None

    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if line.startswith('msgid "'):
                if current_msgid is not None and current_msgstr is not None:
                    entries[current_msgid] = current_msgstr
                current_msgid = unquote_po(line)
                current_msgstr = None
                collecting = 'msgid'
            elif line.startswith('msgstr "'):
                current_msgstr = unquote_po(line)
                collecting = 'msgstr'
            elif line.startswith('"') and collecting:
                value = unquote_po(line)
                if collecting == 'msgid':
                    current_msgid += value
                else:
                    current_msgstr += value
            elif not line.strip():
                if current_msgid is not None and current_msgstr is not None:
                    entries[current_msgid] = current_msgstr
                current_msgid = current_msgstr = None
                collecting = None

        if current_msgid is not None and current_msgstr is not None:
            entries[current_msgid] = current_msgstr

    return entries

def po_quote(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

def merge(template_path, translations_path, language, output_path):
    template = open(template_path, encoding='utf-8').read()
    translations = parse_po(translations_path)

    blocks = template.split('\n\n')
    replaced = missing = 0

    for i, block in enumerate(blocks):
        if not block.strip() or block.lstrip().startswith('msgid ""'):
            continue

        match = re.search(r'(?ms)^msgid ((?:"(?:\\.|[^"\\])*"\n?)+)', block)
        if not match:
            continue

        msgid = unquote_po(match.group(1))
        if msgid not in translations:
            missing += 1
            continue

        translation = translations[msgid]
        block = re.sub(
            r'(?ms)^msgstr ((?:"(?:\\.|[^"\\])*"\n?)+)',
            'msgstr ' + po_quote(translation) + '\n',
            block,
            count=1,
        )
        blocks[i] = block
        replaced += 1

    # Update language metadata in the header.
    header = blocks[0]
    header = re.sub(r'"Language: [^"]*\\n"', f'"Language: {language}\\\\n"', header)
    blocks[0] = header

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(blocks))

    print(f'{output_path}: {replaced} translations applied, {missing} source entries without translation')

if len(sys.argv) != 5:
    print('Usage: python3 merge_po.py de_DE.po translations.po nl_NL output.po')
    sys.exit(1)

merge(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])