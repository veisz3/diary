#!/usr/bin/env python
import os
import sys

def main():
    """日記Botを起動する"""
    sys.path.append(os.path.abspath('.'))
    from src.bot import run_bot
    run_bot()

if __name__ == "__main__":
    main()