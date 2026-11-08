# Data alat: status, kondisi, model, penyimpanan CSV (alat.csv + kategori.csv), dan manager.
import csv
import os
from enum import Enum

FOLDER = os.path.join(os.path.dirname(__file__), "..", "Data_Sistem")


class KondisiAlat(Enum):
    BAIK = "Baik"
    RUSAK_RINGAN = "Rusak ringan"
    RUSAK_BERAT = "Rusak berat"


class StatusAlat(Enum):
    TERSEDIA = "Tersedia"
    DIPINJAM = "Dipinjam"
    PEMELIHARAAN = "Pemeliharaan"


class Alat:
    def __init__(self, kode, nama, kategori):
        self.kode = kode
        self.nama = nama
        self.kategori = kategori
        self.kondisi = KondisiAlat.BAIK
        self.status = StatusAlat.TERSEDIA
        self.trxAktif = None
        self.pernahDipinjam = False  # True jika pernah masuk transaksi (agar riwayat tidak hilang saat dihapus)

    def tersedia(self):
        return self.status == StatusAlat.TERSEDIA

    def tandaiDipinjam(self, idTrx):
        self.status = StatusAlat.DIPINJAM
        self.trxAktif = idTrx
        self.pernahDipinjam = True

    # Alat baik langsung tersedia; alat rusak (ringan/berat) otomatis masuk pemeliharaan.
    def terimaKembali(self, kondisi):
        self.kondisi = kondisi
        self.status = StatusAlat.TERSEDIA if kondisi == KondisiAlat.BAIK else StatusAlat.PEMELIHARAAN

    def selesaiTrx(self, idTrx):
        if self.trxAktif == idTrx:
            self.trxAktif = None

    # Pemeliharaan selesai: alat kembali baik dan tersedia.
    def selesaiPemeliharaan(self):
        if self.status != StatusAlat.PEMELIHARAAN:
            raise ValueError(f"Alat {self.kode} tidak sedang dalam pemeliharaan.")
        self.kondisi = KondisiAlat.BAIK
        self.status = StatusAlat.TERSEDIA


# Membaca dan menulis alat.csv dan kategori.csv.
class PenyimpananAlat:
    # Baca file CSV menjadi daftar dictionary. Jika file belum ada, hasilnya kosong.
    @staticmethod
    def _baca(namaFile):
        try:
            with open(os.path.join(FOLDER, namaFile), newline="") as file:  # newline="" wajib untuk modul csv
                return list(csv.DictReader(file))
        except FileNotFoundError:
            return []

    # Tulis judul kolom lalu semua baris ke file CSV (isi lama ditimpa).
    @staticmethod
    def _tulis(namaFile, kolom, baris):
        os.makedirs(FOLDER, exist_ok=True)  # buat folder Data_Sistem jika belum ada
        with open(os.path.join(FOLDER, namaFile), "w", newline="") as file:
            penulis = csv.writer(file)
            penulis.writerow(kolom)
            penulis.writerows(baris)

    # Hasilnya pasangan (dictionary {kode: Alat}, set kategori).
    def muat(self):
        kategori = set()
        for b in self._baca("kategori.csv"):
            kategori.add(b["kategori"])
        data = {}
        for b in self._baca("alat.csv"):
            alat = Alat(b["kode"], b["nama"], b["kategori"])
            alat.kondisi = KondisiAlat(b["kondisi"])
            alat.status = StatusAlat(b["status"].replace("Tidak tersedia", "Pemeliharaan"))  # data lama
            data[alat.kode] = alat
        return data, kategori

    def simpan(self, daftarAlat, kategori):
        self._tulis("kategori.csv", ["kategori"], [[nama] for nama in sorted(kategori)])
        self._tulis("alat.csv", ["kode", "nama", "kategori", "kondisi", "status"],
                    [[a.kode, a.nama, a.kategori, a.kondisi.value, a.status.value] for a in daftarAlat])


# Mengelola data alat. Disimpan dalam dictionary dengan kunci kode alat.
class AlatManager:
    MAKS_TAMBAH = 100  # batas jumlah unit yang boleh ditambah sekaligus

    def __init__(self):
        self._db = PenyimpananAlat()
        self._data = {}
        self.kategori = set()  # kategori yang sudah ada (tanpa duplikat)

    # Baca kategori dan alat dari file CSV.
    def muat(self):
        self._data, self.kategori = self._db.muat()

    # Tulis kategori dan semua alat ke file CSV.
    def simpan(self):
        self._db.simpan(self._data.values(), self.kategori)

    # Tambah alat baru (kode tidak boleh sama).
    def tambah(self, alat):
        alat.kode = alat.kode.strip()
        alat.nama = alat.nama.strip()
        alat.kategori = alat.kategori.strip().title()
        if not (alat.kode and alat.nama and alat.kategori):
            raise ValueError("Kode, nama, dan kategori alat wajib diisi.")
        if alat.kode in self._data:
            raise ValueError(f"Kode alat {alat.kode} sudah terdaftar.")
        self._data[alat.kode] = alat
        self.kategori.add(alat.kategori)

    # Cari nomor urut berikutnya untuk kode berawalan tertentu.
    # Contoh: sudah ada MKS-01 sampai MKS-10, maka hasilnya 11.
    def _nomorBerikut(self, awalan):
        terbesar = 0
        awalanKode = awalan + "-"  # contoh: MKS-
        for kode in self._data:
            angka = kode[len(awalanKode):]  # contoh: kode MKS-07 -> angka "07"
            if kode.startswith(awalanKode) and angka.isdecimal():  # isdecimal: hanya angka
                terbesar = max(terbesar, int(angka))
        return terbesar + 1

    # Tambah beberapa unit alat sekaligus. Jika jumlah > 1, kode dibuat otomatis
    # dari awalan + nomor urut (MKS-01, MKS-02, ...) dan melanjutkan nomor yang sudah ada.
    # Jika jumlah = 1, kode dipakai apa adanya.
    def tambahBanyak(self, kode, nama, kategori, jumlah):
        kode = kode.strip().rstrip("-")  # buang "-" di ujung agar tidak jadi "MKS--01"
        if not kode:
            raise ValueError("Kode, nama, dan kategori alat wajib diisi.")
        if not 1 <= jumlah <= self.MAKS_TAMBAH:
            raise ValueError(f"Jumlah unit harus 1 sampai {self.MAKS_TAMBAH}.")

        if jumlah == 1:
            daftarKode = [kode]
        else:
            nomorAwal = self._nomorBerikut(kode)
            daftarKode = [f"{kode}-{nomor:02d}" for nomor in range(nomorAwal, nomorAwal + jumlah)]  # 1 -> 01

        # Jika ada yang salah (misal nama kosong), error muncul di unit pertama, jadi belum ada yang tersimpan.
        daftarAlat = []
        for kodeBaru in daftarKode:
            alat = Alat(kodeBaru, nama, kategori)
            self.tambah(alat)
            daftarAlat.append(alat)
        return daftarAlat

    # Ubah nama / kategori alat. Isian kosong berarti tidak diubah.
    def edit(self, kode, nama="", kategori=""):
        alat = self.ambil(kode)
        alat.nama = nama.strip() or alat.nama
        alat.kategori = kategori.strip().title() or alat.kategori
        self.kategori.add(alat.kategori)

    # Hapus alat (ditolak jika pernah dipinjam, karena riwayat disimpan permanen).
    def hapus(self, kode):
        alat = self.ambil(kode)
        if alat.pernahDipinjam:
            raise ValueError(f"Alat {kode} tidak dapat dihapus karena sudah memiliki riwayat peminjaman.")
        del self._data[kode]

    # Cari alat dari sebagian kode, nama, atau kategori.
    def cari(self, kriteria, kata):
        if kriteria not in ("kode", "nama", "kategori"):
            raise ValueError("Kriteria pencarian harus kode, nama, atau kategori.")
        kata = kata.lower()
        # getattr(alat, "nama") sama dengan alat.nama; di sini nama atribut mengikuti kriteria
        return [alat for alat in self._data.values() if kata in getattr(alat, kriteria).lower()]

    # Ambil satu alat berdasarkan kode (error jika tidak ada).
    def ambil(self, kode):
        if kode not in self._data:
            raise ValueError(f"Alat dengan kode {kode} tidak ditemukan.")
        return self._data[kode]

    # Semua alat.
    def semua(self):
        return list(self._data.values())

    # Tambah kategori baru.
    def tambahKategori(self, nama):
        nama = nama.strip().title()
        if not nama:
            raise ValueError("Nama kategori wajib diisi.")
        if nama in self.kategori:
            raise ValueError(f"Kategori {nama} sudah ada.")
        self.kategori.add(nama)

    # Alat dengan status tertentu.
    def filterStatus(self, status):
        return [alat for alat in self._data.values() if alat.status == status]

    # Alat yang kondisinya tidak baik.
    def alatRusak(self):
        return [alat for alat in self._data.values() if alat.kondisi != KondisiAlat.BAIK]

    # Jumlah alat yang tersedia (stok).
    def jumlahTersedia(self):
        return len(self.filterStatus(StatusAlat.TERSEDIA))

    # Alat yang sedang dalam pemeliharaan (masuk otomatis saat dikembalikan dalam kondisi rusak).
    def daftarPemeliharaan(self):
        return self.filterStatus(StatusAlat.PEMELIHARAAN)
