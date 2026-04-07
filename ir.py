from dataclasses import dataclass, field

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


@dataclass
class IRInstruction:
    opcode: str
    operands: tuple = field(default_factory=tuple)


@dataclass
class IRProgram:
    instructions: list


class IRGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0
        self.aggregate_count = 0
        self.function_labels = {}
        self.function_return_types = {}
        self.struct_definitions = {}
        self.global_symbols = {}
        self.scope_stack = []
        self.current_function_return_type = None
        self.current_function_return_buffer = None
        self.loop_stack = []

    def build(self, program):
        self.generate(program)
        return IRProgram(self.instructions)

    def emit(self, opcode, *operands):
        self.instructions.append(IRInstruction(opcode, operands))

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self, prefix):
        self.label_count += 1
        return f"{prefix}_{self.label_count}"

    def new_aggregate(self):
        self.aggregate_count += 1
        return f"agg{self.aggregate_count}"

    def generate(self, node):
        if isinstance(node, Program):
            self.visit_program(node)
        elif isinstance(node, StructDefinition):
            return
        elif isinstance(node, Block):
            self.visit_block(node)
        elif isinstance(node, VariableDeclaration):
            self.visit_variable_declaration(node)
        elif isinstance(node, StructDeclaration):
            self.visit_struct_declaration(node)
        elif isinstance(node, ArrayDeclaration):
            self.visit_array_declaration(node)
        elif isinstance(node, Assignment):
            self.visit_assignment(node)
        elif isinstance(node, ArrayAssignment):
            self.visit_array_assignment(node)
        elif isinstance(node, FieldAssignment):
            self.visit_field_assignment(node)
        elif isinstance(node, PointerAssignment):
            self.visit_pointer_assignment(node)
        elif isinstance(node, ReturnStatement):
            self.visit_return_statement(node)
        elif isinstance(node, BreakStatement):
            self.visit_break_statement()
        elif isinstance(node, ContinueStatement):
            self.visit_continue_statement()
        elif isinstance(node, IfStatement):
            self.visit_if_statement(node)
        elif isinstance(node, WhileStatement):
            self.visit_while_statement(node)
        elif isinstance(node, ForStatement):
            self.visit_for_statement(node)
        elif isinstance(node, FunctionDefinition):
            self.visit_function_definition(node)
        elif isinstance(node, FunctionCall):
            return self.evaluate_expression(node)
        elif isinstance(node, UnaryExpression):
            return self.evaluate_expression(node)

    def visit_program(self, node):
        entry_label = "__entry"
        for decl in node.declarations:
            if isinstance(decl, StructDefinition):
                self.struct_definitions[decl.name] = decl.fields
            elif isinstance(decl, FunctionDefinition):
                self.function_labels[decl.name] = f"func_{decl.name}"
                self.function_return_types[decl.name] = decl.return_type
            elif isinstance(decl, VariableDeclaration):
                self.global_symbols[decl.var_name] = self.make_symbol_info(decl.var_type)
            elif isinstance(decl, StructDeclaration):
                self.global_symbols[decl.var_name] = self.make_symbol_info(decl.struct_type)
            elif isinstance(decl, ArrayDeclaration):
                self.global_symbols[decl.array_name] = {
                    "kind": "array",
                    "type": decl.element_type,
                    "size": decl.size,
                }

        for decl in node.declarations:
            if isinstance(decl, (VariableDeclaration, StructDeclaration, ArrayDeclaration)):
                self.generate(decl)

        if self.function_labels:
            self.emit("JMP", entry_label)

        for decl in node.declarations:
            if isinstance(decl, FunctionDefinition):
                self.generate(decl)

        self.emit("LABEL", entry_label)
        if "main" in self.function_labels:
            self.emit("CALL", self.function_labels["main"], tuple(), "t0")
            self.emit("HALT")

    def visit_function_definition(self, node):
        old_return_type = self.current_function_return_type
        old_return_buffer = self.current_function_return_buffer
        self.current_function_return_type = node.return_type
        self.current_function_return_buffer = "__retbuf" if self.is_aggregate_type(node.return_type) else None

        self.scope_stack.append({})
        self.emit("LABEL", self.function_labels[node.name])

        arg_index = 0
        if self.current_function_return_buffer is not None:
            self.emit("ALLOC", self.current_function_return_buffer, 1)
            self.emit("MOV", self.current_function_return_buffer, "__arg0")
            arg_index = 1

        for param_type, param_name in node.parameters:
            self.declare_local(param_name, self.make_symbol_info(param_type))
            self.emit("ALLOC", param_name, self.type_size(param_type))
            if self.is_aggregate_type(param_type):
                param_ptr = self.address_of_name(param_name, param_type)
                self.emit("COPY", param_ptr, f"__arg{arg_index}", self.type_size(param_type))
            else:
                self.emit("MOV", param_name, f"__arg{arg_index}")
            arg_index += 1

        self.generate(node.body)
        if not self.instructions or self.instructions[-1].opcode != "RET":
            self.emit("RET")
        self.scope_stack.pop()

        self.current_function_return_type = old_return_type
        self.current_function_return_buffer = old_return_buffer

    def visit_block(self, node):
        self.scope_stack.append({})
        for stmt in node.statements:
            self.generate(stmt)
        self.scope_stack.pop()

    def visit_variable_declaration(self, node):
        if self.scope_stack:
            self.declare_local(node.var_name, self.make_symbol_info(node.var_type))
        self.emit("ALLOC", node.var_name, 1)
        value = self.evaluate_expression(node.value)
        if node.var_type == "bool":
            value = self.normalize_bool_value(value)
        self.emit("MOV", node.var_name, value)

    def visit_struct_declaration(self, node):
        if self.scope_stack:
            self.declare_local(node.var_name, self.make_symbol_info(node.struct_type))
        self.emit("ALLOC", node.var_name, self.type_size(node.struct_type))

    def visit_array_declaration(self, node):
        if self.scope_stack:
            self.declare_local(
                node.array_name,
                {"kind": "array", "type": node.element_type, "size": node.size},
            )
        self.emit("ALLOC", node.array_name, node.size * self.type_size(node.element_type))

    def visit_assignment(self, node):
        target_info = self.lookup_symbol_info(node.var_name)
        if target_info["kind"] == "struct":
            src_ptr = self.get_address(node.value)
            dest_ptr = self.address_of_name(node.var_name, target_info["type"])
            self.emit("COPY", dest_ptr, src_ptr, self.type_size(target_info["type"]))
            return
        value = self.evaluate_expression(node.value)
        if target_info["type"] == "bool":
            value = self.normalize_bool_value(value)
        self.emit("MOV", node.var_name, value)

    def visit_array_assignment(self, node):
        element_type = self.lookup_array_element_type(node.array_name)
        address = self.get_address(ArrayAccess(node.array_name, node.index))
        if self.is_aggregate_type(element_type):
            src_ptr = self.get_address(node.value)
            self.emit("COPY", address, src_ptr, self.type_size(element_type))
            return
        value = self.evaluate_expression(node.value)
        if element_type == "bool":
            value = self.normalize_bool_value(value)
        self.emit("STOREPTR", address, value)

    def visit_field_assignment(self, node):
        field_type = self.infer_expression_type(node.field_access)
        address = self.get_address(node.field_access)
        if self.is_aggregate_type(field_type):
            src_ptr = self.get_address(node.value)
            self.emit("COPY", address, src_ptr, self.type_size(field_type))
            return
        value = self.evaluate_expression(node.value)
        if field_type == "bool":
            value = self.normalize_bool_value(value)
        self.emit("STOREPTR", address, value)

    def visit_pointer_assignment(self, node):
        target_type = self.infer_expression_type(node.pointer_expr.operand)
        pointer = self.evaluate_expression(node.pointer_expr.operand)
        pointee_type = self.pointee_type(target_type)
        if self.is_aggregate_type(pointee_type):
            src_ptr = self.get_address(node.value)
            self.emit("COPY", pointer, src_ptr, self.type_size(pointee_type))
            return
        value = self.evaluate_expression(node.value)
        if pointee_type == "bool":
            value = self.normalize_bool_value(value)
        self.emit("STOREPTR", pointer, value)

    def visit_return_statement(self, node):
        if self.is_aggregate_type(self.current_function_return_type):
            src_ptr = self.get_address(node.value)
            self.emit("COPY", self.current_function_return_buffer, src_ptr, self.type_size(self.current_function_return_type))
            self.emit("RET")
            return
        value = self.evaluate_expression(node.value)
        if self.current_function_return_type == "bool":
            value = self.normalize_bool_value(value)
        self.emit("MOV", "ret", value)
        self.emit("RET")

    def visit_break_statement(self):
        self.emit("JMP", self.loop_stack[-1]["break"])

    def visit_continue_statement(self):
        self.emit("JMP", self.loop_stack[-1]["continue"])

    def visit_if_statement(self, node):
        cond = self.emit_bool_expression(node.condition)
        else_label = self.new_label("else")
        end_label = self.new_label("endif")
        self.emit("CMP", cond, "0")
        self.emit("JE", else_label)
        self.generate(node.then_branch)
        self.emit("JMP", end_label)
        self.emit("LABEL", else_label)
        if node.else_branch:
            self.generate(node.else_branch)
        self.emit("LABEL", end_label)

    def visit_while_statement(self, node):
        start_label = self.new_label("while_start")
        end_label = self.new_label("while_end")
        self.loop_stack.append({"break": end_label, "continue": start_label})
        self.emit("LABEL", start_label)
        cond = self.emit_bool_expression(node.condition)
        self.emit("CMP", cond, "0")
        self.emit("JE", end_label)
        self.generate(node.body)
        self.emit("JMP", start_label)
        self.emit("LABEL", end_label)
        self.loop_stack.pop()

    def visit_for_statement(self, node):
        start_label = self.new_label("for_start")
        end_label = self.new_label("for_end")
        update_label = self.new_label("for_update")
        if node.initializer is not None:
            self.generate(node.initializer)
        self.loop_stack.append({"break": end_label, "continue": update_label})
        self.emit("LABEL", start_label)
        if node.condition is not None:
            cond = self.emit_bool_expression(node.condition)
            self.emit("CMP", cond, "0")
            self.emit("JE", end_label)
        self.generate(node.body)
        self.emit("LABEL", update_label)
        if node.update is not None:
            self.generate(node.update)
        self.emit("JMP", start_label)
        self.emit("LABEL", end_label)
        self.loop_stack.pop()

    def evaluate_expression(self, expr):
        expr_type = self.infer_expression_type(expr)
        if self.is_aggregate_type(expr_type):
            raise Exception(f"Aggregate expression '{expr}' requires address context.")
        if isinstance(expr, int):
            return str(expr)
        if isinstance(expr, float):
            return str(expr)
        if isinstance(expr, str):
            if expr == "true":
                return "1"
            if expr == "false":
                return "0"
            return expr
        if isinstance(expr, (ArrayAccess, FieldAccess)):
            address = self.get_address(expr)
            temp = self.new_temp()
            self.emit("LOADPTR", temp, address)
            return temp
        if isinstance(expr, UnaryExpression):
            if expr.operator == "&":
                return self.get_address(expr.operand)
            if expr.operator == "*":
                pointer = self.evaluate_expression(expr.operand)
                temp = self.new_temp()
                self.emit("LOADPTR", temp, pointer)
                return temp
            operand = self.evaluate_expression(expr.operand)
            temp = self.new_temp()
            if expr.operator == "-":
                self.emit("SUB", temp, "0", operand)
            elif expr.operator == "!":
                normalized = self.normalize_bool_value(operand)
                self.emit("CMP", normalized, "0")
                self.emit("SETE", temp)
            else:
                raise Exception(f"Unsupported unary operator '{expr.operator}'.")
            return temp
        if isinstance(expr, BinaryExpression):
            left = self.evaluate_expression(expr.left)
            right = self.evaluate_expression(expr.right)
            left_type = self.infer_expression_type(expr.left)
            right_type = self.infer_expression_type(expr.right)
            temp = self.new_temp()
            if expr.operator == "+":
                if self.is_pointer_type(left_type) and right_type == "int":
                    self.emit("PTRADD", temp, left, right)
                    return temp
                if left_type == "int" and self.is_pointer_type(right_type):
                    self.emit("PTRADD", temp, right, left)
                    return temp
                self.emit("ADD", temp, left, right)
            elif expr.operator == "-":
                if self.is_pointer_type(left_type) and right_type == "int":
                    self.emit("PTRSUB", temp, left, right)
                    return temp
                self.emit("SUB", temp, left, right)
            elif expr.operator == "*":
                self.emit("MUL", temp, left, right)
            elif expr.operator == "/":
                self.emit("DIV", temp, left, right)
            elif expr.operator == "%":
                self.emit("MOD", temp, left, right)
            elif expr.operator == "^":
                self.emit("POW", temp, left, right)
            elif expr.operator == "<":
                self.emit("CMP", left, right)
                self.emit("SETL", temp)
            elif expr.operator == ">":
                self.emit("CMP", left, right)
                self.emit("SETG", temp)
            elif expr.operator == "<=":
                self.emit("CMP", left, right)
                self.emit("SETLE", temp)
            elif expr.operator == ">=":
                self.emit("CMP", left, right)
                self.emit("SETGE", temp)
            elif expr.operator == "==":
                self.emit("CMP", left, right)
                self.emit("SETE", temp)
            elif expr.operator == "!=":
                self.emit("CMP", left, right)
                self.emit("SETNE", temp)
            elif expr.operator == "&&":
                left = self.normalize_bool_value(left)
                right = self.normalize_bool_value(right)
                self.emit("AND", temp, left, right)
            elif expr.operator == "||":
                left = self.normalize_bool_value(left)
                right = self.normalize_bool_value(right)
                self.emit("OR", temp, left, right)
            else:
                raise Exception(f"Unsupported operator '{expr.operator}'.")
            return temp
        if isinstance(expr, FunctionCall):
            return self.visit_function_call(expr)
        raise Exception(f"Unsupported expression type: {expr}")

    def visit_function_call(self, node):
        return_type = self.function_return_types[node.name]
        args = []
        if self.is_aggregate_type(return_type):
            temp_name = self.new_aggregate()
            self.emit("ALLOC", temp_name, self.type_size(return_type))
            retbuf = self.address_of_name(temp_name, return_type)
            args.append(retbuf)
        else:
            temp_name = self.new_temp()

        for argument in node.arguments:
            arg_type = self.infer_expression_type(argument)
            if self.is_aggregate_type(arg_type):
                args.append(self.get_address(argument))
            else:
                args.append(self.evaluate_expression(argument))

        self.emit("CALL", self.function_labels[node.name], tuple(args), temp_name)
        return temp_name

    def get_address(self, expr):
        expr_type = self.infer_expression_type(expr)
        if isinstance(expr, str):
            return self.address_of_name(expr, expr_type)
        if isinstance(expr, ArrayAccess):
            array_info = self.lookup_symbol_info(expr.array_name)
            base = self.address_of_name(
                expr.array_name,
                array_info["type"],
                self.storage_size(array_info),
            )
            index = self.evaluate_expression(expr.index)
            temp = self.new_temp()
            self.emit("INDEXADDR", temp, base, index, self.type_size(expr_type), self.type_size(expr_type))
            return temp
        if isinstance(expr, FieldAccess):
            base_ptr = self.get_address_of_field_base(expr.base)
            offset = self.field_offset(self.struct_base_type(expr.base), expr.field_name)
            temp = self.new_temp()
            self.emit("FIELDPTR", temp, base_ptr, offset, self.type_size(expr_type), self.type_size(expr_type))
            return temp
        if isinstance(expr, UnaryExpression) and expr.operator == "&":
            return self.get_address(expr.operand)
        if isinstance(expr, UnaryExpression) and expr.operator == "*":
            return self.evaluate_expression(expr.operand)
        if isinstance(expr, FunctionCall):
            result = self.visit_function_call(expr)
            return self.address_of_name(result, expr_type)
        raise Exception(f"Expression is not addressable: {expr}")

    def get_address_of_field_base(self, expr):
        base_type = self.struct_base_type(expr)
        if isinstance(expr, str):
            return self.address_of_name(expr, base_type)
        if isinstance(expr, ArrayAccess):
            return self.get_address(expr)
        if isinstance(expr, FieldAccess):
            return self.get_address(expr)
        if isinstance(expr, UnaryExpression) and expr.operator == "*":
            return self.evaluate_expression(expr.operand)
        if isinstance(expr, FunctionCall):
            return self.get_address(expr)
        raise Exception(f"Unsupported field base: {expr}")

    def address_of_name(self, name, type_name, span=None):
        temp = self.new_temp()
        pointee_span = self.type_size(type_name) if span is None else span
        self.emit("ADDR", temp, name, self.type_size(type_name), pointee_span)
        return temp

    def normalize_bool_value(self, value):
        temp = self.new_temp()
        self.emit("CMP", value, "0")
        self.emit("SETNE", temp)
        return temp

    def emit_bool_expression(self, expr):
        return self.normalize_bool_value(self.evaluate_expression(expr))

    def type_size(self, type_name):
        if self.is_pointer_type(type_name):
            return 1
        if type_name in ["int", "float", "bool"]:
            return 1
        return sum(self.type_size(field_type) for field_type, _ in self.get_struct_fields(type_name))

    def storage_size(self, symbol_info):
        if symbol_info["kind"] == "array":
            return symbol_info["size"] * self.type_size(symbol_info["type"])
        return self.type_size(symbol_info["type"])

    def field_offset(self, struct_type, field_name):
        offset = 0
        for field_type, candidate_name in self.get_struct_fields(struct_type):
            if candidate_name == field_name:
                return offset
            offset += self.type_size(field_type)
        raise Exception(f"Unknown field '{field_name}' on {struct_type}.")

    def struct_base_type(self, expr):
        expr_type = self.infer_expression_type(expr)
        if isinstance(expr, UnaryExpression) and expr.operator == "*" and self.is_pointer_type(expr_type):
            expr_type = self.pointee_type(expr_type)
        return expr_type

    def get_struct_fields(self, struct_type):
        return self.struct_definitions[self.struct_name_from_type(struct_type)]

    def declare_local(self, name, symbol_info):
        self.scope_stack[-1][name] = symbol_info

    def lookup_symbol_info(self, name):
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        return self.global_symbols[name]

    def lookup_array_element_type(self, name):
        return self.lookup_symbol_info(name)["type"]

    def make_symbol_info(self, type_name):
        if self.is_aggregate_type(type_name):
            return {"kind": "struct", "type": type_name}
        return {"kind": "scalar", "type": type_name}

    def infer_expression_type(self, expr):
        if isinstance(expr, int):
            return "int"
        if isinstance(expr, float):
            return "float"
        if isinstance(expr, str):
            if expr in ["true", "false"]:
                return "bool"
            return self.lookup_symbol_info(expr)["type"]
        if isinstance(expr, ArrayAccess):
            return self.lookup_array_element_type(expr.array_name)
        if isinstance(expr, FieldAccess):
            return self.lookup_field_type(self.struct_base_type(expr.base), expr.field_name)
        if isinstance(expr, UnaryExpression):
            operand_type = self.infer_expression_type(expr.operand)
            if expr.operator == "-":
                return operand_type
            if expr.operator == "!":
                return "bool"
            if expr.operator == "&":
                if isinstance(expr.operand, UnaryExpression) and expr.operand.operator == "*":
                    return self.infer_expression_type(expr.operand.operand)
                return self.infer_expression_type(expr.operand) + "*"
            if expr.operator == "*":
                return self.pointee_type(operand_type)
        if isinstance(expr, FunctionCall):
            return self.function_return_types[expr.name]
        if isinstance(expr, BinaryExpression):
            left_type = self.infer_expression_type(expr.left)
            right_type = self.infer_expression_type(expr.right)
            if expr.operator in ["+", "-"] and self.is_pointer_type(left_type) and right_type == "int":
                return left_type
            if expr.operator == "+" and left_type == "int" and self.is_pointer_type(right_type):
                return right_type
            if expr.operator in ["+", "-", "*", "/", "%", "^"]:
                if "float" in [left_type, right_type]:
                    return "float"
                return "int"
            return "bool"
        raise Exception(f"Unsupported expression type: {expr}")

    def lookup_field_type(self, struct_type, field_name):
        for field_type, candidate_name in self.get_struct_fields(struct_type):
            if candidate_name == field_name:
                return field_type
        raise Exception(f"Unknown field '{field_name}' on {struct_type}.")

    def is_pointer_type(self, type_name):
        return isinstance(type_name, str) and type_name.endswith("*")

    def is_aggregate_type(self, type_name):
        return isinstance(type_name, str) and type_name.startswith("struct ") and not type_name.endswith("*")

    def struct_name_from_type(self, type_name):
        return type_name.split(" ", 1)[1]

    def pointee_type(self, type_name):
        return type_name[:-1]
