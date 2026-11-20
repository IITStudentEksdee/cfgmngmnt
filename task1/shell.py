import os.path
import shlex
import tkinter as tk

from tkinter import scrolledtext
from vfs import VirtualFileSystem


class ShellApp:
    font = 'Consolas'
    font_size = 11

    def __init__(self, root, vfs: VirtualFileSystem, startup_script_path=None):
        root.title('Shell Emulator with VFS')
        root.geometry('800x600')

        self.root = root
        self.vfs = vfs

        self.console = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state='disabled', bg='black', fg='white',
            font=(self.font, self.font_size)
        )
        self.console.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.input_frame = tk.Frame(root)
        self.input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.prompt_label = tk.Label(
            self.input_frame, text=self.get_prompt(),
            font=(self.font, self.font_size, 'bold')
        )
        self.prompt_label.pack(side=tk.LEFT)

        self.entry = tk.Entry(self.input_frame,
                              font=(self.font, self.font_size))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.entry.bind('<Return>', self.on_enter)
        self.entry.focus_set()

        self.print('Shell Emulator initiated')

        if startup_script_path:
            self.run_script(startup_script_path)

        self._handlers = {
            'ls': self._cmd_ls,
            'cd': self._cmd_cd,
            'cat': self._cmd_cat,
            'pwd': self._cmd_pwd,
        }

    def get_prompt(self):
        return f'[username@vfs {self.vfs.cwd}]$ '

    def rebuild_prompt(self):
        self.prompt_label.config(text=self.get_prompt())

    def print(self, text: str):
        self.console.config(state='normal')
        self.console.insert(tk.END, text + '\n')
        self.console.see(tk.END)
        self.console.config(state='disabled')

    def on_enter(self, _ignored_event):
        cmd = self.entry.get()
        self.entry.delete(0, tk.END)
        self.print(self.get_prompt() + cmd)
        self.execute(cmd, True)

    def run_script(self, path: str):
        if not os.path.exists(path):
            self.print(f'Error: Script not found at: "{path}".')
            return

        with open(path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        for line in lines:
            if '#' in line: line = line[:line.find('#')]
            line = line.strip()
            if not line: continue

            self.print(self.get_prompt() + line)
            err = self.execute(line, False)

            if err:
                self.print(
                    f'Command invalid at line: "{line}". Collapsing script.')
                break

    def _cmd_ls(self, args: list[str]) -> bool:
        target = args[0] if args else '.'
        files = self.vfs.list_dir(target)
        if files is None:
            self.print(f'Error: ls: Directory not found: "{target}"')
            return True
        for file in files:
            self.print(file)
        return False

    def _cmd_cd(self, args: list[str]) -> bool:
        if not args:
            return False
        if not self.vfs.is_dir(args[0]):
            self.print(f'Error: cd: Directory not found: "{args[0]}"')
            return True
        self.vfs.cwd = self.vfs.resolve_path(args[0])
        self.rebuild_prompt()
        return False

    def _cmd_cat(self, args: list[str]) -> bool:
        if not args:
            self.print('Error: cat: Missing operand.')
            return True
        content = self.vfs.read_file(args[0])
        if content is None:
            self.print(f'Error: cat: File not found: "{args[0]}"')
            return True
        try:
            self.print(content.decode('utf-8'))
        except UnicodeDecodeError:
            self.print(f'Error: cat: File format is not utf-8: "{args[0]}"')
            return True
        return False

    def _cmd_pwd(self, args: list[str]) -> bool:
        self.print(self.vfs.cwd)
        return False

    def execute(self, cmd: str, preprocessing: bool):
        if preprocessing:
            if '#' in cmd: cmd = cmd[:cmd.find('#')]
            cmd = cmd.strip()

        if not cmd: return False

        try:
            cmd = shlex.split(cmd)
        except ValueError as e:
            self.print(f'Error: ValueError: {e}')
            return True

        if cmd[0] == 'exit':
            self.print('Exiting...')
            self.root.quit()
            return False

        cmd, args = cmd[0], cmd[1:]

        try:
            handler = self._handlers.get(cmd)
            if handler is None:
                self.print(f'Error: {cmd}: Command not found.')
                return True
            return handler(args)
        except Exception as e:
            self.print(f'Error: {e}')
