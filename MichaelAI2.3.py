#!/usr/bin/env python3
"""
AmigaOS-style Ollama Model Launcher with GUI and GPU Support
Enhanced version with automatic dependency checking and smart model installation
"""

import os
import sys
import time
import subprocess
import requests
import threading
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font
from typing import List, Dict, Optional
import base64
import shutil

# Try to import optional dependencies
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

class SystemChecker:
    """System dependency and resource checker"""
    
    @staticmethod
    def check_python_dependencies():
        """Check if required Python packages are installed"""
        missing_deps = []
        
        # Check for requests
        try:
            import requests
        except ImportError:
            missing_deps.append("requests")
        
        # Check for PIL/Pillow
        try:
            from PIL import Image, ImageTk
        except ImportError:
            missing_deps.append("pillow")
        
        # Check for psutil (optional but recommended)
        if not HAS_PSUTIL:
            missing_deps.append("psutil")
        
        return missing_deps
    
    @staticmethod
    def install_python_dependencies(dependencies):
        """Install missing Python dependencies"""
        AmigaOSStyle.print_header("INSTALLING PYTHON DEPENDENCIES")
        
        for dep in dependencies:
            AmigaOSStyle.print_info(f"Installing {dep}...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                             check=True, capture_output=True)
                AmigaOSStyle.print_success(f"Successfully installed {dep}")
            except subprocess.CalledProcessError as e:
                AmigaOSStyle.print_error(f"Failed to install {dep}: {e}")
                return False
        
        # Reload modules if psutil was installed
        if "psutil" in dependencies:
            global HAS_PSUTIL
            try:
                import psutil
                HAS_PSUTIL = True
            except ImportError:
                AmigaOSStyle.print_warning("psutil installed but failed to load")
        
        return True
    
    @staticmethod
    def get_system_info():
        """Get system information including RAM and VRAM"""
        system_info = {}
        
        # Get RAM info
        if HAS_PSUTIL:
            try:
                ram = psutil.virtual_memory()
                system_info['ram_total_gb'] = ram.total / (1024**3)
                system_info['ram_available_gb'] = ram.available / (1024**3)
            except:
                system_info['ram_total_gb'] = 4.0  # Default assumption
                system_info['ram_available_gb'] = 2.0
        else:
            system_info['ram_total_gb'] = 4.0  # Default assumption
            system_info['ram_available_gb'] = 2.0
        
        # Get VRAM info
        system_info['vram_gb'] = SystemChecker.detect_vram()
        
        return system_info
    
    @staticmethod
    def detect_vram():
        """Detect available VRAM"""
        vram_gb = 0
        
        try:
            # Check NVIDIA GPU
            nvidia_result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'], 
                                         capture_output=True, text=True, timeout=10)
            if nvidia_result.returncode == 0:
                lines = nvidia_result.stdout.strip().split('\n')
                if lines and lines[0]:
                    vram_mb = int(lines[0])
                    vram_gb = vram_mb / 1024
                    AmigaOSStyle.print_success(f"Detected NVIDIA GPU with {vram_gb:.1f}GB VRAM")
                    return vram_gb
            
            # Check AMD GPU (ROCm)
            amd_result = subprocess.run(['rocm-smi', '--showmeminfo', 'vram'], 
                                      capture_output=True, text=True, timeout=10)
            if amd_result.returncode == 0:
                # Parse AMD GPU output
                for line in amd_result.stdout.split('\n'):
                    if 'Total' in line and 'MB' in line:
                        try:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part.isdigit() and i > 0 and parts[i-1] == 'Total':
                                    vram_mb = int(part)
                                    vram_gb = vram_mb / 1024
                                    AmigaOSStyle.print_success(f"Detected AMD GPU with {vram_gb:.1f}GB VRAM")
                                    return vram_gb
                        except (ValueError, IndexError):
                            pass
            
            # Check Apple Silicon (unified memory)
            if sys.platform == "darwin":
                try:
                    result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                          capture_output=True, text=True, timeout=10)
                    for line in result.stdout.split('\n'):
                        if 'VRAM' in line or 'Memory' in line:
                            try:
                                if 'GB' in line:
                                    for part in line.split():
                                        if part.replace('.', '').isdigit():
                                            vram_gb = float(part)
                                            break
                                elif 'MB' in line:
                                    for part in line.split():
                                        if part.replace('.', '').isdigit():
                                            vram_mb = float(part)
                                            vram_gb = vram_mb / 1024
                                            break
                                if vram_gb > 0:
                                    AmigaOSStyle.print_success(f"Detected Apple GPU with {vram_gb:.1f}GB VRAM")
                                    return vram_gb
                            except (ValueError, IndexError):
                                pass
                except:
                    pass
            
            # If no GPU detected, assume CPU-only
            if vram_gb == 0:
                AmigaOSStyle.print_warning("No dedicated GPU detected - using CPU mode")
                return 0
                
        except subprocess.TimeoutExpired:
            AmigaOSStyle.print_warning("GPU detection timed out")
        except Exception as e:
            AmigaOSStyle.print_warning(f"Could not detect VRAM: {e}")
        
        return vram_gb

class AmigaOSStyle:
    """AmigaOS-style terminal formatting"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    # Specific colors for chat
    USER_COLOR = GREEN
    AGENT_COLOR = RED
    THINKING_COLOR = BLUE
    
    @staticmethod
    def print_header(text: str):
        print(f"\n{AmigaOSStyle.BOLD}{AmigaOSStyle.CYAN}╔{'═' * (len(text) + 2)}╗{AmigaOSStyle.END}")
        print(f"{AmigaOSStyle.BOLD}{AmigaOSStyle.CYAN}║ {text} ║{AmigaOSStyle.END}")
        print(f"{AmigaOSStyle.BOLD}{AmigaOSStyle.CYAN}╚{'═' * (len(text) + 2)}╝{AmigaOSStyle.END}")
    
    @staticmethod
    def print_success(text: str):
        print(f"{AmigaOSStyle.GREEN}✓ {text}{AmigaOSStyle.END}")
    
    @staticmethod
    def print_error(text: str):
        print(f"{AmigaOSStyle.RED}✗ {text}{AmigaOSStyle.END}")
    
    @staticmethod
    def print_warning(text: str):
        print(f"{AmigaOSStyle.YELLOW}⚠ {text}{AmigaOSStyle.END}")
    
    @staticmethod
    def print_info(text: str):
        print(f"{AmigaOSStyle.BLUE}ℹ {text}{AmigaOSStyle.END}")

class AnimatedGIF:
    def __init__(self, root, gif_path, scale_factor=0.8):
        self.root = root
        self.gif_path = gif_path
        self.scale_factor = scale_factor
        self.frames = []
        self.delays = []
        self.current_frame = 0
        self.animation = None
        self.label = None
        
        self.load_gif()
    
    def load_gif(self):
        """Load GIF frames and delays"""
        try:
            if not HAS_PIL:
                self.create_fallback_image()
                return
                
            gif = Image.open(self.gif_path)
            self.original_size = gif.size
            
            # Calculate scaled size (80% of title text height)
            title_font_size = 16  # Approximate title font size
            scaled_height = int(title_font_size * self.scale_factor)
            scaled_width = int(self.original_size[0] * scaled_height / self.original_size[1])
            
            self.scaled_size = (scaled_width, scaled_height)
            
            while True:
                # Convert to RGBA if necessary
                if gif.mode != 'RGBA':
                    frame = gif.convert('RGBA')
                else:
                    frame = gif.copy()
                
                # Resize frame
                frame = frame.resize(self.scaled_size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(frame)
                
                self.frames.append(photo)
                
                try:
                    # Get frame delay (convert to milliseconds)
                    delay = gif.info.get('duration', 100)
                    self.delays.append(delay)
                    gif.seek(gif.tell() + 1)
                except EOFError:
                    break
                    
        except Exception as e:
            print(f"Error loading GIF: {e}")
            # Create a fallback static image
            self.create_fallback_image()
    
    def create_fallback_image(self):
        """Create a fallback static image if GIF loading fails"""
        try:
            # Create a simple colored circle as fallback
            size = (40, 40)
            if HAS_PIL:
                image = Image.new('RGBA', size, (0, 0, 0, 0))
                from PIL import ImageDraw
                draw = ImageDraw.Draw(image)
                
                # Draw a red ball
                draw.ellipse([5, 5, 35, 35], fill='red', outline='white', width=2)
                
                photo = ImageTk.PhotoImage(image)
                self.frames = [photo]
                self.delays = [1000]
                self.scaled_size = size
            else:
                # Without PIL, we'll just use a colored label
                self.frames = [None]
                self.delays = [1000]
                self.scaled_size = size
                
        except Exception as e:
            print(f"Error creating fallback image: {e}")
    
    def start_animation(self, label):
        """Start the animation on the given label"""
        self.label = label
        if self.frames and self.frames[0] is not None:
            self.animate()
        else:
            # Fallback: just show a colored label
            label.configure(text="●", font=('Arial', 20), fg='red', bg='#3a3a3a')
    
    def animate(self):
        """Animate the GIF frames"""
        if not self.frames or self.frames[0] is None:
            return
            
        self.label.configure(image=self.frames[self.current_frame])
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        
        # Schedule next frame
        delay = self.delays[self.current_frame] if self.current_frame < len(self.delays) else 100
        self.animation = self.root.after(delay, self.animate)
    
    def stop_animation(self):
        """Stop the animation"""
        if self.animation:
            self.root.after_cancel(self.animation)
            self.animation = None

class ChatGUI:
    def __init__(self, model_name: str, gpu_info: str):
        self.model_name = model_name
        self.gpu_info = gpu_info
        self.root = tk.Tk()
        self.root.title(f"Amiga AI Assistant - {model_name}")
        self.root.geometry("900x700")
        self.root.configure(bg='#2b2b2b')
        
        # Load animated GIF
        self.boing_ball = None
        gif_path = "boingball_10_80x80_256.gif"
        if os.path.exists(gif_path):
            self.boing_ball = AnimatedGIF(self.root, gif_path, scale_factor=1.2)
        else:
            print(f"GIF file not found: {gif_path}")
            # Try to find the GIF in common locations
            search_paths = [
                "./boingball_10_80x80_256.gif",
                "boingball_10_80x80_256.gif",
                "../boingball_10_80x80_256.gif",
                "images/boingball_10_80x80_256.gif"
            ]
            for path in search_paths:
                if os.path.exists(path):
                    self.boing_ball = AnimatedGIF(self.root, path, scale_factor=1.2)
                    break
        
        # Configuration
        self.config = {
            'user_font': ('Arial', 12),
            'user_color': '#00ff00',  # Green
            'agent_font': ('Arial', 12),
            'agent_color': '#ff4444',  # Red
            'bg_color': '#2b2b2b',
            'text_color': '#ffffff'
        }
        
        self.load_config()
        self.setup_gui()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists('chat_config.json'):
                with open('chat_config.json', 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except:
            pass
            
    def save_config(self):
        """Save configuration to file"""
        try:
            with open('chat_config.json', 'w') as f:
                json.dump(self.config, f, indent=2)
        except:
            pass
    
    def setup_gui(self):
        """Setup the GUI components"""
        # Header
        header_frame = tk.Frame(self.root, bg='#3a3a3a', height=70)
        header_frame.pack(fill='x', padx=10, pady=5)
        header_frame.pack_propagate(False)
        
        # Left side: Boing Ball GIF and Title
        left_header = tk.Frame(header_frame, bg='#3a3a3a')
        left_header.pack(side='left', fill='both', expand=True)
        
        # GIF and title container
        title_container = tk.Frame(left_header, bg='#3a3a3a')
        title_container.pack(side='top', fill='x')
        
        # Boing Ball GIF
        if self.boing_ball:
            self.boing_label = tk.Label(title_container, 
                                      bg='#3a3a3a',
                                      borderwidth=0,
                                      highlightthickness=0)
            self.boing_label.pack(side='left', padx=(10, 5), pady=5)
            self.boing_ball.start_animation(self.boing_label)
        else:
            # Fallback: Create a simple colored circle
            fallback_canvas = tk.Canvas(title_container, 
                                      width=40, 
                                      height=40, 
                                      bg='#3a3a3a',
                                      highlightthickness=0)
            fallback_canvas.pack(side='left', padx=(10, 5), pady=5)
            fallback_canvas.create_oval(5, 5, 35, 35, fill='red', outline='white', width=2)
        
        # Title
        title_label = tk.Label(title_container, 
                             text=f"Amiga AI Assistant - {self.model_name}",
                             font=('Arial', 16, 'bold'),
                             fg='#00ffff',
                             bg='#3a3a3a')
        title_label.pack(side='left', padx=5, pady=10)
        
        # Right side: GPU info
        right_header = tk.Frame(header_frame, bg='#3a3a3a')
        right_header.pack(side='right', fill='y')
        
        gpu_label = tk.Label(right_header,
                           text=f"GPU: {self.gpu_info}",
                           font=('Arial', 10),
                           fg='#ffff00',
                           bg='#3a3a3a')
        gpu_label.pack(side='right', padx=10, pady=10)
        
        # Chat display area
        self.chat_frame = tk.Frame(self.root, bg=self.config['bg_color'])
        self.chat_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.chat_text = scrolledtext.ScrolledText(
            self.chat_frame,
            wrap=tk.WORD,
            width=80,
            height=25,
            font=('Arial', 11),
            bg=self.config['bg_color'],
            fg=self.config['text_color'],
            insertbackground='white'
        )
        self.chat_text.pack(fill='both', expand=True)
        self.chat_text.config(state=tk.DISABLED)
        
        # Input area
        input_frame = tk.Frame(self.root, bg=self.config['bg_color'])
        input_frame.pack(fill='x', padx=10, pady=5)
        
        # File upload button
        self.upload_btn = tk.Button(
            input_frame,
            text="📁 Upload File",
            command=self.upload_file,
            font=('Arial', 10),
            bg='#555555',
            fg='white',
            relief='raised'
        )
        self.upload_btn.pack(side='left', padx=(0, 10))
        
        # Input field
        self.input_entry = tk.Entry(
            input_frame,
            font=self.config['user_font'],
            bg='#1a1a1a',
            fg=self.config['user_color'],
            insertbackground='white',
            width=60
        )
        self.input_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.input_entry.bind('<Return>', self.send_message)
        
        # Send button
        self.send_btn = tk.Button(
            input_frame,
            text="🚀 Send",
            command=self.send_message,
            font=('Arial', 10, 'bold'),
            bg='#007acc',
            fg='white',
            relief='raised'
        )
        self.send_btn.pack(side='right')
        
        # Control buttons frame
        control_frame = tk.Frame(self.root, bg=self.config['bg_color'])
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Configuration button
        config_btn = tk.Button(
            control_frame,
            text="⚙️ Configure",
            command=self.open_config,
            font=('Arial', 10),
            bg='#666666',
            fg='white'
        )
        config_btn.pack(side='left', padx=(0, 10))
        
        # Clear chat button
        clear_btn = tk.Button(
            control_frame,
            text="🗑️ Clear Chat",
            command=self.clear_chat,
            font=('Arial', 10),
            bg='#cc4444',
            fg='white'
        )
        clear_btn.pack(side='left', padx=(0, 10))
        
        # Status label
        self.status_label = tk.Label(
            control_frame,
            text="Ready",
            font=('Arial', 9),
            fg='#00ff00',
            bg=self.config['bg_color']
        )
        self.status_label.pack(side='right')
        
        # Focus on input
        self.input_entry.focus()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_closing(self):
        """Handle window closing"""
        if self.boing_ball:
            self.boing_ball.stop_animation()
        self.root.destroy()
    
    def upload_file(self):
        """Handle file upload"""
        file_path = filedialog.askopenfilename(
            title="Select file to upload",
            filetypes=[
                ("Text files", "*.txt"),
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add file info to chat
                self.add_message("System", f"📎 Uploaded file: {os.path.basename(file_path)}\nContent preview: {content[:200]}...", "#ffff00")
                
                # Store file content for context
                self.uploaded_content = content
                self.status_label.config(text=f"File uploaded: {os.path.basename(file_path)}", fg="#ffff00")
                
            except Exception as e:
                messagebox.showerror("Upload Error", f"Could not read file: {str(e)}")
    
    def open_config(self):
        """Open configuration window"""
        config_win = tk.Toplevel(self.root)
        config_win.title("Chat Configuration")
        config_win.geometry("500x600")
        config_win.configure(bg='#2b2b2b')
        config_win.transient(self.root)
        config_win.grab_set()
        
        # Font families
        available_fonts = ['Arial', 'Helvetica', 'Times New Roman', 'Courier New', 
                          'Verdana', 'Georgia', 'Comic Sans MS', 'Impact']
        
        # Font sizes
        font_sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24]
        
        # Colors
        colors = {
            'Green': '#00ff00',
            'Red': '#ff4444',
            'Blue': '#4444ff',
            'Yellow': '#ffff00',
            'Cyan': '#00ffff',
            'Magenta': '#ff00ff',
            'White': '#ffffff',
            'Orange': '#ff8800'
        }
        
        # User settings frame
        user_frame = ttk.LabelFrame(config_win, text="User Message Settings", padding=10)
        user_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(user_frame, text="Font:").grid(row=0, column=0, sticky='w')
        user_font_var = tk.StringVar(value=self.config['user_font'][0])
        user_font_combo = ttk.Combobox(user_frame, textvariable=user_font_var, values=available_fonts)
        user_font_combo.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        
        tk.Label(user_frame, text="Size:").grid(row=1, column=0, sticky='w')
        user_size_var = tk.IntVar(value=self.config['user_font'][1])
        user_size_combo = ttk.Combobox(user_frame, textvariable=user_size_var, values=font_sizes)
        user_size_combo.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        tk.Label(user_frame, text="Color:").grid(row=2, column=0, sticky='w')
        user_color_var = tk.StringVar(value=self.get_color_name(self.config['user_color'], colors))
        user_color_combo = ttk.Combobox(user_frame, textvariable=user_color_var, values=list(colors.keys()))
        user_color_combo.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        
        # Agent settings frame
        agent_frame = ttk.LabelFrame(config_win, text="Agent Message Settings", padding=10)
        agent_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(agent_frame, text="Font:").grid(row=0, column=0, sticky='w')
        agent_font_var = tk.StringVar(value=self.config['agent_font'][0])
        agent_font_combo = ttk.Combobox(agent_frame, textvariable=agent_font_var, values=available_fonts)
        agent_font_combo.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        
        tk.Label(agent_frame, text="Size:").grid(row=1, column=0, sticky='w')
        agent_size_var = tk.IntVar(value=self.config['agent_font'][1])
        agent_size_combo = ttk.Combobox(agent_frame, textvariable=agent_size_var, values=font_sizes)
        agent_size_combo.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        tk.Label(agent_frame, text="Color:").grid(row=2, column=0, sticky='w')
        agent_color_var = tk.StringVar(value=self.get_color_name(self.config['agent_color'], colors))
        agent_color_combo = ttk.Combobox(agent_frame, textvariable=agent_color_var, values=list(colors.keys()))
        agent_color_combo.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        
        # Global settings
        global_frame = ttk.LabelFrame(config_win, text="Global Settings", padding=10)
        global_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(global_frame, text="Background:").grid(row=0, column=0, sticky='w')
        bg_colors = {'Dark': '#2b2b2b', 'Black': '#000000', 'Gray': '#404040', 'Blue': '#1a237e'}
        bg_color_var = tk.StringVar(value=self.get_color_name(self.config['bg_color'], bg_colors))
        bg_color_combo = ttk.Combobox(global_frame, textvariable=bg_color_var, values=list(bg_colors.keys()))
        bg_color_combo.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(config_win, text="Preview", padding=10)
        preview_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        preview_text = scrolledtext.ScrolledText(preview_frame, height=8, wrap=tk.WORD)
        preview_text.pack(fill='both', expand=True)
        
        def update_preview():
            preview_text.delete(1.0, tk.END)
            
            user_font = (user_font_var.get(), user_size_var.get())
            user_color = colors[user_color_var.get()]
            agent_font = (agent_font_var.get(), agent_size_var.get())
            agent_color = colors[agent_color_var.get()]
            bg_color = bg_colors[bg_color_var.get()]
            
            preview_text.configure(bg=bg_color)
            
            # Add sample messages
            preview_text.insert(tk.END, "You: ", f"user_tag")
            preview_text.insert(tk.END, "This is how your messages will look\n", "user_msg")
            
            preview_text.insert(tk.END, "Agent: ", f"agent_tag")
            preview_text.insert(tk.END, "This is how agent responses will look\n", "agent_msg")
            
            # Configure tags
            preview_text.tag_configure("user_tag", font=user_font, foreground=user_color)
            preview_text.tag_configure("user_msg", font=user_font, foreground=user_color)
            preview_text.tag_configure("agent_tag", font=agent_font, foreground=agent_color)
            preview_text.tag_configure("agent_msg", font=agent_font, foreground=agent_color)
        
        def apply_config():
            self.config.update({
                'user_font': (user_font_var.get(), user_size_var.get()),
                'user_color': colors[user_color_var.get()],
                'agent_font': (agent_font_var.get(), agent_size_var.get()),
                'agent_color': colors[agent_color_var.get()],
                'bg_color': bg_colors[bg_color_var.get()]
            })
            self.save_config()
            self.apply_new_config()
            config_win.destroy()
            messagebox.showinfo("Configuration", "Settings applied successfully!")
        
        # Update preview when any setting changes
        for var in [user_font_var, user_size_var, user_color_var, agent_font_var, agent_size_var, agent_color_var, bg_color_var]:
            var.trace('w', lambda *args: update_preview())
        
        update_preview()
        
        # Buttons
        btn_frame = tk.Frame(config_win, bg='#2b2b2b')
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Apply", command=apply_config).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=config_win.destroy).pack(side='right', padx=5)
    
    def get_color_name(self, color_code, color_dict):
        """Get color name from color code"""
        for name, code in color_dict.items():
            if code == color_code:
                return name
        return list(color_dict.keys())[0]
    
    def apply_new_config(self):
        """Apply new configuration to GUI"""
        self.root.configure(bg=self.config['bg_color'])
        self.chat_frame.configure(bg=self.config['bg_color'])
        self.chat_text.configure(
            bg=self.config['bg_color'],
            fg=self.config['text_color']
        )
        self.input_entry.configure(
            font=self.config['user_font'],
            fg=self.config['user_color']
        )
    
    def add_message(self, sender: str, message: str, color: str = None):
        """Add a message to the chat display"""
        self.chat_text.config(state=tk.NORMAL)
        
        if sender == "You":
            tag_color = self.config['user_color']
            tag_font = self.config['user_font']
        elif sender == "Agent":
            tag_color = self.config['agent_color']
            tag_font = self.config['agent_font']
        else:
            tag_color = color or "#ffff00"
            tag_font = ('Arial', 10)
        
        # Create unique tags for this message
        tag_name = f"tag_{len(self.chat_text.get(1.0, tk.END))}"
        
        # Configure the tag
        self.chat_text.tag_configure(tag_name, foreground=tag_color, font=tag_font)
        
        # Insert the message
        self.chat_text.insert(tk.END, f"{sender}: ", tag_name)
        self.chat_text.insert(tk.END, f"{message}\n\n")
        
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
    
    def clear_chat(self):
        """Clear the chat history"""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete(1.0, tk.END)
        self.chat_text.config(state=tk.DISABLED)
        self.add_message("System", "Chat cleared", "#ffff00")
    
    def send_message(self, event=None):
        """Send message to AI model"""
        user_input = self.input_entry.get().strip()
        if not user_input:
            return
        
        # Clear input
        self.input_entry.delete(0, tk.END)
        
        # Add user message to chat
        self.add_message("You", user_input)
        
        # Update status
        self.status_label.config(text="Thinking...", fg="#ffff00")
        self.send_btn.config(state=tk.DISABLED)
        self.upload_btn.config(state=tk.DISABLED)
        
        # Send to AI in separate thread
        threading.Thread(target=self.process_ai_response, args=(user_input,), daemon=True).start()
    
    def process_ai_response(self, user_input: str):
        """Process AI response in background thread"""
        try:
            # Prepare context with uploaded file if available
            context = user_input
            if hasattr(self, 'uploaded_content'):
                context = f"File content: {self.uploaded_content}\n\nUser question: {user_input}"
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": context,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 1000,
                        "num_gpu": 50,
                        "main_gpu": 0,
                        "num_thread": 8
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', 'No response received')
                
                # Update GUI in main thread
                self.root.after(0, self.display_ai_response, response_text)
            else:
                self.root.after(0, self.display_error, f"API error: {response.status_code}")
                
        except Exception as e:
            self.root.after(0, self.display_error, f"Error: {str(e)}")
    
    def display_ai_response(self, response_text: str):
        """Display AI response in GUI (called from main thread)"""
        self.add_message("Agent", response_text)
        self.status_label.config(text="Ready", fg="#00ff00")
        self.send_btn.config(state=tk.NORMAL)
        self.upload_btn.config(state=tk.NORMAL)
    
    def display_error(self, error_msg: str):
        """Display error message in GUI (called from main thread)"""
        self.add_message("System", error_msg, "#ff4444")
        self.status_label.config(text="Error", fg="#ff4444")
        self.send_btn.config(state=tk.NORMAL)
        self.upload_btn.config(state=tk.NORMAL)
    
    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()

# Enhanced server management functions
def check_ollama_installed() -> bool:
    """Check if Ollama is installed on the system"""
    try:
        result = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        # Also check if ollama is in the current directory
        if os.path.exists('./ollama') or os.path.exists('/usr/local/bin/ollama'):
            return True
        return False
    except:
        return False

def install_ollama():
    """Install Ollama if not present"""
    AmigaOSStyle.print_header("OLLAMA INSTALLATION")
    
    if check_ollama_installed():
        AmigaOSStyle.print_success("Ollama is already installed")
        return True
    
    AmigaOSStyle.print_warning("Ollama not found. Installing...")
    
    try:
        # Install Ollama using the official method
        AmigaOSStyle.print_info("Downloading Ollama installer...")
        
        if sys.platform == "linux":
            # For Linux, use the official install script
            result = subprocess.run(['curl', '-fsSL', 'https://ollama.ai/install.sh'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                AmigaOSStyle.print_error("Failed to download installer")
                return False
            
            AmigaOSStyle.print_info("Running installation script...")
            install_result = subprocess.run(['sh', '-c', 'curl -fsSL https://ollama.ai/install.sh | sh'], 
                                          capture_output=True, text=True)
            if install_result.returncode == 0:
                AmigaOSStyle.print_success("Ollama installed successfully!")
                return True
            else:
                AmigaOSStyle.print_error(f"Installation failed: {install_result.stderr}")
                return False
                
        elif sys.platform == "darwin":  # macOS
            result = subprocess.run(['brew', 'install', 'ollama'], capture_output=True, text=True)
            if result.returncode == 0:
                AmigaOSStyle.print_success("Ollama installed successfully!")
                return True
            else:
                AmigaOSStyle.print_error(f"Homebrew installation failed: {result.stderr}")
                return False
        else:
            AmigaOSStyle.print_error("Unsupported platform. Please install Ollama manually from https://ollama.ai")
            return False
        
    except subprocess.CalledProcessError as e:
        AmigaOSStyle.print_error(f"Installation failed: {e}")
        return False
    except Exception as e:
        AmigaOSStyle.print_error(f"Unexpected error during installation: {e}")
        return False

def start_ollama_server():
    """Start the Ollama server with proper error handling"""
    AmigaOSStyle.print_header("STARTING OLLAMA SERVER")
    
    # First, check if server is already running
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            AmigaOSStyle.print_success("Ollama server is already running")
            return True
    except:
        pass  # Server is not running, continue to start it
    
    # Stop any existing Ollama processes
    try:
        if sys.platform == "win32":
            subprocess.run(['taskkill', '/f', '/im', 'ollama.exe'], capture_output=True)
        else:
            subprocess.run(['pkill', '-f', 'ollama'], capture_output=True)
        time.sleep(2)  # Give it time to stop
    except:
        pass
    
    # Start the server
    try:
        AmigaOSStyle.print_info("Starting Ollama server...")
        
        # Start Ollama in background with output redirection
        process = subprocess.Popen(
            ['ollama', 'serve'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give more time for initialization
        time.sleep(5)
        
        # Check process status
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            if stderr:
                AmigaOSStyle.print_error(f"Ollama server failed to start: {stderr}")
            return False
        
        # Wait for server to start with more attempts and better error handling
        max_attempts = 45  # Increased from 30
        for attempt in range(max_attempts):
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    AmigaOSStyle.print_success("Ollama server started successfully!")
                    
                    # Wait a bit more for full initialization
                    time.sleep(2)
                    return True
            except requests.exceptions.ConnectionError:
                # Check if process is still running
                if process.poll() is not None:
                    # Process died, read error output
                    stderr_output = process.stderr.read()
                    if stderr_output:
                        AmigaOSStyle.print_error(f"Ollama process died: {stderr_output}")
                    else:
                        AmigaOSStyle.print_error("Ollama process died with no error output")
                    return False
                
                # Process is still running, continue waiting
                if attempt % 5 == 0:  # Show progress every 5 attempts
                    AmigaOSStyle.print_info(f"Waiting for server... ({attempt + 1}/{max_attempts})")
                time.sleep(1)
            except Exception as e:
                if attempt % 5 == 0:
                    AmigaOSStyle.print_info(f"Waiting for server... ({attempt + 1}/{max_attempts})")
                time.sleep(1)
        
        # If we get here, server didn't start in time
        AmigaOSStyle.print_error("Failed to start Ollama server - timeout")
        
        # Try to get error output
        try:
            stdout, stderr = process.communicate(timeout=1)
            if stderr:
                AmigaOSStyle.print_error(f"Server error: {stderr}")
        except:
            pass
            
        process.terminate()
        return False
        
    except Exception as e:
        AmigaOSStyle.print_error(f"Error starting Ollama server: {e}")
        return False

def get_available_models() -> List[Dict]:
    """Get list of available Ollama models with better error handling"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=30)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                if not models:
                    AmigaOSStyle.print_warning("No models found. You need to pull models first.")
                    AmigaOSStyle.print_info("Try: ollama pull llama2")
                return models
            else:
                AmigaOSStyle.print_error(f"Server returned status code: {response.status_code}")
                
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                AmigaOSStyle.print_warning(f"Connection failed, retrying... ({attempt + 1}/{max_retries})")
                time.sleep(2)
                continue
            AmigaOSStyle.print_error("Cannot connect to Ollama server. Is it running?")
            AmigaOSStyle.print_info("Try: ollama serve")
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                AmigaOSStyle.print_warning(f"Request timeout, retrying... ({attempt + 1}/{max_retries})")
                time.sleep(2)
                continue
            AmigaOSStyle.print_error("Request to Ollama server timed out")
            
        except Exception as e:
            AmigaOSStyle.print_error(f"Error fetching models: {e}")
            
        break  # Break if not retrying
    
    return []

def check_gpu_availability():
    """Check if GPU is available and which type"""
    try:
        # Check for NVIDIA GPU
        nvidia_result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        if nvidia_result.returncode == 0:
            return "NVIDIA GPU"
        
        # Check for AMD GPU (rocm-smi)
        amd_result = subprocess.run(['rocm-smi'], capture_output=True, text=True, timeout=10)
        if amd_result.returncode == 0:
            return "AMD GPU"
        
        # Check for Apple Silicon
        if sys.platform == "darwin":
            try:
                result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                      capture_output=True, text=True, timeout=10)
                if 'Apple' in result.stdout:
                    return "Apple Silicon"
            except:
                pass
        
        return "CPU Only"
        
    except Exception as e:
        return f"Unknown (Error: {str(e)})"

def ensure_ollama_running():
    """Ensure Ollama is running with user-friendly options"""
    if not check_ollama_installed():
        if not install_ollama():
            AmigaOSStyle.print_error("Failed to install Ollama automatically.")
            AmigaOSStyle.print_info("Please install Ollama manually from https://ollama.ai")
            return False
    
    # Try to start server
    if not start_ollama_server():
        AmigaOSStyle.print_error("Automatic server startup failed.")
        AmigaOSStyle.print_info("Please start Ollama manually in a terminal:")
        AmigaOSStyle.print_info("1. Open a new terminal")
        AmigaOSStyle.print_info("2. Run: ollama serve")
        AmigaOSStyle.print_info("3. Keep that terminal open")
        AmigaOSStyle.print_info("4. Return here and press Enter to continue")
        input("Press Enter after starting Ollama server...")
    
    return True

def get_recommended_models(vram_gb: float, ram_gb: float):
    """Get recommended models based on available VRAM and RAM"""
    recommendations = []
    
    if vram_gb >= 8:
        # High VRAM systems
        recommendations.extend([
            {"name": "llama2", "size_gb": 3.8, "description": "Good balance of performance and quality"},
            {"name": "mistral", "size_gb": 4.1, "description": "Excellent for coding and reasoning"},
            {"name": "codellama:13b", "size_gb": 7.3, "description": "Specialized for programming"}
        ])
    elif vram_gb >= 4:
        # Medium VRAM systems
        recommendations.extend([
            {"name": "llama2:7b", "size_gb": 3.8, "description": "Standard 7B model"},
            {"name": "gemma:7b", "size_gb": 4.8, "description": "Google's efficient model"},
            {"name": "mistral", "size_gb": 4.1, "description": "Fast and capable"}
        ])
    elif vram_gb > 0 or ram_gb >= 8:
        # Low VRAM or CPU-only with sufficient RAM
        recommendations.extend([
            {"name": "llama2:3b", "size_gb": 1.9, "description": "Lightweight but capable"},
            {"name": "gemma:2b", "size_gb": 1.6, "description": "Very fast, minimal resources"},
            {"name": "phi", "size_gb": 1.6, "description": "Microsoft's small but smart model"}
        ])
    else:
        # Very limited resources
        recommendations.extend([
            {"name": "tinyllama", "size_gb": 0.5, "description": "Smallest usable model"},
            {"name": "phi:mini", "size_gb": 1.4, "description": "Mini version of Phi"},
            {"name": "gemma:2b", "size_gb": 1.6, "description": "Efficient 2B model"}
        ])
    
    return recommendations

def install_recommended_models():
    """Install recommended models based on system resources"""
    AmigaOSStyle.print_header("MODEL RECOMMENDATION")
    
    # Get system info
    system_info = SystemChecker.get_system_info()
    vram_gb = system_info['vram_gb']
    ram_gb = system_info['ram_total_gb']
    
    AmigaOSStyle.print_info(f"Detected System: {vram_gb:.1f}GB VRAM, {ram_gb:.1f}GB RAM")
    
    # Get recommendations
    recommendations = get_recommended_models(vram_gb, ram_gb)
    
    if not recommendations:
        AmigaOSStyle.print_error("No suitable models found for your system.")
        return None
    
    # Display recommendations
    AmigaOSStyle.print_info("Recommended models for your system:")
    for i, model in enumerate(recommendations, 1):
        print(f"{i}. {model['name']} ({model['size_gb']}GB) - {model['description']}")
    
    print(f"4. Manual model entry")
    print(f"5. Skip model installation")
    
    while True:
        try:
            choice = input(f"\nSelect model to install (1-5): ").strip()
            if choice == "5":
                return None
            elif choice == "4":
                model_name = input("Enter model name (e.g., 'llama2:7b'): ").strip()
                if model_name:
                    return install_specific_model(model_name)
                else:
                    AmigaOSStyle.print_error("Invalid model name")
                    continue
            
            index = int(choice) - 1
            if 0 <= index < len(recommendations):
                selected_model = recommendations[index]['name']
                return install_specific_model(selected_model)
            else:
                AmigaOSStyle.print_error("Invalid selection")
        except ValueError:
            AmigaOSStyle.print_error("Please enter a number")
        except KeyboardInterrupt:
            return None

def install_specific_model(model_name: str) -> str:
    """Install a specific model and return its name"""
    AmigaOSStyle.print_header(f"INSTALLING MODEL: {model_name}")
    AmigaOSStyle.print_warning("This may take several minutes depending on your internet connection...")
    
    try:
        process = subprocess.Popen(
            ['ollama', 'pull', model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Show progress
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # Check result
        if process.returncode == 0:
            AmigaOSStyle.print_success(f"Successfully installed {model_name}")
            return model_name
        else:
            stderr = process.stderr.read()
            AmigaOSStyle.print_error(f"Failed to install {model_name}: {stderr}")
            return None
            
    except Exception as e:
        AmigaOSStyle.print_error(f"Error installing model: {e}")
        return None

def select_model_interactive() -> Optional[str]:
    """Interactive model selection with fallback options"""
    models = get_available_models()
    
    if not models:
        AmigaOSStyle.print_warning("No models available locally.")
        AmigaOSStyle.print_info("Would you like to install a recommended model?")
        
        installed_model = install_recommended_models()
        if installed_model:
            return installed_model
        else:
            AmigaOSStyle.print_info("You can manually install models later using: ollama pull <model-name>")
            return None
    
    # Display available models
    AmigaOSStyle.print_header("AVAILABLE MODELS")
    for i, model in enumerate(models, 1):
        model_name = model.get('name', 'Unknown')
        model_size = model.get('size', 0)
        size_str = f"({model_size / 1024**3:.1f}GB)" if model_size else ""
        print(f"{i}. {model_name} {size_str}")
    
    print(f"{len(models) + 1}. Install new model")
    print(f"{len(models) + 2}. Exit")
    
    # Model selection
    while True:
        try:
            choice = input(f"\nSelect model (1-{len(models) + 2}): ").strip()
            if not choice:
                continue
            
            index = int(choice) - 1
            
            if 0 <= index < len(models):
                selected_model = models[index]['name']
                AmigaOSStyle.print_success(f"Selected: {selected_model}")
                return selected_model
            elif index == len(models):
                # Install new model
                installed_model = install_recommended_models()
                if installed_model:
                    return installed_model
                else:
                    continue
            elif index == len(models) + 1:
                return None
            else:
                AmigaOSStyle.print_error("Invalid selection")
        except ValueError:
            AmigaOSStyle.print_error("Please enter a number")
        except KeyboardInterrupt:
            return None

def check_and_install_dependencies():
    """Check and install all required dependencies"""
    AmigaOSStyle.print_header("SYSTEM CHECK")
    
    # Check Python dependencies
    missing_deps = SystemChecker.check_python_dependencies()
    if missing_deps:
        AmigaOSStyle.print_warning(f"Missing Python dependencies: {', '.join(missing_deps)}")
        response = input("Would you like to install them automatically? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            if not SystemChecker.install_python_dependencies(missing_deps):
                AmigaOSStyle.print_error("Failed to install dependencies. Please install them manually.")
                return False
        else:
            AmigaOSStyle.print_info("Please install dependencies manually:")
            AmigaOSStyle.print_info(f"pip install {' '.join(missing_deps)}")
            return False
    
    # Check Ollama
    if not check_ollama_installed():
        AmigaOSStyle.print_warning("Ollama is not installed.")
        response = input("Would you like to install Ollama automatically? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            if not install_ollama():
                AmigaOSStyle.print_error("Failed to install Ollama automatically.")
                AmigaOSStyle.print_info("Please install Ollama manually from https://ollama.ai")
                return False
        else:
            AmigaOSStyle.print_info("Please install Ollama from https://ollama.ai")
            return False
    
    return True

def main():
    """Main application entry point"""
    AmigaOSStyle.print_header("AMIGA AI ASSISTANT v2.2")
    AmigaOSStyle.print_info("Initializing system check...")
    
    # Check and install dependencies
    if not check_and_install_dependencies():
        AmigaOSStyle.print_error("Dependency check failed. Exiting.")
        return
    
    # Check and setup Ollama
    if not ensure_ollama_running():
        AmigaOSStyle.print_error("Failed to start Ollama. Exiting.")
        return
    
    # Check GPU
    gpu_info = check_gpu_availability()
    AmigaOSStyle.print_success(f"GPU Status: {gpu_info}")
    
    # Model selection
    model_name = select_model_interactive()
    if not model_name:
        AmigaOSStyle.print_error("No model selected. Exiting.")
        return
    
    # Start GUI
    AmigaOSStyle.print_success("Starting GUI...")
    try:
        app = ChatGUI(model_name, gpu_info)
        app.run()
    except Exception as e:
        AmigaOSStyle.print_error(f"Failed to start GUI: {e}")
        AmigaOSStyle.print_info("Make sure you have tkinter installed:")
        AmigaOSStyle.print_info("Ubuntu/Debian: sudo apt-get install python3-tk")
        AmigaOSStyle.print_info("macOS: Pre-installed with Python")
        AmigaOSStyle.print_info("Windows: Pre-installed with Python")

if __name__ == "__main__":
    main()