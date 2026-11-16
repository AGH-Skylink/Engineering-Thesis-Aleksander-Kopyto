"""PyInstaller entry point; keep imports after multiprocessing dispatch."""
from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()
    from nv_lab.packaged import main
    raise SystemExit(main())
