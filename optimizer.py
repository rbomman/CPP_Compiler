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


class ASTOptimizer:
    """Applies lightweight AST-level optimizations."""

    def optimize(self, node):
        if isinstance(node, Program):
            return Program([self.optimize(decl) for decl in node.declarations])
        if isinstance(node, StructDefinition):
            return node
        if isinstance(node, FunctionDefinition):
            return FunctionDefinition(
                node.return_type,
                node.name,
                node.parameters,
                self.optimize(node.body),
            )
        if isinstance(node, Block):
            optimized_statements = []
            for stmt in node.statements:
                optimized_stmt = self.optimize(stmt)
                if isinstance(optimized_stmt, Block):
                    optimized_statements.extend(optimized_stmt.statements)
                else:
                    optimized_statements.append(optimized_stmt)
                if isinstance(optimized_stmt, (ReturnStatement, BreakStatement, ContinueStatement)):
                    break
            return Block(optimized_statements)
        if isinstance(node, VariableDeclaration):
            return VariableDeclaration(node.var_type, node.var_name, self.optimize_expression(node.value))
        if isinstance(node, StructDeclaration):
            return node
        if isinstance(node, ArrayDeclaration):
            return node
        if isinstance(node, Assignment):
            return Assignment(node.var_name, self.optimize_expression(node.value))
        if isinstance(node, ArrayAssignment):
            return ArrayAssignment(
                node.array_name,
                self.optimize_expression(node.index),
                self.optimize_expression(node.value),
            )
        if isinstance(node, FieldAssignment):
            return FieldAssignment(node.field_access, self.optimize_expression(node.value))
        if isinstance(node, PointerAssignment):
            return PointerAssignment(node.pointer_expr, self.optimize_expression(node.value))
        if isinstance(node, ReturnStatement):
            return ReturnStatement(self.optimize_expression(node.value))
        if isinstance(node, IfStatement):
            condition = self.optimize_expression(node.condition)
            then_branch = self.optimize(node.then_branch)
            else_branch = self.optimize(node.else_branch) if node.else_branch else None
            constant_condition = self._as_constant_bool(condition)
            if constant_condition is True:
                return then_branch
            if constant_condition is False:
                return else_branch if else_branch is not None else Block([])
            return IfStatement(condition, then_branch, else_branch)
        if isinstance(node, WhileStatement):
            condition = self.optimize_expression(node.condition)
            body = self.optimize(node.body)
            if self._as_constant_bool(condition) is False:
                return Block([])
            return WhileStatement(condition, body)
        if isinstance(node, ForStatement):
            initializer = self.optimize(node.initializer) if node.initializer is not None else None
            condition = self.optimize_expression(node.condition) if node.condition is not None else None
            update = self.optimize(node.update) if node.update is not None else None
            body = self.optimize(node.body)
            if self._as_constant_bool(condition) is False:
                return Block([initializer] if initializer is not None else [])
            return ForStatement(initializer, condition, update, body)
        return node

    def optimize_expression(self, expr):
        if isinstance(expr, UnaryExpression):
            operand = self.optimize_expression(expr.operand)
            folded = self._fold_unary(expr.operator, operand)
            return folded if folded is not None else UnaryExpression(expr.operator, operand)
        if isinstance(expr, BinaryExpression):
            left = self.optimize_expression(expr.left)
            right = self.optimize_expression(expr.right)
            folded = self._fold_binary(left, expr.operator, right)
            return folded if folded is not None else BinaryExpression(left, expr.operator, right)
        if isinstance(expr, FunctionCall):
            return FunctionCall(expr.name, [self.optimize_expression(arg) for arg in expr.arguments])
        if isinstance(expr, ArrayAccess):
            return ArrayAccess(expr.array_name, self.optimize_expression(expr.index))
        if isinstance(expr, FieldAccess):
            return FieldAccess(self.optimize_expression(expr.base), expr.field_name)
        return expr

    def _fold_unary(self, operator, operand):
        if operator == '-' and isinstance(operand, (int, float)):
            return -operand
        if operator == '!':
            constant = self._as_constant_bool(operand)
            if constant is not None:
                return "false" if constant else "true"
        return None

    def _fold_binary(self, left, operator, right):
        if operator in {'&&', '||'}:
            left_bool = self._as_constant_bool(left)
            right_bool = self._as_constant_bool(right)
            if left_bool is not None and right_bool is not None:
                result = left_bool and right_bool if operator == '&&' else left_bool or right_bool
                return "true" if result else "false"
            return None

        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            if operator in {'==', '!='} and left in {'true', 'false'} and right in {'true', 'false'}:
                result = (left == right) if operator == '==' else (left != right)
                return "true" if result else "false"
            return None

        try:
            if operator == '+':
                return left + right
            if operator == '-':
                return left - right
            if operator == '*':
                return left * right
            if operator == '/':
                return None if right == 0 else (left / right if isinstance(left, float) or isinstance(right, float) else left // right)
            if operator == '%':
                return None if right == 0 else left % right
            if operator == '^':
                return left ** right
            if operator == '<':
                return "true" if left < right else "false"
            if operator == '>':
                return "true" if left > right else "false"
            if operator == '<=':
                return "true" if left <= right else "false"
            if operator == '>=':
                return "true" if left >= right else "false"
            if operator == '==':
                return "true" if left == right else "false"
            if operator == '!=':
                return "true" if left != right else "false"
        except Exception:
            return None
        return None

    def _as_constant_bool(self, expr):
        if expr == "true":
            return True
        if expr == "false":
            return False
        return None


class PeepholeOptimizer:
    """Applies small instruction-stream cleanups."""

    def optimize(self, instructions):
        optimized = []
        index = 0
        while index < len(instructions):
            instruction = instructions[index]

            if instruction.startswith("MOV "):
                operands = [part.strip() for part in instruction[4:].split(",")]
                if len(operands) == 2 and operands[0] == operands[1]:
                    index += 1
                    continue

            if instruction.startswith("JMP ") and index + 1 < len(instructions):
                target = instruction[4:].strip()
                if instructions[index + 1].strip() == f"LABEL {target}":
                    index += 1
                    continue

            if instruction.startswith("JMP ") and optimized and optimized[-1].strip() == "RET":
                index += 1
                continue

            optimized.append(instruction)
            index += 1

        return optimized
