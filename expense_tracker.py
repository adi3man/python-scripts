import os

clear = lambda: os.system('clear')
kategori_pengeluaran = ("Makanan", "Transportasi", "Hiburan", "Lainnya")
list_pengeluaran = []

def tambah_pengeluaran(kategori_input, jumlah):
    pilihan = {1: "Makanan", 2: "Transportasi", 3: "Hiburan", 4: "Lainnya"}
    
    kategori_nama = pilihan.get(kategori_input, "Lainnya") 
    
    list_pengeluaran.append({"Kategori": kategori_nama, "Jumlah": jumlah})
    print("Recorded !")

def lihat_pengeluaran():
  return list_pengeluaran

def total_pengeluaran():
  return

finish = False
while finish == False:
  clear()
  print("-= Expense Tracker V1.0 =-")
  print("Main Menu")
  print("[1]. Tambah Pengeluaran")
  print("[2]. Lihat Pengeluaran")
  print("[3]. Total Pengeluaran")
  print("[4]. Keluar")
  
  uinput = int(input("Pilih menu dengan angka : "))
  match uinput:
    case 1:
      print("Pilih kategori")
      c = 1
      for x in kategori_pengeluaran:
        print(c, ":",x)
        c += 1
      
      kategori_i = input("Pilihan : ")
      jumlah_i = input("Jumlah : Rp ")
      if len(kategori_i) < 1:
        print("Tidak Boleh kosong !")
        print("Tekan tombol Enter untuk lanjut")
        s = input()
      else:
        tambah_pengeluaran(int(kategori_i),int(jumlah_i))
        print("Tekan tombol Enter untuk lanjut")
        s = input()
    case 2:
      if not list_pengeluaran:
        print("List kosong !")
      else:
        print("--- Daftar Pengeluaran ---")
        for x in list_pengeluaran:
            print(f"Kategori: {x['Kategori']} | Jumlah: Rp {x['Jumlah']}")
      print("\nTekan Enter untuk kembali ke menu")
      input()
    case 3:
      total = 0
      for x in list_pengeluaran:
        total += int(x["Jumlah"])
      print(total)
      print("Tekan tombol Enter untuk kembali ke menu")
      s = input()
    case 4:
      print("Keluar")
      finish = True
    case _:
      print("Masukkan angka yang tersedia !")
      print("Tekan tombol Enter untuk kembali ke menu")
      s = input()