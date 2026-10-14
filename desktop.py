import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        from translator.diagnostics import run
        sys.exit(run(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] == '--live-test':
        from translator.diagnostics import run_live
        sys.exit(run_live(sys.argv[2]))
    else:
        from translator.__main__ import main
        main()
