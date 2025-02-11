# code_generator.py

from parser import Program, VariableDeclaration, Assignment, ReturnStatement, BinaryExpression

class CodeGenerator:
    def __init__(self):
        self.instructions = []

    def generate(self, node):
        if isinstance(node, Program):
            self.visit_program(node)
        elif isinstance(node, VariableDeclaration):
            self.visit_variable_declaration(node)
        elif isinstance(node, Assignment):
            self.visit_assignment(node)
        elif isinstance(node, ReturnStatement):
            self.visit_return_statement(node)
        # Note: BinaryExpression nodes are handled during expression evaluation.
        else:
            raise Exception("Unknown AST node: " + str(node))
        return self.instructions

    def visit_program(self, node):
        self.instructions.append("BEGIN")
        for stmt in node.statements:
            self.generate(stmt)
        self.instructions.append("END")

    def visit_variable_declaration(self, node):
        expr_val = self.evaluate_expression(node.value)
        self.instructions.append(f"MOV {node.var_name}, {expr_val}")

    def visit_assignment(self, node):
        expr_val = self.evaluate_expression(node.value)
        self.instructions.append(f"MOV {node.var_name}, {expr_val}")

    def visit_return_statement(self, node):
        expr_val = self.evaluate_expression(node.value)
        self.instructions.append(f"RET {expr_val}")

    def evaluate_expression(self, expr):
        if isinstance(expr, int):
            return str(expr)
        elif isinstance(expr, str):
            return expr
        elif isinstance(expr, BinaryExpression):
            left = self.evaluate_expression(expr.left)
            right = self.evaluate_expression(expr.right)
            return f"({left} {expr.operator} {right})"
        else:
            raise Exception("Unsupported expression type: " + str(expr))

# End of code_generator.py
