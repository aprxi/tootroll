import sys
from .main import cli_main


if __name__ == "__main__":
    sys.exit(cli_main(sys.argv[1:]))
