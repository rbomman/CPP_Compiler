# semantic_analyzer.py

from parser import Program, VariableDeclaration, Assignment, ReturnStatement, BinaryExpression

class SemanticError(Exception):
    pass

class SemanticAnalyzer:
    def __init__(self):
        # Symbol table mapping variable names to types (only 'int' supported)
        self.symbol_table = {}

    def analyze(self, node):
        if isinstance(node, Program):
            for stmt in node.statements:
                self.analyze(stmt)
        elif isinstance(node, VariableDeclaration):
            self.analyze_variable_declaration(node)
        elif isinstance(node, Assignment):
            self.analyze_assignment(node)
        elif isinstance(node, ReturnStatement):
            self.analyze_return_statement(node)
        elif isinstance(node, BinaryExpression):
            self.analyze_binary_expression(node)
        else:
            raise SemanticError(f"Unsupported AST node: {node}")

    def analyze_variable_declaration(self, node):
        if node.var_name in self.symbol_table:
            raise SemanticError(f"Variable '{node.var_name}' already declared.")
        if node.var_type != 'int':
            raise SemanticError(f"Unsupported type '{node.var_type}' for variable '{node.var_name}'.")
        self.symbol_table[node.var_name] = node.var_type
        # Analyze the initialization expression
        self.analyze_expression(node.value)

    def analyze_assignment(self, node):
        if node.var_name not in self.symbol_table:
            raise SemanticError(f"Assignment to undeclared variable '{node.var_name}'.")
        self.analyze_expression(node.value)

    def analyze_return_statement(self, node):
        self.analyze_expression(node.value)

    def analyze_binary_expression(self, node):
        # For now, only support '+' operator.
        if node.operator != '+':
            raise SemanticError(f"Unsupported operator: {node.operator}")
        self.analyze_expression(node.left)
        self.analyze_expression(node.right)

    def analyze_expression(self, expr):
        # Expression can be an int literal, an identifier, or a binary expression.
        if isinstance(expr, int):
            return
        elif isinstance(expr, str):
            if expr not in self.symbol_table:
                raise SemanticError(f"Undeclared variable '{expr}' in expression.")
            return
        elif isinstance(expr, BinaryExpression):
            self.analyze_binary_expression(expr)
        else:
            raise SemanticError(f"Unsupported expression type: {expr}")
