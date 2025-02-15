from parser import Program, Block, VariableDeclaration, Assignment, ReturnStatement, BinaryExpression, IfStatement, WhileStatement, FunctionDefinition, FunctionCall

class CodeGenerator:
    """
    The code generator traverses the Abstract Syntax Tree produced by the parser and
    generates pseudo–assembly instructions that represent the compiled code.

    The generator uses the following scheme:
      - It assigns temporary names (t1, t2, …) for intermediate results.
      - It generates labels for functions and control flow (e.g., if/else, while loops).
      - It produces instructions such as MOV (move), ADD, SUB, MUL, DIV, MOD, POW, CMP,
        and conditional set/jump instructions for relational and logical operations.
      - Function calls are lowered to a CALL instruction with evaluated arguments.

    The output is a list of strings, each representing one pseudo–assembly instruction.
    """

    def __init__(self):
        self.instructions = []       # List of generated instructions.
        self.temp_count = 0          # Counter for temporary registers.
        self.label_count = 0         # Counter for generating unique labels.
        self.function_labels = {}    # Mapping from function names to their unique labels.

    def new_temp(self):
        """Generates and returns a new temporary register name."""
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self, prefix):
        """
        Generates and returns a new label with the given prefix.
        Labels are used to mark jump targets in control flow constructs.
        """
        self.label_count += 1
        return f"{prefix}_{self.label_count}"

    def generate(self, node):
        """
        Main entry point for code generation.
        Recursively dispatches on the type of AST node and produces pseudo–assembly code.
        """
        if isinstance(node, Program):
            self.visit_program(node)
        elif isinstance(node, Block):
            self.visit_block(node)
        elif isinstance(node, VariableDeclaration):
            self.visit_variable_declaration(node)
        elif isinstance(node, Assignment):
            self.visit_assignment(node)
        elif isinstance(node, ReturnStatement):
            self.visit_return_statement(node)
        elif isinstance(node, IfStatement):
            self.visit_if_statement(node)
        elif isinstance(node, WhileStatement):
            self.visit_while_statement(node)
        elif isinstance(node, FunctionDefinition):
            self.visit_function_definition(node)
        elif isinstance(node, FunctionCall):
            return self.visit_function_call(node)
        else:
            raise Exception("Unknown AST node: " + str(node))
        return self.instructions

    # Global and Function-Level Code Generation Methods

    def visit_program(self, node):
        """
        Generates code for the entire program.
        First, it processes global variable declarations, then function definitions.
        If a function named "main" exists, it emits a call to main and halts.
        """
        # Process global variable declarations.
        for decl in node.declarations:
            if isinstance(decl, VariableDeclaration):
                self.generate(decl)
        # Process function definitions.
        for decl in node.declarations:
            if isinstance(decl, FunctionDefinition):
                self.generate(decl)
        # Optionally, call main if it exists.
        if "main" in self.function_labels:
            self.instructions.append("CALL main")
            self.instructions.append("HALT")

    def visit_function_definition(self, node):
        """
        Generates code for a function definition.
        A unique label is assigned to the function.
        The function body (a Block) is then generated, and a RET instruction is appended.
        """
        func_label = self.new_label(f"func_{node.name}")
        self.function_labels[node.name] = func_label
        self.instructions.append(f"LABEL {func_label}")
        # In a full implementation, this is where a new stack frame would be set up.
        self.generate(node.body)
        # Append RET at the end of the function (if not already present).
        self.instructions.append("RET")

    def visit_block(self, node):
        """Generates code for a block of statements."""
        for stmt in node.statements:
            self.generate(stmt)

    def visit_variable_declaration(self, node):
        """
        Generates code for a variable declaration.
        The initializer expression is evaluated, and its result is moved into the variable.
        """
        result = self.evaluate_expression(node.value)
        self.instructions.append(f"MOV {node.var_name}, {result}")

    def visit_assignment(self, node):
        """
        Generates code for an assignment.
        Evaluates the right-hand side expression and moves the result into the variable.
        """
        result = self.evaluate_expression(node.value)
        self.instructions.append(f"MOV {node.var_name}, {result}")

    def visit_return_statement(self, node):
        """
        Generates code for a return statement.
        Evaluates the return expression, moves the result into a special return register,
        and then emits a RET instruction.
        """
        result = self.evaluate_expression(node.value)
        self.instructions.append(f"MOV ret, {result}")  # 'ret' is our designated return register.
        self.instructions.append("RET")

    def visit_if_statement(self, node):
        """
        Generates code for an if-else statement.
        Evaluates the condition and uses conditional jumps to branch to the then or else branch.
        """
        cond_temp = self.evaluate_expression(node.condition)
        else_label = self.new_label("else")
        end_label = self.new_label("endif")
        self.instructions.append(f"CMP {cond_temp}, 0")
        self.instructions.append(f"JE {else_label}")  # Jump to else if condition is false.
        self.generate(node.then_branch)
        self.instructions.append(f"JMP {end_label}")
        self.instructions.append(f"LABEL {else_label}")
        if node.else_branch:
            self.generate(node.else_branch)
        self.instructions.append(f"LABEL {end_label}")

    def visit_while_statement(self, node):
        """
        Generates code for a while loop.
        A label marks the start of the loop. The condition is evaluated; if false, jumps to loop end.
        Otherwise, the body is executed and control jumps back to the loop start.
        """
        start_label = self.new_label("while_start")
        end_label = self.new_label("while_end")
        self.instructions.append(f"LABEL {start_label}")
        cond_temp = self.evaluate_expression(node.condition)
        self.instructions.append(f"CMP {cond_temp}, 0")
        self.instructions.append(f"JE {end_label}")
        self.generate(node.body)
        self.instructions.append(f"JMP {start_label}")
        self.instructions.append(f"LABEL {end_label}")

    def visit_function_call(self, node):
        """
        Generates code for a function call.
        Evaluates all argument expressions, then emits a CALL instruction.
        The result of the function call is stored in a new temporary register, which is returned.
        """
        arg_regs = []
        for arg in node.arguments:
            arg_reg = self.evaluate_expression(arg)
            arg_regs.append(arg_reg)
        args_str = ", ".join(arg_regs)
        temp = self.new_temp()
        # This is a simplified calling convention:
        self.instructions.append(f"CALL {node.name}, {args_str} -> {temp}")
        return temp

    def evaluate_expression(self, expr):
        """
        Recursively evaluates an expression and returns the register or literal where the result is stored.
        For binary expressions, this function emits the appropriate pseudo–assembly instruction
        based on the operator.
        """
        if isinstance(expr, int):
            return str(expr)
        elif isinstance(expr, float):
            return str(expr)
        elif isinstance(expr, str):
            # For boolean literals "true" and "false", they are returned as is.
            return expr
        elif isinstance(expr, BinaryExpression):
            left = self.evaluate_expression(expr.left)
            right = self.evaluate_expression(expr.right)
            temp = self.new_temp()
            op = expr.operator
            if op == '+':
                self.instructions.append(f"ADD {temp}, {left}, {right}")
            elif op == '-':
                # SUB is implemented as ADD with the negative of the right operand.
                self.instructions.append(f"ADD {temp}, {left}, -{right}")
            elif op == '*':
                self.instructions.append(f"MUL {temp}, {left}, {right}")
            elif op == '/':
                self.instructions.append(f"DIV {temp}, {left}, {right}")
            elif op == '%':
                # Lower modulo into a loop:
                #   remainder = left
                #   while (remainder >= right) { remainder = remainder - right }
                remainder_temp = self.new_temp()
                self.instructions.append(f"MOV {remainder_temp}, {left}")  # remainder = left
                loop_label = self.new_label("mod_loop")
                end_label = self.new_label("mod_end")
                self.instructions.append(f"LABEL {loop_label}")
                self.instructions.append(f"CMP {remainder_temp}, {right}")
                # If remainder < right, exit the loop.
                self.instructions.append(f"JL {end_label}")
                # Subtract divisor (using ADD with negative operand)
                self.instructions.append(f"ADD {remainder_temp}, {remainder_temp}, -{right}")
                self.instructions.append(f"JMP {loop_label}")
                self.instructions.append(f"LABEL {end_label}")
                return remainder_temp
            elif op == '^':
                # Lower exponentiation into a loop:
                #   result = 1; counter = right;
                #   while (counter > 0) { result = result * left; counter = counter - 1 }
                result_temp = self.new_temp()
                counter_temp = self.new_temp()
                loop_label = self.new_label("pow_loop")
                end_label = self.new_label("pow_end")
                self.instructions.append(f"MOV {result_temp}, 1")            # result = 1
                self.instructions.append(f"MOV {counter_temp}, {right}")        # counter = exponent
                self.instructions.append(f"LABEL {loop_label}")
                self.instructions.append(f"CMP {counter_temp}, 0")             # Compare counter with 0
                self.instructions.append(f"JE {end_label}")                    # If 0, exit loop
                self.instructions.append(f"MUL {result_temp}, {result_temp}, {left}")  # result *= left
                # Decrement counter using ADD with negative operand.
                self.instructions.append(f"ADD {counter_temp}, {counter_temp}, -1")
                self.instructions.append(f"JMP {loop_label}")
                self.instructions.append(f"LABEL {end_label}")
                return result_temp
            # For relational operators, we emit a CMP followed by a conditional set instruction.
            elif op == '<':
                self.instructions.append(f"CMP {left}, {right}")
                self.instructions.append(f"SETL {temp}")  # SETL sets temp=1 if left < right, else 0.
            elif op == '>':
                self.instructions.append(f"CMP {left}, {right}")
                self.instructions.append(f"SETG {temp}")
            elif op == '<=':
                self.instructions.append(f"CMP {left}, {right}")
                self.instructions.append(f"SETLE {temp}")
            elif op == '>=':
                self.instructions.append(f"CMP {left}, {right}")
                self.instructions.append(f"SETGE {temp}")
            elif op == '==':
                self.instructions.append(f"CMP {left}, {right}")
                self.instructions.append(f"SETE {temp}")
            elif op == '!=':
                self.instructions.append(f"CMP {left}, {right}")
                self.instructions.append(f"SETNE {temp}")
            # For logical operators, assume boolean values (0 or 1) and use bitwise operations.
            elif op == '&&':
                self.instructions.append(f"AND {temp}, {left}, {right}")
            elif op == '||':
                self.instructions.append(f"OR {temp}, {left}, {right}")
            else:
                raise Exception("Unsupported operator: " + op)
            return temp
        elif isinstance(expr, FunctionCall):
            return self.visit_function_call(expr)
        else:
            raise Exception("Unsupported expression type: " + str(expr))


# Example usage:
if __name__ == "__main__":
    # This example constructs an AST for a simple program with function calls and control flow.
    from parser import Program, VariableDeclaration, FunctionDefinition, ReturnStatement, BinaryExpression, IfStatement, WhileStatement, Block, FunctionCall, Assignment

    # You can define your Abstract Synax Tree using main_func and call the code generator on it

    # Placeholder value
    main_func = 0; 

    prog = Program([main_func])
    generator = CodeGenerator()
    code = generator.generate(prog)
    for instr in code:
        print(instr)
