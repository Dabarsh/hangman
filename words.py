"""Word list, grouped by category. The category is shown to the player as a hint.

Words must be letters A-Z only and at most MAX_WORD_LENGTH long so the tiles fit.
"""

MAX_WORD_LENGTH = 10

WORDS = {
    "Programming language": (
        "JAVA", "RUBY", "PERL", "BASH", "LOGO", "DART", "RUST", "PYTHON", "SWIFT",
        "KOTLIN", "SCALA", "HASKELL", "ELIXIR", "FORTRAN", "COBOL", "PASCAL",
        "JULIA", "ERLANG", "CLOJURE",
    ),
    "Hardware": (
        "CHIP", "DISK", "MOUSE", "MODEM", "LAPTOP", "MEMORY", "ROUTER", "WEBCAM",
        "MONITOR", "SCANNER", "PRINTER", "BATTERY", "CIRCUIT", "KEYBOARD",
        "PROCESSOR", "TRANSISTOR",
    ),
    "Web & data": (
        "HTML", "JSON", "YAML", "NODE", "WIFI", "SERVER", "DOMAIN", "COOKIE",
        "SOCKET", "BROWSER", "WEBSITE", "PROTOCOL", "FIREWALL", "DATABASE",
        "BANDWIDTH", "HYPERLINK",
    ),
    "Computing": (
        "TECH", "CODE", "BYTE", "DATA", "BETA", "ARRAY", "STRING", "LAMBDA",
        "BINARY", "BRANCH", "COMMIT", "KERNEL", "SYNTAX", "BOOLEAN", "INTEGER",
        "POINTER", "LIBRARY", "PACKAGE", "VARIABLE", "FUNCTION", "COMPILER",
        "DEBUGGER", "ALGORITHM", "RECURSION", "FRAMEWORK",
    ),
}
