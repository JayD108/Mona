"""Text-cleaning rules shared by the data pipeline and the app (part of the installed package).

normalise()     NFC, drop invisible/control characters (keep newline, tab, ZWNJ, ZWJ), tidy whitespace
fix_hinglish()  fix the ~70 most frequent spellings of machine-transliterated Hinglish ("haye" -> "hai")
keep()          MONA's keep/drop rule for a document of a given language
"""
import unicodedata

import regex

MIN_CHARS = 200

INVISIBLE = regex.compile(r"[^\P{C}\n\t‌‍]")          # category C except allowed ones
SPACES    = regex.compile(r"[^\S\n]+")                           # runs of spaces/tabs (not newlines)
BLANKS    = regex.compile(r"\n\s*\n\s*\n+")                      # 2+ blank lines
LETTER    = regex.compile(r"\p{L}")
DEVA      = regex.compile(r"\p{Devanagari}")
LATIN     = regex.compile(r"\p{Latin}")

# Sangraha's romanized Hindi is machine-transliterated with spellings nobody types
# ("ack prajaati haye" for "ek prajati hai"). Map the most frequent ones (measured: the top
# function words) to common Hinglish spellings; everything else is left as it is.
HINGLISH_FIX = dict(pair.split(":") for pair in """
key:ke kii:ki haye:hai koo:ko seey:se ack:ek kaa:ka thaa:tha ney:ne gayaa:gaya parr:par joe:jo
they:the diyaa:diya bhee:bhi thee:thi taka:tak apane:apne jaataa:jata curr:kar naheen:nahi
nahin:nahi hoe:ho dee:di gaee:gayi pahale:pehle yaa:ya unake:unke unhein:unhe way:ve see:se
jisamen:jisme kartaa:karta apani:apni karate:karte vaale:wale jaba:jab dou:do huaa:hua
karane:karne kaee:kai hotey:hote hotaa:hota sakate:sakte isake:iske usake:uske unakaa:unka
unakee:unki inake:inke kahaa:kaha rahaa:raha rahee:rahi rahey:rahe liyaa:liya kiyaa:kiya
jaatey:jate jaatee:jati karatee:karti vaalaa:wala vaalee:wali sabase:sabse iskaa:iska
iskee:iski jisase:jisse kisee:kisi koee:koi jisakaa:jiska jisakee:jiski aapakaa:aapka
""".split())
HINGLISH_WORD = regex.compile(r"\b(" + "|".join(sorted(HINGLISH_FIX, key=len, reverse=True)) + r")\b")


def fix_hinglish(text):
    return HINGLISH_WORD.sub(lambda m: HINGLISH_FIX[m.group(1)], text)


def normalise(text):
    text = unicodedata.normalize("NFC", text)
    text = INVISIBLE.sub("", text)
    text = SPACES.sub(" ", text)
    text = BLANKS.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def keep(lang, text):
    if len(text) < MIN_CHARS:
        return False
    if lang == "english":
        return True
    letters = len(LETTER.findall(text)) or 1
    if lang == "hindi":
        return len(DEVA.findall(text)) / letters >= 0.6
    if lang == "hinglish":
        return len(LATIN.findall(text)) / letters >= 0.8
    return True
