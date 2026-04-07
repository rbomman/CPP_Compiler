from cpp_parser import (
    Assignment,
    ArrayAccess,
    ArrayAssignment,
    ArrayDeclaration,
    BinaryExpression,
    Block,
    BreakStatement,
    ContinueStatement,
    FieldAccess,
    FieldAssignment,
    ForStatement,
    FunctionCall,
    FunctionDefinition,
    IfStatement,
    PointerAssignment,
    Program,
    ReturnStatement,
    StructDeclaration,
    StructDefinition,
    UnaryExpression,
    VariableDeclaration,
    WhileStatement,
)


class SemanticError(Exception):
    """Custom exception for semantic errors during analysis."""


class SemanticAnalyzer:
    def __init__(self):
        self.global_symbols = {}
        self.function_table = {}
        self.struct_table = {}
        self.scope_stack = []
        self.current_function = None
        self.loop_depth = 0

    def analyze(self, node):
        if isinstance(node, Program):
            self._register_struct_definitions(node)
            self._validate_struct_definitions()
            self._register_global_symbols(node)
            for decl in node.declarations:
                self.analyze(decl)
        elif isinstance(node, StructDefinition):
            return
        elif isinstance(node, FunctionDefinition):
            self._validate_function_signature(node)
            old_function = self.current_function
            self.current_function = node
            self.scope_stack.append({})
            for param_type, param_name in node.parameters:
                self.declare_symbol(param_name, self.make_symbol_info(param_type))
            self.analyze(node.body)
            self.scope_stack.pop()
            self.current_function = old_function
        elif isinstance(node, Block):
            self.scope_stack.append({})
            for stmt in node.statements:
                self.analyze(stmt)
            self.scope_stack.pop()
        elif isinstance(node, VariableDeclaration):
            self.validate_type_exists(node.var_type)
            expr_type = self.infer_type(node.value)
            if self.is_struct_type(node.var_type):
                raise self.error("Struct values must be declared separately without an initializer.")
            if not self.is_assignable(node.var_type, expr_type):
                raise self.error(
                    f"Type mismatch in declaration of '{node.var_name}': declared "
                    f"{node.var_type}, got {expr_type}."
                )
            if self.scope_stack:
                self.declare_symbol(node.var_name, self.make_symbol_info(node.var_type))
        elif isinstance(node, StructDeclaration):
            self.validate_type_exists(node.struct_type)
            if self.scope_stack:
                self.declare_symbol(node.var_name, self.make_symbol_info(node.struct_type))
        elif isinstance(node, ArrayDeclaration):
            self.validate_type_exists(node.element_type)
            if node.size <= 0:
                raise self.error(f"Array '{node.array_name}' must have a positive size.")
            if self.scope_stack:
                self.declare_symbol(
                    node.array_name,
                    {"kind": "array", "type": node.element_type, "size": node.size},
                )
        elif isinstance(node, Assignment):
            target_symbol = self.lookup_symbol_info(node.var_name)
            expr_type = self.infer_type(node.value)
            if target_symbol["kind"] == "struct":
                var_type = target_symbol["type"]
            else:
                var_type = self.lookup_scalar_type(node.var_name)
            if not self.is_assignable(var_type, expr_type):
                raise self.error(
                    f"Type mismatch in assignment to '{node.var_name}': variable type "
                    f"{var_type}, but expression is {expr_type}."
                )
        elif isinstance(node, ArrayAssignment):
            index_type = self.infer_type(node.index)
            if index_type != "int":
                raise self.error(f"Array index for '{node.array_name}' must be int, got {index_type}.")
            element_type = self.lookup_array_type(node.array_name)
            value_type = self.infer_type(node.value)
            if not self.is_assignable(element_type, value_type):
                raise self.error(
                    f"Type mismatch in assignment to '{node.array_name}[]': element type "
                    f"{element_type}, but expression is {value_type}."
                )
        elif isinstance(node, FieldAssignment):
            field_type = self.infer_type(node.field_access)
            value_type = self.infer_type(node.value)
            if not self.is_assignable(field_type, value_type):
                raise self.error(
                    f"Type mismatch in assignment to field '{self.describe_field_access(node.field_access)}': "
                    f"field type {field_type}, but expression is {value_type}."
                )
        elif isinstance(node, PointerAssignment):
            if not isinstance(node.pointer_expr, UnaryExpression) or node.pointer_expr.operator != "*":
                raise self.error("Dereference assignment requires a pointer operand.")
            pointer_type = self.infer_type(node.pointer_expr.operand)
            if not self.is_pointer(pointer_type):
                raise self.error("Dereference assignment requires a pointer operand.")
            value_type = self.infer_type(node.value)
            target_type = self.pointee_type(pointer_type)
            if not self.is_assignable(target_type, value_type):
                raise self.error(
                    f"Type mismatch in pointer assignment: target type {target_type}, "
                    f"but expression is {value_type}."
                )
        elif isinstance(node, ReturnStatement):
            if self.current_function is None:
                raise self.error("Return statement is only valid inside a function.")
            return_type = self.infer_type(node.value)
            if not self.is_assignable(self.current_function.return_type, return_type):
                raise self.error(
                    f"Return type mismatch in function '{self.current_function.name}': "
                    f"expected {self.current_function.return_type}, got {return_type}."
                )
        elif isinstance(node, IfStatement):
            cond_type = self.infer_type(node.condition)
            if cond_type != "bool":
                raise self.error(f"Condition in if-statement must be bool, got {cond_type}.")
            self.analyze(node.then_branch)
            if node.else_branch:
                self.analyze(node.else_branch)
        elif isinstance(node, WhileStatement):
            cond_type = self.infer_type(node.condition)
            if cond_type != "bool":
                raise self.error(f"Condition in while-statement must be bool, got {cond_type}.")
            self.loop_depth += 1
            self.analyze(node.body)
            self.loop_depth -= 1
        elif isinstance(node, ForStatement):
            self.scope_stack.append({})
            self.loop_depth += 1
            if node.initializer is not None:
                self.analyze(node.initializer)
            if node.condition is not None:
                cond_type = self.infer_type(node.condition)
                if cond_type != "bool":
                    raise self.error(f"Condition in for-statement must be bool, got {cond_type}.")
            self.analyze(node.body)
            if node.update is not None:
                self.analyze(node.update)
            self.loop_depth -= 1
            self.scope_stack.pop()
        elif isinstance(node, BreakStatement):
            if self.loop_depth == 0:
                raise self.error("'break' is only valid inside a loop.")
        elif isinstance(node, ContinueStatement):
            if self.loop_depth == 0:
                raise self.error("'continue' is only valid inside a loop.")
        elif isinstance(node, FunctionCall):
            self._validate_function_call(node)
        elif isinstance(node, (ArrayAccess, FieldAccess, UnaryExpression, BinaryExpression)):
            self.infer_type(node)

    def infer_type(self, expr):
        if isinstance(expr, int):
            return "int"
        if isinstance(expr, float):
            return "float"
        if isinstance(expr, str):
            if expr in ["true", "false"]:
                return "bool"
            symbol = self.lookup_symbol_info(expr)
            return symbol["type"]
        if isinstance(expr, ArrayAccess):
            index_type = self.infer_type(expr.index)
            if index_type != "int":
                raise self.error(f"Array index for '{expr.array_name}' must be int, got {index_type}.")
            return self.lookup_array_type(expr.array_name)
        if isinstance(expr, FieldAccess):
            return self.lookup_field_access_type(expr)
        if isinstance(expr, UnaryExpression):
            operand_type = self.infer_type(expr.operand)
            if expr.operator == "-":
                if operand_type not in ["int", "float"]:
                    raise self.error(f"Operator '-' requires a numeric operand, got {operand_type}.")
                return operand_type
            if expr.operator == "!":
                if operand_type != "bool":
                    raise self.error(f"Operator '!' requires a bool operand, got {operand_type}.")
                return "bool"
            if expr.operator == "&":
                return self.address_of_type(expr.operand)
            if expr.operator == "*":
                if not self.is_pointer(operand_type):
                    raise self.error(f"Operator '*' requires a pointer operand, got {operand_type}.")
                return self.pointee_type(operand_type)
            raise self.error(f"Unsupported unary operator '{expr.operator}'.")
        if isinstance(expr, BinaryExpression):
            op = expr.operator
            left_type = self.infer_type(expr.left)
            right_type = self.infer_type(expr.right)
            if op in ["+", "-"] and self.is_pointer(left_type) and right_type == "int":
                return left_type
            if op == "+" and left_type == "int" and self.is_pointer(right_type):
                return right_type
            if op in ["+", "-", "*", "/", "%", "^"]:
                if not self.is_numeric(left_type) or not self.is_numeric(right_type):
                    raise self.error(
                        f"Operator '{op}' requires numeric operands, got {left_type} and {right_type}."
                    )
                if op == "/" and ("float" in [left_type, right_type]):
                    return "float"
                return self.promote_numeric(left_type, right_type)
            if op in ["<", ">", "<=", ">="]:
                if not self.is_numeric(left_type) or not self.is_numeric(right_type):
                    raise self.error(
                        f"Operator '{op}' requires numeric operands, got {left_type} and {right_type}."
                    )
                return "bool"
            if op in ["==", "!="]:
                if not (
                    left_type == right_type
                    or (self.is_numeric(left_type) and self.is_numeric(right_type))
                ):
                    raise self.error(
                        f"Operator '{op}' requires compatible operands, got {left_type} and {right_type}."
                    )
                return "bool"
            if op in ["&&", "||"]:
                if left_type != "bool" or right_type != "bool":
                    raise self.error(
                        f"Operator '{op}' requires bool operands, got {left_type} and {right_type}."
                    )
                return "bool"
            raise self.error(f"Unsupported operator '{op}'.")
        if isinstance(expr, FunctionCall):
            return self._validate_function_call(expr)
        raise self.error(f"Unsupported expression type: {expr}")

    def _register_struct_definitions(self, program):
        for decl in program.declarations:
            if not isinstance(decl, StructDefinition):
                continue
            if decl.name in self.struct_table:
                raise self.error(f"Struct '{decl.name}' is already defined.")
            field_map = {}
            field_order = []
            for field_type, field_name in decl.fields:
                if field_name in field_map:
                    raise self.error(f"Struct '{decl.name}' already defines field '{field_name}'.")
                field_map[field_name] = field_type
                field_order.append((field_type, field_name))
            self.struct_table[decl.name] = {"fields": field_map, "order": field_order}

    def _validate_struct_definitions(self):
        for struct_name, struct_info in self.struct_table.items():
            for field_type, _ in struct_info["order"]:
                self.validate_type_exists(field_type)
                if self.is_pointer(field_type):
                    continue
                if self.is_struct_type(field_type):
                    self._assert_struct_not_recursive(struct_name, field_type, [struct_name])

    def _assert_struct_not_recursive(self, root_name, field_type, path):
        nested_name = self.struct_name_from_type(field_type)
        if nested_name == root_name:
            raise self.error(
                f"Struct '{root_name}' cannot contain itself by value: {' -> '.join(path + [nested_name])}."
            )
        nested_info = self.struct_table[nested_name]
        for nested_field_type, _ in nested_info["order"]:
            if self.is_pointer(nested_field_type):
                continue
            if self.is_struct_type(nested_field_type):
                self._assert_struct_not_recursive(root_name, nested_field_type, path + [nested_name])

    def _register_global_symbols(self, program):
        for decl in program.declarations:
            if isinstance(decl, StructDefinition):
                continue
            if isinstance(decl, FunctionDefinition):
                if decl.name in self.function_table:
                    raise self.error(f"Function '{decl.name}' already defined.")
                self.function_table[decl.name] = decl
            elif isinstance(decl, VariableDeclaration):
                if decl.var_name in self.global_symbols:
                    raise self.error(f"Variable '{decl.var_name}' already declared.")
                self.validate_type_exists(decl.var_type)
                self.global_symbols[decl.var_name] = self.make_symbol_info(decl.var_type)
            elif isinstance(decl, StructDeclaration):
                if decl.var_name in self.global_symbols:
                    raise self.error(f"Variable '{decl.var_name}' already declared.")
                self.validate_type_exists(decl.struct_type)
                self.global_symbols[decl.var_name] = self.make_symbol_info(decl.struct_type)
            elif isinstance(decl, ArrayDeclaration):
                if decl.array_name in self.global_symbols:
                    raise self.error(f"Variable '{decl.array_name}' already declared.")
                self.validate_type_exists(decl.element_type)
                self.global_symbols[decl.array_name] = {
                    "kind": "array",
                    "type": decl.element_type,
                    "size": decl.size,
                }

    def _validate_function_signature(self, node):
        self.validate_type_exists(node.return_type)
        for param_type, _ in node.parameters:
            self.validate_type_exists(param_type)

    def declare_symbol(self, name, symbol_info):
        for scope in reversed(self.scope_stack):
            if name in scope:
                raise self.error(f"Variable '{name}' already declared in this scope.")
        self.scope_stack[-1][name] = symbol_info

    def lookup_symbol_info(self, name):
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        if name in self.global_symbols:
            return self.global_symbols[name]
        raise self.error(f"Undeclared variable '{name}'.")

    def lookup_scalar_type(self, name):
        symbol = self.lookup_symbol_info(name)
        if symbol["kind"] == "array":
            raise self.error(f"Array '{name}' cannot be used as a scalar value.")
        if symbol["kind"] == "struct":
            raise self.error(f"Struct '{name}' cannot be used as a scalar value.")
        return symbol["type"]

    def lookup_array_type(self, name):
        symbol = self.lookup_symbol_info(name)
        if symbol["kind"] != "array":
            raise self.error(f"Variable '{name}' is not an array.")
        return symbol["type"]

    def lookup_field_access_type(self, expr):
        base_type = self.lookup_struct_base_type(expr.base)
        field_type = self.lookup_field_type(base_type, expr.field_name)
        return field_type

    def lookup_struct_base_type(self, expr):
        if isinstance(expr, str):
            symbol = self.lookup_symbol_info(expr)
            if symbol["kind"] != "struct":
                raise self.error(f"Variable '{expr}' is not a struct.")
            return symbol["type"]
        base_type = self.infer_type(expr)
        if not self.is_struct_type(base_type):
            raise self.error("Field access requires a struct-valued base expression.")
        return base_type

    def lookup_field_type(self, struct_type, field_name):
        struct_name = self.struct_name_from_type(struct_type)
        struct_info = self.struct_table.get(struct_name)
        if struct_info is None:
            raise self.error(f"Struct '{struct_name}' is not defined.")
        if field_name not in struct_info["fields"]:
            raise self.error(f"Struct '{struct_name}' has no field named '{field_name}'.")
        return struct_info["fields"][field_name]

    def _validate_function_call(self, expr):
        if expr.name not in self.function_table:
            raise self.error(f"Function '{expr.name}' is not defined.")

        func_def = self.function_table[expr.name]
        if len(expr.arguments) != len(func_def.parameters):
            raise self.error(
                f"Function '{expr.name}' expects {len(func_def.parameters)} arguments, "
                f"got {len(expr.arguments)}."
            )

        for argument, (expected_type, _) in zip(expr.arguments, func_def.parameters):
            actual_type = self.infer_type(argument)
            if not self.is_assignable(expected_type, actual_type):
                raise self.error(
                    f"Function '{expr.name}' expects argument type {expected_type}, got {actual_type}."
                )

        return func_def.return_type

    def validate_type_exists(self, type_name):
        if self.is_pointer(type_name):
            self.validate_type_exists(self.pointee_type(type_name))
            return
        if type_name in ["int", "float", "bool"]:
            return
        if self.is_struct_type(type_name):
            if self.struct_name_from_type(type_name) not in self.struct_table:
                raise self.error(f"Unknown struct type '{type_name}'.")
            return
        raise self.error(f"Unknown type '{type_name}'.")

    def make_symbol_info(self, type_name):
        if self.is_struct_type(type_name):
            return {"kind": "struct", "type": type_name}
        return {"kind": "scalar", "type": type_name}

    def is_numeric(self, symbol_type):
        return symbol_type in ["int", "float"]

    def is_pointer(self, symbol_type):
        return isinstance(symbol_type, str) and symbol_type.endswith("*")

    def is_struct_type(self, symbol_type):
        return isinstance(symbol_type, str) and symbol_type.startswith("struct ") and not symbol_type.endswith("*")

    def struct_name_from_type(self, struct_type):
        return struct_type.split(" ", 1)[1]

    def pointee_type(self, symbol_type):
        return symbol_type[:-1]

    def address_of_type(self, operand):
        if isinstance(operand, str):
            symbol = self.lookup_symbol_info(operand)
            return symbol["type"] + "*"
        if isinstance(operand, ArrayAccess):
            return self.lookup_array_type(operand.array_name) + "*"
        if isinstance(operand, FieldAccess):
            return self.lookup_field_access_type(operand) + "*"
        if isinstance(operand, UnaryExpression) and operand.operator == "*":
            return self.infer_type(operand.operand)
        raise self.error("Operator '&' requires an addressable variable, field, or array element.")

    def promote_numeric(self, left_type, right_type):
        if "float" in [left_type, right_type]:
            return "float"
        return "int"

    def is_assignable(self, target_type, value_type):
        if target_type == value_type:
            return True
        return target_type == "float" and value_type == "int"

    def describe_field_access(self, expr):
        if isinstance(expr.base, str):
            return f"{expr.base}.{expr.field_name}"
        return f"{self.describe_field_access(expr.base)}.{expr.field_name}"

    def error(self, message):
        if self.current_function is not None:
            return SemanticError(f"In function '{self.current_function.name}': {message}")
        return SemanticError(message)
