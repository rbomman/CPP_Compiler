import re


class VirtualCPUError(Exception):
    """Raised when the virtual CPU encounters an invalid instruction or state."""


class VirtualCPU:
    def __init__(self, instructions):
        self.instructions = instructions
        self.parsed_instructions = []
        self.labels = {}
        self.globals = {}
        self.memory = {}
        self.call_stack = []
        self.last_cmp = 0
        self.ip = 0
        self.halted = False
        self.return_value = None
        self.next_address = 1
        self._parse_instructions()

    def run(self):
        while not self.halted and self.ip < len(self.parsed_instructions):
            instruction = self.parsed_instructions[self.ip]
            try:
                self.execute_instruction(instruction)
            except VirtualCPUError as exc:
                source = instruction.get("source", instruction["opcode"])
                raise VirtualCPUError(
                    f"{exc} At instruction {instruction.get('index', self.ip) + 1}: {source}"
                ) from exc
        return self.return_value

    def execute_instruction(self, instruction):
        opcode = instruction["opcode"]
        operands = instruction.get("operands", [])

        if opcode == "LABEL":
            self.ip += 1
        elif opcode == "ALLOC":
            name, size = operands
            self.allocate_symbol(name, self.resolve_value(size))
            self.ip += 1
        elif opcode == "ADDR":
            dest, name, stride, span = operands
            entry = self.get_symbol_entry(name)
            self.write_name(
                dest,
                self.make_pointer(
                    entry["addr"],
                    self.resolve_value(stride),
                    self.resolve_value(span),
                    entry["addr"],
                    entry["addr"] + entry["size"] - 1,
                    name,
                ),
            )
            self.ip += 1
        elif opcode == "INDEXADDR":
            dest, base_pointer, index, stride, span = operands
            pointer = self.resolve_pointer(base_pointer)
            self.write_name(
                dest,
                self.make_pointer(
                    pointer["addr"] + self.resolve_value(index) * self.resolve_value(stride),
                    self.resolve_value(stride),
                    self.resolve_value(span),
                    pointer["lower"],
                    pointer["upper"],
                    pointer["origin"],
                ),
            )
            self.ip += 1
        elif opcode == "FIELDPTR":
            dest, base_pointer, offset, stride, span = operands
            pointer = self.resolve_pointer(base_pointer)
            self.write_name(
                dest,
                self.make_pointer(
                    pointer["addr"] + self.resolve_value(offset),
                    self.resolve_value(stride),
                    self.resolve_value(span),
                    pointer["lower"],
                    pointer["upper"],
                    pointer["origin"],
                ),
            )
            self.ip += 1
        elif opcode == "MOV":
            dest, src = operands
            self.write_name(dest, self.resolve_value(src))
            self.ip += 1
        elif opcode == "LOADPTR":
            dest, pointer = operands
            pointer_value = self.resolve_pointer(pointer)
            self.ensure_pointer_range(pointer_value, pointer_value["span"], "read")
            self.write_name(dest, self.memory_get(pointer_value["addr"]))
            self.ip += 1
        elif opcode == "STOREPTR":
            pointer, value = operands
            pointer_value = self.resolve_pointer(pointer)
            self.ensure_pointer_range(pointer_value, pointer_value["span"], "write")
            self.memory_set(pointer_value["addr"], self.resolve_value(value))
            self.ip += 1
        elif opcode == "COPY":
            dest_pointer, src_pointer, size = operands
            dest = self.resolve_pointer(dest_pointer)
            src = self.resolve_pointer(src_pointer)
            size_value = self.resolve_value(size)
            self.ensure_pointer_range(dest, size_value, "copy destination")
            self.ensure_pointer_range(src, size_value, "copy source")
            for offset in range(size_value):
                self.memory_set(dest["addr"] + offset, self.memory_get(src["addr"] + offset))
            self.ip += 1
        elif opcode in {"PTRADD", "PTRSUB"}:
            dest, pointer, offset = operands
            pointer_value = self.resolve_pointer(pointer)
            step = self.resolve_value(offset) * pointer_value["stride"]
            if opcode == "PTRSUB":
                step = -step
            self.write_name(
                dest,
                self.make_pointer(
                    pointer_value["addr"] + step,
                    pointer_value["stride"],
                    pointer_value["span"],
                    pointer_value["lower"],
                    pointer_value["upper"],
                    pointer_value["origin"],
                ),
            )
            self.ip += 1
        elif opcode in {"ADD", "SUB", "MUL", "DIV", "MOD", "POW", "AND", "OR"}:
            dest, left, right = operands
            left_value = self.resolve_value(left)
            right_value = self.resolve_value(right)
            if opcode == "ADD":
                result = left_value + right_value
            elif opcode == "SUB":
                result = left_value - right_value
            elif opcode == "MUL":
                result = left_value * right_value
            elif opcode == "DIV":
                if right_value == 0:
                    raise VirtualCPUError("Division by zero.")
                result = left_value / right_value if isinstance(left_value, float) or isinstance(right_value, float) else left_value // right_value
            elif opcode == "MOD":
                if right_value == 0:
                    raise VirtualCPUError("Modulo by zero.")
                result = left_value % right_value
            elif opcode == "POW":
                result = left_value ** right_value
            elif opcode == "AND":
                result = 1 if left_value and right_value else 0
            else:
                result = 1 if left_value or right_value else 0
            self.write_name(dest, result)
            self.ip += 1
        elif opcode == "CMP":
            left, right = operands
            self.last_cmp = self.resolve_value(left) - self.resolve_value(right)
            self.ip += 1
        elif opcode in {"SETL", "SETG", "SETLE", "SETGE", "SETE", "SETNE"}:
            dest = operands[0]
            comparisons = {
                "SETL": self.last_cmp < 0,
                "SETG": self.last_cmp > 0,
                "SETLE": self.last_cmp <= 0,
                "SETGE": self.last_cmp >= 0,
                "SETE": self.last_cmp == 0,
                "SETNE": self.last_cmp != 0,
            }
            self.write_name(dest, 1 if comparisons[opcode] else 0)
            self.ip += 1
        elif opcode == "JMP":
            self.jump_to_label(operands[0])
        elif opcode == "JE":
            if self.last_cmp == 0:
                self.jump_to_label(operands[0])
            else:
                self.ip += 1
        elif opcode == "JL":
            if self.last_cmp < 0:
                self.jump_to_label(operands[0])
            else:
                self.ip += 1
        elif opcode == "CALL":
            self.handle_call(instruction)
        elif opcode == "RET":
            self.handle_return()
        elif opcode == "HALT":
            self.return_value = self.resolve_name("ret", default=self.return_value)
            self.halted = True
        else:
            raise VirtualCPUError(f"Unsupported opcode '{opcode}'.")

    def handle_call(self, instruction):
        arg_values = [self.resolve_value(arg) for arg in instruction["args"]]
        frame = {
            "symbols": {},
            "return_ip": self.ip + 1,
            "return_dest": instruction["dest"],
        }
        self.call_stack.append(frame)
        for index, arg in enumerate(arg_values):
            self.write_name(f"__arg{index}", arg)
        self.jump_to_label(instruction["target"])

    def handle_return(self):
        if not self.call_stack:
            self.return_value = self.resolve_name("ret", default=self.return_value)
            self.halted = True
            return

        frame = self.call_stack.pop()
        result = self.read_symbol_value(frame["symbols"].get("ret")) if "ret" in frame["symbols"] else self.resolve_name("ret", default=0)
        if self.call_stack:
            if frame["return_dest"] is not None:
                self.write_name_in_frame(self.call_stack[-1], frame["return_dest"], result)
        elif frame["return_dest"] is not None:
            self.write_global_name(frame["return_dest"], result)
        self.return_value = result
        self.ip = frame["return_ip"]

    def jump_to_label(self, label):
        if label not in self.labels:
            raise VirtualCPUError(f"Unknown label '{label}'.")
        self.ip = self.labels[label]

    def resolve_value(self, token):
        if isinstance(token, (int, float, dict)):
            return token
        if re.fullmatch(r"-?\d+\.\d+", token):
            return float(token)
        if re.fullmatch(r"-?\d+", token):
            return int(token)
        return self.resolve_name(token)

    def resolve_pointer(self, token):
        value = self.resolve_value(token)
        if not isinstance(value, dict) or "addr" not in value:
            raise VirtualCPUError(f"Expected pointer value, got '{value}'.")
        return value

    def resolve_name(self, name, default=None):
        entry = self.lookup_symbol_entry(name)
        if entry is None:
            if default is not None:
                return default
            raise VirtualCPUError(f"Undefined value '{name}'.")
        return self.read_symbol_value(entry)

    def write_name(self, name, value):
        if self.call_stack:
            self.write_name_in_frame(self.call_stack[-1], name, value)
            return
        self.write_global_name(name, value)

    def write_name_in_frame(self, frame, name, value):
        entry = frame["symbols"].get(name)
        if entry is None:
            entry = self.allocate_symbol(name, 1, frame=frame)
        self.memory_set(entry["addr"], value)

    def write_global_name(self, name, value):
        entry = self.globals.get(name)
        if entry is None:
            entry = self.allocate_symbol(name, 1, frame=None)
        self.memory_set(entry["addr"], value)

    def allocate_symbol(self, name, size, frame="current"):
        if frame == "current":
            target_frame = self.call_stack[-1] if self.call_stack else None
        else:
            target_frame = frame
        table = self.globals if target_frame is None else target_frame["symbols"]
        if name in table:
            return table[name]
        size_value = int(size)
        entry = {"addr": self.next_address, "size": size_value}
        table[name] = entry
        for offset in range(size_value):
            self.memory[self.next_address + offset] = 0
        self.next_address += size_value
        return entry

    def get_symbol_entry(self, name):
        entry = self.lookup_symbol_entry(name)
        if entry is None:
            raise VirtualCPUError(f"Undefined symbol '{name}'.")
        return entry

    def lookup_symbol_entry(self, name):
        if self.call_stack and name in self.call_stack[-1]["symbols"]:
            return self.call_stack[-1]["symbols"][name]
        if name in self.globals:
            return self.globals[name]
        return None

    def read_symbol_value(self, entry):
        if entry is None:
            raise VirtualCPUError("Cannot read undefined symbol entry.")
        return self.memory_get(entry["addr"])

    def memory_get(self, address):
        if address not in self.memory:
            raise VirtualCPUError(f"Invalid memory address '{address}'.")
        return self.memory[address]

    def memory_set(self, address, value):
        if address not in self.memory:
            raise VirtualCPUError(f"Invalid memory address '{address}'.")
        self.memory[address] = value

    def make_pointer(self, addr, stride, span, lower, upper, origin):
        return {
            "addr": addr,
            "stride": stride,
            "span": span,
            "lower": lower,
            "upper": upper,
            "origin": origin,
        }

    def ensure_pointer_range(self, pointer, span, action):
        start = pointer["addr"]
        end = start + span - 1
        if start < pointer["lower"] or end > pointer["upper"]:
            raise VirtualCPUError(
                f"Out-of-bounds {action} through pointer from '{pointer['origin']}' "
                f"(address {start}..{end}, valid {pointer['lower']}..{pointer['upper']})."
            )

    def snapshot_globals(self):
        return {name: self.memory_get(entry["addr"]) for name, entry in self.globals.items() if entry["size"] == 1}

    def _parse_instructions(self):
        call_pattern = re.compile(r"^CALL\s+(?P<target>\S+)(?:,\s*(?P<args>.*?))?\s*->\s*(?P<dest>\S+)$")
        for index, line in enumerate(self.instructions):
            text = line.strip()
            if not text:
                continue
            if text.startswith("CALL "):
                match = call_pattern.match(text)
                if not match:
                    raise VirtualCPUError(f"Invalid CALL instruction: '{text}'")
                args_text = match.group("args")
                args = [] if not args_text else [part.strip() for part in args_text.split(",")]
                self.parsed_instructions.append(
                    {"opcode": "CALL", "target": match.group("target"), "args": args, "dest": match.group("dest")}
                )
                continue

            parts = text.split(maxsplit=1)
            opcode = parts[0]
            operand_text = parts[1] if len(parts) > 1 else ""
            operands = [operand.strip() for operand in operand_text.split(",")] if operand_text else []
            if opcode == "LABEL":
                if len(operands) != 1:
                    raise VirtualCPUError(f"Invalid LABEL instruction: '{text}'")
                self.labels[operands[0]] = len(self.parsed_instructions)
            self.parsed_instructions.append(
                {"opcode": opcode, "operands": operands, "source": text, "index": index}
            )
