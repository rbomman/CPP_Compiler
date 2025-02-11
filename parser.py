# parser.py

class ASTNode:
    pass

class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

class VariableDeclaration(ASTNode):
    def __init__(self, var_type, var_name, value):
        self.var_type = var_type  # e.g. "int"
        self.var_name = var_name  # e.g. "a"
        self.value = value        # now can be a literal or an expression

class Assignment(ASTNode):
    def __init__(self, var_name, value):
        self.var_name = var_name
        self.value = value

class ReturnStatement(ASTNode):
    def __init__(self, value):
        self.value = value

# New: BinaryExpression for arithmetic expressions
class BinaryExpression(ASTNode):
    def __init__(self, left, operator, right):
        self.left = left      # Left operand (could be a literal, identifier, or nested expression)
        self.operator = operator  # e.g. '+'
        self.right = right    # Right operand

# --------------------------
# Parser class (updated)
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        self.pos += 1

    def expect(self, token_type):
        token = self.current_token()
        if token and token[0] == token_type:
            self.advance()
            return token
        raise SyntaxError(f"Expected {token_type}, but got {token}")

    def parse_program(self):
        statements = []
        while self.current_token():
            statements.append(self.parse_statement())
        return Program(statements)

    def parse_statement(self):
        token = self.current_token()
        if token[0] == 'KEYWORD':
            if token[1] == 'int':
                return self.parse_variable_declaration()
            elif token[1] == 'return':
                return self.parse_return_statement()
        elif token[0] == 'IDENTIFIER':
            return self.parse_assignment()
        raise SyntaxError(f"Unexpected token {token}")

    def parse_variable_declaration(self):
        self.expect('KEYWORD')  # 'int'
        var_name = self.expect('IDENTIFIER')[1]
        self.expect('SYMBOL')  # '='
        value_expr = self.parse_expression()  # Use the new expression parser
        self.expect('SYMBOL')  # ';'
        return VariableDeclaration('int', var_name, value_expr)

    def parse_assignment(self):
        var_name = self.expect('IDENTIFIER')[1]
        self.expect('SYMBOL')  # '='
        value_expr = self.parse_expression()
        self.expect('SYMBOL')  # ';'
        return Assignment(var_name, value_expr)

    def parse_return_statement(self):
        self.expect('KEYWORD')  # 'return'
        value_expr = self.parse_expression()
        self.expect('SYMBOL')  # ';'
        return ReturnStatement(value_expr)

    # Expression parsing: For now, we support only addition in a left-associative way.
    def parse_expression(self):
        node = self.parse_primary()
        # Check for '+' operator; you can later extend to support '-' or others.
        while self.current_token() and self.current_token()[0] == 'SYMBOL' and self.current_token()[1] == '+':
            op = self.expect('SYMBOL')[1]  # consume the '+'
            right = self.parse_primary()
            node = BinaryExpression(node, op, right)
        return node

    def parse_primary(self):
        token = self.current_token()
        if token[0] == 'NUMBER':
            return int(self.expect('NUMBER')[1])
        elif token[0] == 'IDENTIFIER':
            return self.expect('IDENTIFIER')[1]
        raise SyntaxError(f"Expected primary expression but got {token}")
