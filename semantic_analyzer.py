from parser import Program, VariableDeclaration, Assignment, ReturnStatement, BinaryExpression, IfStatement, WhileStatement, Block, FunctionDefinition, FunctionCall

class SemanticError(Exception):
    """Custom exception for semantic errors during analysis."""
    pass

class SemanticAnalyzer:
    """
    The semantic analyzer traverses the Abstract Syntax Tree to enforce semantic rules such as...
      - All variables must be declared before use.
      - Function calls must match their definitions (number of arguments, etc.).
      - Expressions use operators with operands of compatible types.
    
    It supports a simple type system with "int", "float", and "bool". 
    
    The analyzer uses:
      - self.global_symbols: for global variable declarations.
      - self.function_table: mapping function names to their definitions.
      - self.current_scope: representing the local scope for a function body.
    """
    def __init__(self):
        self.global_symbols = {}  # Global variables (name -> type)
        self.function_table = {}  # Function definitions (name -> FunctionDefinition)
        self.current_scope = {}   # Local variables (name -> type) for the current function

    def analyze(self, node):
        """
        Recursively traverses the AST node and performs semantic checks.
        Raises SemanticError if any rule is violated.
        """
        # Global level: process each declaration.
        if isinstance(node, Program):
            for decl in node.declarations:
                self.analyze(decl)
       
        # Process a function definition.
        elif isinstance(node, FunctionDefinition):
            if node.name in self.function_table:
                raise SemanticError(f"Function '{node.name}' already defined.")
            self.function_table[node.name] = node
            # Save the current scope and create a new scope for the function body.
            old_scope = self.current_scope.copy()
            for param_type, param_name in node.parameters:
                self.current_scope[param_name] = param_type
            self.analyze(node.body)
            self.current_scope = old_scope  # Restore previous scope
        
        # Process a block of statements.
        elif isinstance(node, Block):
            for stmt in node.statements:
                self.analyze(stmt)
        
        # Process a variable declaration.
        elif isinstance(node, VariableDeclaration):
            # Check if the variable is already declared.
            if node.var_name in self.current_scope or node.var_name in self.global_symbols:
                raise SemanticError(f"Variable '{node.var_name}' already declared.")
            expr_type = self.infer_type(node.value)
            # In this simple system, the type of the initializer must match the declared type.
            if expr_type != node.var_type:
                raise SemanticError(f"Type mismatch in declaration of '{node.var_name}': declared {node.var_type}, got {expr_type}.")
            self.current_scope[node.var_name] = node.var_type
            self.infer_type(node.value)  # Also perform type inference on the expression.
        
        # Process an assignment.
        elif isinstance(node, Assignment):
            if node.var_name not in self.current_scope and node.var_name not in self.global_symbols:
                raise SemanticError(f"Assignment to undeclared variable '{node.var_name}'.")
            expr_type = self.infer_type(node.value)
            var_type = self.current_scope.get(node.var_name, self.global_symbols.get(node.var_name))
            if expr_type != var_type:
                raise SemanticError(f"Type mismatch in assignment to '{node.var_name}': variable type {var_type}, but expression is {expr_type}.")
        
        # Process a return statement.
        elif isinstance(node, ReturnStatement):
            self.infer_type(node.value)
       
        # Process an if statement.
        elif isinstance(node, IfStatement):
            cond_type = self.infer_type(node.condition)
            if cond_type != "bool":
                raise SemanticError(f"Condition in if-statement must be bool, got {cond_type}.")
            self.analyze(node.then_branch)
            if node.else_branch:
                self.analyze(node.else_branch)
        
        # Process a while loop.
        elif isinstance(node, WhileStatement):
            cond_type = self.infer_type(node.condition)
            if cond_type != "bool":
                raise SemanticError(f"Condition in while-statement must be bool, got {cond_type}.")
            self.analyze(node.body)
        
        # Process a function call.
        elif isinstance(node, FunctionCall):
            if node.name not in self.function_table:
                raise SemanticError(f"Function '{node.name}' is not defined.")
            func_def = self.function_table[node.name]
            if len(node.arguments) != len(func_def.parameters):
                raise SemanticError(f"Function '{node.name}' expects {len(func_def.parameters)} arguments, got {len(node.arguments)}.")
            for arg in node.arguments:
                self.infer_type(arg)
        
        # For binary expressions, simply infer the type (which includes checking the operator's operands).
        elif isinstance(node, BinaryExpression):
            self.infer_type(node)
        
        # Literals and identifiers are handled in infer_type.
        else:
            pass

    def infer_type(self, expr):
        """
        Infers the type of an expression as a string (e.g., 'int', 'float', 'bool').
        This function also performs type checking on binary expressions and function calls.
        Raises SemanticError if type mismatches are found.
        """
        if isinstance(expr, int):
            return "int"
        
        elif isinstance(expr, float):
            return "float"
        
        elif isinstance(expr, str):
            
            # Check for boolean literals.
            if expr in ["true", "false"]:
                return "bool"
            
            # For identifiers, look them up in the current scope or global symbols.
            if expr in self.current_scope:
                return self.current_scope[expr]
            
            elif expr in self.global_symbols:
                return self.global_symbols[expr]
            
            else:
                raise SemanticError(f"Undeclared variable '{expr}'.")
        elif isinstance(expr, BinaryExpression):
            op = expr.operator
            left_type = self.infer_type(expr.left)
            right_type = self.infer_type(expr.right)
            
            # For arithmetic operators, operands must be numeric.
            if op in ['+', '-', '*', '/', '%', '^']:
                
                if left_type not in ['int', 'float'] or right_type not in ['int', 'float']:
                    raise SemanticError(f"Operator '{op}' requires numeric operands, got {left_type} and {right_type}.")
                
                # If either operand is float, result is float.
                if left_type == "float" or right_type == "float":
                    return "float"
                return "int"
           
            # For relational operators, result is always bool.
            elif op in ['<', '>', '<=', '>=']:
                
                if left_type not in ['int', 'float'] or right_type not in ['int', 'float']:
                    raise SemanticError(f"Operator '{op}' requires numeric operands, got {left_type} and {right_type}.")
                return "bool"
            
            # For equality operators, both operands must have the same type.
            elif op in ['==', '!=']:
                
                if left_type != right_type:
                    raise SemanticError(f"Operator '{op}' requires both operands to be of the same type, got {left_type} and {right_type}.")
                return "bool"
            
            # For logical operators, both operands must be bool.
            elif op in ['&&', '||']:
                
                if left_type != "bool" or right_type != "bool":
                    raise SemanticError(f"Operator '{op}' requires bool operands, got {left_type} and {right_type}.")
                return "bool"
            else:
                raise SemanticError(f"Unsupported operator '{op}'.")
        
        elif isinstance(expr, FunctionCall):
            
            if expr.name not in self.function_table:
                raise SemanticError(f"Function '{expr.name}' is not defined.")
            # For this example, we assume functions return int by default.
            return "int"
        
        else:
            raise SemanticError(f"Unsupported expression type: {expr}")
