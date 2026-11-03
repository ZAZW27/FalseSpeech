Changelog - False Speech

Dokumen ini mencatat seluruh riwayat pengembangan, perubahan arsitektur, dan penambahan fitur pada proyek False Speech.
Riwayat Pengembangan

17 Oktober 2026

    Inisialisasi awal proyek dan struktur dasar repositori.

    Setup environment backend menggunakan FastAPI, Docker, dan PostgreSQL.

31 Oktober 2026

    Melakukan refactor besar pada struktur proyek menjadi arsitektur Monorepo.

    Memisahkan direktori backend dan frontend untuk memudahkan proses development dan deployment.

    Memindahkan file konfigurasi utama (.env, compose.yaml) ke direktori root.

1 November 2026

    Menambahkan halaman Landing Page (Frontend) lengkap dengan Hero Section, About, dan Pricing.

    Mengimplementasikan halaman Login dengan integrasi API autentikasi (JWT).

    Mengimplementasikan halaman Registrasi untuk pembuatan akun pengguna baru.

2 November 2026

    Menambahkan layouting dasar (Sidebar, Topbar, Mobile Drawer) untuk halaman Dashboard.

    Membuat inisialisasi struktur dan komponen versi pertama (V1) untuk Dashboard.

    Menyelesaikan pembuatan Dashboard fungsional secara utuh, termasuk pemisahan tampilan antarmuka antara Free User dan Paid User.

    Memperbaiki bug pada halaman Riwayat (History) yang sebelumnya selalu menampilkan durasi 0 detik dan persentase statis 0% atau 100%.

Status Pengujian (Test Case Review)

Berdasarkan hasil evaluasi pengujian sistem, berikut adalah rekapitulasi status fitur yang telah berjalan dan yang masih memerlukan perbaikan.
Fitur yang Telah Berjalan (Passed)

    Autentikasi & Keamanan Akun: Registrasi, Login, Logout, serta proteksi token.

    Live Monitoring & WebSocket: Koneksi WebSocket dengan JWT, penanganan audio korup, dan penyimpanan sesi saat koneksi terputus.

    AI Engine & Output: Penanganan audio hening (Silent) dan logika threshold untuk output Uncertain.

    Kuota & Tier: Pencegahan sesi saat kuota habis, pemutusan sesi real-time, dan reset kuota harian.

    Riwayat & Database: Penarikan data riwayat, penolakan akses tanpa token, dan proteksi IDOR (tidak bisa melihat data pengguna lain).

Fitur yang Belum Selesai / Memerlukan Perbaikan (Failed)

    AUTH-05: Validasi Pydantic belum menolak format email yang salah pada form Login.

    AUTH-08 & WSS-05: Belum ada implementasi rate-limiting pada Login dan WebSocket (rawan brute-force / DoS).

    AUTH-09: Belum ada fitur 2FA (OTP).

    AI-01 & AI-02: Perlu re-testing karena sebelumnya gagal akibat size mismatch pada model (saat ini sudah diperbaiki ke arsitektur model Large).

    QTA-04: Celah bypass kuota jika pengguna membuka beberapa tab browser secara bersamaan.
