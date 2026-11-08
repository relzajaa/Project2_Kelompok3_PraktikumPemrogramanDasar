# Data transaksi: model, penyimpanan CSV (transaksi.csv + detail.csv), dan manager.
import csv
import os
from collections import Counter
from datetime import date, timedelta
from enum import Enum

from .alat import KondisiAlat
from .mahasiswa import Mahasiswa

FOLDER = os.path.join(os.path.dirname(__file__), "..", "Data_Sistem")


class StatusTransaksi(Enum):
    DIPINJAM = "Dipinjam"
    SEBAGIAN_DIKEMBALIKAN = "Sebagian dikembalikan"
    SELESAI = "Selesai"


class DetailPeminjaman:
    def __init__(self, alat):
        self.alat = alat
        self.sudahKembali = False
        self.tglKembali = None
        self.kondisiKembali = None
        self.hariTerlambat = 0

    def prosesKembali(self, kondisi, tgl, batas):
        self.sudahKembali = True
        self.tglKembali = tgl
        self.kondisiKembali = kondisi
        self.hariTerlambat = max(0, (tgl - batas).days)

    def isKembali(self):
        return self.sudahKembali


class Transaksi:
    MAKS_HARI = 7

    def __init__(self, idTrx, mahasiswa, hari=MAKS_HARI, tglPinjam=None):
        self.id = idTrx
        self.mahasiswa = mahasiswa
        self.daftarDetail = []
        self.tglPinjam = tglPinjam or date.today()  # tglPinjam diisi saat data dibaca dari file
        self.batasKembali = self.tglPinjam + timedelta(days=hari)
        self.status = StatusTransaksi.DIPINJAM

    def tambahAlat(self, alat):
        self.daftarDetail.append(DetailPeminjaman(alat))
        alat.tandaiDipinjam(self.id)

    def kembalikanAlat(self, kode, kondisi, tgl):
        if tgl < self.tglPinjam:
            raise ValueError("Tanggal kembali tidak boleh sebelum tanggal pinjam.")
        for detail in self.daftarDetail:
            if detail.alat.kode == kode and not detail.isKembali():
                detail.prosesKembali(kondisi, tgl, self.batasKembali)
                detail.alat.terimaKembali(kondisi)
                detail.alat.selesaiTrx(self.id)
                self.hitungStatus()
                return
        raise ValueError(f"Alat {kode} tidak ada di transaksi {self.id} atau sudah dikembalikan.")

    def hitungStatus(self):
        kembali = [detail.isKembali() for detail in self.daftarDetail]
        if all(kembali):
            self.status = StatusTransaksi.SELESAI
        elif any(kembali):
            self.status = StatusTransaksi.SEBAGIAN_DIKEMBALIKAN
        else:
            self.status = StatusTransaksi.DIPINJAM

    def aktif(self):
        return self.status != StatusTransaksi.SELESAI

    def daftarAlat(self):
        return [detail.alat for detail in self.daftarDetail]

    def alatBelumKembali(self):
        return [detail.alat for detail in self.daftarDetail if not detail.isKembali()]

    def terlambat(self, tgl):
        return tgl > self.batasKembali


# Membaca dan menulis transaksi.csv dan detail.csv.
class PenyimpananTransaksi:
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

    # Hasilnya dictionary {id: Transaksi}. Mahasiswa dan alat harus sudah dimuat.
    # Status alat, status transaksi, dan transaksi aktif mahasiswa dihitung ulang dari data yang dibaca.
    def muat(self, mgrMahasiswa, mgrAlat):
        data = {}
        for b in self._baca("transaksi.csv"):
            mahasiswa = mgrMahasiswa.ambil(b["nim"])
            trx = Transaksi(b["id"], mahasiswa, int(b["hari"]), date.fromisoformat(b["tglPinjam"]))
            data[trx.id] = trx
            mahasiswa.tambahTrx(trx.id)

        for b in self._baca("detail.csv"):
            trx = data[b["idTrx"]]
            alat = mgrAlat.ambil(b["kodeAlat"])
            detail = DetailPeminjaman(alat)
            alat.pernahDipinjam = True
            if b["tglKembali"]:  # kolom tglKembali terisi = alat sudah dikembalikan
                detail.prosesKembali(KondisiAlat(b["kondisiKembali"]), date.fromisoformat(b["tglKembali"]), trx.batasKembali)
            else:
                alat.tandaiDipinjam(trx.id)
            trx.daftarDetail.append(detail)

        for trx in data.values():
            trx.hitungStatus()
            if not trx.aktif():
                trx.mahasiswa.selesaiTrx(trx.id)
        return data

    def simpan(self, daftarTrx):
        barisTrx = []
        barisDetail = []
        for t in daftarTrx:
            barisTrx.append([t.id, t.mahasiswa.nim, t.tglPinjam.isoformat(), (t.batasKembali - t.tglPinjam).days])
            for d in t.daftarDetail:
                if d.isKembali():
                    barisDetail.append([t.id, d.alat.kode, d.tglKembali.isoformat(), d.kondisiKembali.value])
                else:
                    barisDetail.append([t.id, d.alat.kode, "", ""])  # belum kembali: tanggal dan kondisi kosong
        self._tulis("transaksi.csv", ["id", "nim", "tglPinjam", "hari"], barisTrx)
        self._tulis("detail.csv", ["idTrx", "kodeAlat", "tglKembali", "kondisiKembali"], barisDetail)


# Mengelola transaksi peminjaman. Disimpan dalam dictionary dengan kunci ID transaksi.
class TransaksiManager:
    # Manager mahasiswa dan alat dipakai untuk memeriksa data.
    def __init__(self, mgrMahasiswa, mgrAlat):
        self._db = PenyimpananTransaksi()
        self._data = {}
        self._counter = 0  # nomor urut untuk membuat ID transaksi
        self._mgrMahasiswa = mgrMahasiswa
        self._mgrAlat = mgrAlat

    # Baca transaksi dari file CSV. Harus dipanggil setelah mahasiswa dan alat dimuat.
    def muat(self):
        self._data = self._db.muat(self._mgrMahasiswa, self._mgrAlat)
        # lanjutkan nomor ID dari yang terbesar di file (TRX001 -> 1)
        self._counter = 0
        for idTrx in self._data:
            self._counter = max(self._counter, int(idTrx[3:]))

    # Tulis semua transaksi dan detail alatnya ke file CSV.
    def simpan(self):
        self._db.simpan(self._data.values())

    # Buat transaksi baru setelah semua aturan peminjaman dipenuhi.
    def buat(self, nim, listKode, hari=Transaksi.MAKS_HARI):
        mahasiswa = self._mgrMahasiswa.ambil(nim)
        if not mahasiswa.bolehPinjam():
            raise ValueError(
                f"{mahasiswa.nama} sudah memiliki {Mahasiswa.MAKS_TRX_AKTIF} transaksi aktif (batas maksimum)."
            )
        if not listKode:
            raise ValueError("Pilih minimal satu alat untuk dipinjam.")

        daftarAlat = []
        for kode in listKode:
            alat = self._mgrAlat.ambil(kode)
            if alat not in daftarAlat:  # kode yang diketik dua kali dihitung sekali
                daftarAlat.append(alat)
        for alat in daftarAlat:
            if not alat.tersedia():
                raise ValueError(f"Alat {alat.kode} ({alat.nama}) tidak tersedia, status: {alat.status.value}.")
        if not 1 <= hari <= Transaksi.MAKS_HARI:
            raise ValueError(f"Lama pinjam harus 1 sampai {Transaksi.MAKS_HARI} hari.")

        self._counter += 1
        trx = Transaksi(f"TRX{self._counter:03d}", mahasiswa, hari)  # TRX001, TRX002, ...
        for alat in daftarAlat:
            trx.tambahAlat(alat)
        self._data[trx.id] = trx
        mahasiswa.tambahTrx(trx.id)
        return trx

    # Proses pengembalian satu alat dalam sebuah transaksi.
    def kembalikan(self, idTrx, kode, kondisi, tgl):
        if idTrx not in self._data:
            raise ValueError(f"Transaksi {idTrx} tidak ditemukan.")
        trx = self._data[idTrx]
        trx.kembalikanAlat(kode, kondisi, tgl)
        if not trx.aktif():  # semua alat sudah kembali
            trx.mahasiswa.selesaiTrx(idTrx)

    # Semua transaksi.
    def semua(self):
        return list(self._data.values())

    # Semua transaksi milik satu mahasiswa.
    def cariByMahasiswa(self, nim):
        self._mgrMahasiswa.ambil(nim)  # pastikan NIM terdaftar
        return [trx for trx in self._data.values() if trx.mahasiswa.nim == nim]

    # Transaksi mahasiswa yang sudah selesai, yang terbaru di atas.
    def riwayat(self, nim):
        selesai = [trx for trx in self.cariByMahasiswa(nim) if not trx.aktif()]
        return sorted(selesai, key=lambda trx: trx.tglPinjam, reverse=True)

    # Alat yang paling sering dipinjam, berupa daftar (nama, jumlah) dari yang terbanyak.
    def alatTerpopuler(self):
        hitung = Counter()
        for trx in self._data.values():
            for d in trx.daftarDetail:
                hitung[d.alat.nama] += 1
        return hitung.most_common()

    # Mahasiswa yang paling sering meminjam, berupa daftar (nama (nim), jumlah) dari yang terbanyak.
    def mahasiswaTerAktif(self):
        return Counter(f"{trx.mahasiswa.nama} ({trx.mahasiswa.nim})" for trx in self._data.values()).most_common()

    # Jumlah transaksi yang masih aktif.
    def jumlahAktif(self):
        return len([trx for trx in self._data.values() if trx.aktif()])

    # Jumlah transaksi yang sudah selesai.
    def jumlahSelesai(self):
        return len(self._data) - self.jumlahAktif()

    # Kumpulan data statistik untuk ditampilkan.
    def statistik(self):
        return {
            "alatTerpopuler": self.alatTerpopuler(),
            "mahasiswaTerAktif": self.mahasiswaTerAktif(),
            "jumlahSelesai": self.jumlahSelesai(),
            "jumlahAktif": self.jumlahAktif(),
        }
