import unicodedata
import re

async def only_digits(text: str):
    return int(''.join(filter(str.isdigit, text)))

async def clean_text(text:str):
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\u2002', ' ')
    text = re.sub(
        r'(?<!^)([А-ЯA-Z][а-яa-z])',
        r' \1',
        text
        )
    return text

async def collec_avito_id(url):
    match = re.search(r"_(\d+)", url)

    if match:
        avito_id = int(match.group(1))

    return avito_id

