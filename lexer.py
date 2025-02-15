import re

def tokenize(code):
    """
    This function tokenizes the given source code into a list of tokens.

    It does so in the following steps:
    
    1. **Comment Removal:**  
       Removes inline comments as in any line starting with "//"
       
    2. **Token Specification:**  
       It defines a list of token types and associated regular expressions:
         - KEYWORD: Matches language keywords
         - NUMBER: Matches integer literals.
         - IDENTIFIER: Matches identifiers that start with a letter or underscore followed by letters, digits, or underscores.
         - LAND: Matches the logical AND operator '&&'.
         - LOR: Matches the logical OR operator '||'.
         - EQ: Matches the equality operator '=='.
         - NEQ: Matches the inequality operator '!='.
         - LE: Matches the LE operator '<='.
         - GE: Matches the GE operator '>='.
         - EXP: Matches the exponentiation operator for integers '^'.
         - SYMBOL: Matches various single-character symbols.
         - WHITESPACE: Matches spaces, tabs, and newlines.
         - UNKNOWN: Matches any single character that doesn't match the above patterns.
    
    3. **Regex Combination:**  
       All token patterns are combined into a single regular expression using named groups.
    
    4. **Token Extraction:**  
       The function iterates over all regex matches in the source code and for each match:
         - It calculates the line and column number for the token.
         - It skips whitespace tokens.
         - It appends a tuple (token_type, token_value, line_number, column_number) to the token list.

    Parameters:
        str: The code which you want to tokenize

    Returns:
        list: A list of tokens, where each token is represented as a tuple: (token_type, token_value, line_number, column_number).
    """

    # Remove C++-style inline comments: anything from '//' to the end of the line.
    code = re.sub(r'//.*', '', code)
    
    # Token specification table
    token_specification = [
        # Include 'bool', 'true', 'false' along with other keywords.
        ('KEYWORD',   r'\b(int|bool|return|if|else|while|true|false)\b'),
        ('NUMBER',    r'\b\d+\b'),
        ('IDENTIFIER',r'\b[A-Za-z_]\w*\b'),
        ('LAND',      r'&&'),
        ('LOR',       r'\|\|'),
        ('EQ',        r'=='),
        ('NEQ',       r'!='),
        ('LE',        r'<='),
        ('GE',        r'>='),
        ('EXP',       r'\^'),
        ('SYMBOL',    r'[<>+\-\*/%();={}\[\],]'),
        ('WHITESPACE',r'\s+'),
        ('UNKNOWN',   r'.')
    ]

    # Performs regex to detect tokens
    token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
    tokens = []
    line_num = 1
    line_start = 0
    for mo in re.finditer(token_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        start_index = mo.start()
        # Update line and column information:
        line_breaks = code[line_start:start_index].count("\n")
        if line_breaks:
            line_num += line_breaks
            line_start = code.rfind("\n", 0, start_index) + 1
        column = start_index - line_start + 1

        if kind == 'WHITESPACE':
            continue
        tokens.append((kind, value, line_num, column))
    return tokens

# Place code in the sample code string to test tokenizer
if __name__ == "__main__":
    sample_code = """
   
    """
    for token in tokenize(sample_code):
        print(token)
