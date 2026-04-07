# CPP_Compiler

`CPP_Compiler` is a compact standalone compiler for a custom C-like language. It reads source from `input.cpp`, tokenizes it, parses it into an abstract syntax tree, validates the program semantically, performs a small AST optimization pass, lowers the result into an explicit intermediate representation, formats that IR as pseudo-assembly, and executes the final program on a custom virtual CPU.

This is not a partial C++ implementation. It is a deliberately constrained language and runtime designed to make the compiler pipeline readable, inspectable, and complete at a small scale.

## Table Of Contents

- Overview
- Language Summary
- Pipeline
- Design Principles
- Lexer
- Parser And AST
- Semantic Analysis
- AST Optimization
- Intermediate Representation
- Pseudo-Assembly
- Virtual CPU And Runtime Model
- Worked Lowering Example
- Diagnostics
- Testing
- Running The Project
- Current Limits

## Overview

The project contains the full set of stages needed for a real small compiler:

- lexical analysis
- recursive-descent parsing
- semantic analysis and type checking
- source-level optimization
- an explicit IR layer
- backend lowering to assembly-like instructions
- execution on a virtual machine
- automated integration tests

The language is intentionally narrow, but the implementation is not a stub. Arrays, structs, pointers, aggregate copies, function calls, control flow, and runtime memory operations all compile and execute through the same pipeline.

## Language Summary

The language currently supports:

- primitive types: `int`, `float`, `bool`
- user-defined structs
- nested structs
- whole-struct assignment
- struct-by-value parameters and returns
- fixed-size arrays, including arrays of structs
- pointers, address-of, dereference, pointer arithmetic, and `->`
- functions
- `if`, `while`, `for`, `break`, and `continue`
- unary operators `-`, `!`, `&`, `*`
- arithmetic, comparisons, and boolean operators

The language intentionally does not include:

- the preprocessor
- headers or includes
- strings, chars, enums, unions, classes, templates, or the standard library
- a full C or C++ memory model

## Pipeline

The compiler pipeline is:

```text
source
  -> lexer
  -> parser / AST
  -> semantic analysis
  -> AST optimizer
  -> IR generator
  -> pseudo-assembly generator
  -> peephole optimizer
  -> virtual CPU
```

The stages are deliberately separated. Parsing is not mixed with execution, semantic checks are not embedded in the parser, and backend memory decisions are not spread across multiple layers.

At a high level:

1. source text becomes tokens
2. tokens become AST nodes
3. AST nodes are type-checked and scope-checked
4. simple source-level simplifications run
5. high-level operations are lowered into an explicit IR
6. the IR is rendered as pseudo-assembly
7. small textual cleanups run
8. the VM executes the final program

## Design Principles

Several implementation choices shape the project:

### Keep Each Stage Honest

Each stage does one kind of work:

- the lexer recognizes tokens
- the parser recognizes structure
- semantic analysis assigns meaning
- the optimizer simplifies
- the IR generator lowers
- the VM executes

This keeps the code readable and makes debugging easier.

### Prefer Explicit Lowering Over Implicit Magic

The project does not hide aggregate behavior in the runtime. Struct-by-value arguments, struct returns, array indexing, field access, and whole-struct copies are all lowered explicitly into address computations and copy operations before execution.

### Use The Simplest Representation That Still Scales

Examples:

- types are stored as strings rather than rich algebraic type objects
- the IR is small and instruction-based rather than SSA-based
- the VM uses integer-indexed memory slots rather than byte-addressed memory

Those choices keep the compiler compact while still supporting nontrivial language features.

## Lexer

The lexer is regex-based.

It first strips `//` line comments, then scans the remaining source with one combined regular expression and emits tokens in the form:

```text
(token_type, token_value, line_number, column_number)
```

### Token Categories

The lexer recognizes:

- keywords
- identifiers
- integer literals
- floating-point literals
- multi-character operators such as `&&`, `||`, `==`, `!=`, `<=`, `>=`, `^`, and `->`
- single-character symbols such as `(`, `)`, `{`, `}`, `[`, `]`, `;`, `,`, `.`, `+`, `-`, `*`, `/`, `%`, `<`, `>`, `=`, `!`, and `&`

### Error Behavior

Unknown characters fail immediately with a syntax error.

This is intentional. The lexer does not try to recover or reinterpret invalid characters because that tends to make later errors less clear.

### Why The Lexer Is Kept Simple

The lexer does not know:

- whether an identifier is a type
- whether an identifier is local or global
- whether a token sequence is semantically valid

Those decisions belong to later stages.

## Parser And AST

The parser is handwritten recursive descent.

Each grammar region is implemented by a dedicated method rather than by a parser generator. This makes the grammar easy to modify and keeps precedence handling direct and readable.

### AST Node Families

The AST includes nodes for:

- top-level declarations
- blocks and statements
- scalar declarations
- struct declarations
- array declarations
- scalar assignments
- array assignments
- field assignments
- pointer assignments
- array access
- field access
- unary expressions
- binary expressions
- control flow
- function definitions
- function calls

Literals are represented directly as Python values where practical, and identifiers are often represented as plain strings until a richer node is necessary.

### Expression Parsing Strategy

Expressions are parsed by precedence layer:

1. logical OR
2. logical AND
3. equality
4. relational
5. addition and subtraction
6. multiplication, division, and modulo
7. exponentiation
8. unary operators
9. primary and postfix forms

That means expressions such as:

```cpp
!(a < b) || x + y * z
```

parse with the expected binding.

### Postfix Forms

Postfix parsing handles:

- function calls
- array indexing
- field access with `.`
- pointer field access with `->`

Internally, `->` is normalized into field access on top of an implicit dereference. This matters because the rest of the compiler only has to understand one general field-access model.

### Why The AST Is Still Fairly High Level

The AST preserves source intent. It still has concepts like:

- loops
- function calls
- field access
- array access
- aggregate assignment

It does not try to model addresses, slots, or hidden buffers yet. That work belongs to lowering.

## Semantic Analysis

Semantic analysis turns parsed structure into a valid, typed program or rejects it.

The analyzer maintains:

- a global symbol table
- a function table
- a struct table
- a stack of local scopes
- the current function context
- current loop depth

### Symbol And Scope Model

Symbols carry both kind and type information.

Examples of symbol kinds:

- scalar
- struct
- array

That distinction is important because:

- arrays cannot be used like scalars
- structs can be assigned by value but not used as plain numeric operands
- arrays need both element type and size

### Type Model

Types are represented as strings such as:

- `int`
- `float`
- `bool`
- `struct Point`
- `int*`
- `struct Point*`

This is intentionally lightweight, but it is enough to express:

- pointer types
- aggregate types
- array element types
- numeric promotion rules

### Major Semantic Checks

The analyzer validates:

- names are declared before use
- duplicate declarations are rejected in active scopes
- functions exist before they are called
- function calls use the correct number of arguments
- each argument type is assignable to the expected parameter type
- array indexes are integers
- field accesses refer to valid fields of valid struct-valued bases
- unary and binary operators are applied to valid operand types
- return expressions are compatible with function return types
- `break` and `continue` appear only inside loops
- recursive by-value struct definitions are rejected

### Assignment Rules

Assignment is type-checked by target category:

- scalar assignment checks scalar compatibility
- array element assignment checks element compatibility
- field assignment checks field compatibility
- pointer assignment checks pointee compatibility
- struct assignment checks aggregate type equality

### Numeric Promotion

The language allows widening from `int` to `float` in assignment and expression contexts. It does not implement arbitrary implicit conversions beyond that.

### Struct Validation Details

Struct validation happens in two phases:

1. register struct names and field lists
2. validate field types and recursive layout constraints

This allows mutually referential pointer fields while still rejecting infinite-size value layouts.

## AST Optimization

Before lowering, a small AST optimization pass performs simple source-level simplifications.

### Current Optimizations

- constant folding for arithmetic and boolean expressions
- dead statement elimination after `return`, `break`, or `continue`
- elimination of constant-false loops
- simplification of constant `if` conditions

### Why This Pass Happens Before Lowering

These transformations are easier and clearer at the AST level because:

- the original control-flow shape still exists
- expressions are still structural rather than address-based
- dead branches can be removed before they generate backend noise

### What The Optimizer Does Not Try To Do

It does not attempt:

- alias analysis
- aggregate copy elimination
- loop-invariant motion
- dataflow analysis
- global optimization

The goal is clarity, not a sophisticated optimizer.

## Intermediate Representation

The explicit IR is the core backend boundary in the project.

### Why The IR Matters

Once the language gained:

- structs
- arrays of structs
- by-value aggregate parameters and returns
- field addressing
- bounds-aware pointer metadata

direct AST-to-text code generation stopped scaling well.

The IR separates:

- source structure
- lowering and address computation
- final text formatting

This makes the backend easier to reason about and easier to evolve.

### IR Shape

The IR consists of small structured instructions. Each instruction has:

- an opcode
- a tuple of operands

This is intentionally minimal. The project does not introduce a full compiler framework just to gain explicit lowering.

### What The IR Generator Owns

The IR generator is responsible for most of the real backend work:

- temporary allocation
- label generation
- stable function labels
- control-flow lowering
- lvalue-to-address conversion
- field offset calculation
- array element address calculation
- hidden return-buffer handling for aggregate returns
- lowering aggregate copies into explicit copy instructions

This is the stage where high-level operations are turned into memory-oriented operations.

### Lvalues And Addressing

The IR generator makes address computation explicit for:

- variables
- array elements
- struct fields
- dereferenced pointers
- pointer field access

That is why the backend can support a statement like:

```cpp
ptr->point.x = 5;
```

without inventing a special opcode for every source-level operation.

### Pointer Metadata

When the IR constructs a pointer value, it carries enough information for the VM to enforce runtime safety:

- `stride`: how far pointer arithmetic moves per logical element
- `span`: how many slots a dereference or copy covers

Those two values are what connect type information to runtime bounds checking.

### Aggregate Convention

Struct values are lowered explicitly:

- aggregate arguments are passed by address
- aggregate returns use a hidden return-buffer pointer
- aggregate assignment lowers to a copy over contiguous memory slots

This avoids special aggregate behavior in the VM instruction set.

## Pseudo-Assembly

The pseudo-assembly layer is intentionally thin.

By the time lowering reaches this stage, the hard decisions are already done. The pseudo-assembly generator mainly formats structured IR instructions into readable text.

Typical storage-related instructions include:

- `ALLOC`
- `ADDR`
- `INDEXADDR`
- `FIELDPTR`
- `LOADPTR`
- `STOREPTR`
- `COPY`

Arithmetic, comparison, and control-flow instructions are then expressed in a conventional assembly-like style.

### Why This Layer Is Kept Thin

Keeping the pseudo-assembly generator simple has two benefits:

- backend logic stays centralized in the IR generator
- the generated output is easy to read because it directly reflects the lowered IR

## Peephole Optimization

After pseudo-assembly generation, a small peephole pass removes a few common redundant patterns:

- `MOV x, x`
- jumps to the next immediate label
- jumps that appear immediately after `RET`

This pass is deliberately small. It is a cleanup pass, not a serious machine-level optimizer.

## Virtual CPU And Runtime Model

The virtual CPU executes the generated pseudo-assembly.

### VM State

The VM maintains:

- parsed instructions
- a label table
- a global symbol table
- a memory map indexed by address
- a call stack
- a comparison register
- an instruction pointer
- a final return value

### Address-Based Storage

The runtime is address-based rather than purely name-based.

Each symbol owns a contiguous address range, and memory values are stored by address. Global and local symbol tables map names to base-address and size information.

This allows:

- arrays to occupy contiguous slots
- structs to occupy contiguous slots
- aggregate copies to work as block operations
- pointers to refer to actual memory locations rather than just symbolic names

### Pointer Runtime Representation

Pointers are runtime objects carrying:

- `addr`
- `stride`
- `span`
- `lower`
- `upper`
- `origin`

These fields let the VM:

- advance pointers by logical element size
- know how much memory a dereference or copy touches
- detect out-of-bounds reads, writes, and copies
- report where the pointer came from when an error occurs

### Allocation Model

Allocation is simple:

- each new symbol is assigned the next available address range
- allocations are contiguous
- slot values are initialized to zero

This is not a production allocator or stack layout, but it is sufficient for the language subset and makes memory behavior explicit.

### Call Frames

Each function call creates a frame containing:

- a local symbol table
- a saved return instruction pointer
- the destination that should receive a returned scalar result

Arguments are written into synthetic names such as `__arg0`, `__arg1`, and so on.

Aggregate returns use the hidden return-buffer pointer provided by the caller. The callee copies the return value into that buffer before returning.

### Comparison Model

Comparisons are implemented through a classic two-step pattern:

1. `CMP left, right`
2. a conditional set or jump such as `SETL`, `SETE`, or `JE`

The VM stores the result of the last comparison in a dedicated comparison register.

### Bounds Checking

The VM performs bounds checks for:

- pointer reads
- pointer writes
- aggregate copies

The compiler does not attempt to prove safety statically. Instead, it lowers enough metadata that the VM can check safety dynamically at the point of use.

## Worked Lowering Example

The best way to understand the backend is to walk a statement through the pipeline.

Consider this source:

```cpp
struct Point {
    int x;
    int y;
};

int main() {
    struct Point p;
    struct Point* ptr = &p;
    ptr->x = ptr->x + 1;
    return ptr->x;
}
```

### Source-Level Meaning

At the source level:

- `p` is a struct value with two integer fields
- `ptr` is a pointer to `p`
- `ptr->x` means:
  1. dereference `ptr`
  2. find field `x`
  3. treat that location as an lvalue or rvalue

### AST Shape

The assignment:

```cpp
ptr->x = ptr->x + 1;
```

is represented conceptually as:

```text
FieldAssignment(
  field_access = FieldAccess(
    base = UnaryExpression('*', 'ptr'),
    field_name = 'x'
  ),
  value = BinaryExpression(
    left = FieldAccess(
      base = UnaryExpression('*', 'ptr'),
      field_name = 'x'
    ),
    operator = '+',
    right = 1
  )
)
```

The important point is that `->` has already been normalized into field access on top of an explicit dereference.

### Semantic Interpretation

During semantic analysis:

- `p` has type `struct Point`
- `ptr` has type `struct Point*`
- dereferencing `ptr` yields `struct Point`
- field `x` is resolved against the `Point` layout
- field `x` has type `int`

So the assignment is validated as a scalar field assignment to an `int`.

### IR-Level Lowering

At the IR layer, the compiler stops thinking in terms of field syntax and starts thinking in terms of addresses:

1. allocate storage for `p`
2. allocate storage for `ptr`
3. compute the address of `p`
4. store that pointer into `ptr`
5. compute the address of field `x` through `ptr`
6. load the current value
7. add `1`
8. store the result back through the computed field pointer

Conceptually, the lowered instruction shape is:

```text
ALLOC p, 2
ALLOC ptr, 1
ADDR t1, p, 2, 2
MOV ptr, t1
FIELDPTR t2, ptr, 0, 1, 1
FIELDPTR t3, ptr, 0, 1, 1
LOADPTR t4, t3
ADD t5, t4, 1
STOREPTR t2, t5
```

The numbers here come from the type layout:

- `Point` occupies `2` slots because it has two `int` fields
- field `x` has offset `0`
- field `x` has stride `1` and span `1` because it is a scalar field

### Final Pseudo-Assembly

The pseudo-assembly layer renders those instructions almost directly:

```text
ALLOC p, 2
ALLOC ptr, 1
ADDR t1, p, 2, 2
MOV ptr, t1
FIELDPTR t2, ptr, 0, 1, 1
FIELDPTR t3, ptr, 0, 1, 1
LOADPTR t4, t3
ADD t5, t4, 1
STOREPTR t2, t5
```

The VM then executes those instructions using the address-based memory model.

### Why This Example Matters

This single statement demonstrates the project’s core design:

- source syntax is normalized early
- types are resolved before lowering
- addresses are made explicit in the IR
- the final assembly is simple because the semantic lowering already happened upstream

That is the reason the compiler can support arrays, structs, pointers, and aggregate copies without scattering special cases across every layer.

## Diagnostics

The project has three main layers of diagnostics.

### Syntax Errors

Lexer and parser errors include source locations. When line and column are available, the top-level driver prints the relevant source line and a caret pointing at the failure.

### Semantic Errors

Semantic errors include function context when relevant, which makes it easier to diagnose invalid field usage, type mismatches, and bad calls.

### Runtime Errors

Runtime failures include instruction context. A VM error reports:

- the runtime problem
- the failing instruction index
- the exact pseudo-assembly instruction being executed

This is not full source-level debug mapping, but it is enough to make backend and runtime failures practical to investigate.

## Testing

The repository includes automated integration tests that compile and execute representative programs and also verify failure modes.

Current coverage includes:

- scalar pointer write-through
- struct-by-value parameter passing and return
- arrays of structs
- `->` field access
- whole-struct assignment
- invalid field access
- out-of-bounds runtime failures
- runtime error instruction reporting

Run the test suite with:

```powershell
python -m unittest discover -s tests -v
```

## Running The Project

To compile and run the demo program:

```powershell
python compiler.py
```

That command will:

1. read `input.cpp`
2. compile it
3. print the generated pseudo-assembly
4. write the assembly to `output.txt`
5. execute the result on the VM
6. print the final result and scalar global state

## Current Limits

The project is complete for its intended scale, but it is still intentionally narrow:

- no strings, chars, enums, unions, classes, templates, or standard library
- no preprocessor, headers, or includes
- no block comments
- no advanced dataflow or SSA-based optimization pipeline
- no native code or LLVM backend
- no source-level debug mapping from runtime failures back to AST nodes
- no full C or C++ memory model

## Final Perspective

The most important thing about this repository is not just the feature list. It is that the compiler is organized around clear layers:

- AST construction
- semantic validation
- small source-level optimization
- explicit memory-aware IR lowering
- textual code generation
- execution on an address-based VM

That structure is what makes it a solid standalone compiler project rather than just a parser demo with an attached interpreter.
