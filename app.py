import streamlit as st
import yt_dlp
import os
import tempfile
import glob
import shutil
import shutil as shutil_lib

# ------------------------------------------------------------
# 1. Fungsi mencari ffmpeg (dengan fallback manual)
# ------------------------------------------------------------
def find_ffmpeg():
    ffmpeg_path = shutil_lib.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
    custom_paths = [
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        r'D:\ffmpeg\bin\ffmpeg.exe',
        os.path.expanduser('~/ffmpeg/bin/ffmpeg.exe'),
    ]
    for path in custom_paths:
        if os.path.exists(path):
            return path
    common_paths = ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None

# ------------------------------------------------------------
# 2. Fungsi unduh (dengan perbaikan untuk MP4)
# ------------------------------------------------------------
def download_video(url, platform, format_choice, progress_placeholder, text_placeholder):
    temp_dir = tempfile.mkdtemp()
    ffmpeg_loc = find_ffmpeg()
    if not ffmpeg_loc:
        raise RuntimeError("ffmpeg tidak ditemukan. Pastikan ffmpeg terinstal.")

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                downloaded = d.get('downloaded_bytes', 0)
                percent = downloaded / total * 100
                progress_placeholder.progress(percent / 100)
                speed = d.get('speed')
                eta = d.get('eta')
                speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "N/A"
                eta_str = f"{eta // 60}m {eta % 60}s" if eta else "N/A"
                text_placeholder.text(
                    f"⏳ Mengunduh: {percent:.1f}% | Kecepatan: {speed_str} | Sisa: {eta_str}"
                )
        elif d['status'] == 'finished':
            text_placeholder.text("✅ Mengunduh selesai, memproses (konversi/gabung)...")
            progress_placeholder.progress(1.0)

    # Opsi dasar
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': False,               # biar dapat log error
        'no_warnings': False,
        'ignoreerrors': False,
        'progress_hooks': [progress_hook],
        'ffmpeg_location': ffmpeg_loc,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'geo_bypass': True,
        'geo_bypass_country': 'US',
    }

    # --------------------------------------------------------
    # Atur opsi berdasarkan platform dan format
    # --------------------------------------------------------
    if platform == "YouTube":
        if format_choice == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'extractaudio': True,
                'audioformat': 'mp3',
            })
        else:  # mp4
            # Gunakan merge untuk memastikan output MP4
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            })
    else:  # Instagram
        if format_choice == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'extractaudio': True,
                'audioformat': 'mp3',
            })
        else:
            ydl_opts.update({
                'format': 'best',
            })

    # --------------------------------------------------------
    # Eksekusi unduhan
    # --------------------------------------------------------
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

            # Cari file dengan ekstensi yang diharapkan
            ext = '.mp3' if format_choice == 'mp3' else '.mp4'
            files = glob.glob(os.path.join(temp_dir, f'*{ext}'))
            if not files:
                # Jika tidak ada, ambil file terbaru (fallback)
                all_files = glob.glob(os.path.join(temp_dir, '*'))
                if all_files:
                    files = [max(all_files, key=os.path.getmtime)]
                else:
                    raise FileNotFoundError("Tidak ada file yang dihasilkan.")
            return files[0], temp_dir
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        # Lempar ulang exception agar ditangkap di UI
        raise e

# ------------------------------------------------------------
# 3. Aplikasi Streamlit
# ------------------------------------------------------------
def main():
    st.set_page_config(page_title="Multi Downloader", page_icon="📥")
    
    # CSS untuk memperbesar font
    st.markdown("""
    <style>
        .stApp { font-size: 20px; }
        h1 { font-size: 3.5rem !important; font-weight: 700; }
        h2, h3 { font-size: 2.2rem !important; }
        p, label, .stTextInput label, .stRadio label, .stMarkdown { font-size: 1.2rem !important; }
        input, textarea, .stTextInput input { font-size: 1.3rem !important; }
        .stButton button { font-size: 1.3rem !important; padding: 0.5rem 1.5rem; }
        .stRadio div[role="radiogroup"] label { font-size: 1.2rem !important; }
        .stAlert, .stSuccess, .stWarning, .stError, .stInfo { font-size: 1.1rem !important; }
    </style>
    """, unsafe_allow_html=True)

    st.title("📥 Download YT dan IG Ora Ono Iklan")
    st.markdown("Unduh video/audio dari **YouTube** atau **Instagram** dengan mudah.")

    # Cek ffmpeg
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        st.success(f"✅ ffmpeg terdeteksi di: `{ffmpeg_path}`")
    else:
        st.warning("⚠️ ffmpeg tidak ditemukan! Pastikan ffmpeg terinstal dan tersedia di PATH.")

    platform_choice = st.radio(
        "🌐 Pilih platform:",
        options=["YouTube", "Instagram"],
        index=0
    )

    url = st.text_input("🔗 Masukkan URL:", placeholder="https://www.youtube.com/watch?v=...  atau  https://www.instagram.com/...")

    format_choice = st.radio(
        "📁 Pilih format:",
        options=["MP3 (Audio)", "MP4 (Video)"],
        index=0
    )

    if 'download_ready' not in st.session_state:
        st.session_state.download_ready = False
        st.session_state.file_path = None
        st.session_state.temp_dir = None
        st.session_state.file_name = None

    if st.button("⬇️ Unduh", use_container_width=True):
        if not url.strip():
            st.warning("Silakan masukkan URL terlebih dahulu.")
            return

        if not find_ffmpeg():
            st.error("ffmpeg tidak ditemukan. Tidak dapat memproses unduhan.")
            return

        fmt = 'mp3' if format_choice == "MP3 (Audio)" else 'mp4'

        progress_placeholder = st.empty()
        text_placeholder = st.empty()
        progress_placeholder.progress(0)
        text_placeholder.text("⏳ Memulai unduhan...")

        try:
            file_path, temp_dir = download_video(url, platform_choice, fmt, progress_placeholder, text_placeholder)
            text_placeholder.text("✅ Unduhan selesai! File siap diunduh.")

            st.session_state.download_ready = True
            st.session_state.file_path = file_path
            st.session_state.temp_dir = temp_dir
            st.session_state.file_name = os.path.basename(file_path)

        except Exception as e:
            text_placeholder.text("❌ Gagal mengunduh")
            st.error(f"Terjadi kesalahan:\n\n{e}")
            st.info("Pastikan URL valid. Untuk Instagram, konten privat memerlukan cookies (fitur belum ditambahkan).")
            st.session_state.download_ready = False

    if st.session_state.download_ready:
        file_path = st.session_state.file_path
        file_name = st.session_state.file_name
        fmt = 'mp3' if file_name.endswith('.mp3') else 'mp4'
        mime = 'audio/mpeg' if fmt == 'mp3' else 'video/mp4'

        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()

            st.success(f"✅ File siap diunduh: **{file_name}**")
            st.download_button(
                label=f"💾 Simpan {file_name}",
                data=file_data,
                file_name=file_name,
                mime=mime,
                use_container_width=True
            )

            shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
            st.session_state.download_ready = False

        except Exception as e:
            st.error(f"Gagal membaca file: {e}")
            st.session_state.download_ready = False

if __name__ == "__main__":
    main()