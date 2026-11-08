# Data mahasiswa: model, penyimpanan CSV, dan manager (aturan + pengelolaan data).
import csv
import os

FOLDER = os.path.join(os.path.dirname(__file__), "..", "Data_Sistem")


class Mahasiswa:
    MAKS_TRX_AKTIF = 2
    MIN_HP = 10
    MAX_HP = 13

    def __init__(self, nim, nama, noHp):
        self.nim = nim
        self.nama = nama
        self.noHp = noHp
        self.trxAktif = set()
        self.statusAktif = False
        self.pernahPinjam = False  # True jika pernah punya transaksi (agar riwayat tidak hilang saat dihapus)

    def jumlahAktif(self):
        return len(self.trxAktif)

    def bolehPinjam(self):
        return self.jumlahAktif() < self.MAKS_TRX_AKTIF

    def tambahTrx(self, idTrx):
        self.trxAktif.add(idTrx)
        self.statusAktif = True
        self.pernahPinjam = True

    def selesaiTrx(self, idTrx):
        self.trxAktif.discard(idTrx)
        self.statusAktif = len(self.trxAktif) > 0


# Membaca dan menulis mahasiswa.csv.
class PenyimpananMahasiswa:
    FILE = os.path.join(FOLDER, "mahasiswa.csv")

    # Baca file menjadi dictionary {nim: Mahasiswa}. Jika file belum ada, hasilnya kosong.
    def muat(self):
        try:
            data = {}
            with open(self.FILE, newline="") as file:  # newline="" wajib untuk modul csv
                for b in csv.DictReader(file):
                    data[b["nim"]] = Mahasiswa(b["nim"], b["nama"], b["noHp"])
            return data
        except FileNotFoundError:
            return {}

    # Tulis semua mahasiswa ke file (isi lama ditimpa).
    def simpan(self, daftar):
        os.makedirs(FOLDER, exist_ok=True)  # buat folder Data_Sistem jika belum ada
        with open(self.FILE, "w", newline="") as file:
            penulis = csv.writer(file)
            penulis.writerow(["nim", "nama", "noHp"])
            for mhs in daftar:
                penulis.writerow([mhs.nim, mhs.nama, mhs.noHp])


# Mengelola data mahasiswa. Disimpan dalam dictionary dengan kunci NIM.
class MahasiswaManager:
    def __init__(self):
        self._db = PenyimpananMahasiswa()
        self._data = {}

    # Baca data dari file CSV.
    def muat(self):
        self._data = self._db.muat()

    # Tulis semua data ke file CSV.
    def simpan(self):
        self._db.simpan(self._data.values())

    # Periksa nama dan nomor HP; error jika tidak sesuai.
    def _periksa(self, nama, noHp):
        if not nama:
            raise ValueError("Nama mahasiswa wajib diisi.")
        if not noHp.isdigit() or not Mahasiswa.MIN_HP <= len(noHp) <= Mahasiswa.MAX_HP:
            raise ValueError(
                f"No. HP wajib diisi, hanya berisi angka, {Mahasiswa.MIN_HP} sampai {Mahasiswa.MAX_HP} digit."
            )

    # Tambah mahasiswa baru (NIM tidak boleh sama).
    def tambah(self, nim, nama, noHp):
        nim, nama, noHp = nim.strip(), nama.strip(), noHp.strip()
        if not nim:
            raise ValueError("NIM wajib diisi.")
        if nim in self._data:
            raise ValueError(f"NIM {nim} sudah terdaftar.")
        self._periksa(nama, noHp)
        self._data[nim] = Mahasiswa(nim, nama, noHp)

    # Ubah nama / no. HP. Isian kosong berarti tidak diubah.
    def edit(self, nim, nama="", noHp=""):
        mhs = self.ambil(nim)
        nama = nama.strip() or mhs.nama
        noHp = noHp.strip() or mhs.noHp
        self._periksa(nama, noHp)
        mhs.nama = nama
        mhs.noHp = noHp

    # Hapus mahasiswa (ditolak jika sudah punya riwayat transaksi, karena riwayat disimpan permanen).
    def hapus(self, nim):
        mhs = self.ambil(nim)
        if mhs.pernahPinjam:
            raise ValueError(f"{mhs.nama} tidak dapat dihapus karena sudah memiliki riwayat transaksi.")
        del self._data[nim]

    # Cari mahasiswa dari sebagian NIM atau nama.
    def cari(self, kata):
        kata = kata.lower()
        return [mhs for mhs in self._data.values() if kata in mhs.nim.lower() or kata in mhs.nama.lower()]

    # Ambil satu mahasiswa berdasarkan NIM (error jika tidak ada).
    def ambil(self, nim):
        if nim not in self._data:
            raise ValueError(f"Mahasiswa dengan NIM {nim} tidak ditemukan.")
        return self._data[nim]

    # Semua mahasiswa.
    def semua(self):
        return list(self._data.values())