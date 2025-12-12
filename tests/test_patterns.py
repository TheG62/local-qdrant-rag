#!/usr/bin/env python3
"""
Comprehensive tests for CLI pattern recognition.

Tests all patterns: greeting, meta, index, collection, filesystem commands.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli import (
    is_greeting,
    is_meta_question,
    parse_index_command,
    parse_collection_command,
    parse_filesystem_command,
    extract_path_from_text,
)


class Colors:
    """Terminal colors for output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def test_result(name: str, passed: bool, details: str = ""):
    """Print test result."""
    if passed:
        print(f"  {Colors.GREEN}✓{Colors.RESET} {name}")
    else:
        print(f"  {Colors.RED}✗{Colors.RESET} {name}")
        if details:
            print(f"    {Colors.YELLOW}→ {details}{Colors.RESET}")
    return passed


def test_greetings():
    """Test greeting pattern recognition."""
    print(f"\n{Colors.BOLD}═══ GREETING PATTERNS ═══{Colors.RESET}")
    
    # Should be recognized as greetings
    greetings = [
        "hallo",
        "Hallo!",
        "hi",
        "hey",
        "moin",
        "guten morgen",
        "guten tag",
        "wie geht's",
        "wie geht es dir",
        "danke",
        "vielen dank",
        "danke für die hilfe",
        "tschüss",
        "bye",
    ]
    
    # Should NOT be recognized as greetings
    not_greetings = [
        "hallo, was ist RAG?",
        "danke, kannst du mir noch helfen?",
        "hi, indexiere /Users/test",
        "guten tag, was macht TimeSkipCom?",
    ]
    
    passed = 0
    total = 0
    
    print("\n  Should be greetings:")
    for query in greetings:
        total += 1
        result = is_greeting(query)
        if test_result(f"'{query}'", result, f"Expected True, got {result}"):
            passed += 1
    
    print("\n  Should NOT be greetings:")
    for query in not_greetings:
        total += 1
        result = not is_greeting(query)
        if test_result(f"'{query}'", result, f"Expected False, got {not result}"):
            passed += 1
    
    return passed, total


def test_meta_questions():
    """Test meta question pattern recognition."""
    print(f"\n{Colors.BOLD}═══ META QUESTION PATTERNS ═══{Colors.RESET}")
    
    # Should be recognized as meta questions
    meta_questions = [
        "was kannst du",
        "was kannst du?",
        "wer bist du",
        "wie funktionierst du",
        "welche dokumente hast du",
        "was weißt du",
        "hilfe",
        "help",
        "was kann ich fragen",
    ]
    
    # Should NOT be meta questions (contain paths or are content questions)
    not_meta = [
        "was kannst du in /Users/test finden",
        "welche dokumente hast du in ~/Desktop",
        "was ist RAG",
        "erkläre mir GDPR",
        "zeige mir /Users/test",
    ]
    
    passed = 0
    total = 0
    
    print("\n  Should be meta questions:")
    for query in meta_questions:
        total += 1
        result = is_meta_question(query)
        if test_result(f"'{query}'", result, f"Expected True, got {result}"):
            passed += 1
    
    print("\n  Should NOT be meta questions:")
    for query in not_meta:
        total += 1
        result = not is_meta_question(query)
        if test_result(f"'{query}'", result, f"Expected False, got {not result}"):
            passed += 1
    
    return passed, total


def test_path_extraction():
    """Test path extraction from text."""
    print(f"\n{Colors.BOLD}═══ PATH EXTRACTION ═══{Colors.RESET}")
    
    test_cases = [
        # (input, expected_path)
        ("/Users/test/documents", "/Users/test/documents"),
        ("~/Desktop", "~/Desktop"),
        ("~/Desktop/test", "~/Desktop/test"),
        ("bitte den gesamten inhalt /Users/test", "/Users/test"),
        ("/Users/guneyyilmaz/Destop", "/Users/guneyyilmaz/Desktop"),  # Typo correction
        ("./documents", "./documents"),
        ("../parent", "../parent"),
        ("/Users/../../../etc/passwd", "/Users/../../../etc/passwd"),  # Path traversal detected
        ("/Users/test//double//slashes", "/Users/test/double/slashes"),  # Normalized
        ("~test", None),  # Invalid home path (no /)
    ]
    
    passed = 0
    total = 0
    
    for input_text, expected in test_cases:
        total += 1
        result = extract_path_from_text(input_text)
        match = result == expected
        if test_result(f"'{input_text}' → '{result}'", match, f"Expected '{expected}'"):
            passed += 1
    
    return passed, total


def test_index_commands():
    """Test index command pattern recognition."""
    print(f"\n{Colors.BOLD}═══ INDEX COMMAND PATTERNS ═══{Colors.RESET}")
    
    test_cases = [
        # (input, expected_path, expected_recursive)
        ("indexiere /Users/test", "/Users/test", False),
        ("indexiere /Users/test -r", "/Users/test", True),
        ("indexiere /Users/test rekursiv", "/Users/test", True),
        ("indiziere ~/Desktop", "~/Desktop", False),
        ("lade /Users/documents", "/Users/documents", False),
        ("importiere ~/Dokumente", "~/Dokumente", False),
        ("füge /Users/test hinzu", "/Users/test", False),
        ("füge ~/Desktop zur datenbank hinzu", "~/Desktop", False),
        ("lerne /Users/test", "/Users/test", False),
        ("ingest /Users/test", "/Users/test", False),
        ("bitte indexiere /Users/test", "/Users/test", False),
        ("indexiere bitte den gesamten inhalt /Users/test", "/Users/test", False),
        # Edge cases
        ("indexiere /Users/test und dann suche nach RAG", "/Users/test", False),  # Stop at "und"
    ]
    
    passed = 0
    total = 0
    
    for input_text, expected_path, expected_recursive in test_cases:
        total += 1
        result = parse_index_command(input_text)
        
        if result is None:
            match = expected_path is None
            details = f"Expected path '{expected_path}', got None"
        else:
            # Normalize paths for comparison
            result_path = result.get("path", "")
            match = (result_path == expected_path and 
                    result.get("recursive", False) == expected_recursive)
            details = f"Expected ({expected_path}, rec={expected_recursive}), got ({result_path}, rec={result.get('recursive')})"
        
        if test_result(f"'{input_text}'", match, details if not match else ""):
            passed += 1
    
    return passed, total


def test_collection_commands():
    """Test collection command pattern recognition."""
    print(f"\n{Colors.BOLD}═══ COLLECTION COMMAND PATTERNS ═══{Colors.RESET}")
    
    test_cases = [
        # (input, expected_action, expected_name)
        ("erstelle wissensdatenbank projekt-2025", "create", "projekt-2025"),
        ("erstelle neue datenbank test", "create", "test"),
        ("zeige alle wissensdatenbanken", "list", None),
        ("welche collections gibt es", "list", None),
        ("lösche wissensdatenbank test", "delete", "test"),
        ("wechsel zu projekt-2025", "switch", "projekt-2025"),
        ("nutze datenbank archiv", "switch", "archiv"),
        ("info projekt-2025", "info", "projekt-2025"),
    ]
    
    passed = 0
    total = 0
    
    for input_text, expected_action, expected_name in test_cases:
        total += 1
        result = parse_collection_command(input_text)
        
        if result is None:
            match = expected_action is None
            details = f"Expected action '{expected_action}', got None"
        else:
            match = (result.get("action") == expected_action and 
                    result.get("name") == expected_name)
            details = f"Expected ({expected_action}, {expected_name}), got ({result.get('action')}, {result.get('name')})"
        
        if test_result(f"'{input_text}'", match, details if not match else ""):
            passed += 1
    
    return passed, total


def test_filesystem_commands():
    """Test filesystem command pattern recognition."""
    print(f"\n{Colors.BOLD}═══ FILESYSTEM COMMAND PATTERNS ═══{Colors.RESET}")
    
    test_cases = [
        # (input, expected_action)
        ("ls", "list"),
        ("ls /Users/test", "list"),
        ("zeige inhalt von /Users/test", "list"),
        ("was befindet sich auf meinem desktop", "list"),
        ("cd /Users/test", "navigate"),
        ("navigiere zu ~/Desktop", "navigate"),
        ("gehe in /Users/test", "navigate"),
        ("wo bin ich", "where"),
        ("pwd", "where"),
        ("tree", "tree"),
        ("tree /Users/test", "tree"),
        ("erstelle ordner test", "create_dir"),
        ("mkdir /Users/test/new", "create_dir"),
        ("erstelle datei test.txt", "create_file"),
        ("verschiebe file.txt nach new.txt", "move"),
        ("mv source.txt dest.txt", "move"),
        ("kopiere file.txt nach backup.txt", "copy"),
        ("cp source.txt dest.txt", "copy"),
        ("lösche file.txt", "delete"),
        ("rm /Users/test/file.txt", "delete"),
        ("organisiere /Users/test nach themen", "organize"),
        ("organisiere ~/Desktop mit wissen", "organize"),
        ("räume auf den desktop", "organize"),
        ("finde ähnliche dokumente zu /Users/test/doc.pdf", "find_similar"),
    ]
    
    passed = 0
    total = 0
    
    for input_text, expected_action in test_cases:
        total += 1
        result = parse_filesystem_command(input_text)
        
        if result is None:
            match = expected_action is None
            details = f"Expected action '{expected_action}', got None"
        else:
            match = result.get("action") == expected_action
            details = f"Expected '{expected_action}', got '{result.get('action')}'"
        
        if test_result(f"'{input_text}'", match, details if not match else ""):
            passed += 1
    
    return passed, total


def test_command_priority():
    """Test that commands have correct priority."""
    print(f"\n{Colors.BOLD}═══ COMMAND PRIORITY ═══{Colors.RESET}")
    
    # When path is present, filesystem should take priority over collection
    test_cases = [
        # (input, should_be_filesystem, should_be_collection)
        ("zeige /Users/test", True, False),
        ("zeige alle wissensdatenbanken", False, True),
        ("wechsel zu /Users/test", True, False),  # Path = filesystem
        ("wechsel zu projekt-2025", False, True),  # No path = collection
    ]
    
    passed = 0
    total = 0
    
    for input_text, expect_fs, expect_coll in test_cases:
        total += 1
        
        fs_result = parse_filesystem_command(input_text)
        coll_result = parse_collection_command(input_text)
        
        is_fs = fs_result is not None
        is_coll = coll_result is not None and fs_result is None
        
        match = (is_fs == expect_fs) and (is_coll == expect_coll)
        details = f"FS={is_fs} (expected {expect_fs}), Coll={is_coll} (expected {expect_coll})"
        
        if test_result(f"'{input_text}'", match, details if not match else ""):
            passed += 1
    
    return passed, total


def test_security_patterns():
    """Test security-related pattern handling."""
    print(f"\n{Colors.BOLD}═══ SECURITY PATTERNS ═══{Colors.RESET}")
    
    test_cases = [
        # Path traversal should be detected but not blocked (validation happens later)
        ("/Users/../../../etc/passwd", True),  # Detected as path
        ("indexiere /Users/../../../etc/passwd", True),  # Should parse but path contains ..
    ]
    
    passed = 0
    total = 0
    
    print("\n  Path traversal detection:")
    for input_text, should_detect_path in test_cases:
        total += 1
        
        path = extract_path_from_text(input_text)
        detected = path is not None
        
        match = detected == should_detect_path
        has_traversal = path and ".." in path
        
        details = f"Path: '{path}', Has traversal: {has_traversal}"
        if test_result(f"'{input_text}'", match, details):
            passed += 1
    
    return passed, total


def main():
    """Run all pattern tests."""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("CLI PATTERN RECOGNITION TESTS")
    print(f"{'='*60}{Colors.RESET}")
    
    results = []
    
    # Run all test suites
    results.append(("Greetings", test_greetings()))
    results.append(("Meta Questions", test_meta_questions()))
    results.append(("Path Extraction", test_path_extraction()))
    results.append(("Index Commands", test_index_commands()))
    results.append(("Collection Commands", test_collection_commands()))
    results.append(("Filesystem Commands", test_filesystem_commands()))
    results.append(("Command Priority", test_command_priority()))
    results.append(("Security Patterns", test_security_patterns()))
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{Colors.RESET}")
    
    total_passed = 0
    total_tests = 0
    
    for name, (passed, total) in results:
        total_passed += passed
        total_tests += total
        
        if passed == total:
            status = f"{Colors.GREEN}✓ PASSED{Colors.RESET}"
        else:
            status = f"{Colors.RED}✗ FAILED{Colors.RESET}"
        
        print(f"  {status}: {name} ({passed}/{total})")
    
    print(f"\n{Colors.BOLD}Total: {total_passed}/{total_tests} tests passed{Colors.RESET}")
    
    if total_passed == total_tests:
        print(f"\n{Colors.GREEN}🎉 All tests passed!{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}⚠️ Some tests failed{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
