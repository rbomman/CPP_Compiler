class ASTNode:
    """Base class for all AST nodes."""


class Program(ASTNode):
    def __init__(self, declarations):
        self.declarations = declarations


class Block(ASTNode):
    def __init__(self, statements):
        self.statements = statements


class StructDefinition(ASTNode):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields


class StructDeclaration(ASTNode):
    def __init__(self, struct_type, var_name):
        self.struct_type = struct_type
        self.var_name = var_name


class VariableDeclaration(ASTNode):
    def __init__(self, var_type, var_name, value):
        self.var_type = var_type
        self.var_name = var_name
        self.value = value


class ArrayDeclaration(ASTNode):
    def __init__(self, element_type, array_name, size):
        self.element_type = element_type
        self.array_name = array_name
        self.size = size


class Assignment(ASTNode):
    def __init__(self, var_name, value):
        self.var_name = var_name
        self.value = value


class ArrayAssignment(ASTNode):
    def __init__(self, array_name, index, value):
        self.array_name = array_name
        self.index = index
        self.value = value


class FieldAssignment(ASTNode):
    def __init__(self, field_access, value):
        self.field_access = field_access
        self.value = value


class PointerAssignment(ASTNode):
    def __init__(self, pointer_expr, value):
        self.pointer_expr = pointer_expr
        self.value = value


class ReturnStatement(ASTNode):
    def __init__(self, value):
        self.value = value


class BreakStatement(ASTNode):
    pass


class ContinueStatement(ASTNode):
    pass


class ArrayAccess(ASTNode):
    def __init__(self, array_name, index):
        self.array_name = array_name
        self.index = index


class FieldAccess(ASTNode):
    def __init__(self, base, field_name):
        self.base = base
        self.field_name = field_name


class BinaryExpression(ASTNode):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right


class UnaryExpression(ASTNode):
    def __init__(self, operator, operand):
        self.operator = operator
        self.operand = operand


class IfStatement(ASTNode):
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch


class WhileStatement(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body


class ForStatement(ASTNode):
    def __init__(self, initializer, condition, update, body):
        self.initializer = initializer
        self.condition = condition
        self.update = update
        self.body = body


class FunctionDefinition(ASTNode):
    def __init__(self, return_type, name, parameters, body):
        self.return_type = return_type
        self.name = name
        self.parameters = parameters
        self.body = body


class FunctionCall(ASTNode):
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek(self, offset):
        index = self.pos + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return None

    def advance(self):
        self.pos += 1

    def expect(self, token_type, value=None):
        token = self.current_token()
        if token and token[0] == token_type and (value is None or token[1] == value):
            self.advance()
            return token
        line = token[2] if token else "EOF"
        col = token[3] if token else ""
        expected = f"{token_type} {value}" if value else token_type
        actual = f"{token[0]} '{token[1]}'" if token else "EOF"
        raise SyntaxError(f"Line {line}, Col {col}: Expected {expected}, but got {actual}.")

    def parse_program(self):
        declarations = []
        while self.current_token():
            declarations.append(self.parse_global_declaration())
        return Program(declarations)

    def parse_global_declaration(self):
        if self._starts_struct_definition():
            return self.parse_struct_definition()

        _, parsed_type = self.parse_type()
        name_tok = self.expect("IDENTIFIER")
        if self._match_symbol("("):
            return self.parse_function_definition(parsed_type, name_tok[1])
        if self._match_symbol("["):
            return self.parse_array_declaration_with_prefix(parsed_type, name_tok[1])
        return self.parse_declaration_with_prefix(parsed_type, name_tok[1], expect_semicolon=True)

    def parse_struct_definition(self):
        self.expect("KEYWORD", "struct")
        name = self.expect("IDENTIFIER")[1]
        self.expect("SYMBOL", "{")
        fields = []
        while not self._match_symbol("}"):
            _, field_type = self.parse_type()
            field_name = self.expect("IDENTIFIER")[1]
            self.expect("SYMBOL", ";")
            fields.append((field_type, field_name))
        self.expect("SYMBOL", "}")
        self.expect("SYMBOL", ";")
        return StructDefinition(name, fields)

    def parse_declaration_with_prefix(self, parsed_type, var_name, expect_semicolon):
        if self._match_symbol("["):
            self.expect("SYMBOL", "[")
            size = int(self.expect("NUMBER")[1])
            self.expect("SYMBOL", "]")
            if expect_semicolon:
                self.expect("SYMBOL", ";")
            return ArrayDeclaration(parsed_type, var_name, size)

        if self.is_struct_type(parsed_type):
            if not expect_semicolon or not self._match_symbol(";"):
                token = self.current_token()
                raise SyntaxError(
                    f"Line {token[2]}, Col {token[3]}: Struct variables must use 'struct Name value;' syntax."
                )
            self.expect("SYMBOL", ";")
            return StructDeclaration(parsed_type, var_name)

        self.expect("SYMBOL", "=")
        value_expr = self.parse_expression()
        if expect_semicolon:
            self.expect("SYMBOL", ";")
        return VariableDeclaration(parsed_type, var_name, value_expr)

    def parse_array_declaration_with_prefix(self, element_type, array_name):
        self.expect("SYMBOL", "[")
        size = int(self.expect("NUMBER")[1])
        self.expect("SYMBOL", "]")
        self.expect("SYMBOL", ";")
        return ArrayDeclaration(element_type, array_name, size)

    def parse_function_definition(self, return_type, name):
        self.expect("SYMBOL", "(")
        parameters = []
        if not self._match_symbol(")"):
            parameters = self.parse_parameter_list()
        self.expect("SYMBOL", ")")
        body = self.parse_block()
        return FunctionDefinition(return_type, name, parameters, body)

    def parse_parameter_list(self):
        params = []
        while True:
            _, param_type = self.parse_type()
            param_name = self.expect("IDENTIFIER")[1]
            params.append((param_type, param_name))
            if self._match_symbol(","):
                self.expect("SYMBOL", ",")
            else:
                break
        return params

    def parse_statement(self):
        token = self.current_token()
        if token[0] == "KEYWORD":
            if token[1] in ["int", "float", "bool"]:
                return self.parse_variable_declaration()
            if token[1] == "struct":
                if self._starts_struct_definition():
                    raise SyntaxError("Struct definitions are only allowed at global scope.")
                return self.parse_variable_declaration()
            if token[1] == "return":
                return self.parse_return_statement()
            if token[1] == "if":
                return self.parse_if_statement()
            if token[1] == "while":
                return self.parse_while_statement()
            if token[1] == "for":
                return self.parse_for_statement()
            if token[1] == "break":
                return self.parse_break_statement()
            if token[1] == "continue":
                return self.parse_continue_statement()
        if token[0] == "SYMBOL" and token[1] == "{":
            return self.parse_block()
        if token[0] == "SYMBOL" and token[1] == "*":
            return self.parse_pointer_assignment_statement()
        if token[0] == "IDENTIFIER":
            return self.parse_assignment_or_function_call()
        raise SyntaxError(f"Unexpected token {token}")

    def parse_block(self):
        self.expect("SYMBOL", "{")
        statements = []
        while self.current_token() and not self._match_symbol("}"):
            statements.append(self.parse_statement())
        self.expect("SYMBOL", "}")
        return Block(statements)

    def parse_variable_declaration(self):
        return self.parse_variable_declaration_core(expect_semicolon=True)

    def parse_variable_declaration_core(self, expect_semicolon):
        _, parsed_type = self.parse_type()
        var_name = self.expect("IDENTIFIER")[1]
        return self.parse_declaration_with_prefix(parsed_type, var_name, expect_semicolon)

    def parse_pointer_assignment_statement(self):
        pointer_expr = self.parse_unary()
        self.expect("SYMBOL", "=")
        value_expr = self.parse_expression()
        self.expect("SYMBOL", ";")
        return PointerAssignment(pointer_expr, value_expr)

    def parse_assignment_or_function_call(self):
        ident = self.expect("IDENTIFIER")[1]
        if self._match_symbol("("):
            fc = self.parse_function_call(ident)
            self.expect("SYMBOL", ";")
            return fc

        target = self.parse_postfix_tail(ident)
        self.expect("SYMBOL", "=")
        value_expr = self.parse_expression()
        self.expect("SYMBOL", ";")

        if isinstance(target, str):
            return Assignment(target, value_expr)
        if isinstance(target, ArrayAccess):
            return ArrayAssignment(target.array_name, target.index, value_expr)
        if isinstance(target, FieldAccess):
            return FieldAssignment(target, value_expr)
        raise SyntaxError("Invalid assignment target.")

    def parse_return_statement(self):
        self.expect("KEYWORD", "return")
        value_expr = self.parse_expression()
        self.expect("SYMBOL", ";")
        return ReturnStatement(value_expr)

    def parse_break_statement(self):
        self.expect("KEYWORD", "break")
        self.expect("SYMBOL", ";")
        return BreakStatement()

    def parse_continue_statement(self):
        self.expect("KEYWORD", "continue")
        self.expect("SYMBOL", ";")
        return ContinueStatement()

    def parse_if_statement(self):
        self.expect("KEYWORD", "if")
        self.expect("SYMBOL", "(")
        condition = self.parse_expression()
        self.expect("SYMBOL", ")")
        then_branch = self.parse_statement()
        else_branch = None
        if self.current_token() and self.current_token()[0] == "KEYWORD" and self.current_token()[1] == "else":
            self.expect("KEYWORD", "else")
            else_branch = self.parse_statement()
        return IfStatement(condition, then_branch, else_branch)

    def parse_while_statement(self):
        self.expect("KEYWORD", "while")
        self.expect("SYMBOL", "(")
        condition = self.parse_expression()
        self.expect("SYMBOL", ")")
        body = self.parse_statement()
        return WhileStatement(condition, body)

    def parse_for_statement(self):
        self.expect("KEYWORD", "for")
        self.expect("SYMBOL", "(")
        initializer = self.parse_for_initializer()
        self.expect("SYMBOL", ";")
        condition = None
        if not self._match_symbol(";"):
            condition = self.parse_expression()
        self.expect("SYMBOL", ";")
        update = None
        if not self._match_symbol(")"):
            update = self.parse_for_update()
        self.expect("SYMBOL", ")")
        body = self.parse_statement()
        return ForStatement(initializer, condition, update, body)

    def parse_for_initializer(self):
        token = self.current_token()
        if token[0] == "KEYWORD" and token[1] in ["int", "float", "bool", "struct"]:
            return self.parse_variable_declaration_core(expect_semicolon=False)
        if token[0] == "IDENTIFIER":
            ident = self.expect("IDENTIFIER")[1]
            if self._match_symbol("("):
                return self.parse_function_call(ident)

            target = self.parse_postfix_tail(ident)
            self.expect("SYMBOL", "=")
            value_expr = self.parse_expression()
            if isinstance(target, str):
                return Assignment(target, value_expr)
            if isinstance(target, ArrayAccess):
                return ArrayAssignment(target.array_name, target.index, value_expr)
            if isinstance(target, FieldAccess):
                return FieldAssignment(target, value_expr)
            raise SyntaxError("Invalid assignment target in for-loop initializer.")
        return None

    def parse_for_update(self):
        token = self.current_token()
        if token[0] != "IDENTIFIER":
            raise SyntaxError(f"Expected assignment or function call in for-loop update, but got {token}.")
        ident = self.expect("IDENTIFIER")[1]
        if self._match_symbol("("):
            return self.parse_function_call(ident)

        target = self.parse_postfix_tail(ident)
        self.expect("SYMBOL", "=")
        value_expr = self.parse_expression()
        if isinstance(target, str):
            return Assignment(target, value_expr)
        if isinstance(target, ArrayAccess):
            return ArrayAssignment(target.array_name, target.index, value_expr)
        if isinstance(target, FieldAccess):
            return FieldAssignment(target, value_expr)
        raise SyntaxError("Invalid assignment target in for-loop update.")

    def parse_expression(self):
        return self.parse_logical_or()

    def parse_logical_or(self):
        node = self.parse_logical_and()
        while self.current_token() and self.current_token()[0] == "LOR":
            op = self.expect("LOR")[1]
            right = self.parse_logical_and()
            node = BinaryExpression(node, op, right)
        return node

    def parse_logical_and(self):
        node = self.parse_equality()
        while self.current_token() and self.current_token()[0] == "LAND":
            op = self.expect("LAND")[1]
            right = self.parse_equality()
            node = BinaryExpression(node, op, right)
        return node

    def parse_equality(self):
        node = self.parse_relational()
        while self.current_token() and self.current_token()[0] in ["EQ", "NEQ"]:
            if self.current_token()[0] == "EQ":
                op = self.expect("EQ")[1]
            else:
                op = self.expect("NEQ")[1]
            right = self.parse_relational()
            node = BinaryExpression(node, op, right)
        return node

    def parse_relational(self):
        node = self.parse_addition()
        while self.current_token() and (
            (self.current_token()[0] == "SYMBOL" and self.current_token()[1] in ["<", ">"])
            or self.current_token()[0] in ["LE", "GE"]
        ):
            token = self.current_token()
            if token[0] in ["LE", "GE"]:
                op = self.expect(token[0])[1]
            else:
                op = self.expect("SYMBOL")[1]
            right = self.parse_addition()
            node = BinaryExpression(node, op, right)
        return node

    def parse_addition(self):
        node = self.parse_term()
        while self.current_token() and self.current_token()[0] == "SYMBOL" and self.current_token()[1] in ["+", "-"]:
            op = self.expect("SYMBOL")[1]
            right = self.parse_term()
            node = BinaryExpression(node, op, right)
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.current_token() and self.current_token()[0] == "SYMBOL" and self.current_token()[1] in ["*", "/", "%"]:
            op = self.expect("SYMBOL")[1]
            right = self.parse_factor()
            node = BinaryExpression(node, op, right)
        return node

    def parse_factor(self):
        node = self.parse_unary()
        if self.current_token() and self.current_token()[0] == "EXP":
            self.expect("EXP", "^")
            right = self.parse_factor()
            node = BinaryExpression(node, "^", right)
        return node

    def parse_unary(self):
        token = self.current_token()
        if token and token[0] == "SYMBOL" and token[1] in ["!", "-", "&", "*"]:
            operator = self.expect("SYMBOL")[1]
            operand = self.parse_unary()
            return UnaryExpression(operator, operand)
        return self.parse_primary()

    def parse_type(self):
        type_tok = self.expect("KEYWORD")
        if type_tok[1] in ["int", "float", "bool"]:
            parsed_type = type_tok[1]
            while self._match_symbol("*"):
                self.expect("SYMBOL", "*")
                parsed_type += "*"
            return type_tok, parsed_type

        if type_tok[1] == "struct":
            struct_name = self.expect("IDENTIFIER")[1]
            parsed_type = f"struct {struct_name}"
            while self._match_symbol("*"):
                self.expect("SYMBOL", "*")
                parsed_type += "*"
            return type_tok, parsed_type

        raise SyntaxError(f"Expected type but got '{type_tok[1]}'.")

    def parse_primary(self):
        token = self.current_token()
        if token[0] == "FLOAT":
            return float(self.expect("FLOAT")[1])
        if token[0] == "NUMBER":
            return int(self.expect("NUMBER")[1])
        if token[0] == "KEYWORD" and token[1] in ["true", "false"]:
            return self.expect("KEYWORD")[1]
        if token[0] == "IDENTIFIER":
            ident = self.expect("IDENTIFIER")[1]
            if self._match_symbol("("):
                return self.parse_function_call(ident)
            return self.parse_postfix_tail(ident)
        if token[0] == "SYMBOL" and token[1] == "(":
            self.expect("SYMBOL", "(")
            node = self.parse_expression()
            self.expect("SYMBOL", ")")
            return node
        raise SyntaxError(f"Expected primary expression but got {token}")

    def parse_postfix_tail(self, node):
        while self.current_token():
            if self._match_symbol("["):
                if not isinstance(node, str):
                    raise SyntaxError("Array access is only supported on named arrays.")
                self.expect("SYMBOL", "[")
                index_expr = self.parse_expression()
                self.expect("SYMBOL", "]")
                node = ArrayAccess(node, index_expr)
                continue
            if self._match_symbol("."):
                self.expect("SYMBOL", ".")
                field_name = self.expect("IDENTIFIER")[1]
                node = FieldAccess(node, field_name)
                continue
            if self.current_token()[0] == "ARROW":
                self.expect("ARROW")
                field_name = self.expect("IDENTIFIER")[1]
                node = FieldAccess(UnaryExpression("*", node), field_name)
                continue
            break
        return node

    def parse_function_call(self, func_name):
        self.expect("SYMBOL", "(")
        arguments = []
        if not self._match_symbol(")"):
            arguments = self.parse_argument_list()
        self.expect("SYMBOL", ")")
        return FunctionCall(func_name, arguments)

    def parse_argument_list(self):
        args = []
        while True:
            args.append(self.parse_expression())
            if self._match_symbol(","):
                self.expect("SYMBOL", ",")
            else:
                break
        return args

    def is_struct_type(self, type_name):
        return type_name.startswith("struct ") and not type_name.endswith("*")

    def _match_symbol(self, value):
        token = self.current_token()
        return token is not None and token[0] == "SYMBOL" and token[1] == value

    def _starts_struct_definition(self):
        current = self.current_token()
        second = self.peek(1)
        third = self.peek(2)
        return (
            current is not None
            and current[0] == "KEYWORD"
            and current[1] == "struct"
            and second is not None
            and second[0] == "IDENTIFIER"
            and third is not None
            and third[0] == "SYMBOL"
            and third[1] == "{"
        )
