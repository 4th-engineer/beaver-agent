"""Code Analyzer Tool - Analyze repository structure and generate dependency graph"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()

__all__ = ["FunctionInfo", "ClassInfo", "ModuleInfo", "CodeAnalyzer", "analyze_repository"]


@dataclass
class FunctionInfo:
    """Represents a function definition extracted from Python source code.

    Attributes:
        name: Name of the function.
        line: Line number where the function is defined.
        docstring: Optional docstring extracted from the function body.
        calls: List of function names called within this function's body.
        decorators: List of decorator names applied to the function.
    """

    name: str
    line: int
    docstring: Optional[str] = None
    calls: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Represents a class definition extracted from Python source code.

    Attributes:
        name: Name of the class.
        line: Line number where the class is defined.
        docstring: Optional docstring extracted from the class body.
        methods: List of method names defined in this class.
        bases: List of base class names this class inherits from.
    """

    name: str
    line: int
    docstring: Optional[str] = None
    methods: List[str] = field(default_factory=list)
    bases: List[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Represents a Python module with its imports, classes, and functions.

    Attributes:
        path: File path to the module.
        imports: List of module names imported via `import X`.
        from_imports: Dict mapping source module to list of imported names via `from X import Y`.
        classes: List of ClassInfo objects for each class defined in this module.
        functions: List of FunctionInfo objects for each function defined in this module.
        calls_module: List of module names this module calls (imports + uses).
    """

    path: str
    imports: List[str] = field(default_factory=list)
    from_imports: Dict[str, List[str]] = field(default_factory=dict)
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    calls_module: List[str] = field(default_factory=list)  # modules this module calls


class CodeAnalyzer:
    """Analyze Python repository and build dependency graph"""

    # Compiled regex patterns (class-level, compiled once)
    _RE_FROM_IMPORT = re.compile(r"from\s+(\.[+]?\w*)\s+import\s+(.+)")
    _RE_CLASS_DEF = re.compile(r"class\s+(\w+)\s*(\([^)]*\))?\s*:")
    _RE_FUNC_DEF = re.compile(r"def\s+(\w+)\s*\(([^)]*)\)")
    _RE_FUNC_DEF_SIMPLE = re.compile(r"def\s+(\w+)\s*\(")
    _RE_FUNC_CALLS = re.compile(r"(?:(\w+)\.)?(\w+)\s*\(")

    def __init__(self, root_path: str):
        """Initialize the CodeAnalyzer with a project root path.

        Args:
            root_path: Absolute path to the project root directory to analyze.
                   The analyzer will scan `root_path/src/beaver_agent` for Python files.
        """
        self.root_path = Path(root_path)
        self.modules: Dict[str, ModuleInfo] = {}
        self.all_functions: Dict[str, Tuple[str, FunctionInfo]] = {}  # name -> (module, func)
        self.all_classes: Dict[str, Tuple[str, ClassInfo]] = {}  # name -> (module, class)
        self.call_graph: Dict[str, Set[str]] = {}  # module -> set of modules it calls

    def analyze(self) -> None:
        """Scan and analyze all Python files"""
        src_path = self.root_path / "src" / "beaver_agent"
        if not src_path.exists():
            logger.warning("code_analyzer_src_path_not_found", path=str(src_path))
            return

        # Find all Python files
        py_files = list(src_path.rglob("*.py"))
        py_files = [f for f in py_files if "__pycache__" not in str(f)]

        logger.info("code_analyzer_scanning", file_count=len(py_files))

        for py_file in py_files:
            self._analyze_file(py_file)

        # Build cross-module call graph
        self._build_call_graph()

    def _analyze_file(self, path: Path) -> None:
        """Analyze a single Python file"""
        rel_path = str(path.relative_to(self.root_path))
        module_name = self._file_to_module(path)
        module = ModuleInfo(path=rel_path)

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("code_analyzer_read_error", path=str(path), exc_info=e)
            return

        lines = content.split("\n")

        # Parse imports
        module.imports, module.from_imports = self._parse_imports(lines)

        # Parse classes
        module.classes = self._parse_classes(lines)

        # Parse functions
        module.functions = self._parse_functions(lines)

        # Track all functions and classes globally
        for cls in module.classes:
            self.all_classes[cls.name] = (module_name, cls)
            for method in cls.methods:
                full_name = f"{cls.name}.{method}"
                # Find method info
                for func in module.functions:
                    if func.name == method:
                        self.all_functions[full_name] = (module_name, func)
                        break

        for func in module.functions:
            self.all_functions[func.name] = (module_name, func)

        self.modules[module_name] = module

    def _file_to_module(self, path: Path) -> str:
        """Convert file path to module name"""
        parts = list(path.relative_to(self.root_path / "src" / "beaver_agent").parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1][:-3]  # Remove .py
        return ".".join(parts) if parts else "root"

    def _parse_imports(self, lines: List[str]) -> Tuple[List[str], Dict[str, List[str]]]:
        """Parse import statements"""
        imports = []
        from_imports = {}

        for line in lines:
            line = line.strip()
            if line.startswith("import "):
                name = line.replace("import ", "").split(" as ")[0].strip()
                imports.append(name)
            elif line.startswith("from "):
                match = self._RE_FROM_IMPORT.match(line)
                if match:
                    from_module = match.group(1)
                    items = [x.strip().split(" as ")[0] for x in match.group(2).split(",")]
                    from_imports[from_module] = items

        return imports, from_imports

    def _parse_classes(self, lines: List[str]) -> List[ClassInfo]:
        """Parse class definitions"""
        classes = []

        for i, line in enumerate(lines):
            # Class definition
            match = self._RE_CLASS_DEF.match(line)
            if match:
                name = match.group(1)
                bases = match.group(2).strip("() ").split(",") if match.group(2) else []
                bases = [b.strip() for b in bases if b.strip()]

                # Get docstring
                docstring = self._get_docstring(lines, i)

                # Find methods in this class
                methods = self._find_class_methods(lines, i)

                classes.append(
                    ClassInfo(
                        name=name, line=i + 1, docstring=docstring, methods=methods, bases=bases
                    )
                )

        return classes

    def _parse_functions(self, lines: List[str]) -> List[FunctionInfo]:
        """Parse function definitions"""
        functions = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check for decorated or normal function
            if line.startswith("def "):
                match = self._RE_FUNC_DEF.match(line)
                if match:
                    name = match.group(1)
                    decorators = self._get_decorators(lines, i)

                    docstring = self._get_docstring(lines, i)

                    # Find what this function calls
                    func_body = self._get_function_body(lines, i)
                    calls = self._find_calls(func_body)

                    functions.append(
                        FunctionInfo(
                            name=name,
                            line=i + 1,
                            docstring=docstring,
                            calls=calls,
                            decorators=decorators,
                        )
                    )
            i += 1

        return functions

    def _get_docstring(self, lines: List[str], start: int) -> Optional[str]:
        """Get docstring from a class or function"""
        if start + 1 >= len(lines):
            return None

        next_line = lines[start + 1].strip()
        if next_line.startswith('"""') or next_line.startswith("'''"):
            quote = next_line[:3]
            if next_line.count(quote) >= 2:
                return next_line.strip(quote)
            # Multi-line docstring
            doc_parts = [next_line.strip(quote)]
            j = start + 2
            while j < len(lines):
                line = lines[j].strip()
                if quote in line:
                    doc_parts.append(line.split(quote)[0])
                    break
                doc_parts.append(line)
                j += 1
            return " ".join(doc_parts).strip()[:100]
        return None

    def _get_decorators(self, lines: List[str], start: int) -> List[str]:
        """Get decorators for a function"""
        decorators = []
        for i in range(start - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith("@"):
                decorators.append(line[1:])
            elif line and not line.startswith("#"):
                break
        return decorators

    def _get_function_body(self, lines: List[str], start: int) -> str:
        """Get the body of a function"""
        indent = len(lines[start]) - len(lines[start].lstrip())

        body_lines = []
        for i in range(start + 1, len(lines)):
            line = lines[i]
            if line.strip() and not line.startswith(" " * (indent + 1)):
                break
            body_lines.append(line)
        return "\n".join(body_lines)

    def _find_class_methods(self, lines: List[str], class_start: int) -> List[str]:
        """Find method names in a class"""
        methods = []

        # Find end of class
        class_indent = len(lines[class_start]) - len(lines[class_start].lstrip())
        i = class_start + 1
        while i < len(lines):
            line = lines[i]
            if line.strip() and not line.startswith(" " * (class_indent + 1)):
                break
            if line.strip().startswith("def "):
                match = self._RE_FUNC_DEF_SIMPLE.match(line.strip())
                if match:
                    methods.append(match.group(1))
            i += 1

        return methods

    def _find_calls(self, body: str) -> List[str]:
        """Find function calls in a code block"""
        calls = []
        # Match function calls like foo() or module.foo()
        matches = self._RE_FUNC_CALLS.findall(body)
        for match in matches:
            if match[1] not in (
                "if",
                "else",
                "for",
                "while",
                "try",
                "except",
                "finally",
                "with",
                "as",
                "in",
                "is",
                "not",
                "and",
                "or",
                "True",
                "False",
                "None",
                "class",
                "def",
                "return",
                "yield",
                "raise",
                "import",
                "from",
                "pass",
                "break",
                "continue",
                "lambda",
                "assert",
                "del",
                "global",
                "nonlocal",
            ):
                calls.append(f"{match[0]}.{match[1]}" if match[0] else match[1])
        return list(set(calls))

    def _build_call_graph(self) -> None:
        """Build cross-module call graph"""
        for module_name, module in self.modules.items():
            self.call_graph[module_name] = set()

            for func in module.functions:
                for call in func.calls:
                    # Check if it's a known function/class
                    if call in self.all_functions:
                        called_module, _ = self.all_functions[call]
                        if called_module != module_name:
                            self.call_graph[module_name].add(called_module)
                    elif call in self.all_classes:
                        called_module, _ = self.all_classes[call]
                        if called_module != module_name:
                            self.call_graph[module_name].add(called_module)

            for cls in module.classes:
                for call in self._get_class_calls(module, cls):
                    if call in self.all_functions:
                        called_module, _ = self.all_functions[call]
                        if called_module != module_name:
                            self.call_graph[module_name].add(called_module)

    def _get_class_calls(self, module: ModuleInfo, cls: ClassInfo) -> List[str]:
        """Get all calls made by class methods"""
        calls = []
        for method_name in cls.methods:
            full_name = f"{cls.name}.{method_name}"
            if full_name in self.all_functions:
                _, func_info = self.all_functions[full_name]
                calls.extend(func_info.calls)
        return calls

    def generate_tree(self) -> str:
        """Generate a text tree visualization of the codebase structure.

        Produces a formatted ASCII tree showing:
        - Module hierarchy with directory groupings
        - Class definitions with bases, methods, and line numbers
        - Top-level functions with line numbers
        - Call graph connectivity indicators

        Returns:
            A formatted multi-line string representing the codebase map.
            The output includes a summary header (modules/classes/functions counts),
            the module tree, class details, call graph, and public API listings.

        Example:
            >>> analyzer = CodeAnalyzer("/path/to/project")
            >>> analyzer.analyze()
            >>> print(analyzer.generate_tree())
            🦫 Beaver Agent - Code Repository Map
            ============================================================
            <...module tree...>
        """
        lines = []
        lines.append("🦫 Beaver Agent - Code Repository Map")
        lines.append("=" * 60)
        lines.append("")

        # Summary
        total_modules = len(self.modules)
        total_classes = sum(len(m.classes) for m in self.modules.values())
        total_functions = sum(len(m.functions) for m in self.modules.values())

        lines.append(
            f"📊 Summary: {total_modules} modules | {total_classes} classes | {total_functions} functions"
        )
        lines.append("")

        # Sort modules
        sorted_modules = sorted(self.modules.keys())

        # Build tree by directory
        dirs = {}
        for module_name in sorted_modules:
            parts = module_name.split(".")
            if len(parts) > 1:
                dir_name = parts[0]
                if dir_name not in dirs:
                    dirs[dir_name] = []
                dirs[dir_name].append(module_name)
            else:
                if "_root" not in dirs:
                    dirs["_root"] = []
                dirs["_root"].append(module_name)

        def print_tree(items: List[str], prefix: str = "", is_last: bool = True) -> None:
            """Recursively build ASCII tree lines for module hierarchy display.

            Args:
                items: Module names to display at this level.
                prefix: Prefix string for indentation (tree branches).
                is_last: True if these items are the last siblings at this level.
            """
            for i, item in enumerate(sorted(items)):
                is_last_item = i == len(items) - 1
                connector = "└── " if is_last_item else "├── "
                lines.append(f"{prefix}{connector}{item}")

                # Add submodule indicator
                if "." in item:
                    current_prefix = prefix + ("    " if is_last_item else "│   ")
                    lines.append(f"{current_prefix}📄 {self.modules[item].path}")

                # Show classes
                module = self.modules[item]
                if module.classes:
                    for j, cls in enumerate(module.classes):
                        cls_connector = "└── " if j == len(module.classes) - 1 else "├── "
                        cls_prefix = prefix + ("    " if is_last_item else "│   ")
                        methods_str = (
                            f"({', '.join(cls.methods[:3])}{'...' if len(cls.methods) > 3 else ''})"
                            if cls.methods
                            else ""
                        )
                        bases_str = f" ← {', '.join(cls.bases)}" if cls.bases else ""
                        lines.append(f"{cls_prefix}{cls_connector}📦 {cls.name}{bases_str}")
                        lines.append(
                            f"{cls_prefix}    └─ methods: {', '.join(cls.methods)}"
                            if cls.methods
                            else f"{cls_prefix}    └─ methods: (none)"
                        )

                # Show functions
                if module.functions:
                    func_indent = "│   " if not is_last_item else "    "
                    lines.append(f"{prefix}{func_indent}└─ 📌 Functions:")
                    for func in module.functions[:5]:  # Limit to 5
                        lines.append(f"{prefix}{func_indent}   └─ {func.name}()")
                    if len(module.functions) > 5:
                        lines.append(
                            f"{prefix}{func_indent}   └─ ... and {len(module.functions) - 5} more"
                        )

        # Print each directory
        for dir_name, modules in sorted(dirs.items()):
            if dir_name != "_root":
                lines.append(f"📁 {dir_name}/")
                print_tree(modules, prefix="    ")
                lines.append("")
            else:
                for mod in modules:
                    lines.append(f"📄 {mod}")
                    module = self.modules[mod]
                    if module.classes:
                        for cls in module.classes:
                            lines.append(f"    └─ 📦 {cls.name}")
                    if module.functions:
                        lines.append(f"    └─ 📌 {', '.join(f.name for f in module.functions[:3])}")
                    lines.append("")

        # Call relationships
        lines.append("=" * 60)
        lines.append("🔗 Module Dependencies")
        lines.append("=" * 60)

        for module_name in sorted(self.call_graph.keys()):
            deps = self.call_graph[module_name]
            if deps:
                lines.append(f"\n📍 {module_name} →")
                for dep in sorted(deps):
                    lines.append(f"    └── {dep}")
                    # Show what functions are called
                    module = self.modules[module_name]
                    called_funcs = []
                    for func in module.functions:
                        for call in func.calls:
                            if call in self.all_functions:
                                dep_module, _ = self.all_functions[call]
                                if dep_module == dep:
                                    called_funcs.append(f"{func.name}() → {call}")
                            elif call in self.all_classes:
                                dep_module, _ = self.all_classes[call]
                                if dep_module == dep:
                                    called_funcs.append(f"{func.name}() → {call}")
                    for cf in called_funcs[:3]:
                        lines.append(f"        └─ {cf}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("📌 Key Entry Points")

        # Find main.py functions
        if "main" in self.modules:
            main_mod = self.modules["main"]
            for func in main_mod.functions:
                if not func.name.startswith("_"):
                    lines.append(f"  • main.{func.name}() - line {func.line}")

        # Find CLI commands
        if "cli.commands" in self.modules:
            cli_mod = self.modules["cli.commands"]
            for func in cli_mod.functions:
                if not func.name.startswith("_"):
                    lines.append(f"  • cli.commands.{func.name}() - line {func.line}")

        lines.append("")
        return "\n".join(lines)


def analyze_repository(root_path: str) -> str:
    """Analyze a repository and return a formatted code map.

    This is the main entry point for the CodeAnalyzer module. It:
    1. Discovers all Python source files under root_path (recursive)
    2. Parses each file for imports, classes, functions, and docstrings
    3. Builds a cross-module call graph
    4. Produces a formatted tree visualization

    Args:
        root_path: Absolute or relative path to the repository root.
            Must be a directory containing Python source files.

    Returns:
        A formatted multi-line string (same as CodeAnalyzer.generate_tree())
        containing the complete code map with summary stats, module tree,
        class details, call graph, and public API listings.

    Example:
        >>> result = analyze_repository("/path/to/project")
        >>> print(result)
        🦫 Beaver Agent - Code Repository Map
        ============================================================
        📊 Summary: 42 modules | 156 classes | 203 functions
        <...full tree output...>
    """
    analyzer = CodeAnalyzer(root_path)
    analyzer.analyze()
    return analyzer.generate_tree()
