# Fungsi bantu mencetak tampilan di terminal: teks rata tengah, warna, kotak, dan tabel.
import os
import re
import shutil

LEBAR_KOTAK = 68
SIMBOL = "♦"  # simbol hiasan judul utama (ganti di sini jika ingin simbol lain)

# Kode warna dan gaya teks di terminal
RESET = "\033[0m"
PUTIH = "\033[97m"
KUNING = "\033[93m"
HIJAU = "\033[92m"
MERAH = "\033[91m"
TEBAL = "\033[1m"
TIDAK_TEBAL = "\033[22m"

# Garis kotak dan simbol selalu dicetak kuning
POLA_KUNING = re.compile("[┌┐└┘┬┴─│╔╗╚╝═║╞╡╪" + SIMBOL + "]+")
# Kode warna di atas, dipakai untuk menghitung panjang teks yang benar-benar tampil
POLA_KODE = re.compile(r"\033\[[0-9;]*m")

# Ikon dan warna untuk tiap jenis pesan
JENIS_PESAN = {
    "sukses": ("[OK] ", HIJAU),
    "error": ("[!] ", MERAH),
    "info": ("[i] ", PUTIH),
}

os.system("")  # supaya warna tampil juga di terminal Windows


# Lebar terminal saat ini (jumlah karakter).
def lebarLayar():
    return shutil.get_terminal_size((100, 30)).columns


# Hapus isi layar.
def bersihkan():
    os.system("cls" if os.name == "nt" else "clear")


# Buat teks menjadi tebal.
def tebal(teks):
    return TEBAL + teks + TIDAK_TEBAL


# Panjang teks yang tampil di layar (kode warna tidak dihitung).
def panjang(teks):
    return len(POLA_KODE.sub("", teks))


# Letakkan teks di tengah ruang selebar `lebar` dengan spasi kiri-kanan.
def tengahkan(teks, lebar):
    sisa = max(0, lebar - panjang(teks))
    kiri = sisa // 2
    return " " * kiri + teks + " " * (sisa - kiri)


# Spasi di kiri agar blok selebar `lebarBlok` berada di tengah layar.
def margin(lebarBlok):
    return " " * max(0, (lebarLayar() - lebarBlok) // 2)


# Beri warna pada teks; garis dan simbol tetap kuning.
def warnai(teks, warna=PUTIH):
    teks = POLA_KUNING.sub(KUNING + r"\g<0>" + warna, teks)  # \g<0> = karakter yang cocok
    return warna + teks + RESET


# Cetak satu baris teks tepat di tengah layar.
def tengah(teks, warna=PUTIH):
    print(warnai(tengahkan(teks, lebarLayar()), warna))


# Cetak beberapa baris sebagai satu blok yang berada di tengah layar.
def blok(baris):
    spasi = margin(max(panjang(teks) for teks in baris))
    for teks in baris:
        print(spasi + warnai(teks))


# Bersihkan layar lalu cetak judul halaman. Simbol hanya dipakai pada judul utama.
def judulHalaman(teks, utama=False):
    bersihkan()
    if utama:
        teks = f"{SIMBOL}  {teks}  {SIMBOL}"
    lebar = LEBAR_KOTAK - 2
    print()
    blok(["╔" + "═" * lebar + "╗",
          "║" + tengahkan(tebal(teks), lebar) + "║",
          "╚" + "═" * lebar + "╝"])
    print()


# Cetak judul bagian (tebal dan rata tengah).
def subjudul(teks):
    tengah(tebal(teks))


# Cetak kotak berisi daftar teks. Judul boleh dikosongkan.
def kotak(judul, isi):
    lebar = LEBAR_KOTAK
    for teks in isi:  # lebarkan kotak jika ada baris yang terlalu panjang
        lebar = max(lebar, len(teks) + 4)
    baris = ["┌" + "─" * (lebar - 2) + "┐"]
    if judul:
        baris.append("│" + tengahkan(tebal(judul), lebar - 2) + "│")
        baris.append("╞" + "═" * (lebar - 2) + "╡")
    for teks in isi:
        baris.append("│ " + teks.ljust(lebar - 4) + " │")
    baris.append("└" + "─" * (lebar - 2) + "┘")
    blok(baris)
    print()


# Garis mendatar tabel, misalnya garis atas, garis bawah, atau pemisah judul.
def garisTabel(lebar, kiri, sambung, kanan, isi="─"):
    return kiri + sambung.join([isi * (lebarKolom + 2) for lebarKolom in lebar]) + kanan


# Satu baris tabel. Teks yang terlalu panjang dipotong; judul kolom dibuat tebal.
def barisTabel(isiBaris, lebar, judul=False):
    hasil = []
    for teks, lebarKolom in zip(isiBaris, lebar):
        if len(teks) > lebarKolom:
            teks = teks[:lebarKolom - 1] + "…"
        if judul:
            teks = tebal(tengahkan(teks, lebarKolom))
        else:
            teks = teks.ljust(lebarKolom)
        hasil.append(teks)
    return "│ " + " │ ".join(hasil) + " │"


# Cetak tabel. `header` = daftar judul kolom, `baris` = daftar baris data.
def tabel(header, baris):
    if not baris:
        pesan("Tidak ada data untuk ditampilkan.")
        return
    baris = [[str(isi) for isi in satuBaris] for satuBaris in baris]

    # lebar tiap kolom = teks terpanjang di kolom itu
    lebar = [len(judul) for judul in header]
    for satuBaris in baris:
        for i, isi in enumerate(satuBaris):
            lebar[i] = max(lebar[i], len(isi))

    # jika tabel lebih lebar dari layar, kolom terlebar dipersempit
    lebihan = sum(lebar) + 3 * len(lebar) + 1 - lebarLayar()
    if lebihan > 0:
        kolomTerlebar = lebar.index(max(lebar))
        lebar[kolomTerlebar] = max(8, lebar[kolomTerlebar] - lebihan)

    tampil = [garisTabel(lebar, "┌", "┬", "┐"),
              barisTabel(header, lebar, judul=True),
              garisTabel(lebar, "╞", "╪", "╡", "═")]
    for satuBaris in baris:
        tampil.append(barisTabel(satuBaris, lebar))
    tampil.append(garisTabel(lebar, "└", "┴", "┘"))
    blok(tampil)
    print()


# Cetak pesan berwarna. Jenis: "info" (putih), "sukses" (hijau), "error" (merah).
def pesan(teks, jenis="info"):
    ikon, warna = JENIS_PESAN[jenis]
    tengah(ikon + teks, warna)
    print()


# Tampilkan pertanyaan dan kembalikan jawaban pengguna (tanpa spasi di pinggir).
def tanya(pertanyaan):
    jawaban = input(margin(LEBAR_KOTAK) + PUTIH + pertanyaan + ": ")
    print(RESET, end="")
    return jawaban.strip()


# Tahan layar sampai pengguna menekan Enter.
def tekanEnter():
    input(margin(LEBAR_KOTAK) + PUTIH + "Tekan Enter untuk melanjutkan...")
    print(RESET, end="")