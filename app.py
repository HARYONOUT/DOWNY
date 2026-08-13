import streamlit as st
import yt_dlp
import os
import tempfile
import glob
import shutil
import shutil as shutil_lib

# ------------------------------------------------------------
# 1. Fungsi untuk mencari ffmpeg (di PATH atau lokasi manual)
# ------------------------------------------------------------
def find_ffmpeg():
    """Cari ffmpeg di PATH atau lokasi umum, dengan fallback manual."""
    ffmpeg_path = shutil_lib.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path
    
    # Tambahkan path pribadi jika perlu (sesuaikan)
    custom_paths = [
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        r'D:\ffmpeg\bin\ffmpeg.exe',
        os.path.expanduser('~/ffmpeg/bin/ffmpeg.exe'),
    ]
    for path in custom_paths:
        if os.path.exists(path):
            return path
    
    # Fallback untuk Linux/macOS
    common_paths = ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None

# ------------------------------------------------------------
# 2. Fungsi utama unduh (mendukung YouTube & Instagram)
# ------------------------------------------------------------
def download_video(url, platform, format_choice, progress_placeholder, text_placeholder):
    """
    platform : 'YouTube' atau 'Instagram'
    format_choice : 'mp3' atau 'mp4'
    """
    temp_dir = tempfile.mkdtemp()
    ffmpeg_loc = find_ffmpeg()
    if not ffmpeg_loc:
        raise RuntimeError("ffmpeg tidak ditemukan. Silakan instal ffmpeg dan pastikan di PATH, atau tambahkan path manual di kode.")

    # Hook untuk progress bar
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
            text_placeholder.text("✅ Mengunduh selesai, sekarang memproses (konversi/gabung)...")
            progress_placeholder.progress(1.0)

    # Opsi dasar yt-dlp
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'progress_hooks': [progress_hook],
        'ffmpeg_location': ffmpeg_loc,
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
            ydl_opts.update({
                'format': 'best[ext=mp4]/best',   # cari file MP4 tunggal, fallback ke terbaik
                'merge_output_format': 'mp4',
            })

    else:  # Instagram
        # Instagram: video biasanya sudah dalam satu file (tanpa perlu merge)
        if format_choice == 'mp3':
            # Ekstrak audio dari video Instagram
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
            ydl_opts.update({
                'format': 'best',   # ambil video kualitas terbaik (sudah ada audio)
            })

    # --------------------------------------------------------
    # Eksekusi unduhan
    # --------------------------------------------------------
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

            # Cari file hasil
            ext = '.mp3' if format_choice == 'mp3' else '.mp4'
            files = glob.glob(os.path.join(temp_dir, f'*{ext}'))
            if not files:
                # Jika tidak ditemukan, ambil file terbaru di direktori
                all_files = glob.glob(os.path.join(temp_dir, '*'))
                if all_files:
                    files = [max(all_files, key=os.path.getmtime)]
                else:
                    raise FileNotFoundError("Tidak ada file yang dihasilkan.")
            return files[0], temp_dir
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e

# ------------------------------------------------------------
# 3. Aplikasi Streamlit (UI)
# ------------------------------------------------------------
def main():
    st.set_page_config(page_title="Multi Downloader", page_icon="📥")
    st.title("📥 Multi Platform Downloader")
    st.markdown("Unduh video/audio dari **YouTube** atau **Instagram** dengan mudah.")

    # Cek ffmpeg
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        st.success(f"✅ ffmpeg terdeteksi di: `{ffmpeg_path}`")
    else:
        st.warning("⚠️ ffmpeg tidak ditemukan! Pastikan ffmpeg terinstal dan tersedia di PATH.")
        st.info("Jika sudah terinstal tetapi tidak terdeteksi, tambahkan path ke fungsi `find_ffmpeg()` di kode.")

    # Pilihan platform
    platform_choice = st.radio(
        "🌐 Pilih platform:",
        options=["YouTube", "Instagram"],
        index=0
    )

    # Input URL
    url = st.text_input("🔗 Masukkan URL:", placeholder="https://www.youtube.com/watch?v=...  atau  https://www.instagram.com/...")

    # Pilihan format
    format_choice = st.radio(
        "📁 Pilih format:",
        options=["MP3 (Audio)", "MP4 (Video)"],
        index=0
    )

    # State session untuk tombol download
    if 'download_ready' not in st.session_state:
        st.session_state.download_ready = False
        st.session_state.file_path = None
        st.session_state.temp_dir = None
        st.session_state.file_name = None

    # Tombol unduh
    if st.button("⬇️ Unduh", use_container_width=True):
        if not url.strip():
            st.warning("Silakan masukkan URL terlebih dahulu.")
            return

        if not find_ffmpeg():
            st.error("ffmpeg tidak ditemukan. Tidak dapat memproses unduhan.")
            return

        fmt = 'mp3' if format_choice == "MP3 (Audio)" else 'mp4'

        # Placeholder untuk progress
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

    # Tampilkan tombol download jika file siap
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

            # Hapus file temporary setelah tombol muncul
            shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
            st.session_state.download_ready = False

        except Exception as e:
            st.error(f"Gagal membaca file: {e}")
            st.session_state.download_ready = False

if __name__ == "__main__":
    main()