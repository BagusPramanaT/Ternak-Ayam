import psycopg2
from tabulate import tabulate
import getpass
import os
import questionary
import shutil

def clear_screen():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def get_connection():
    try:
        return psycopg2.connect( host="localhost", database=" ", user="postgres", password=" ", port=" ")
    except Exception as e:
        print("Koneksi gagal:", e)
        return None

def get_terminal_width():
    try:
        columns, _ = shutil.get_terminal_size()
        return columns
    except:
        return 80 

def print_table_auto(data, headers):
    if not data:
        print("Tidak ada data untuk ditampilkan")
        return
    
    terminal_width = get_terminal_width()
    num_columns = len(headers)
    
    max_widths = []
    for i in range(num_columns):
        col_data = [str(row[i]) for row in data]
        col_data.append(headers[i])
    
        max_content = max(len(str(x)) for x in col_data)
        
        max_widths.append(min(max_content + 2, 30))
    
    total_width = sum(max_widths) + (num_columns * 3) + 1  
    
    if total_width > terminal_width:
        excess = total_width - terminal_width
        for i in sorted(range(len(max_widths)), key=lambda i: -max_widths[i]):
            if max_widths[i] > 15: 
                reduce_by = min(excess, max_widths[i] - 15)
                max_widths[i] -= reduce_by
                excess -= reduce_by
                if excess <= 0:
                    break
    
    print(tabulate(data, headers=headers, tablefmt="grid", 
                  maxcolwidths=max_widths, stralign="left"))

def print_centered(text):
    width = get_terminal_width()
    print(text.center(width))

def print_line(char='='):
    width = get_terminal_width()
    print(char * width)

def validate_password(password):
    if len(password) < 5:
        return False, "Password harus terdiri dari minimal 5 karakter"
    return True, ""

def get_kecamatan_options():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT k.id_kecamatan, k.nama_kecamatan, kb.nama_kabupaten 
            FROM kecamatan k 
            JOIN kabupaten kb ON k.id_kabupaten = kb.id_kabupaten
            ORDER BY k.nama_kecamatan""")
        kecamatan_data = cursor.fetchall()
        
        options = []
        for kec in kecamatan_data:
            options.append({
                'name': f"{kec[1]} ({kec[2]})",
                'value': kec[0] })
        
        cursor.close()
        conn.close()
        return options
        
    except Exception as e:
        print("Error mengambil data kecamatan:", e)
        return []

def register():
    clear_screen()
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print_line()
        print_centered("Register Pelanggan Baru")
        print_line()
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            print(f"\nError: {error_msg}")
            input("Tekan Enter untuk melanjutkan...")
            clear_screen()
            return
        
        cursor.execute(
            "INSERT INTO akun (username, password) VALUES (%s, %s) RETURNING id_akun",
            (username, password))
        id_akun = cursor.fetchone()[0]
        
        clear_screen()
        print_line()
        print_centered("Data Pelanggan")
        print_line()
        nama_pelanggan = input("Nama Lengkap: ")
        no_telp = input("No telepon: ")
        
        kecamatan_options = get_kecamatan_options()
        if not kecamatan_options:
            print("Error: Tidak bisa mengambil data kecamatan!")
            return
        
        selected_kecamatan = questionary.select(
            "Pilih Kecamatan:",
            choices=[option['name'] for option in kecamatan_options]).ask()
        
        id_kecamatan = None
        for option in kecamatan_options:
            if option['name'] == selected_kecamatan:
                id_kecamatan = option['value']
                break
        
        if not id_kecamatan:
            print("Error: Kecamatan tidak valid!")
            return
        
        jalan = input("\nAlamat (jalan/gang/nomor): ")
        
        cursor.execute(
            "INSERT INTO pelanggan (nama_pelanggan, no_telp, jalan, id_akun, id_kecamatan) VALUES (%s, %s, %s, %s, %s)",
            (nama_pelanggan, no_telp, jalan, id_akun, id_kecamatan))
        
        conn.commit()
        print(f"\nAkun pelanggan {username} berhasil dibuat!")
        print(f"Lokasi: {selected_kecamatan}")
        
        cursor.close()
        conn.close()
        input("\nTekan Enter untuk melanjutkan...")
        clear_screen()
        
    except psycopg2.IntegrityError:
        print("Username sudah digunakan!")
        input("Tekan Enter untuk melanjutkan...")
        clear_screen()
    except Exception as e:
        print("Error:", e)
        input("Tekan Enter untuk melanjutkan...")
        clear_screen()

def login():
    clear_screen()
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        print_line()
        print_centered("Login")
        print_line()
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        
        cursor.execute(
            "SELECT id_akun, username FROM akun WHERE username = %s AND password = %s",
            (username, password))
        user = cursor.fetchone()
        
        if not user:
            print("\nUsername atau password salah!")
            cursor.close()
            conn.close()
            input("\nTekan Enter untuk melanjutkan...")
            clear_screen()
            return None
        
        user_data = {
            "id_akun": user[0],
            "username": user[1]}
        
        cursor.execute("SELECT id_admin FROM admin WHERE id_akun = %s", (user[0],))
        if cursor.fetchone():
            user_data["tipe"] = "admin"
            print(f"\nLogin berhasil! Selamat datang {user[1]}")
        
        else:
            cursor.execute("""
                SELECT k.id_karyawan, tk.nama_tugas_karyawan 
                FROM karyawan k
                JOIN tugas_karyawan tk ON k.id_tugas = tk.id_tugas
                WHERE k.id_akun = %s
            """, (user[0],))
            
            karyawan_data = cursor.fetchone()
            if karyawan_data:
                user_data["tipe"] = "karyawan"
                user_data["id_karyawan"] = karyawan_data[0]
                user_data["tugas"] = karyawan_data[1]
                print(f"\nLogin berhasil! Selamat datang {user[1]}")
                print(f"Tugas: {karyawan_data[1]}")
            
            else:
                cursor.execute("SELECT id_pelanggan FROM pelanggan WHERE id_akun = %s", (user[0],))
                pelanggan_result = cursor.fetchone()
                if pelanggan_result:
                    user_data["tipe"] = "pelanggan"
                    user_data["id_pelanggan"] = pelanggan_result[0]
                    print(f"\nLogin berhasil! Selamat datang {user[1]}")
                else:
                    print("\nAkun tidak memiliki akses!")
                    cursor.close()
                    conn.close()
                    input("\nTekan Enter untuk melanjutkan...")
                    clear_screen()
        
        cursor.close()
        conn.close()
        
        input("\nTekan Enter untuk melanjutkan...")
        clear_screen()
        return user_data
            
    except Exception as e:
        print("Error:", e)
        input("\nTekan Enter untuk melanjutkan...")
        clear_screen()
        return None

def kelola_akun():
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        while True:
            clear_screen()
            print_line()
            print_centered("Kelola Akun")
            print_line()
            cursor.execute("SELECT id_akun, username FROM akun ORDER BY id_akun")
            accounts = cursor.fetchall()
            
            if not accounts:
                print("Tidak ada akun!")
                break
            
            print("\nDaftar Akun:")
            print_table_auto(accounts, ["ID", "Username"])
            print("\nPilihan:")
            print("1. Edit Akun")
            print("2. Hapus Akun")
            print("3. Kembali")
            choice = input("\nPilihan (1-3): ")
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("Edit Akun")
                print_line()
                
                account_id = input("ID akun yang akan diedit: ")
                
                cursor.execute("SELECT username FROM akun WHERE id_akun = %s", (account_id,))
                akun_data = cursor.fetchone()
                
                if not akun_data:
                    print("Akun tidak ditemukan!")
                    continue
                
                print(f"\nMengedit akun: {akun_data[0]}")
                print("\nPilih yang akan diedit:")
                print("1. Username")
                print("2. Password")
                edit_choice = input("Pilihan (1/2): ")
                
                if edit_choice == "1":
                    new_username = input("Username baru: ")
                    cursor.execute(
                        "UPDATE akun SET username = %s WHERE id_akun = %s",
                        (new_username, account_id))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        print("\nUsername berhasil diupdate!")
                    else:
                        print("\nGagal mengupdate username!")
                        
                elif edit_choice == "2":
                    new_password = getpass.getpass("Password baru: ")
                    is_valid, error_msg = validate_password(new_password)
                    if not is_valid:
                        print(f"\nError: {error_msg}")
                        input("Tekan Enter untuk melanjutkan...")
                        continue
                    cursor.execute(
                        "UPDATE akun SET password = %s WHERE id_akun = %s",
                        (new_password, account_id))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        print("\nPassword berhasil diupdate!")
                    else:
                        print("\nGagal mengupdate password!")
                else:
                    print("\nPilihan tidak valid!")
                
            elif choice == "2":
                
                clear_screen()
                print_line()
                print_centered("Hapus Akun")
                print_line()
                account_id = input("ID akun yang akan dihapus: ")
                
                if account_id in ["1", "2"]:
                    print("\nTidak bisa menghapus akun admin sendiri!")
                    continue
                
                cursor.execute("SELECT id_akun FROM akun WHERE id_akun = %s", (account_id,))
                if not cursor.fetchone():
                    print("\nAkun tidak ditemukan!")
                    input("Tekan Enter untuk melanjutkan...")
                    continue

                konfirmasi = input("Yakin ingin menghapus akun ini? (y/n): ").lower()
                if konfirmasi == 'y':
                    cursor.execute("DELETE FROM pelanggan WHERE id_akun = %s", (account_id,))
                    cursor.execute("DELETE FROM karyawan WHERE id_akun = %s", (account_id,))
                    cursor.execute("DELETE FROM akun WHERE id_akun = %s", (account_id,))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        print("\nAkun berhasil dihapus!")
                    else:
                        print("\nAkun tidak ditemukan!")
                else:
                    print("\nPenghapusan dibatalkan!")
                
            elif choice == "3":
                break
            else:
                print("\nPilihan tidak valid!")
                
    except Exception as e:
        print("Error:", e)
    finally:
        cursor.close()
        conn.close()

def lihat_data_pelanggan():
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        while True:
            clear_screen()
            print_line()
            print_centered("Data Pelanggan")
            print_line()
            
            cursor.execute("""
                SELECT p.id_pelanggan, p.nama_pelanggan, p.no_telp, p.jalan, 
                       k.nama_kecamatan, kb.nama_kabupaten, a.username
                FROM pelanggan p
                JOIN kecamatan k ON p.id_kecamatan = k.id_kecamatan
                JOIN kabupaten kb ON k.id_kabupaten = kb.id_kabupaten
                JOIN akun a ON p.id_akun = a.id_akun
                ORDER BY p.id_pelanggan""")
            pelanggan_data = cursor.fetchall()
            
            if pelanggan_data:
                print("\nDaftar Pelanggan:")
                headers = ["ID", "Nama", "No Telp", "Alamat", "Kecamatan", "Kabupaten", "Username"]
                print_table_auto(pelanggan_data, headers)
            else:
                print("Tidak ada data pelanggan!")
            
            print("\n1. Edit Data Pelanggan")
            print("2. Kembali")
            choice = input("\nPilihan (1-2): ")
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("Edit Data Pelanggan")
                print_line()
                
                pelanggan_id = input("ID pelanggan yang akan diedit: ")
                
                cursor.execute("SELECT id_pelanggan FROM pelanggan WHERE id_pelanggan = %s", (pelanggan_id,))
                if not cursor.fetchone():
                    print("Pelanggan tidak ditemukan!")
                    continue
                
                print("\nData yang bisa diedit:")
                print("1. Nama Pelanggan")
                print("2. No Telepon")
                print("3. Alamat (jalan)")
                print("4. Kecamatan")
                edit_choice = input("Pilihan (1-4): ")
                
                if edit_choice == "1":
                    new_nama = input("Nama baru: ")
                    cursor.execute(
                        "UPDATE pelanggan SET nama_pelanggan = %s WHERE id_pelanggan = %s",
                        (new_nama, pelanggan_id))
                    
                elif edit_choice == "2":
                    new_telp = input("No telepon baru: ")
                    cursor.execute(
                        "UPDATE pelanggan SET no_telp = %s WHERE id_pelanggan = %s",
                        (new_telp, pelanggan_id))
                    
                elif edit_choice == "3":
                    new_jalan = input("Alamat jalan baru: ")
                    cursor.execute(
                        "UPDATE pelanggan SET jalan = %s WHERE id_pelanggan = %s",
                        (new_jalan, pelanggan_id))
                    
                elif edit_choice == "4":
                    kecamatan_options = get_kecamatan_options()
                    if kecamatan_options:
                        selected_kecamatan = questionary.select(
                            "Pilih Kecamatan baru:",
                            choices=[option['name'] for option in kecamatan_options]).ask()
                        
                        id_kecamatan = None
                        for option in kecamatan_options:
                            if option['name'] == selected_kecamatan:
                                id_kecamatan = option['value']
                                break
                        
                        if id_kecamatan:
                            cursor.execute(
                                "UPDATE pelanggan SET id_kecamatan = %s WHERE id_pelanggan = %s",
                                (id_kecamatan, pelanggan_id))
                        else:
                            print("Kecamatan tidak valid!")
                            continue
                    else:
                        print("Tidak bisa mengambil data kecamatan!")
                        continue
                else:
                    print("Pilihan tidak valid!")
                    continue
                
                conn.commit()
                print("\nData pelanggan berhasil diupdate!")
                
            elif choice == "2":
                break
            else:
                print("Pilihan tidak valid!")
                
    except Exception as e:
        print("Error:", e)
    finally:
        cursor.close()
        conn.close()

def lihat_data_karyawan():
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        while True:
            clear_screen()
            print_line()
            print_centered("Data Karyawan")
            print_line()
            
            cursor.execute("""
                SELECT k.id_karyawan, k.nama_karyawan, k.no_telp, 
                       CASE WHEN k.status_karyawan THEN 'Aktif' ELSE 'Tidak Aktif' END as status,
                       k.id_tugas, a.username
                FROM karyawan k
                JOIN akun a ON k.id_akun = a.id_akun
                ORDER BY k.id_karyawan""")
            
            karyawan_data = cursor.fetchall()
            
            if karyawan_data:
                print("\nDaftar Karyawan:")
                headers = ["ID", "Nama", "No Telp", "Status", "ID Tugas", "Username"]
                print_table_auto(karyawan_data, headers)
            else:
                print("Tidak ada data karyawan!")
            
            print("\n1. Edit Data Karyawan")
            print("2. Kembali")
            
            choice = input("\nPilihan (1-2): ")
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("Edit Data Karyawan")
                print_line()
                karyawan_id = input("ID karyawan yang akan diedit: ")
                
                cursor.execute("SELECT id_karyawan FROM karyawan WHERE id_karyawan = %s", (karyawan_id,))
                if not cursor.fetchone():
                    print("Karyawan tidak ditemukan!")
                    continue
                
                print("\nData yang bisa diedit:")
                print("1. Nama Karyawan")
                print("2. No Telepon")
                print("3. Status Karyawan")
                print("4. Tugas (ID Tugas)")
                edit_choice = input("Pilihan (1-4): ")
                
                if edit_choice == "1":
                    new_nama = input("Nama baru: ")
                    cursor.execute(
                        "UPDATE karyawan SET nama_karyawan = %s WHERE id_karyawan = %s",
                        (new_nama, karyawan_id))
                    
                elif edit_choice == "2":
                    new_telp = input("No telepon baru: ")
                    cursor.execute(
                        "UPDATE karyawan SET no_telp = %s WHERE id_karyawan = %s",
                        (new_telp, karyawan_id))
                    
                elif edit_choice == "3":
                    print("\nStatus Karyawan:")
                    print("1. Aktif")
                    print("2. Tidak Aktif")
                    status_choice = input("Pilihan (1-2): ")
                    new_status = (status_choice == "1")
                    
                    cursor.execute(
                        "UPDATE karyawan SET status_karyawan = %s WHERE id_karyawan = %s",
                        (new_status, karyawan_id))
                    
                elif edit_choice == "4":
                    new_tugas = input("ID tugas baru: ")
                    cursor.execute(
                        "UPDATE karyawan SET id_tugas = %s WHERE id_karyawan = %s",
                        (new_tugas, karyawan_id))
                    
                else:
                    print("Pilihan tidak valid!")
                    continue
                
                conn.commit()
                print("\nData karyawan berhasil diupdate!")
                
            elif choice == "2":
                break
            else:
                print("Pilihan tidak valid!")
                
    except Exception as e:
        print("Error:", e)
    finally:
        cursor.close()
        conn.close()

def lihat_data_akun():
    while True:
        clear_screen()
        print_line()
        print_centered("Lihat Data Akun")
        print_line()
        print("1. Lihat Data Pelanggan")
        print("2. Lihat Data Karyawan")
        print("3. Kembali")
        choice = input("\nPilihan (1-3): ")
        
        if choice == "1":
            lihat_data_pelanggan()
        elif choice == "2":
            lihat_data_karyawan()
        elif choice == "3":
            break
        else:
            print("Pilihan tidak valid!")

def restock_pakan():
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        clear_screen()
        print_line()
        print_centered("Restock Pakan")
        print_line()
        
        cursor.execute("SELECT * FROM pakan")
        pakan_data = cursor.fetchall()
        
        if pakan_data:
            print("\nStok saat ini:")
            print_table_auto(pakan_data, ["ID", "Jumlah", "Nama Pakan"])
            
            pakan_id = input("\nID pakan yang akan di-restock: ")
            tambahan_stok = int(input("Jumlah stok yang ditambahkan (kg): "))
            
            cursor.execute(
                "UPDATE pakan SET jumlah_stok = jumlah_stok + %s WHERE id_pakan = %s",
                (tambahan_stok, pakan_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                print("\nStok berhasil ditambahkan!")
            else:
                print("\nID pakan tidak ditemukan!")
        else:
            print("Data pakan kosong!")
        input("\nTekan Enter untuk melanjutkan...")
        
    except Exception:
        print("Error: Tidak Boleh Kosong Tolong Inputkan dengan Benar")
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def tambah_akun_karyawan():
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        clear_screen()
        print_line()
        print_centered("Tambah Akun Karyawan")
        print_line()
        
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            print(f"\nError: {error_msg}")
            input("Tekan Enter untuk melanjutkan...")
            clear_screen()
            return
        
        cursor.execute(
            "INSERT INTO akun (username, password) VALUES (%s, %s) RETURNING id_akun",
            (username, password))
        id_akun = cursor.fetchone()[0]
        
        print("\nData Karyawan")
        nama_karyawan = input("Nama karyawan: ")
        no_telp = input("No telepon: ")
        status_karyawan = True
        id_tugas = input("ID tugas: ")
        
        cursor.execute(
            "INSERT INTO karyawan (nama_karyawan, no_telp, status_karyawan, id_akun, id_tugas) VALUES (%s, %s, %s, %s, %s)",
            (nama_karyawan, no_telp, status_karyawan, id_akun, id_tugas))
        
        conn.commit()
        print(f"\nAkun karyawan {username} berhasil dibuat!")
        input("\nTekan Enter untuk melanjutkan...")
        
    except psycopg2.IntegrityError:
        print("Username sudah digunakan!")
        input("Tekan Enter untuk melanjutkan...")
    except Exception as e:
        print("Error:", e)
        input("Tekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def menu_admin(user_data):
    while True:
        clear_screen()
        print_line()
        print_centered("Menu Admin")
        print_line()
        print("1. Kelola Akun")
        print("2. Lihat Data Akun")
        print("3. Restock Pakan")
        print("4. Tambah Akun Karyawan")
        print("5. Logout")
        choice = input("\nPilihan (1-5): ")
        
        if choice == "1":
            kelola_akun()
        elif choice == "2":
            lihat_data_akun()
        elif choice == "3":
            restock_pakan()
        elif choice == "4":
            tambah_akun_karyawan()
        elif choice == "5":
            print("\nLogout dari admin...")
            input("Tekan Enter untuk melanjutkan...")
            clear_screen()
            break
        else:
            print("\nPilihan tidak valid!")

def get_kandang_options():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT k.id_kandang, k.kapasitas, p.nama_pakan, ja.nama_jenis_ayam
            FROM kandang k 
            JOIN pakan p ON k.id_pakan = p.id_pakan
            JOIN jenis_ayam ja ON k.id_jenis = ja.id_jenis
            ORDER BY k.id_kandang
        """)
        kandang_data = cursor.fetchall()
        
        options = []
        for kandang in kandang_data:
            options.append({
                'id': kandang[0],
                'kapasitas': kandang[1],
                'pakan': kandang[2],
                'jenis_ayam': kandang[3]
            })
        
        cursor.close()
        conn.close()
        return options
        
    except Exception as e:
        print("Error mengambil data kandang:", e)
        return []

def get_pakan_options():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_pakan, nama_pakan, jumlah_stok FROM pakan ORDER BY id_pakan")
        pakan_data = cursor.fetchall()
        
        options = []
        for pakan in pakan_data:
            options.append({
                'id': pakan[0],
                'nama': pakan[1],
                'stok': pakan[2]
            })
        
        cursor.close()
        conn.close()
        return options
        
    except Exception as e:
        print("Error mengambil data pakan:", e)
        return []

def get_produk_options():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_produk, nama_produk, stok_produk, harga_produk FROM produk ORDER BY id_produk")
        produk_data = cursor.fetchall()
        
        options = []
        for produk in produk_data:
            options.append({
                'id': produk[0],
                'nama': produk[1],
                'stok': produk[2],
                'harga': produk[3]
            })
        
        cursor.close()
        conn.close()
        return options
        
    except Exception as e:
        print("Error mengambil data produk:", e)
        return []

def menu_penjaga_kandang(user_data):
    while True:
        clear_screen()
        print_line()
        print_centered(f"Menu Penjaga Kandang - {user_data['username']}")
        print_line()
        print("1. Kelola Pakan Kandang")
        print("2. Input Hasil Panen")
        print("3. Lihat Laporan")
        print("4. Logout")
        pilihan = input("\nPilihan (1-4): ")
        
        if pilihan == "1":
            kelola_pakan_kandang()
        elif pilihan == "2":
            input_hasil_panen()
        elif pilihan == "3":
            lihat_laporan_kandang()
        elif pilihan == "4":
            print("\nLogout dari penjaga kandang...")
            input("Tekan Enter untuk melanjutkan...")
            clear_screen()
            break
        else:
            print("\nPilihan tidak valid!")

def kelola_pakan_kandang():
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        while True:
            clear_screen()
            print_line()
            print_centered("Kelola Pakan Kandang")
            print_line()
            
            cursor.execute("SELECT id_pakan, nama_pakan, jumlah_stok FROM pakan ORDER BY id_pakan")
            pakan_data = cursor.fetchall()
            
            print("\nStock Pakan Tersedia:")
            if pakan_data:
                headers = ["ID", "Nama Pakan", "Stok (kg)"]
                print(tabulate(pakan_data, headers=headers, tablefmt="grid"))
            else:
                print("Tidak ada data pakan!")
            
            kandang_options = get_kandang_options()
            if kandang_options:
                print("\nData Kandang:")
                kandang_table = []
                for kandang in kandang_options:
                    kandang_table.append([
                        kandang['id'],
                        kandang['kapasitas'],
                        kandang['jenis_ayam'],
                        kandang['pakan']
                    ])
                print(tabulate(kandang_table, headers=["ID", "Kapasitas", "Jenis Ayam", "Pakan Saat Ini"], tablefmt="grid"))
            
            print("\n1. Ganti Pakan Kandang")
            print("2. Kembali")
            choice = input("\nPilihan (1-2): ")
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("Ganti Pakan Kandang")
                print_line()
                
                if not kandang_options:
                    print("Tidak ada data kandang!")
                    continue
                
                kandang_list = [f"{k['id']}. Kapasitas: {k['kapasitas']} - {k['jenis_ayam']} (Pakan: {k['pakan']})" for k in kandang_options]
                print("Pilih Kandang:")
                for kandang in kandang_list:
                    print(f"  {kandang}")
                
                kandang_id = input("\nID kandang: ")
                
                kandang_valid = False
                for kandang in kandang_options:
                    if str(kandang['id']) == kandang_id:
                        kandang_valid = True
                        kandang_data = kandang
                        break
                
                if not kandang_valid:
                    print("Kandang tidak valid!")
                    continue
                
                pakan_options = get_pakan_options()
                if not pakan_options:
                    print("Tidak ada data pakan!")
                    continue
                
                pakan_list = [f"{p['id']}. {p['nama']} (Stok: {p['stok']} kg)" for p in pakan_options]
                print("\nPilih Pakan Baru:")
                for pakan in pakan_list:
                    print(f"  {pakan}")
                
                pakan_id = input("\nID pakan: ")
                
                pakan_valid = False
                for pakan in pakan_options:
                    if str(pakan['id']) == pakan_id:
                        pakan_valid = True
                        pakan_nama = pakan['nama']
                        break
                
                if not pakan_valid:
                    print("Pakan tidak valid!")
                    continue
                
                konfirmasi = input(f"\nYakin ganti pakan kandang {kandang_id} dari {kandang_data['pakan']} ke {pakan_nama}? (y/n): ").lower()
                
                if konfirmasi == 'y':
                    cursor.execute("UPDATE kandang SET id_pakan = %s WHERE id_kandang = %s",
                        (pakan_id, kandang_id))
                    
                    conn.commit()
                    print(f"\nBerhasil mengganti pakan kandang {kandang_id} ke {pakan_nama}!")
                else:
                    print("Perubahan dibatalkan!")
                
                input("\nTekan Enter untuk melanjutkan...")
                
            elif choice == "2":
                break
            else:
                print("Pilihan tidak valid!")
                
    except Exception as e:
        print("Error:", e)
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def input_hasil_panen():
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        clear_screen()
        print_line()
        print_centered("Input Hasil Panen")
        print_line()
        
        produk_options = get_produk_options()
        if not produk_options:
            print("Tidak ada data produk!")
            input("\nTekan Enter untuk melanjutkan...")
            return
        
        print("\nProduk yang Tersedia:")
        produk_table = []
        for produk in produk_options:
            produk_table.append([
                produk['id'],
                produk['nama'],
                produk['stok'],
                f"Rp {produk['harga']:,}"
            ])
        print(tabulate(produk_table, headers=["ID", "Nama Produk", "Stok", "Harga"], tablefmt="grid"))
        
        kandang_options = get_kandang_options()
        if not kandang_options:
            print("Tidak ada data kandang!")
            input("\nTekan Enter untuk melanjutkan...")
            return
        
        print("\nKandang:")
        kandang_table = []
        for kandang in kandang_options:
            kandang_table.append([
                kandang['id'],
                kandang['kapasitas'],
                kandang['jenis_ayam']
            ])
        print(tabulate(kandang_table, headers=["ID", "Kapasitas", "Jenis Ayam"], tablefmt="grid"))
        
        print("\nInput Data Panen:")
        
        produk_list = [f"{p['id']}. {p['nama']}" for p in produk_options]
        print("Pilih Produk:")
        for produk in produk_list:
            print(f"  {produk}")
        
        produk_id = input("\nPilih Salah Satu: ")
        
        produk_valid = False
        for produk in produk_options:
            if str(produk['id']) == produk_id:
                produk_valid = True
                produk_nama = produk['nama']
                break
        
        if not produk_valid:
            print("Produk tidak valid!")
            input("\nTekan Enter untuk melanjutkan...")
            return
        
        kandang_list = [f"{k['id']}. {k['jenis_ayam']}" for k in kandang_options]
        print("\nPilih Kandang:")
        for kandang in kandang_list:
            print(f"  {kandang}")
        
        kandang_id = input("ID kandang: ")
        
        kandang_valid = False
        for kandang in kandang_options:
            if str(kandang['id']) == kandang_id:
                kandang_valid = True
                break
        
        if not kandang_valid:
            print("Kandang tidak valid!")
            input("\nTekan Enter untuk melanjutkan...")
            return
        
        try:
            tanggal_panen = input("Tanggal panen (YYYY-MM-DD): ")
            kuantitas = int(input("Kuantitas hasil panen: "))
            
            if kuantitas <= 0:
                print("Kuantitas harus lebih dari 0!")
                input("\nTekan Enter untuk melanjutkan...")
                return
            
            cursor.execute(
                "INSERT INTO panen (tanggal_panen, id_kandang) VALUES (%s, %s) RETURNING id_panen",
                (tanggal_panen, kandang_id))
            id_panen = cursor.fetchone()[0]
            
            cursor.execute(
                "INSERT INTO detail_panen (kuantitas, id_panen, id_produk) VALUES (%s, %s, %s)",
                (kuantitas, id_panen, produk_id))
            
            cursor.execute(
                "UPDATE produk SET stok_produk = stok_produk + %s WHERE id_produk = %s",
                (kuantitas, produk_id))
            
            conn.commit()
            
            cursor.execute("SELECT stok_produk FROM produk WHERE id_produk = %s", (produk_id,))
            stok_baru = cursor.fetchone()[0]
            
            print(f"\nBerhasil menambahkan {kuantitas} hasil panen {produk_nama}!")
            print(f"Stok {produk_nama} sekarang: {stok_baru}")
            
        except ValueError:
            print("Input kuantitas harus angka!")
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()
        
        input("\nTekan Enter untuk melanjutkan...")
                
    except Exception as e:
        print("Error:", e)
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def lihat_laporan_kandang():
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        clear_screen()
        print_line()
        print_centered("Laporan Kandang")
        print_line()
        
        cursor.execute("""
            SELECT k.id_kandang, k.kapasitas, ja.nama_jenis_ayam, p.nama_pakan, p.jumlah_stok
            FROM kandang k
            JOIN jenis_ayam ja ON k.id_jenis = ja.id_jenis
            JOIN pakan p ON k.id_pakan = p.id_pakan
            ORDER BY k.id_kandang
        """)
        kandang_data = cursor.fetchall()
        
        if kandang_data:
            print("\nData Kandang:")
            headers = ["ID", "Kapasitas", "Jenis Ayam", "Pakan", "Stok Pakan"]
            print(tabulate(kandang_data, headers=headers, tablefmt="grid"))
        else:
            print("Tidak ada data kandang!")
        
        cursor.execute("SELECT nama_produk, stok_produk, harga_produk FROM produk ORDER BY nama_produk")
        produk_data = cursor.fetchall()
        
        if produk_data:
            print("\nData Produk:")
            headers = ["Produk", "Stok", "Harga"]
            print(tabulate(produk_data, headers=headers, tablefmt="grid"))
        
        cursor.execute("""
            SELECT p.tanggal_panen, k.id_kandang, ja.nama_jenis_ayam, pr.nama_produk, dp.kuantitas
            FROM panen p
            JOIN kandang k ON p.id_kandang = k.id_kandang
            JOIN jenis_ayam ja ON k.id_jenis = ja.id_jenis
            JOIN detail_panen dp ON p.id_panen = dp.id_panen
            JOIN produk pr ON dp.id_produk = pr.id_produk
            ORDER BY p.tanggal_panen DESC
            LIMIT 5
        """)
        panen_data = cursor.fetchall()
        
        if panen_data:
            print("\n5 Panen Terbaru:")
            headers = ["Tanggal", "Kandang", "Jenis Ayam", "Produk", "Kuantitas"]
            print(tabulate(panen_data, headers=headers, tablefmt="grid"))
        
        input("\nTekan Enter untuk melanjutkan...")
                
    except Exception as e:
        print("Error:", e)
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def get_pemesanan_pending():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                pm.id_pemesanan,
                pm.tanggal_pemesanan,
                plg.nama_pelanggan,
                plg.no_telp,
                kc.nama_kecamatan,
                kb.nama_kabupaten,
                t.metode_pembayaran,
                dp.jumlah_produk,
                pr.nama_produk,
                pr.harga_produk,
                (dp.jumlah_produk * pr.harga_produk) as total_harga
            FROM pemesanan pm
            JOIN pelanggan plg ON pm.id_pelanggan = plg.id_pelanggan
            JOIN kecamatan kc ON plg.id_kecamatan = kc.id_kecamatan
            JOIN kabupaten kb ON kc.id_kabupaten = kb.id_kabupaten
            JOIN transaksi t ON pm.id_transaksi = t.id_transaksi
            JOIN detail_pemesanan dp ON pm.id_pemesanan = dp.id_pemesanan
            JOIN produk pr ON dp.id_produk = pr.id_produk
            WHERE pm.status_pemesanan = false  -- HANYA YANG BELUM DISETUJUI
            ORDER BY pm.tanggal_pemesanan
        """)
        pemesanan_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return pemesanan_data
        
    except Exception as e:
        print("Error mengambil data pemesanan:", e)
        return []

def get_all_produk():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_produk, nama_produk, stok_produk, harga_produk FROM produk ORDER BY id_produk")
        produk_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return produk_data
        
    except Exception as e:
        print("Error mengambil data produk:", e)
        return []

def menu_kasir(user_data):
    while True:
        clear_screen()
        print_line()
        print_centered(f"Menu Kasir - {user_data['username']}")
        print_line()
        print("1. Setujui Pemesanan Pelanggan")
        print("2. Ubah Harga Produk")
        print("3. Logout")
        pilihan = input("\nPilihan (1-3): ")
        
        if pilihan == "1":
            setujui_pemesanan(user_data)
        elif pilihan == "2":
            ubah_harga_produk(user_data)
        elif pilihan == "3":
            print("\nLogout dari kasir...")
            input("Tekan Enter untuk melanjutkan...")
            clear_screen()
            break
        else:
            print("\nPilihan tidak valid!")

def setujui_pemesanan(user_data):
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        while True:
            clear_screen()
            print_line()
            print_centered("Setujui Pemesanan Pelanggan")
            print_line()
            
            pemesanan_pending = get_pemesanan_pending()
            
            if not pemesanan_pending:
                print("\nTidak ada pemesanan yang perlu disetujui!")
                input("\nTekan Enter untuk melanjutkan...")
                break
            
            print("\nDaftar Pemesanan Pending:")
            headers = ["ID", "Tanggal", "Pelanggan", "Telp", "Kecamatan", "Kabupaten", "Pembayaran", "Jumlah", "Produk", "Harga/Unit", "Total"]
            print(tabulate(pemesanan_pending, headers=headers, tablefmt="grid"))
            
            print("\n1. Setujui Pemesanan")
            print("2. Tolak Pemesanan")
            print("3. Kembali")
            
            choice = input("\nPilihan (1-3): ")
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("Setujui Pemesanan")
                print_line()
                
                pemesanan_id = input("ID pemesanan yang akan disetujui: ")
                
                cursor.execute("SELECT id_pemesanan FROM pemesanan WHERE id_pemesanan = %s AND status_pemesanan = false", (pemesanan_id,))
                if not cursor.fetchone():
                    print("Pemesanan tidak ditemukan atau sudah diproses!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                cursor.execute("""
                    SELECT dp.id_produk, pr.nama_produk, dp.jumlah_produk, pr.stok_produk
                    FROM detail_pemesanan dp
                    JOIN produk pr ON dp.id_produk = pr.id_produk
                    WHERE dp.id_pemesanan = %s
                """, (pemesanan_id,))
                detail_pemesanan = cursor.fetchall()
                stok_cukup = True
                for detail in detail_pemesanan:
                    id_produk, nama_produk, jumlah_pesan, stok_tersedia = detail
                    if jumlah_pesan > stok_tersedia:
                        stok_cukup = False
                        print(f"Stok {nama_produk} tidak cukup! (Pesan: {jumlah_pesan}, Tersedia: {stok_tersedia})")
                
                if not stok_cukup:
                    print("Tidak bisa menyetujui pemesanan karena stok tidak mencukupi!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                cursor.execute("""
                    UPDATE pemesanan 
                    SET status_pemesanan = true 
                    WHERE id_pemesanan = %s
                """, (pemesanan_id,))
                
                
                for detail in detail_pemesanan:
                    id_produk, nama_produk, jumlah_pesan, stok_tersedia = detail
                    cursor.execute("""
                        UPDATE produk 
                        SET stok_produk = stok_produk - %s 
                        WHERE id_produk = %s
                    """, (jumlah_pesan, id_produk))
                
                conn.commit()
                print(f"\nPemesanan ID {pemesanan_id} berhasil disetujui!")
                print("Stok produk telah diperbarui!")
                input("\nTekan Enter untuk melanjutkan...")
                
            elif choice == "2":
                clear_screen()
                print_line()
                print_centered("Tolak Pemesanan")
                print_line()
                pemesanan_id = input("ID pemesanan yang akan ditolak: ")
                cursor.execute("SELECT id_pemesanan FROM pemesanan WHERE id_pemesanan = %s AND status_pemesanan = false", (pemesanan_id,))
                if not cursor.fetchone():
                    print("Pemesanan tidak ditemukan atau sudah diproses!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                cursor.execute("DELETE FROM pemesanan WHERE id_pemesanan = %s", (pemesanan_id,))
                conn.commit()
                print(f"\nPemesanan ID {pemesanan_id} berhasil ditolak dan dihapus!")
                input("\nTekan Enter untuk melanjutkan...")
            elif choice == "3":
                break
            else:
                print("Pilihan tidak valid!")

    except Exception as e:
        print("Error:", e)
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def ubah_harga_produk(user_data):
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        while True:
            clear_screen()
            print_line()
            print_centered("Ubah Harga Produk")
            print_line()
            
            produk_data = get_all_produk()
            if not produk_data:
                print("Tidak ada data produk!")
                input("\nTekan Enter untuk melanjutkan...")
                break
            
            print("\nDaftar Produk:")
            headers = ["ID", "Nama Produk", "Stok", "Harga Saat Ini"]
            print(tabulate(produk_data, headers=headers, tablefmt="grid"))
            
            print("\n1. Ubah Harga Produk")
            print("2. Kembali")
            
            choice = input("\nPilihan (1-2): ")
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("Ubah Harga Produk")
                print_line()
                produk_id = input("ID produk yang akan diubah harganya: ")
                cursor.execute("SELECT id_produk, nama_produk, harga_produk FROM produk WHERE id_produk = %s", (produk_id,))
                produk = cursor.fetchone()
                if not produk:
                    print("Produk tidak ditemukan!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                id_produk, nama_produk, harga_lama = produk
                print(f"\nProduk: {nama_produk}")
                print(f"Harga saat ini: Rp {harga_lama:,}")
                
                try:
                    harga_baru = int(input("\nHarga baru: Rp "))
                    if harga_baru <= 0:
                        print("Harga harus lebih dari 0!")
                        input("\nTekan Enter untuk melanjutkan...")
                        continue
                    
                    konfirmasi = input(f"\nYakin ubah harga {nama_produk} dari Rp {harga_lama:,} menjadi Rp {harga_baru:,}? (y/n): ").lower()
                    if konfirmasi == 'y':
                        cursor.execute(
                            "UPDATE produk SET harga_produk = %s WHERE id_produk = %s",
                            (harga_baru, produk_id)
                        )
                        conn.commit()
                        print(f"\nHarga {nama_produk} berhasil diubah menjadi Rp {harga_baru:,}!")
                    else:
                        print("Perubahan dibatalkan!")
                except ValueError:
                    print("Input harga harus angka!")
                
                input("\nTekan Enter untuk melanjutkan...")
                
            elif choice == "2":
                break
            else:
                print("Pilihan tidak valid!")
                
    except Exception as e:
        print("Error:", e)
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def get_pemesanan_dikirim():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                pm.id_pemesanan,
                pm.tanggal_pemesanan,
                plg.nama_pelanggan,
                plg.no_telp,
                plg.jalan,
                kc.nama_kecamatan,
                kb.nama_kabupaten,
                t.metode_pembayaran,
                dp.jumlah_produk,
                pr.nama_produk,
                pr.harga_produk,
                (dp.jumlah_produk * pr.harga_produk) as total_harga
            FROM pemesanan pm
            JOIN pelanggan plg ON pm.id_pelanggan = plg.id_pelanggan
            JOIN kecamatan kc ON plg.id_kecamatan = kc.id_kecamatan
            JOIN kabupaten kb ON kc.id_kabupaten = kb.id_kabupaten
            JOIN transaksi t ON pm.id_transaksi = t.id_transaksi
            JOIN detail_pemesanan dp ON pm.id_pemesanan = dp.id_pemesanan
            JOIN produk pr ON dp.id_produk = pr.id_produk
            WHERE pm.status_pemesanan = true 
            AND t.metode_pembayaran = 'non_tunai'
            AND t.status_transaksi = false  -- HANYA YANG BELUM DIKIRIM
            ORDER BY pm.tanggal_pemesanan
        """)
        pemesanan_data = cursor.fetchall()
        cursor.close()
        conn.close()
        return pemesanan_data
        
    except Exception as e:
        print("Error mengambil data pengiriman:", e)
        return []
    
def update_status_pengiriman():
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        clear_screen()
        print_line()
        print_centered("Update Status Pengiriman")
        print_line()
        pemesanan_kirim = get_pemesanan_dikirim()
        if not pemesanan_kirim:
            print("\nTidak ada pesanan yang perlu dikirim!")
            input("\nTekan Enter untuk melanjutkan...")
            return
        
        print("\nDaftar Pesanan yang Perlu Dikirim:")
        headers = ["ID", "Tanggal", "Pelanggan", "Telp", "Alamat", "Kecamatan", "Kabupaten", "Produk", "Jumlah", "Total"]
        
        table_data = []
        for pesanan in pemesanan_kirim:
            table_data.append([
                pesanan[0],
                pesanan[1],
                pesanan[2],
                pesanan[3],
                f"{pesanan[4]}",
                pesanan[5],
                pesanan[6],
                pesanan[9],
                pesanan[8],
                f"Rp {pesanan[11]:,}"
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        pemesanan_id = input("\nID pemesanan yang sudah diterima: ")
        
        cursor.execute("""
            SELECT pm.id_pemesanan, t.id_transaksi
            FROM pemesanan pm
            JOIN transaksi t ON pm.id_transaksi = t.id_transaksi
            WHERE pm.id_pemesanan = %s 
            AND pm.status_pemesanan = true 
            AND t.metode_pembayaran = 'non_tunai'
            AND t.status_transaksi = false
        """, (pemesanan_id,))
        
        result = cursor.fetchone()
        if not result:
            print("Pemesanan tidak ditemukan, belum disetujui, bukan metode non-tunai, atau sudah diterima!")
            input("\nTekan Enter untuk melanjutkan...")
            return
        
        id_transaksi = result[1]
        
        konfirmasi = input("Konfirmasi pesanan sudah diterima? (y/n): ").lower()
        
        if konfirmasi == 'y':
            cursor.execute("""
                UPDATE transaksi 
                SET status_transaksi = true 
                WHERE id_transaksi = %s
            """, (id_transaksi,))
            
            conn.commit()
            
            print(f"\nPesanan ID {pemesanan_id} telah dikonfirmasi diterima!")
            print("Status pengiriman berhasil diperbarui!")
        else:
            print("Update status dibatalkan!")
        
        input("\nTekan Enter untuk melanjutkan...")
                
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def get_riwayat_pemesanan(pelanggan_id):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                pm.id_pemesanan,
                pm.tanggal_pemesanan,
                CASE 
                    WHEN pm.status_pemesanan = false THEN 'Menunggu Kasir'
                    WHEN t.metode_pembayaran = 'tunai' THEN 'Selesai'
                    WHEN t.metode_pembayaran = 'non_tunai' AND t.status_transaksi = false THEN 'Menunggu Pengiriman'
                    WHEN t.metode_pembayaran = 'non_tunai' AND t.status_transaksi = true THEN 'Terkirim'
                END as status,
                t.metode_pembayaran,
                dp.jumlah_produk,
                pr.nama_produk,
                pr.harga_produk,
                (dp.jumlah_produk * pr.harga_produk) as total_harga
            FROM pemesanan pm
            JOIN transaksi t ON pm.id_transaksi = t.id_transaksi
            JOIN detail_pemesanan dp ON pm.id_pemesanan = dp.id_pemesanan
            JOIN produk pr ON dp.id_produk = pr.id_produk
            WHERE pm.id_pelanggan = %s
            ORDER BY pm.tanggal_pemesanan DESC
        """, (pelanggan_id,))
        riwayat_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return riwayat_data
        
    except Exception as e:
        print("Error mengambil riwayat pemesanan:", e)
        return []

def lihat_riwayat_pemesanan(pelanggan_id):
    clear_screen()
    print_line()
    print_centered("Riwayat Pemesanan")
    print_line()
    riwayat_data = get_riwayat_pemesanan(pelanggan_id)
    
    if not riwayat_data:
        print("\nBelum ada riwayat pemesanan!")
    else:
        print("\nDaftar Riwayat Pemesanan:")
        headers = ["ID", "Tanggal", "Status", "Pembayaran", "Jumlah", "Produk", "Harga", "Total"]
        print(tabulate(riwayat_data, headers=headers, tablefmt="grid"))
    
    input("\nTekan Enter untuk melanjutkan...")

def edit_lokasi_pelanggan(pelanggan_id):
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        clear_screen()
        print_line()
        print_centered("Edit Lokasi Pelanggan")
        print_line()
        cursor.execute("""
            SELECT p.nama_pelanggan, p.no_telp, p.jalan, k.nama_kecamatan, kb.nama_kabupaten
            FROM pelanggan p
            JOIN kecamatan k ON p.id_kecamatan = k.id_kecamatan
            JOIN kabupaten kb ON k.id_kabupaten = kb.id_kabupaten
            WHERE p.id_pelanggan = %s
        """, (pelanggan_id,))
        data_sekarang = cursor.fetchone()
        
        if data_sekarang:
            print("\nData Lokasi Saat Ini:")
            print(f"Nama: {data_sekarang[0]}")
            print(f"No Telp: {data_sekarang[1]}")
            print(f"Alamat: {data_sekarang[2]}")
            print(f"Kecamatan: {data_sekarang[3]}")
            print(f"Kabupaten: {data_sekarang[4]}")
        
        print("\nData yang bisa diedit:")
        print("1. Alamat (jalan/gang/nomor)")
        print("2. Kecamatan")
        
        edit_choice = input("\nPilihan (1-2): ")
        
        if edit_choice == "1":
            new_jalan = input("\nAlamat baru: ")
            cursor.execute(
                "UPDATE pelanggan SET jalan = %s WHERE id_pelanggan = %s",
                (new_jalan, pelanggan_id))
            conn.commit()
            print("\nAlamat berhasil diupdate!")
            
        elif edit_choice == "2":
            kecamatan_options = get_kecamatan_options()
            if kecamatan_options:
                selected_kecamatan = questionary.select(
                    "Pilih Kecamatan baru:",
                    choices=[option['name'] for option in kecamatan_options]).ask()
                
                id_kecamatan = None
                for option in kecamatan_options:
                    if option['name'] == selected_kecamatan:
                        id_kecamatan = option['value']
                        break
                
                if id_kecamatan:
                    cursor.execute(
                        "UPDATE pelanggan SET id_kecamatan = %s WHERE id_pelanggan = %s",
                        (id_kecamatan, pelanggan_id))
                    conn.commit()
                    print(f"\nKecamatan berhasil diupdate ke {selected_kecamatan}!")
                else:
                    print("Kecamatan tidak valid!")
            else:
                print("Tidak bisa mengambil data kecamatan!")
        else:
            print("Pilihan tidak valid!")
        
        input("\nTekan Enter untuk melanjutkan...")
        
    except Exception as e:
        print("Error:", e)
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def buat_pemesanan(pelanggan_id):
    conn = get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        clear_screen()
        print_line()
        print_centered("Buat Pemesanan")
        print_line()
        id_karyawan = 3
        from datetime import datetime
        tanggal_sekarang = datetime.now().strftime("%Y-%m-%d")
        print("\nPilih Metode Pembayaran:")
        print("1. Tunai (ambil sendiri)")
        print("2. Non-tunai (diantar)")
        metode_choice = input("Pilihan (1-2): ")
        
        if metode_choice not in ["1", "2"]:
            print("Pilihan tidak valid!")
            input("\nTekan Enter untuk melanjutkan...")
            return
        
        metode_pembayaran = "tunai" if metode_choice == "1" else "non_tunai"
        
        if metode_choice == "1":
            status_transaksi = True  
            status_pemesanan = True 
        else: 
            status_transaksi = False  
            status_pemesanan = False 
        
        cursor.execute(
            "INSERT INTO transaksi (status_transaksi, metode_pembayaran) VALUES (%s, %s) RETURNING id_transaksi",
            (status_transaksi, metode_pembayaran))
        id_transaksi = cursor.fetchone()[0]
        
        cursor.execute(
            "INSERT INTO pemesanan (tanggal_pemesanan, status_pemesanan, id_pelanggan, id_karyawan, id_transaksi) VALUES (%s, %s, %s, %s, %s) RETURNING id_pemesanan",
            (tanggal_sekarang, status_pemesanan, pelanggan_id, id_karyawan, id_transaksi))
        id_pemesanan = cursor.fetchone()[0]
        
        while True:
            clear_screen()
            print_line()
            print_centered("Pilih Produk")
            print_line()
            
            produk_data = get_all_produk()
            if not produk_data:
                print("Tidak ada produk yang tersedia!")
                break
            
            print("\nProduk yang Tersedia:")
            produk_table = []
            for produk in produk_data:
                produk_table.append([
                    produk[0],
                    produk[1],
                    f"{produk[2]} kg",
                    f"Rp {produk[3]:,}"
                ])
            
            headers = ["ID", "Nama Produk", "Stok Tersedia", "Harga per kg"]
            print(tabulate(produk_table, headers=headers, tablefmt="grid"))
            produk_id = input("\nMasukkan ID produk yang ingin dipesan: ")
            produk_valid = False
            produk_info = None
            for produk in produk_data:
                if str(produk[0]) == produk_id:
                    produk_valid = True
                    produk_info = produk
                    break
            
            if not produk_valid:
                print("Produk tidak valid!")
                input("\nTekan Enter untuk melanjutkan...")
                continue
            
            try:
                jumlah = int(input(f"\nMasukkan jumlah ({produk_info[1]}) dalam kg: "))
                if jumlah <= 0:
                    print("Jumlah harus lebih dari 0!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                if jumlah > produk_info[2]:
                    print(f"Stok tidak mencukupi! Stok tersedia: {produk_info[2]} kg")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                total_harga = jumlah * produk_info[3]
                print(f"\nTotal harga: Rp {total_harga:,}")
                
                cursor.execute(
                    "INSERT INTO detail_pemesanan (jumlah_produk, id_pemesanan, id_produk) VALUES (%s, %s, %s)",
                    (jumlah, id_pemesanan, produk_id))
                
                print(f"\n{produk_info[1]} berhasil ditambahkan ke pesanan!")
                
            except ValueError:
                print("Input jumlah harus angka!")
                input("\nTekan Enter untuk melanjutkan...")
                continue
            
            print("\nApakah ingin memesan produk lain?")
            lanjut = input("(y/n): ").lower()
            if lanjut != 'y':
                break
        
        conn.commit()
        
        if metode_choice == "1":
            print(f"\nPemesanan berhasil dibuat! ID Pemesanan: {id_pemesanan}")
            print("Status: Langsung disetujui (tunai)")
            print("Silakan ambil produk di lokasi dengan menunjukkan ID pemesanan ini.")
        else:
            print(f"\nPemesanan berhasil dibuat! ID Pemesanan: {id_pemesanan}")
            print("Status: Menunggu persetujuan kasir")
            print("Pemesanan akan ditampilkan setelah disetujui kasir.")
        
        input("\nTekan Enter untuk melanjutkan...")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def menu_karyawan(user_data):
    if user_data.get("tugas") == "penjaga_kandang":
        menu_penjaga_kandang(user_data)
    elif user_data.get("tugas") == "kurir":
        while True:
            clear_screen()
            print_line()
            print_centered(f"Menu Kurir - {user_data['username']}")
            print_line()
            print("1. Lihat Data Pengiriman")
            print("2. Update Status Pengiriman") 
            print("3. Logout")
            pilihan = input("\nPilihan (1-3): ")
            
            if pilihan == "1":
                clear_screen()
                print_line()
                print_centered("Data Pengirim")
                print_line()
                
                pemesanan_kirim = get_pemesanan_dikirim()
                
                if not pemesanan_kirim:
                    print("\nTidak ada pesanan yang perlu dikirim!")
                else:
                    print("\nDaftar Pesanan yang Perlu Dikirim:")
                    headers = ["ID", "Tanggal", "Pelanggan", "Telp", "Alamat", "Kecamatan", "Kabupaten", "Produk", "Jumlah", "Total"]
                    
                    table_data = []
                    for pesanan in pemesanan_kirim:
                        table_data.append([
                            pesanan[0],
                            pesanan[1],
                            pesanan[2],
                            pesanan[3],
                            f"{pesanan[4]}",
                            pesanan[5], 
                            pesanan[6],
                            pesanan[9],
                            pesanan[8], 
                            f"Rp {pesanan[11]:,}" 
                        ])
                    
                    print(tabulate(table_data, headers=headers, tablefmt="grid"))
                
                input("\nTekan Enter untuk melanjutkan...")
                
            elif pilihan == "2":
                update_status_pengiriman()
            elif pilihan == "3":
                print("\nLogout dari kurir...")
                input("Tekan Enter untuk melanjutkan...")
                clear_screen()
                break
            else:
                print("\nPilihan tidak valid!")
    elif user_data.get("tugas") == "kasir":
        menu_kasir(user_data)
    else:
        print(f"\nTugas {user_data.get('tugas', 'Unknown')} belum memiliki menu khusus.")
        input("Tekan Enter untuk melanjutkan...")

def menu_pelanggan(user_data):
    pelanggan_id = user_data.get("id_pelanggan")
    
    if not pelanggan_id:
        print("Error: ID pelanggan tidak ditemukan!")
        input("Tekan Enter untuk melanjutkan...")
        return
    
    while True:
        clear_screen()
        print_line()
        print_centered(f"Menu Pelanggan - {user_data['username']}")
        print_line()
        print("1. Buat Pemesanan")
        print("2. Edit Lokasi/Alamat")
        print("3. Lihat Riwayat Pemesanan")
        print("4. Logout")
        pilihan = input("\nPilihan (1-4): ")
        
        if pilihan == "1":
            buat_pemesanan(pelanggan_id)
        elif pilihan == "2":
            edit_lokasi_pelanggan(pelanggan_id)
        elif pilihan == "3":
            lihat_riwayat_pemesanan(pelanggan_id)
        elif pilihan == "4":
            print("\nLogout dari pelanggan...")
            input("Tekan Enter untuk melanjutkan...")
            clear_screen()
            break
        else:
            print("\nPilihan tidak valid!")
            input("Tekan Enter untuk melanjutkan...")

while True:
    clear_screen()
    print_line()
    print_centered("Sistem Manajement Ternak")
    print_line()
    print("1. Register")
    print("2. Login") 
    print("3. Keluar")
    choice = input("\nPilihan (1-3): ")
    
    if choice == "1":
        register()
    elif choice == "2":
        user_data = login()
        if user_data:
            if user_data["tipe"] == "admin":
                menu_admin(user_data)
            elif user_data["tipe"] == "karyawan":
                menu_karyawan(user_data)
            elif user_data["tipe"] == "pelanggan":
                menu_pelanggan(user_data)
    elif choice == "3":
        clear_screen()
        print("\nTerima kasih! Sampai jumpa!")
        break
    else:
        print("\nPilihan tidak valid!")
        input("Tekan Enter untuk melanjutkan...")
        clear_screen()
