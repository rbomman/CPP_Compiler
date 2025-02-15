import re

# --- AST Node Definitions ---
class ASTNode:
    """Base class for all AST nodes."""
    pass

class Program(ASTNode):
    """
    Represents the entire program as a collection of global declarations,
    which can be either function definitions or global variable declarations.
    """
    def __init__(self, declarations):
        self.declarations = declarations

class Block(ASTNode):
    """Represents a block of statements enclosed in '{' and '}'."""
    def __init__(self, statements):
        self.statements = statements

class VariableDeclaration(ASTNode):
    """Represents a variable declaration with its type, name, and initialization expression."""
    def __init__(self, var_type, var_name, value):
        self.var_type = var_type  # e.g., "int" or "bool"
        self.var_name = var_name
        self.value = value        # Expression assigned to the variable

class Assignment(ASTNode):
    """Represents an assignment to a variable."""
    def __init__(self, var_name, value):
        self.var_name = var_name
        self.value = value

class ReturnStatement(ASTNode):
    """Represents a return statement with an expression to return."""
    def __init__(self, value):
        self.value = value

class BinaryExpression(ASTNode):
    """
    Represents a binary operation (e.g., arithmetic, relational, logical) on two expressions.
    The operator is stored as a string (such as '+', '-', '*', '/', '<', etc.).
    """
    def __init__(self, left, operator, right):
        self.left = left        # Left operand (expression)
        self.operator = operator  # Operator (string)
        self.right = right      # Right operand (expression)

class IfStatement(ASTNode):
    """Represents an if statement with an optional else branch."""
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

class WhileStatement(ASTNode):
    """Represents a while loop with a condition and loop body."""
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class FunctionDefinition(ASTNode):
    """
    Represents a function definition, including its return type, name,
    parameters (a list of (type, name) pairs), and the body (a Block).
    """
    def __init__(self, return_type, name, parameters, body):
        self.return_type = return_type  # e.g., "int" or "bool"
        self.name = name
        self.parameters = parameters    # List of tuples, e.g., [('int', 'x'), ('int', 'y')]
        self.body = body

class FunctionCall(ASTNode):
    """Represents a function call with its name and a list of argument expressions."""
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

# --- Parser Class ---
class Parser:
    """
    The Parser class takes a list of tokens produced by the lexer and
    converts them into an Abstract Syntax Tree. 
    
    It supports global declarations (functions or global variable declarations) and statements within function bodies,
    including variable declarations, assignments, control flow statements, and expressions.
    
    The parser uses a recursive descent approach with helper methods for each grammar
    rule and operator-precedence levels for expressions.
    
    Each token is expected to be a tuple of the form:
       (token_type, token_value, line_number, column_number)
    """
    
    def __init__(self, tokens):
        self.tokens = tokens  # List of tokens from the lexer
        self.pos = 0          # Current position in the token list

    def current_token(self):
        """Returns the current token or None if at the end of the token list."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        """Advances to the next token."""
        self.pos += 1

    def expect(self, token_type, value=None):
        """
        Expects the current token to match the given token_type (and optionally value).
        If matched, advances and returns the token; otherwise, raises a SyntaxError
        with line and column information.
        """
        token = self.current_token()
        if token and token[0] == token_type and (value is None or token[1] == value):
            self.advance()
            return token
        line = token[2] if token else "EOF"
        col = token[3] if token else ""
        expected = f"{token_type} {value}" if value else token_type
        actual = f"{token[0]} '{token[1]}'" if token else "EOF"
        raise SyntaxError(f"Line {line}, Col {col}: Expected {expected}, but got {actual}.")

    # Global Parsing Methods
    def parse_program(self):
        """
        Parses the entire program as a series of global declarations.
        Returns a Program AST node.
        """
        declarations = []
        while self.current_token():
            declarations.append(self.parse_global_declaration())
        return Program(declarations)

    def parse_global_declaration(self):
        """
        Parses a global declaration, which must start with a type (int or bool).
        If the declaration is followed by a '(' token, it is parsed as a function definition;
        otherwise, it's treated as a global variable declaration.
        """
        type_tok = self.expect('KEYWORD')
        if type_tok[1] not in ['int', 'bool']:
            raise SyntaxError(f"Expected global declaration to start with type 'int' or 'bool', but got '{type_tok[1]}'.")
        name_tok = self.expect('IDENTIFIER')
        # If the next token is '(', it's a function definition.
        if self.current_token() and self.current_token()[0] == 'SYMBOL' and self.current_token()[1] == '(':
            return self.parse_function_definition(type_tok[1], name_tok[1])
        else:
            return self.parse_variable_declaration_with_prefix(type_tok[1], name_tok[1])

    def parse_variable_declaration_with_prefix(self, var_type, var_name):
        """
        Parses a variable declaration when the type and name have already been read.
        Expects an '=' token, an expression, and a terminating ';'.
        """
        self.expect('SYMBOL', '=')
        value_expr = self.parse_expression()
        self.expect('SYMBOL', ';')
        return VariableDeclaration(var_type, var_name, value_expr)

    def parse_function_definition(self, return_type, name):
        """
        Parses a function definition. Assumes that the return type and function name have been read.
        Parses the parameter list (if any) and the function body (a Block).
        """
        self.expect('SYMBOL', '(')
        parameters = []
        # If the next token is not a closing ')', parse the parameter list.
        if not (self.current_token()[0] == 'SYMBOL' and self.current_token()[1] == ')'):
            parameters = self.parse_parameter_list()
        self.expect('SYMBOL', ')')
        body = self.parse_block()
        return FunctionDefinition(return_type, name, parameters, body)

    def parse_parameter_list(self):
        """
        Parses a list of function parameters.
        Each parameter starts with a type (int or bool) followed by an identifier.
        Parameters are separated by commas.
        """
        params = []
        while True:
            type_tok = self.expect('KEYWORD')
            if type_tok[1] not in ['int', 'bool']:
                raise SyntaxError(f"Expected parameter type 'int' or 'bool', but got '{type_tok[1]}'.")
            param_name = self.expect('IDENTIFIER')[1]
            params.append((type_tok[1], param_name))
            if self.current_token() and self.current_token()[0] == 'SYMBOL' and self.current_token()[1] == ',':
                self.expect('SYMBOL', ',')
            else:
                break
        return params

    # Statement Parsing Methods
    def parse_statement(self):
        """
        Parses a statement inside a function or block.
        A statement can be a variable declaration, return statement, if-statement, while-loop,
        a block, or an assignment/function call.
        """
        token = self.current_token()
        if token[0] == 'KEYWORD':
            # Variable declarations can start with either 'int' or 'bool'.
            if token[1] in ['int', 'bool']:
                return self.parse_variable_declaration()
            elif token[1] == 'return':
                return self.parse_return_statement()
            elif token[1] == 'if':
                return self.parse_if_statement()
            elif token[1] == 'while':
                return self.parse_while_statement()
        elif token[0] == 'SYMBOL' and token[1] == '{':
            return self.parse_block()
        elif token[0] == 'IDENTIFIER':
            return self.parse_assignment_or_function_call()
        raise SyntaxError(f"Unexpected token {token}")

    def parse_block(self):
        """
        Parses a block of statements enclosed in '{' and '}'.
        Returns a Block AST node.
        """
        self.expect('SYMBOL', '{')
        statements = []
        while self.current_token() and not (self.current_token()[0] == 'SYMBOL' and self.current_token()[1] == '}'):
            statements.append(self.parse_statement())
        self.expect('SYMBOL', '}')
        return Block(statements)

    def parse_variable_declaration(self):
        """
        Parses a variable declaration inside a function or block.
        Expects a type ('int' or 'bool'), an identifier, an '=' token,
        an expression, and a terminating ';'.
        """
        type_tok = self.expect('KEYWORD')
        if type_tok[1] not in ['int', 'bool']:
            raise SyntaxError(f"Line {type_tok[2]}, Col {type_tok[3]}: Expected type 'int' or 'bool', but got '{type_tok[1]}'.")
        var_name = self.expect('IDENTIFIER')[1]
        self.expect('SYMBOL', '=')
        value_expr = self.parse_expression()
        self.expect('SYMBOL', ';')
        return VariableDeclaration(type_tok[1], var_name, value_expr)

    def parse_assignment_or_function_call(self):
        """
        Parses an assignment or a function call.
        First consumes an identifier. If followed by '(' it is treated as a function call;
        otherwise, it is an assignment.
        """
        ident = self.expect('IDENTIFIER')[1]
        if self.current_token() and self.current_token()[0] == 'SYMBOL' and self.current_token()[1] == '(':
            fc = self.parse_function_call(ident)
            self.expect('SYMBOL', ';')
            return fc
        else:
            self.expect('SYMBOL', '=')
            value_expr = self.parse_expression()
            self.expect('SYMBOL', ';')
            return Assignment(ident, value_expr)

    def parse_return_statement(self):
        """
        Parses a return statement.
        Expects the keyword 'return', an expression, and a terminating ';'.
        """
        self.expect('KEYWORD', 'return')
        value_expr = self.parse_expression()
        self.expect('SYMBOL', ';')
        return ReturnStatement(value_expr)

    def parse_if_statement(self):
        """
        Parses an if statement with an optional else branch.
        Expects 'if' followed by a condition in parentheses, then a statement for the 'then' branch,
        and optionally 'else' followed by a statement.
        """
        self.expect('KEYWORD', 'if')
        self.expect('SYMBOL', '(')
        condition = self.parse_expression()
        self.expect('SYMBOL', ')')
        then_branch = self.parse_statement()
        else_branch = None
        if self.current_token() and self.current_token()[0] == 'KEYWORD' and self.current_token()[1] == 'else':
            self.expect('KEYWORD', 'else')
            else_branch = self.parse_statement()
        return IfStatement(condition, then_branch, else_branch)

    def parse_while_statement(self):
        """
        Parses a while loop.
        Expects 'while', a condition in parentheses, and a statement as the loop body.
        """
        self.expect('KEYWORD', 'while')
        self.expect('SYMBOL', '(')
        condition = self.parse_expression()
        self.expect('SYMBOL', ')')
        body = self.parse_statement()
        return WhileStatement(condition, body)

    # Expression Parsing Methods (with operator precedence)
    def parse_expression(self):
        """Parses an expression using logical OR as the top precedence level."""
        return self.parse_logical_or()

    def parse_logical_or(self):
        node = self.parse_logical_and()
        while self.current_token() and self.current_token()[0] == 'LOR':
            op = self.expect('LOR')[1]
            right = self.parse_logical_and()
            node = BinaryExpression(node, op, right)
        return node

    def parse_logical_and(self):
        node = self.parse_equality()
        while self.current_token() and self.current_token()[0] == 'LAND':
            op = self.expect('LAND')[1]
            right = self.parse_equality()
            node = BinaryExpression(node, op, right)
        return node

    def parse_equality(self):
        node = self.parse_relational()
        while self.current_token() and self.current_token()[0] in ['EQ', 'NEQ']:
            if self.current_token()[0] == 'EQ':
                op = self.expect('EQ')[1]
            else:
                op = self.expect('NEQ')[1]
            right = self.parse_relational()
            node = BinaryExpression(node, op, right)
        return node

    def parse_relational(self):
        node = self.parse_addition()
        while self.current_token() and (
            (self.current_token()[0] == 'SYMBOL' and self.current_token()[1] in ['<', '>']) or 
            self.current_token()[0] in ['LE', 'GE']
        ):
            token = self.current_token()
            if token[0] in ['LE', 'GE']:
                op = self.expect(token[0])[1]
            else:
                op = self.expect('SYMBOL')[1]
            right = self.parse_addition()
            node = BinaryExpression(node, op, right)
        return node

    def parse_addition(self):
        node = self.parse_term()
        while self.current_token() and self.current_token()[0] == 'SYMBOL' and self.current_token()[1] in ['+', '-']:
            op = self.expect('SYMBOL')[1]
            right = self.parse_term()
            node = BinaryExpression(node, op, right)
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.current_token() and self.current_token()[0] == 'SYMBOL' and self.current_token()[1] in ['*', '/', '%']:
            op = self.expect('SYMBOL')[1]
            right = self.parse_factor()
            node = BinaryExpression(node, op, right)
        return node

    def parse_factor(self):
        node = self.parse_primary()
        if self.current_token() and self.current_token()[0] == 'EXP':
            self.expect('EXP', '^')
            right = self.parse_factor()  # Right-associative exponentiation.
            node = BinaryExpression(node, '^', right)
        return node

    def parse_primary(self):
        """
        Parses a primary expression. Primary expressions can be:
          - A number literal.
          - A boolean literal ('true' or 'false').
          - An identifier (which might be a variable or a function call).
          - A parenthesized expression.
        If none of these match, a SyntaxError is raised.
        """
        token = self.current_token()
        if token[0] == 'NUMBER':
            return int(self.expect('NUMBER')[1])
        elif token[0] == 'KEYWORD' and token[1] in ['true', 'false']:
            # Consume and return the boolean literal.
            return self.expect('KEYWORD')[1]
        elif token[0] == 'IDENTIFIER':
            # Look ahead for a function call.
            ident = self.expect('IDENTIFIER')[1]
            if self.current_token() and self.current_token()[0] == 'SYMBOL' and self.current_token()[1] == '(':
                return self.parse_function_call(ident)
            return ident
        elif token[0] == 'SYMBOL' and token[1] == '(':
            self.expect('SYMBOL', '(')
            node = self.parse_expression()
            self.expect('SYMBOL', ')')
            return node
        raise SyntaxError(f"Expected primary expression but got {token}")

    def parse_function_call(self, func_name):
        """
        Parses a function call.
        Expects '(' followed by an optional argument list and a closing ')'.
        Returns a FunctionCall AST node.
        """
        self.expect('SYMBOL', '(')
        arguments = []
        if not (self.current_token()[0] == 'SYMBOL' and self.current_token()[1] == ')'):
            arguments = self.parse_argument_list()
        self.expect('SYMBOL', ')')
        return FunctionCall(func_name, arguments)

    def parse_argument_list(self):
        """
        Parses a comma-separated list of expressions for function call arguments.
        Returns a list of argument expressions.
        """
        args = []
        while True:
            arg_expr = self.parse_expression()
            args.append(arg_expr)
            if self.current_token() and self.current_token()[0] == 'SYMBOL' and self.current_token()[1] == ',':
                self.expect('SYMBOL', ',')
            else:
                break
        return args
