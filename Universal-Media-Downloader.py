import customtkinter as ctk
from tkinter import filedialog, messagebox, PhotoImage
import yt_dlp
import threading
import os
import sys
import subprocess
from datetime import datetime
import re
import ctypes # Görev çubuğu ikonu için gerekli
from PIL import Image # Uygulama içi PNG görseli için gerekli

# --- Tema Ayarları ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class UltraDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 1. Görev Çubuğu Kimliği (Taskbar Fix) ---
        myappid = 'unimedia.downloader.app.v1' 
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass

        # --- Pencere Ayarları ---
        self.title("UniMedia - Evrensel İndirici")
        self.geometry("950x700")
        self.resizable(False, False)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.download_path = os.path.join(os.path.expanduser("~"), "Desktop")

        # --- 2. PROFESYONEL DOSYA YOLU AYARLARI ---
        
        # A) DAHİLİ VARLIKLAR (Gömülü İkonlar için)
        # PyInstaller ile 'onefile' yapıldığında dosyalar geçici bir klasöre (_MEIPASS) açılır.
        if hasattr(sys, '_MEIPASS'):
            internal_path = sys._MEIPASS
        else:
            internal_path = os.path.dirname(os.path.abspath(__file__))

        # B) HARİCİ VARLIKLAR (FFmpeg gibi yan dosyalar için)
        # Exe'nin kendi bulunduğu klasörü gösterir.
        if getattr(sys, 'frozen', False):
            external_path = os.path.dirname(sys.executable)
        else:
            external_path = os.path.dirname(os.path.abspath(__file__))
            
        # FFmpeg harici olarak (Exe'nin yanında) duracak
        self.ffmpeg_path = os.path.join(external_path, "ffmpeg.exe")
        
        # Logolar Exe'nin içine gömülecek
        self.icon_path_ico = os.path.join(internal_path, "logo.ico") 
        self.icon_path_png = os.path.join(internal_path, "logo.png") 

        # --- 3. Sistem İkonunu (.ico) Yükle ---
        if os.path.exists(self.icon_path_ico):
            try:
                self.iconbitmap(self.icon_path_ico)
            except Exception as e:
                print(f"ICO yükleme hatası: {e}")

        self.create_sidebar()
        self.create_main_area()
        self.check_ffmpeg()

    def check_ffmpeg(self):
        if not os.path.exists(self.ffmpeg_path):
            messagebox.showwarning("Eksik Dosya", f"ffmpeg.exe bulunamadı!\n\nAranan yer:\n{self.ffmpeg_path}\n\nLütfen ffmpeg.exe dosyasını uygulamanın yanına koyun.")

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # --- GÖRSEL LOGO (.png) EKLEME ---
        if os.path.exists(self.icon_path_png):
            try:
                pil_image = Image.open(self.icon_path_png)
                my_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(120, 120))
                image_label = ctk.CTkLabel(self.sidebar_frame, text="", image=my_image)
                image_label.grid(row=0, column=0, padx=20, pady=(20, 10))
            except Exception as e:
                print(f"PNG Logo yükleme hatası: {e}")
        else:
            print(f"logo.png bulunamadı: {self.icon_path_png}")

        # Başlık
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="UniMedia", font=ctk.CTkFont(size=26, weight="bold"))
        self.logo_label.grid(row=1, column=0, padx=20, pady=(5, 5))

        # Versiyon
        ctk.CTkLabel(self.sidebar_frame, text="v1.0 Stable", text_color="gray70", font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=20, pady=(0, 20))

        # Tema Menüsü
        self.appearance_mode_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light", "System"], command=ctk.set_appearance_mode)
        self.appearance_mode_menu.grid(row=6, column=0, padx=20, pady=20, sticky="s")

    def create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        # URL Giriş
        ctk.CTkLabel(self.main_frame, text="Medya Bağlantısı (URL):", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=10)
        self.url_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Link yapıştırın...", height=45)
        self.url_entry.grid(row=1, column=0, padx=10, pady=(5, 15), sticky="ew")

        # Ayarlar Paneli
        self.settings_frame = ctk.CTkFrame(self.main_frame)
        self.settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        # Format Seçimi
        ctk.CTkLabel(self.settings_frame, text="Format:").pack(side="left", padx=(20, 5), pady=20)
        self.format_var = ctk.StringVar(value="Video (MP4)")
        self.format_switch = ctk.CTkSegmentedButton(self.settings_frame, values=["Video (MP4)", "Ses (MP3)"], variable=self.format_var, command=self.update_ui_state)
        self.format_switch.pack(side="left", padx=5, pady=20)

        # Kalite Seçimi
        self.res_label = ctk.CTkLabel(self.settings_frame, text="Kalite:")
        self.res_label.pack(side="left", padx=(20, 5), pady=20)
        self.res_option = ctk.CTkOptionMenu(self.settings_frame, values=["En İyi", "1080p", "720p", "480p", "360p", "240p"], width=100)
        self.res_option.pack(side="left", padx=5, pady=20)

        # Klasör Seçimi
        self.path_button = ctk.CTkButton(self.settings_frame, text=f"📂 {os.path.basename(self.download_path)}", command=self.select_folder, fg_color="#3B8ED0", width=140)
        self.path_button.pack(side="right", padx=20, pady=20)

        # İlerleme Çubuğu
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, height=15)
        self.progress_bar.grid(row=3, column=0, padx=10, pady=(25, 10), sticky="ew")
        self.progress_bar.set(0)

        # Başlat Butonu
        self.download_btn = ctk.CTkButton(self.main_frame, text="İNDİRMEYİ BAŞLAT", command=self.start_thread, height=50, font=ctk.CTkFont(size=16, weight="bold"), fg_color="#2CC985", hover_color="#229D68")
        self.download_btn.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        # Klasörü Aç Butonu (Gizli)
        self.open_folder_btn = ctk.CTkButton(self.main_frame, text="📂 İndirilen Klasörü Aç", command=lambda: os.startfile(self.download_path), fg_color="#E59400", hover_color="#B87700")
        self.open_folder_btn.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        self.open_folder_btn.grid_remove()

        # Log Konsolu
        ctk.CTkLabel(self.main_frame, text="İşlem Kayıtları:", anchor="w", font=ctk.CTkFont(size=12)).grid(row=6, column=0, sticky="w", padx=10, pady=(10, 0))
        self.log_box = ctk.CTkTextbox(self.main_frame, height=120, font=("Consolas", 12))
        self.log_box.grid(row=7, column=0, padx=10, pady=5, sticky="nsew")
        self.log_box.configure(state="disabled")

    def update_ui_state(self, value):
        if value == "Ses (MP3)":
            self.res_option.configure(state="disabled", fg_color="gray")
            self.res_label.configure(text_color="gray")
        else:
            self.res_option.configure(state="normal", fg_color=("#3B8ED0", "#1F6AA5"))
            self.res_label.configure(text_color=("black", "white"))

    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def select_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.download_path = os.path.abspath(d)
            self.path_button.configure(text=f"📂 {os.path.basename(d)}")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                percent_str = d.get('_percent_str', '0%').replace('%', '')
                clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).strip()
                percent_float = float(clean_percent)
                
                self.progress_bar.set(percent_float / 100)
                
                info = d.get('info_dict', {})
                is_audio_only = info.get('vcodec') == 'none'
                status_text = "Ses İndiriliyor..." if is_audio_only else "Görüntü İndiriliyor..."
                self.download_btn.configure(text=f"{status_text} %{percent_float:.1f}")
                
            except ValueError:
                self.download_btn.configure(text="İndiriliyor... (Hesaplanıyor)")

        elif d['status'] == 'finished':
            self.progress_bar.set(1)
            self.download_btn.configure(text="Birleştiriliyor/Dönüştürülüyor...")
            self.log("İndirme bitti, son işlemler yapılıyor...")

    def get_unique_filename(self, path, title, quality_tag, extension):
        clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
        base_name = f"{clean_title}_{quality_tag}.{extension}"
        
        counter = 1
        final_name = base_name
        
        while os.path.exists(os.path.join(path, final_name)):
            counter += 1
            final_name = f"{counter}_{base_name}"
            
        return os.path.splitext(final_name)[0]

    def start_thread(self):
        url = self.url_entry.get().strip()
        if not url: return
        
        self.download_btn.configure(state="disabled", text="İndirme Başlatılıyor...")
        self.open_folder_btn.grid_remove()
        threading.Thread(target=self.run_download, args=(url,), daemon=True).start()

    def run_download(self, url):
        mode = self.format_var.get()
        quality_selection = self.res_option.get()
        
        self.log("Bağlantı analiz ediliyor...")

        try:
            with yt_dlp.YoutubeDL({'ignoreerrors': True, 'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'Medyam')
        except Exception as e:
            self.log(f"Hata: {e}")
            self.download_btn.configure(state="normal", text="HATA OLUŞTU")
            return

        ext = "mp4" if mode == "Video (MP4)" else "mp3"
        quality_tag = quality_selection if mode == "Video (MP4)" else "Audio"
        unique_name = self.get_unique_filename(self.download_path, video_title, quality_tag, ext)
        
        opts = {
            'paths': {'home': self.download_path},
            'outtmpl': f'{unique_name}.%(ext)s',
            'ffmpeg_location': self.ffmpeg_path,
            'progress_hooks': [self.progress_hook],
            'nocheckcertificate': True,
            'ignoreerrors': True,
        }

        if mode == "Video (MP4)":
            self.log(f"Video İndiriliyor: {unique_name}")
            if quality_selection == "En İyi":
                fmt = "bestvideo+bestaudio/best"
            else:
                h = quality_selection.replace("p", "")
                fmt = f"bestvideo[height={h}]+bestaudio/best[height={h}]/best"
            
            opts.update({'format': fmt, 'merge_output_format': 'mp4'})
            
        else: # MP3
            self.log(f"Ses İndiriliyor: {unique_name}")
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
                'final_ext': 'mp3',
            })

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            self.log("✅ İŞLEM TAMAMLANDI!")
            self.download_btn.configure(text="✅ İndirme Tamamlandı")
            self.open_folder_btn.grid()
            messagebox.showinfo("UniMedia", f"İndirme Başarılı!\nDosya: {unique_name}.{ext}")
            
        except Exception as e:
            self.log(f"Kritik Hata: {e}")
            messagebox.showerror("Hata", str(e))
        finally:
            self.download_btn.configure(state="normal", text="İNDİRMEYİ BAŞLAT")

if __name__ == "__main__":
    app = UltraDownloader()
    app.mainloop()