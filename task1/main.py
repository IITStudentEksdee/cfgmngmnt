import argparse
import tkinter as tk

from shell import ShellApp
from vfs import VirtualFileSystem

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Shell Emulator with VFS')
    parser.add_argument('--vfs', type=str,
                        help='Path to the VFS zip archive', required=False)
    parser.add_argument('--script', type=str,
                        help='Path to the startup script', required=False)

    args = parser.parse_args()

    vfs = VirtualFileSystem(args.vfs)

    root = tk.Tk()
    app = ShellApp(root, vfs, args.script)
    root.mainloop()
