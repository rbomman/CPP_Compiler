import re

def tokenize(code):
    # Define token specifications with named groups
    token_specification = [
        ('KEYWORD', r'\b(int|return)\b'),     # Keywords: int, return
        ('NUMBER', r'\b\d+\b'),               # Integer literals
        ('IDENTIFIER', r'\b[A-Za-z_]\w*\b'),   # Identifiers
        ('SYMBOL', r'[;=+\-*/()]'),           # Symbols
        ('WHITESPACE', r'\s+'),               # Whitespace (ignored)
        ('UNKNOWN', r'.')                    # Any other character (error fallback)
    ]
    # Combine the patterns into a master regex pattern
    token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
    
    tokens = []
    for mo in re.finditer(token_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'WHITESPACE':
            continue  # Skip whitespace
        tokens.append((kind, value))
    return tokens

# Example test
if __name__ == "__main__":
    code_snippet = """
    int a = 5;
    return a;
    """
    for token in tokenize(code_snippet):
        print(token)
