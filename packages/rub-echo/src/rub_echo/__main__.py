"""Standalone CLI for the echo adapter.

echo -h                     Discover operations
echo greet -h               Inspect greet operation
echo greet name=Philip      Invoke greet
"""

from rub.standalone import standalone_cli

from rub_echo.adapter import EchoAdapter

app = standalone_cli(EchoAdapter(), name="echo", default_url="echo://local")

if __name__ == "__main__":
    app()
