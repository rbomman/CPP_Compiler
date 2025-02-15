from lexer import tokenize
from parser import Parser
from semantic_analyzer import SemanticAnalyzer, SemanticError
from code_generator import CodeGenerator

def compile_source(source_code):
    """
    This function turn the input into pseudo-assembly
    """

    # Run the tokenizer on the code
    tokens = tokenize(source_code)
    print("Tokens:", tokens)
    
    # Parse the tokens into an Abstract Syntax Tree
    parser = Parser(tokens)
    try:
        ast = parser.parse_program()
    except Exception as e:
        print("Parsing error:", e)
        return None
    
    # Run the semantic analyzer on the code to enforce semantic rules
    analyzer = SemanticAnalyzer()
    try:
        analyzer.analyze(ast)
    except SemanticError as se:
        print("Semantic analysis error:", se)
        return None
    
    # Use the code generator on the abstract syntax tree to make pseudo-assembly
    generator = CodeGenerator()
    try:
        code = generator.generate(ast)
    except Exception as e:
        print("Code generation error:", e)
        return None

    return code

if __name__ == "__main__":
    try:
        with open("input.cpp", "r") as file:
            source_code = file.read()
    except FileNotFoundError:
        print("File 'input.cpp' not found.")
        exit(1)
    
    generated_code = compile_source(source_code)
    if generated_code:
        print("\nGenerated Code:")
        for instruction in generated_code:
            print(instruction)
            file.write

        # Write the generated instructions to a file
        with open("output.txt", "w") as f:
            f.write("------Compiled Program------ \n")
            for instruction in generated_code:
                f.write(instruction + "\n")
