import re
from urllib.parse import urlparse

# Trusted domains list
TRUSTED_DOMAINS = [
    'google.com', 'facebook.com', 'youtube.com', 'twitter.com',
    'instagram.com', 'linkedin.com', 'microsoft.com', 'apple.com',
    'amazon.com', 'wikipedia.org', 'github.com', 'stackoverflow.com',
    'gmail.com', 'yahoo.com', 'netflix.com', 'reddit.com',
    'whatsapp.com', 'telegram.org', 'zoom.us', 'dropbox.com'
]

SUSPICIOUS_WORDS = [
    'login', 'verify', 'secure', 'account', 'update', 'banking',
    'confirm', 'paypal', 'signin', 'password', 'credential',
    'free', 'winner', 'prize', 'click', 'urgent', 'suspended',
    'limited', 'offer', 'congratulations', 'selected'
]

SUSPICIOUS_TLDS = ['.xyz', '.tk', '.ml', '.ga', '.cf', '.gq', '.pw']

def get_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def is_trusted(url):
    domain = get_domain(url)
    return any(domain == t or domain.endswith('.' + t) 
               for t in TRUSTED_DOMAINS)

def extract_features(url):
    parsed  = urlparse(url)
    domain  = get_domain(url)
    url_low = url.lower()

    return {
        # Length features
        'url_length':         len(url),
        'domain_length':      len(parsed.netloc),
        'path_length':        len(parsed.path),
        'query_length':       len(parsed.query),

        # Character counts
        'dot_count':          url.count('.'),
        'dash_count':         url.count('-'),
        'underscore_count':   url.count('_'),
        'slash_count':        url.count('/'),
        'question_count':     url.count('?'),
        'equal_count':        url.count('='),
        'at_count':           url.count('@'),
        'amp_count':          url.count('&'),
        'digit_count':        sum(c.isdigit() for c in url),
        'letter_count':       sum(c.isalpha() for c in url),
        'special_char_count': len(re.findall(r'[!@#$%^&*()_+]', url)),
        'percent_count':      url.count('%'),  # encoded chars

        # Security features
        'has_ip':             1 if re.match(
                                r'\d+\.\d+\.\d+\.\d+',
                                parsed.netloc) else 0,
        'is_https':           1 if parsed.scheme == 'https' else 0,
        'has_at_symbol':      1 if '@' in url else 0,
        'has_double_slash':   1 if '//' in url[7:] else 0,
        'subdomain_count':    max(len(parsed.netloc.split('.')) - 2, 0),
        'has_port':           1 if ':' in parsed.netloc else 0,

        # Suspicious indicators
        'has_suspicious':     1 if any(w in url_low 
                                for w in SUSPICIOUS_WORDS) else 0,
        'suspicious_word_count': sum(1 for w in SUSPICIOUS_WORDS 
                                     if w in url_low),
        'has_suspicious_tld': 1 if any(tld in parsed.netloc 
                                for tld in SUSPICIOUS_TLDS) else 0,

        # Trusted domain
        'is_trusted_domain':  1 if is_trusted(url) else 0,

        # Domain features
        'domain_dash_count':  domain.count('-'),
        'domain_digit_count': sum(c.isdigit() for c in domain),
        'domain_dot_count':   domain.count('.'),

        # URL structure
        'path_depth':         len([p for p in parsed.path.split('/') if p]),
        'has_fragment':       1 if parsed.fragment else 0,
        'url_entropy':        len(set(url)) / len(url) if url else 0,
    }