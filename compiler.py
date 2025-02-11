# compiler.py

from lexer import tokenize
from parser import Parser, Program, VariableDeclaration, Assignment, ReturnStatement
from semantic_analyzer import SemanticAnalyzer, SemanticError
from code_generator import CodeGenerator

def compile_source(source_code):
    # Lexical Analysis
    tokens = tokenize(source_code)
    print("Tokens:", tokens)
    
    # Parsing
    parser = Parser(tokens)
    try:
        ast = parser.parse_program()
    except Exception as e:
        print("Parsing error:", e)
        return None
    
    # Semantic Analysis
    analyzer = SemanticAnalyzer()
    try:
        analyzer.analyze(ast)
    except SemanticError as se:
        print("Semantic analysis error:", se)
        return None
    
    # Code Generation
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
