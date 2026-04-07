from pathlib import Path
import re

from lexer import tokenize
from cpp_parser import Parser
from semantic_analyzer import SemanticAnalyzer, SemanticError
from ir import IRGenerator
from code_generator import CodeGenerator
from optimizer import ASTOptimizer, PeepholeOptimizer
from virtual_cpu import VirtualCPU, VirtualCPUError

def compile_source(source_code):
    """Compile source code into pseudo-assembly instructions."""
    tokens = tokenize(source_code)

    try:
        ast = Parser(tokens).parse_program()
        SemanticAnalyzer().analyze(ast)
        optimized_ast = ASTOptimizer().optimize(ast)
        ir_program = IRGenerator().build(optimized_ast)
        code = CodeGenerator().generate(ir_program)
        return PeepholeOptimizer().optimize(code)
    except (SyntaxError, SemanticError, ValueError) as exc:
        print(format_compilation_error(exc, source_code))
        return None


def format_compilation_error(exc, source_code):
    message = f"Compilation error: {exc}"
    match = re.search(r"Line\s+(\d+),\s*Col\s+(\d+)", str(exc))
    if not match:
        return message

    line_number = int(match.group(1))
    col_number = int(match.group(2))
    source_lines = source_code.splitlines()
    if not (1 <= line_number <= len(source_lines)):
        return message

    source_line = source_lines[line_number - 1]
    pointer = " " * max(col_number - 1, 0) + "^"
    return f"{message}\n{source_line}\n{pointer}"


def execute_program(instructions):
    """Execute generated pseudo-assembly and return the VM result."""
    try:
        cpu = VirtualCPU(instructions)
        result = cpu.run()
        return result, cpu.snapshot_globals()
    except VirtualCPUError as exc:
        print(f"Execution error: {exc}")
        return None, None

if __name__ == "__main__":
    input_path = Path("input.cpp")
    output_path = Path("output.txt")

    try:
        source_code = input_path.read_text()
    except FileNotFoundError:
        print(f"File '{input_path}' not found.")
        exit(1)

    generated_code = compile_source(source_code)
    if generated_code is None:
        exit(1)

    print("\nGenerated Code:")
    for instruction in generated_code:
        print(instruction)

    output_text = "------Compiled Program------\n" + "\n".join(generated_code) + "\n"
    output_path.write_text(output_text)

    result, globals_state = execute_program(generated_code)
    if globals_state is not None:
        print(f"\nProgram Result: {result}")
        print(f"Global State: {globals_state}")
