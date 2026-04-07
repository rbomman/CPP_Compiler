from ir import IRProgram


class CodeGenerator:
    """Lower a structured IR program into pseudo-assembly strings."""

    def generate(self, ir_program):
        if not isinstance(ir_program, IRProgram):
            raise TypeError("CodeGenerator expects an IRProgram.")

        lines = []
        for instruction in ir_program.instructions:
            opcode = instruction.opcode
            operands = list(instruction.operands)

            if opcode == "CALL":
                target, args, dest = operands
                if args:
                    lines.append(f"CALL {target}, {', '.join(args)} -> {dest}")
                else:
                    lines.append(f"CALL {target} -> {dest}")
                continue

            if operands:
                lines.append(f"{opcode} {', '.join(str(operand) for operand in operands)}")
            else:
                lines.append(opcode)

        return lines
