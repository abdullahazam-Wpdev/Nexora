"""Explicit approval, content hashing, document-level splits, and secret rejection."""
import hashlib
import re
import unicodedata

def prepare(texts, *, approved, license, provenance):
    if not approved or license not in {'CC0-1.0','MIT','Apache-2.0','public-domain'} or not provenance.strip():
        raise ValueError('Explicit approval, supported license and provenance are required')
    clean = {}
    for text in texts:
        text = unicodedata.normalize('NFC', text).strip()
        if re.search(r'(?i)(api[_-]?key\s*[=:]|password\s*[=:]|-----BEGIN .*PRIVATE KEY|\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b)', text):
            raise ValueError('Potential secret or personal data detected; ingestion rejected')
        if len(text) >= 20:
            digest = hashlib.sha256(text.encode()).hexdigest()
            clean[digest] = text
    if len(clean) < 10:
        raise ValueError('At least ten unique documents required')
    ordered = sorted(clean.items())
    n = len(ordered)
    train_end, val_end = max(1,int(n*.8)), max(2,int(n*.9))
    return {'license':license,'provenance':provenance,'approved':True,
            'documents':len(ordered),'hashes':[h for h,_ in ordered],
            'splits':{'train':[t for _,t in ordered[:train_end]],'validation':[t for _,t in ordered[train_end:val_end]],'test':[t for _,t in ordered[val_end:]]}}
