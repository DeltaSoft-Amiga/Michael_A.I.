#!/usr/bin/env python3
"""
AmigaOS-style Ollama Model Launcher v3.0
Feature: Dual-Mode Interface (GUI or Shell) with Enhanced Terminal Coloring
"""

import os
import sys
import time
import subprocess
import requests
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import List, Dict, Optional

class AmigaOSStyle:
    RED, GREEN, YELLOW, BLUE, CYAN, WHITE, BOLD, END = '\033[91m', '\033[92m', '\033[93m', '\033[94m', '\033[96m', '\033[97m', '\033[1m', '\033[0m'
    BLINK = '\033[5m'
    
    @staticmethod
    def print_header(text: str):
        print(f"\n{AmigaOSStyle.BOLD}{AmigaOSStyle.CYAN}╔{'═' * (len(text) + 2)}╗{AmigaOSStyle.END}")
        print(f"{AmigaOSStyle.BOLD}{AmigaOSStyle.CYAN}║ {text} ║{AmigaOSStyle.END}")
        print(f"{AmigaOSStyle.BOLD}{AmigaOSStyle.CYAN}╚{'═' * (len(text) + 2)}╝{AmigaOSStyle.END}")

    @staticmethod
    def print_success(text: str): print(f"{AmigaOSStyle.GREEN}✓ {text}{AmigaOSStyle.END}")
    @staticmethod
    def print_error(text: str): print(f"{AmigaOSStyle.RED}✗ {text}{AmigaOSStyle.END}")
    @staticmethod
    def print_warning(text: str): print(f"{AmigaOSStyle.YELLOW}⚠ {text}{AmigaOSStyle.END}")
    @staticmethod
    def print_info(text: str): print(f"{AmigaOSStyle.BLUE}ℹ {text}{AmigaOSStyle.END}")

# --- Core Logic ---

def get_local_models():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        return r.json().get('models', [])
    except: return []

def run_shell_chat(model_name: str, hardware: str):
    """Terminal-based chat with colored user/AI logic"""
    AmigaOSStyle.print_header(f"TERMINAL SESSION: {model_name} ({hardware})")
    print(f"{AmigaOSStyle.YELLOW}Type 'exit' or 'quit' to return to menu.{AmigaOSStyle.END}\n")
    
    while True:
        # User Prompt in Green
        user_input = input(f"{AmigaOSStyle.GREEN}{AmigaOSStyle.BOLD}USER > {AmigaOSStyle.END}").strip()
        
        if user_input.lower() in ['exit', 'quit']:
            break
        if not user_input:
            continue
            
        try:
            # AI Response in Cyan
            print(f"{AmigaOSStyle.CYAN}{AmigaOSStyle.BOLD}AI ({hardware}) > {AmigaOSStyle.END}", end="", flush=True)
            
            # Streaming response for a better Shell feel
            r = requests.post("http://localhost:11434/api/generate", 
                             json={"model": model_name, "prompt": user_input, "stream": True}, 
                             timeout=120, stream=True)
            
            full_response = ""
            for line in r.iter_lines():
                if line:
                    chunk = json.loads(line)
                    text = chunk.get('response', '')
                    print(f"{AmigaOSStyle.CYAN}{text}{AmigaOSStyle.END}", end="", flush=True)
                    full_response += text
                    if chunk.get('done'):
                        print("\n")
        except Exception as e:
            AmigaOSStyle.print_error(f"\nCommunication Error: {e}")

# --- GUI Class ---

class ChatGUI:
    def __init__(self, model_name: str, hardware: str):
        self.model_name = model_name
        self.hardware = hardware
        self.root = tk.Tk()
        self.root.title(f"Amiga AI - {model_name}")
        self.root.geometry("900x750")
        self.root.configure(bg='#2b2b2b')
        self.setup_gui()
        
    def setup_gui(self):
        header = tk.Frame(self.root, bg='#3a3a3a', height=50)
        header.pack(fill='x', padx=10, pady=5)
        hw_color = "cyan" if self.hardware == "GPU" else "red"
        tk.Label(header, text=f"MODEL: {self.model_name}", bg='#3a3a3a', fg='white').pack(side='left', padx=10)
        tk.Label(header, text=f"COMPUTE: {self.hardware}", bg='#3a3a3a', fg=hw_color, font=('Arial', 10, 'bold')).pack(side='left', padx=10)
        tk.Button(header, text="CLOSE", command=self.root.destroy, bg='#444', fg='white').pack(side='right', padx=10)
        
        self.chat_text = scrolledtext.ScrolledText(self.root, bg='#111', fg='#eee', font=('Courier', 11))
        self.chat_text.pack(fill='both', expand=True, padx=10)
        
        input_frame = tk.Frame(self.root, bg='#2b2b2b')
        input_frame.pack(fill='x', padx=10, pady=10)
        self.input_entry = tk.Entry(input_frame, bg='#000', fg='#00ff00', font=('Courier', 12))
        self.input_entry.pack(side='left', fill='x', expand=True)
        self.input_entry.bind('<Return>', lambda e: self.send_message())
        tk.Button(input_frame, text="SEND", command=self.send_message, bg='#0055ff', fg='white').pack(side='right', padx=5)

    def send_message(self):
        txt = self.input_entry.get().strip()
        if not txt: return
        self.input_entry.delete(0, tk.END)
        self.chat_text.insert(tk.END, f"YOU: {txt}\n\n")
        threading.Thread(target=self.fetch_ai, args=(txt,), daemon=True).start()

    def fetch_ai(self, prompt):
        try:
            r = requests.post("http://localhost:11434/api/generate", json={"model": self.model_name, "prompt": prompt, "stream": False}, timeout=120)
            resp = r.json().get('response')
            self.root.after(0, lambda: self.chat_text.insert(tk.END, f"AI: {resp}\n\n"))
            self.root.after(0, lambda: self.chat_text.see(tk.END))
        except: pass

    def run(self): self.root.mainloop()

# --- Main Entry ---

def main():
    AmigaOSStyle.print_header("AMIGA AI ASSISTANT v3.0")
    
    # Check if Ollama is running
    try: requests.get("http://localhost:11434/api/tags", timeout=2)
    except:
        subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)

    while True:
        models = get_local_models()
        AmigaOSStyle.print_header("MAIN MENU")
        for i, m in enumerate(models, 1):
            print(f"{i}. {m['name']} ({m['size']/(1024**3):.1f} GB)")
        
        print(f"\nU. {AmigaOSStyle.RED}CHECK FOR UPDATES{AmigaOSStyle.END}")
        print(f"I. Install Model")
        print(f"R. Remove Model")
        print(f"X. Exit")
        
        cmd = input(f"\n{AmigaOSStyle.BOLD}Selection: {AmigaOSStyle.END}").strip().upper()
        
        if cmd == 'X': break
        
        if cmd.isdigit():
            idx = int(cmd) - 1
            if 0 <= idx < len(models):
                selected_model = models[idx]['name']
                
                # Hardware Detection
                has_gpu = False
                try:
                    res = subprocess.run(['nvidia-smi'], capture_output=True)
                    if res.returncode == 0: has_gpu = True
                except: pass
                
                if has_gpu:
                    print(f"{AmigaOSStyle.BLUE}{AmigaOSStyle.BOLD}HARDWARE: GPU DETECTED{AmigaOSStyle.END}")
                    hardware = "GPU"
                else:
                    print(f"{AmigaOSStyle.RED}{AmigaOSStyle.BOLD}{AmigaOSStyle.BLINK}WARNING: CPU MODE (SLOW){AmigaOSStyle.END}")
                    hardware = "CPU"
                
                # Interface Selection
                print(f"\n{AmigaOSStyle.BOLD}CHOOSE INTERFACE:{AmigaOSStyle.END}")
                print("1. GUI (Amiga Workbench)")
                print("2. Shell (Terminal)")
                mode = input("Choice [1-2]: ").strip()
                
                if mode == '2':
                    run_shell_chat(selected_model, hardware)
                else:
                    ChatGUI(selected_model, hardware).run()
        
        # ... (Handle I, R, U as in previous versions) ...

if __name__ == "__main__":
    main()
