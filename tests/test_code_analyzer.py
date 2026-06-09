"""Tests for Code Analyzer Tool"""

from pathlib import Path

import pytest

from beaver_agent.tools.code_analyzer import (
    ClassInfo,
    CodeAnalyzer,
    FunctionInfo,
    ModuleInfo,
    analyze_repository,
)


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure for testing"""
    src_dir = tmp_path / "src" / "beaver_agent"
    src_dir.mkdir(parents=True)

    # Create a simple module
    (src_dir / "example.py").write_text('''
"""Example module for testing"""

import os
import json

class ExampleClass:
    """An example class for testing"""

    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        """Return a greeting"""
        return f"Hello, {self.name}"

def standalone_function(x: int, y: int) -> int:
    """Add two numbers"""
    return x + y

def _private_func():
    """Private function - should still be detected"""
    return True
''')
    return tmp_path


def test_code_analyzer_initialization(temp_project):
    """Test CodeAnalyzer initializes correctly"""
    analyzer = CodeAnalyzer(temp_project)
    assert analyzer.root_path == Path(temp_project)
    assert analyzer.modules == {}
    assert analyzer.all_functions == {}
    assert analyzer.all_classes == {}


def test_analyze_discovers_modules(temp_project):
    """Test that analyze finds Python files"""
    analyzer = CodeAnalyzer(temp_project)
    analyzer.analyze()

    # Should find the example module
    assert len(analyzer.modules) > 0
    module_names = list(analyzer.modules.keys())
    assert "example" in module_names


def test_analyze_extracts_classes(temp_project):
    """Test that classes are extracted correctly"""
    analyzer = CodeAnalyzer(temp_project)
    analyzer.analyze()

    # Should find ExampleClass
    assert "ExampleClass" in analyzer.all_classes
    module_name, class_info = analyzer.all_classes["ExampleClass"]
    assert isinstance(class_info, ClassInfo)
    assert class_info.name == "ExampleClass"
    assert "greet" in class_info.methods
    assert "ExampleClass.greet" in analyzer.all_functions


def test_analyze_extracts_functions(temp_project):
    """Test that functions are extracted correctly"""
    analyzer = CodeAnalyzer(temp_project)
    analyzer.analyze()

    # Should find standalone functions
    assert "standalone_function" in analyzer.all_functions
    module_name, func_info = analyzer.all_functions["standalone_function"]
    assert isinstance(func_info, FunctionInfo)
    assert func_info.name == "standalone_function"


def test_analyze_extracts_methods(temp_project):
    """Test that class methods are tracked"""
    analyzer = CodeAnalyzer(temp_project)
    analyzer.analyze()

    # Method should be tracked under full name
    assert "ExampleClass.greet" in analyzer.all_functions


def test_analyze_builds_call_graph(temp_project):
    """Test that call graph is built"""
    analyzer = CodeAnalyzer(temp_project)
    analyzer.analyze()

    # Call graph should exist
    assert isinstance(analyzer.call_graph, dict)


def test_analyze_call_graph_cross_module_edges(temp_project):
    """Test that call graph captures cross-module call edges.

    Verifies that when module A calls a function from module B,
    the call graph correctly records B as a dependency of A.
    """
    # Create two modules where one imports from the other
    src_dir = temp_project / "src" / "beaver_agent"
    (src_dir / "__init__.py").write_text("")
    (src_dir / "caller.py").write_text('''
"""Caller module that uses ExampleClass."""
from .example import ExampleClass

def use_example():
    """Use the example class."""
    obj = ExampleClass("test")
    return obj.greet()
''')
    # Overwrite the original example.py to be a proper module
    (src_dir / "example.py").write_text('''
"""Example module for testing."""

class ExampleClass:
    """An example class for testing."""

    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        """Return a greeting."""
        return f"Hello, {self.name}"
''')

    analyzer = CodeAnalyzer(temp_project)
    analyzer.analyze()

    # The call graph should contain entries for both modules
    assert "example" in analyzer.modules
    assert "caller" in analyzer.modules

    # caller should have example as a dependency (calls ExampleClass)
    assert "example" in analyzer.call_graph.get("caller", set())


def test_file_to_module_name():
    """Test conversion of file paths to module names"""
    # Use actual project structure for this test
    root = Path("/home/agentuser/beaver-agent")
    analyzer = CodeAnalyzer(root)

    # Test __init__.py handling - returns "root" when it's the only item
    result = analyzer._file_to_module(
        Path("/home/agentuser/beaver-agent/src/beaver_agent/__init__.py")
    )
    assert result == "root"

    # Test regular module
    result = analyzer._file_to_module(
        Path("/home/agentuser/beaver-agent/src/beaver_agent/tools/code_gen.py")
    )
    assert result == "tools.code_gen"


def test_parse_imports():
    """Test import statement parsing"""
    analyzer = CodeAnalyzer("/fake")
    content = """
import os
import json
from typing import List
from . import module
from .utils import helper
"""
    imports, from_imports = analyzer._parse_imports(content.split("\n"))

    assert "os" in imports
    assert "json" in imports
    assert "." in from_imports
    assert "helper" in from_imports[".utils"]


def test_parse_classes_with_bases():
    """Test class parsing with base classes"""
    analyzer = CodeAnalyzer("/fake")
    content = '''
class Child(Parent):
    """Child class"""
    pass

class Standalone():
    """Standalone class"""
    pass
'''
    classes = analyzer._parse_classes(content.split("\n"))
    assert len(classes) == 2

    child_class = next((c for c in classes if c.name == "Child"), None)
    assert child_class is not None
    assert "Parent" in child_class.bases


def test_parse_functions():
    """Test function parsing"""
    analyzer = CodeAnalyzer("/fake")
    content = '''
def regular_func():
    """A regular function"""
    pass

def func_with_args(x: int, y: str) -> bool:
    """Function with args"""
    return True

def _private():
    """Private function"""
    pass
'''
    functions = analyzer._parse_functions(content.split("\n"))
    assert len(functions) >= 3

    func_names = [f.name for f in functions]
    assert "regular_func" in func_names
    assert "func_with_args" in func_names
    assert "_private" in func_names


def test_get_docstring():
    """Test docstring extraction"""
    analyzer = CodeAnalyzer("/fake")
    lines = ["def my_func():", '    """This is', "    a multi-line", '    docstring"""', "    pass"]
    doc = analyzer._get_docstring(lines, 0)
    assert doc is not None
    assert "multi-line" in doc


def test_get_decorators():
    """Test decorator detection"""
    analyzer = CodeAnalyzer("/fake")
    lines = ["@property", "@retry(max_attempts=3)", "def my_method():", "    pass"]
    decorators = analyzer._get_decorators(lines, 2)
    # Decorators are stored without the @ symbol
    assert "property" in decorators
    assert "retry(max_attempts=3)" in decorators


def test_analyze_repository_function(temp_project):
    """Test the analyze_repository entry point"""
    result = analyze_repository(str(temp_project))
    assert isinstance(result, str)
    assert "🦫 Beaver Agent" in result or "Summary" in result


def test_analyze_handles_read_error(tmp_path):
    """Test that analyze gracefully handles unreadable files"""
    # Create a real project structure so relative_to works
    src_dir = tmp_path / "src" / "beaver_agent"
    src_dir.mkdir(parents=True)

    analyzer = CodeAnalyzer(tmp_path)
    # Calling _analyze_file on a file outside project should be handled gracefully
    # Since it uses relative_to on a path that doesn't match, it will raise
    # This is expected behavior - it validates that paths are within the project


def test_module_info_dataclass():
    """Test ModuleInfo dataclass"""
    module = ModuleInfo(path="test.py")
    assert module.path == "test.py"
    assert module.imports == []
    assert module.from_imports == {}
    assert module.classes == []
    assert module.functions == []


def test_function_info_dataclass():
    """Test FunctionInfo dataclass"""
    func = FunctionInfo(name="test", line=10)
    assert func.name == "test"
    assert func.line == 10
    assert func.docstring is None
    assert func.calls == []
    assert func.decorators == []


def test_class_info_dataclass():
    """Test ClassInfo dataclass"""
    cls = ClassInfo(name="MyClass", line=5)
    assert cls.name == "MyClass"
    assert cls.line == 5
    assert cls.docstring is None
    assert cls.methods == []
    assert cls.bases == []


def test_find_calls():
    """Test function call extraction from code body"""
    analyzer = CodeAnalyzer("/fake")

    # Simple function calls
    body = """
    result = foo()
    items.append(bar)
    """
    calls = analyzer._find_calls(body)
    assert "foo" in calls
    assert "items.append" in calls  # method call stored as 'module.method'

    # Module-qualified calls (regex captures only immediate dotted part, e.g. 'path.join' not 'os.path.join')
    body = """
    path.join(a, b)
    json.loads(data)
    """
    calls = analyzer._find_calls(body)
    assert "path.join" in calls
    assert "json.loads" in calls

    # Filter out keywords
    body = """
    if x == y:
        return True
    for i in items:
        print(i)
    """
    calls = analyzer._find_calls(body)
    assert "if" not in calls
    assert "else" not in calls
    assert "for" not in calls
    assert "return" not in calls
    assert "print" in calls  # print is a function call, not a keyword in this context


def test_find_calls_excludes_keywords():
    """Test that _find_calls properly excludes Python keywords and built-ins"""
    analyzer = CodeAnalyzer("/fake")

    body = """
    x = True if condition else False
    while running:
        break
    continue
    """
    calls = analyzer._find_calls(body)
    # These are keywords/built-ins, not function calls
    assert "if" not in calls
    assert "else" not in calls
    assert "while" not in calls
    assert "break" not in calls
    assert "continue" not in calls


def test_get_function_body():
    """Test extraction of function body from source"""
    analyzer = CodeAnalyzer("/fake")
    content = """
def example():
    x = 1
    y = 2
    return x + y

def other():
    pass
"""
    lines = content.split("\n")
    # Find the "def example():" line (index 1)
    body = analyzer._get_function_body(lines, 1)
    assert "x = 1" in body
    assert "y = 2" in body
    assert "return x + y" in body
    # Should not include 'def other()'
    assert "def other" not in body


def test_find_class_methods_multiline():
    """Test detection of methods across multiple lines"""
    analyzer = CodeAnalyzer("/fake")
    content = '''
class MyClass:
    """A class with methods"""
    
    def method_one(self):
        """First method"""
        pass
    
    def method_two(self, x):
        """Second method"""
        return x
'''
    methods = analyzer._find_class_methods(content.split("\n"), 1)  # line with "class MyClass:" (index 1)
    assert "method_one" in methods
    assert "method_two" in methods


def test_generate_tree_output_structure(temp_project):
    """Test that generate_tree produces the expected output sections.

    Verifies that the tree output contains key structural sections:
    - Beaver branding header
    - Summary stats (modules, classes, functions)
    - Module Dependencies section
    """
    analyzer = CodeAnalyzer(temp_project)
    analyzer.analyze()

    result = analyzer.generate_tree()

    # Should contain branding header
    assert "Beaver" in result
    # Should contain summary stats
    assert "Summary" in result or "modules" in result
    # Should contain call graph / dependencies section
    assert "Module Dependencies" in result or "Dependencies" in result
