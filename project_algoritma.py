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
        return psycopg2.connect( host="localhost", database="project_algoritma", user="postgres", password="topitumbuh", port="5432")
    except Exception as e:
        print("Koneksi gagal:", e)
        return None

def get_terminal_width():
    try:
        columns, _ = shutil.get_terminal_size()
        return columns
    except:
        return 80 

def aturan_nama_akun(name):
    name = name.strip()
    
    if not name:
        return False, "Nama tidak boleh kosong!"
    
    if name.isspace():
        return False, "Nama tidak boleh hanya spasi!"
    
    for char in name:
        if not (char.isalpha() or char.isspace()):
            return False, "Nama hanya boleh mengandung huruf dan spasi!"
    
    if "  " in name:
        return False, "Nama tidak boleh mengandung spasi ganda!"
    
    return True, ""


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
        
    
        while True:
            username = input("Username: ").strip()
            
            if not username:
                print("Error: Username tidak boleh kosong!")
                continue
            
            if username.isspace():
                print("Error: Username tidak boleh hanya spasi!")
                continue
            
            if len(username) < 5:
                print("Error: Username minimal 5 karakter!")
                continue
            
            
            cursor.execute("SELECT id_akun FROM akun WHERE username = %s", (username,))
            if cursor.fetchone():
                print("Error: Username sudah digunakan!")
                continue
            
            break
        
    
        while True:
            password = getpass.getpass("Password: ")
            
            if password.isspace():
                print("Error: Password tidak boleh hanya spasi!")
                continue
            
            if len(password) < 5:
                print("Error: Password harus terdiri dari minimal 5 karakter!")
                continue
            
            break
        
        cursor.execute(
            "INSERT INTO akun (username, password) VALUES (%s, %s) RETURNING id_akun",
            (username, password))
        id_akun = cursor.fetchone()[0]
        
        clear_screen()
        print_line()
        print_centered("DATA PELANGGAN")
        print_line()
        
        while True:
            nama_pelanggan = input("Nama Lengkap: ").strip()
            
            validation_result = aturan_nama_akun(nama_pelanggan)
            
            if isinstance(validation_result, tuple) and len(validation_result) == 2:
                is_valid, error_msg = validation_result
            else:

                print("Error: Validasi nama gagal!")
                continue
            
            if not is_valid:
                print(f"Error: {error_msg}")
                print("Silakan coba lagi.")
                continue
            break
        
    
        no_telp = input("No telepon: ").strip()
        if not no_telp.isdigit():
            print("Error: Nomor telepon hanya boleh angka!")
            input("Tekan Enter untuk melanjutkan...")
            return
        
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
        
        jalan = input("\nAlamat (jalan/gang/nomor): ").strip()
        if not jalan:
            print("Error: Alamat tidak boleh kosong!")
            input("Tekan Enter untuk melanjutkan...")
            return
        
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
        print(f"Error: {e}")
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
                SELECT k.id_karyawan, k.id_tugas 
                FROM karyawan k
                WHERE k.id_akun = %s
            """, (user[0],))
            
            karyawan_data = cursor.fetchone()
            if karyawan_data:
                user_data["tipe"] = "karyawan"
                user_data["id_karyawan"] = karyawan_data[0]
                user_data["tugas"] = karyawan_data[1]  
                
                if karyawan_data[1] == 1:
                    tugas_nama = "Penjaga Kandang"
                elif karyawan_data[1] == 2:
                    tugas_nama = "Kurir"
                elif karyawan_data[1] == 3:
                    tugas_nama = "Kasir"
                else:
                    tugas_nama = f"Tugas ID {karyawan_data[1]}"
                
                print(f"\nLogin berhasil! Selamat datang {user[1]}")
                print(f"Tugas: {tugas_nama}")
            
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
            print_centered("KELOLA AKUN")
            print_line()
            
            cursor.execute("SELECT id_akun, username FROM akun ORDER BY id_akun")
            accounts = cursor.fetchall()
            
            if not accounts:
                print("Tidak ada akun!")
                break
            
            print("\nDAFTAR AKUN:")
            print_table_auto(accounts, ["ID", "Username"])
            
            print("\nPilihan:")
            print("1. Edit Akun")
            print("2. Hapus Akun")
            print("3. Kembali")
            
            choice = input("\nPilihan (1-3): ").strip()
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("EDIT AKUN")
                print_line()
                
                print("\nDAFTAR AKUN:")
                print_table_auto(accounts, ["ID", "Username"])

                account_id = input("ID akun yang akan diedit: ").strip()
                
                cursor.execute("SELECT username FROM akun WHERE id_akun = %s", (account_id,))
                akun_data = cursor.fetchone()
                
                if not akun_data:
                    print("Akun tidak ditemukan!")
                    input("Tekan Enter untuk melanjutkan...")
                    continue
                
                print(f"\nMengedit akun: {akun_data[0]}")
                print("\nPilih yang akan diedit:")
                print("1. Username")
                print("2. Password")
                
                edit_choice = input("Pilihan (1/2): ").strip()
                
                if edit_choice == "1":

                    new_username = input("Username baru: ").strip()
                    
                    if not new_username:
                        print("\nError: Username tidak boleh kosong!")
                        input("Tekan Enter untuk melanjutkan...")
                        continue
                    
                    if new_username.isspace():
                        print("\nError: Username tidak boleh hanya spasi!")
                        input("Tekan Enter untuk melanjutkan...")
                        continue
                
                    if len(new_username) < 5:
                        print("\nError: Username minimal 5 karakter!")
                        input("Tekan Enter untuk melanjutkan...")
                        continue
                    
                    cursor.execute("""
                        SELECT id_akun FROM akun 
                        WHERE username = %s AND id_akun != %s
                    """, (new_username, account_id))
                    if cursor.fetchone():
                        print("\nError: Username sudah digunakan!")
                        input("Tekan Enter untuk melanjutkan...")
                        continue
                    
                    cursor.execute(
                        "UPDATE akun SET username = %s WHERE id_akun = %s",
                        (new_username, account_id))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        print("\nUsername berhasil diupdate!")
                    else:
                        print("\nGagal mengupdate username!")
                        
            elif choice == "2":
                clear_screen()
                print_line()
                print_centered("HAPUS AKUN")
                print_line()
                
                print("\nDAFTAR AKUN:")
                print_table_auto(accounts, ["ID", "Username"])

                account_id = input("ID akun yang akan dihapus: ").strip()
                
                if account_id in ["1", "2"]:
                    print("\nTidak bisa menghapus akun admin sendiri!")
                    input("Tekan Enter untuk melanjutkan...")
                    continue
                
                cursor.execute("SELECT username FROM akun WHERE id_akun = %s", (account_id,))
                akun_info = cursor.fetchone()
                
                if not akun_info:
                    print("\nAkun tidak ditemukan!")
                    input("Tekan Enter untuk melanjutkan...")
                    continue
                
                print(f"\nAkun yang akan dihapus: {akun_info[0]}")
                
                konfirmasi = input("\nYakin ingin menghapus akun ini? (y/n): ").lower()
                
                if konfirmasi == 'y':
                    try:
                        cursor.execute("""
                            -- Hapus detail pemesanan
                            DELETE FROM detail_pemesanan 
                            WHERE id_pemesanan IN (
                                SELECT id_pemesanan FROM pemesanan 
                                WHERE id_pelanggan IN (
                                    SELECT id_pelanggan FROM pelanggan WHERE id_akun = %s
                                )
                            );
                            
                            -- Hapus pemesanan
                            DELETE FROM pemesanan 
                            WHERE id_pelanggan IN (
                                SELECT id_pelanggan FROM pelanggan WHERE id_akun = %s
                            );
                            
                            -- Hapus pelanggan
                            DELETE FROM pelanggan WHERE id_akun = %s;
                            
                            -- Update pemesanan untuk karyawan
                            UPDATE pemesanan 
                            SET id_karyawan = NULL 
                            WHERE id_karyawan IN (
                                SELECT id_karyawan FROM karyawan WHERE id_akun = %s
                            );
                            
                            -- Hapus karyawan
                            DELETE FROM karyawan WHERE id_akun = %s;
                            
                            -- Hapus akun
                            DELETE FROM akun WHERE id_akun = %s;
                        """, (account_id, account_id, account_id, account_id, account_id, account_id))
                        
                        conn.commit()
                        print("\n✓ Akun berhasil dihapus!")
                        print("✓ Semua data terkait telah terhapus.")
                        
                    except Exception as e:
                        conn.rollback()
                        print(f"\n✗ Gagal menghapus akun: {e}")
                        print("Kemungkinan masih ada constraint foreign key.")
                        
                else:
                    print("\nPenghapusan dibatalkan!")
                
                input("\nTekan Enter untuk melanjutkan...")

            elif choice == "3":
                break
            else:
                print("\nPilihan tidak valid!")
                input("Tekan Enter untuk melanjutkan...")
                
    
    except Exception as e:
        print(f"Error: {e}")
        input("Tekan Enter untuk melanjutkan...")
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
            print_centered("DATA PELANGGAN")
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
                print("\nDAFTAR PELANGGAN:")
                headers = ["ID", "Nama", "No Telp", "Alamat", "Kecamatan", "Kabupaten", "Username"]
                print_table_auto(pelanggan_data, headers)
            else:
                print("Tidak ada data pelanggan!")
            
            print("\n1. Edit Data Pelanggan")
            print("2. Kembali")
            
            choice = input("\nPilihan (1-2): ").strip()
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("EDIT DATA PELANGGAN")
                print_line()
                
                pelanggan_id = input("ID pelanggan yang akan diedit: ").strip()
                
                cursor.execute("SELECT id_pelanggan FROM pelanggan WHERE id_pelanggan = %s", (pelanggan_id,))
                if not cursor.fetchone():
                    print("Pelanggan tidak ditemukan!")
                    input("Tekan Enter untuk melanjutkan...")
                    continue
                
                print("\nData yang bisa diedit:")
                print("1. Nama Pelanggan")
                print("2. No Telepon")
                print("3. Alamat (jalan)")
                print("4. Kecamatan")
                
                edit_choice = input("Pilihan (1-4): ").strip()
                
                if edit_choice == "1":

                    while True:
                        new_nama = input("Nama baru: ").strip()
                        
                        if not new_nama:
                            print("Error: Nama tidak boleh kosong!")
                            continue
                        
                        if new_nama.isspace():
                            print("Error: Nama tidak boleh hanya spasi!")
                            continue
                        
                        if len(new_nama) < 2:
                            print("Error: Nama terlalu pendek!")
                            continue
                        
                        nama_tanpa_spasi = new_nama.replace(" ", "")
                        if not nama_tanpa_spasi.isalpha():
                            print("Error: Nama hanya boleh mengandung huruf dan spasi!")
                            continue
                        
                        break  
                    
                    cursor.execute(
                        "UPDATE pelanggan SET nama_pelanggan = %s WHERE id_pelanggan = %s",
                        (new_nama, pelanggan_id))
                    conn.commit()
                    print("\nNama pelanggan berhasil diupdate!")
                    
                elif edit_choice == "2":
            
                    while True:
                        new_telp = input("No telepon baru: ").strip()
                        
                        if not new_telp:
                            print("Error: Nomor telepon tidak boleh kosong!")
                            continue
                        
                        if not new_telp.isdigit():
                            print("Error: Nomor telepon hanya boleh mengandung angka!")
                            continue
                        
                        if len(new_telp) < 10:
                            print("Error: Nomor telepon terlalu pendek! Minimal 10 digit")
                            continue
                        
                        if len(new_telp) > 15:
                            print("Error: Nomor telepon terlalu panjang! Maksimal 15 digit")
                            continue
                        
                        break  
                    
                    cursor.execute(
                        "UPDATE pelanggan SET no_telp = %s WHERE id_pelanggan = %s",
                        (new_telp, pelanggan_id))
                    conn.commit()
                    print("\nNomor telepon berhasil diupdate!")
                    
                elif edit_choice == "3":
        
                    while True:
                        new_jalan = input("Alamat jalan baru: ").strip()
                        
                        if not new_jalan:
                            print("Error: Alamat tidak boleh kosong!")
                            continue
                        
                        if new_jalan.isspace():
                            print("Error: Alamat tidak boleh hanya spasi!")
                            continue
                        
                        break
                    
                    cursor.execute(
                        "UPDATE pelanggan SET jalan = %s WHERE id_pelanggan = %s",
                        (new_jalan, pelanggan_id))
                    conn.commit()
                    print("\nAlamat berhasil diupdate!")
                    
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
                            conn.commit()
                            print(f"\nKecamatan berhasil diupdate ke {selected_kecamatan}!")
                        else:
                            print("Kecamatan tidak valid!")
                            input("Tekan Enter untuk melanjutkan...")
                            continue
                    else:
                        print("Tidak bisa mengambil data kecamatan!")
                        input("Tekan Enter untuk melanjutkan...")
                        continue
                else:
                    print("Pilihan tidak valid!")
                    input("Tekan Enter untuk melanjutkan...")
                    continue
                
                input("\nTekan Enter untuk melanjutkan...")
                
            elif choice == "2":
                break
            else:
                print("Pilihan tidak valid!")
                input("Tekan Enter untuk melanjutkan...")
                
    except Exception as e:
        print(f"Error: {e}")
        input("Tekan Enter untuk melanjutkan...")
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
            print_centered("DATA KARYAWAN")
            print_line()
            
            cursor.execute("""
                SELECT k.id_karyawan, k.nama_karyawan, k.no_telp, 
                       k.id_tugas, a.username
                FROM karyawan k
                JOIN akun a ON k.id_akun = a.id_akun
                ORDER BY k.id_karyawan""")
            
            karyawan_data = cursor.fetchall()
            
            if karyawan_data:
                print("\nDAFTAR KARYAWAN:")
                headers = ["ID", "Nama", "No Telp", "ID Tugas", "Username"]
                print_table_auto(karyawan_data, headers)
            else:
                print("Tidak ada data karyawan!")
            
            print("\n1. Edit Data Karyawan")
            print("2. Kembali")
            
            choice = input("\nPilihan (1-2): ").strip()
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("EDIT DATA KARYAWAN")
                print_line()
                
                karyawan_id = input("ID karyawan yang akan diedit: ").strip()
                
                cursor.execute("SELECT id_karyawan FROM karyawan WHERE id_karyawan = %s", (karyawan_id,))
                if not cursor.fetchone():
                    print("Karyawan tidak ditemukan!")
                    input("Tekan Enter untuk melanjutkan...")
                    continue
                
                print("\nData yang bisa diedit:")
                print("1. Nama Karyawan")
                print("2. No Telepon")
                print("3. Tugas (ID Tugas)")
                
                edit_choice = input("Pilihan (1-3): ").strip()
                
                if edit_choice == "1":
            
                    while True:
                        new_nama = input("Nama baru: ").strip()
                        
                        if not new_nama:
                            print("Error: Nama tidak boleh kosong!")
                            continue
                        
                        if new_nama.isspace():
                            print("Error: Nama tidak boleh hanya spasi!")
                            continue
                        
                        if len(new_nama) < 2:
                            print("Error: Nama terlalu pendek!")
                            continue
                        
                        nama_tanpa_spasi = new_nama.replace(" ", "")
                        if not nama_tanpa_spasi.isalpha():
                            print("Error: Nama hanya boleh mengandung huruf dan spasi!")
                            continue
                        
                        break 
                    
                    cursor.execute(
                        "UPDATE karyawan SET nama_karyawan = %s WHERE id_karyawan = %s",
                        (new_nama, karyawan_id))
                    conn.commit()
                    print("\nNama karyawan berhasil diupdate!")
                    
                elif edit_choice == "2":

                    while True:
                        new_telp = input("No telepon baru: ").strip()
                        
                        if not new_telp:
                            print("Error: Nomor telepon tidak boleh kosong!")
                            continue
                        
                        if not new_telp.isdigit():
                            print("Error: Nomor telepon hanya boleh mengandung angka!")
                            continue
                        
                        if len(new_telp) < 10:
                            print("Error: Nomor telepon terlalu pendek! Minimal 10 digit")
                            continue
                        
                        if len(new_telp) > 15:
                            print("Error: Nomor telepon terlalu panjang! Maksimal 15 digit")
                            continue
                        
                        break  
                    
                    cursor.execute(
                        "UPDATE karyawan SET no_telp = %s WHERE id_karyawan = %s",
                        (new_telp, karyawan_id))
                    conn.commit()
                    print("\nNomor telepon berhasil diupdate!")
                    
                elif edit_choice == "3":

                    while True:
                        print("\nPilihan Tugas:")
                        print("1 = Penjaga Kandang")
                        print("2 = Kurir")
                        print("3 = Kasir")
                        
                        new_tugas_input = input("ID Tugas baru (1-3): ").strip()
                        
                        if not new_tugas_input:
                            print("Error: ID Tugas tidak boleh kosong!")
                            continue
                        
                        if not new_tugas_input.isdigit():
                            print("Error: ID Tugas harus angka!")
                            continue
                        
                        new_tugas = int(new_tugas_input)
                        
                        if new_tugas not in [1, 2, 3]:
                            print("Error: ID Tugas harus antara 1-3!")
                            continue
                        
                        tugas_map = {1: "Penjaga Kandang", 2: "Kurir", 3: "Kasir"}
                        selected_tugas = tugas_map.get(new_tugas)
                        
                        konfirmasi = input(f"Yakin ubah tugas ke {selected_tugas}? (y/n): ").lower()
                        if konfirmasi == 'y':
                            cursor.execute(
                                "UPDATE karyawan SET id_tugas = %s WHERE id_karyawan = %s",
                                (new_tugas, karyawan_id))
                            conn.commit()
                            print(f"\nTugas berhasil diupdate ke {selected_tugas}!")
                            break
                        else:
                            print("Perubahan dibatalkan!")
                            continue
                    
                else:
                    print("Pilihan tidak valid!")
                    input("Tekan Enter untuk melanjutkan...")
                    continue
                
                input("\nTekan Enter untuk melanjutkan...")
                
            elif choice == "2":
                break
            else:
                print("Pilihan tidak valid!")
                input("Tekan Enter untuk melanjutkan...")
                
    except Exception as e:
        print(f"Error: {e}")
        input("Tekan Enter untuk melanjutkan...")
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
        print("Error: Tidak bisa terhubung ke database!")
        input("Tekan Enter untuk melanjutkan...")
        return
    
    try:
        cursor = conn.cursor()
        
        clear_screen()
        print_line()
        print_centered("TAMBAH AKUN KARYAWAN")
        print_line()
        
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")
        
        if not username:
            print("Error: Username tidak boleh kosong!")
            input("Tekan Enter untuk melanjutkan...")
            return
        
        if not password:
            print("Error: Password tidak boleh kosong!")
            input("Tekan Enter untuk melanjutkan...")
            return
        
        cursor.execute("SELECT id_akun FROM akun WHERE username = %s", (username,))
        if cursor.fetchone():
            print("Error: Username sudah digunakan!")
            input("Tekan Enter untuk melanjutkan...")
            return
        
        cursor.execute(
            "INSERT INTO akun (username, password) VALUES (%s, %s) RETURNING id_akun",
            (username, password))
        id_akun = cursor.fetchone()[0]
        
        print("\nDATA KARYAWAN")
        
        nama_karyawan = input("Nama karyawan: ").strip()
        
        no_telp = input("No telepon: ").strip()
        
        if not nama_karyawan:
            print("Error: Nama karyawan tidak boleh kosong!")
            input("Tekan Enter untuk melanjutkan...")
            return
        
        if not no_telp:
            print("Error: Nomor telepon tidak boleh kosong!")
            input("Tekan Enter untuk melanjutkan...")
            return
        
        print("\nPilihan ID Tugas:")
        print("1 = Penjaga Kandang")
        print("2 = Kurir")
        print("3 = Kasir")
        
        id_tugas_input = input("ID Tugas (1/2/3): ").strip()
        
        if id_tugas_input not in ["1", "2", "3"]:
            print("Error: ID Tugas harus 1, 2, atau 3!")
            input("Tekan Enter untuk melanjutkan...")
            return
        
        id_tugas = int(id_tugas_input)
        
        status_karyawan = True
        
        tugas_map = {1: "Penjaga Kandang", 2: "Kurir", 3: "Kasir"}
        nama_tugas = tugas_map.get(id_tugas, "Unknown")
        
        print(f"\nKonfirmasi Data Karyawan:")
        print(f"Username: {username}")
        print(f"Nama Karyawan: {nama_karyawan}")
        print(f"No Telepon: {no_telp}")
        print(f"Tugas: {nama_tugas} (ID: {id_tugas})")
        print(f"Status: {'Aktif' if status_karyawan else 'Tidak Aktif'}")
        
        konfirmasi = input("\nSimpan data karyawan? (y/n): ").lower()
        
        if konfirmasi != 'y':
            print("Penambahan karyawan dibatalkan!")
            conn.rollback()  
            input("Tekan Enter untuk melanjutkan...")
            return

        cursor.execute(
            "INSERT INTO karyawan (nama_karyawan, no_telp, status_karyawan, id_akun, id_tugas) VALUES (%s, %s, %s, %s, %s)",
            (nama_karyawan, no_telp, status_karyawan, id_akun, id_tugas))
        conn.commit()
        
        print(f"\n✓ Akun karyawan berhasil dibuat!")
        print(f"  Username: {username}")
        print(f"  Nama: {nama_karyawan}")
        print(f"  Tugas: {nama_tugas}")
        print(f"  Status: {'Aktif' if status_karyawan else 'Tidak Aktif'}")
        
        input("\nTekan Enter untuk melanjutkan...")
        
    except psycopg2.IntegrityError as e:
        conn.rollback()
        print(f"Error Integrity: {e}")
        print("Kemungkinan username sudah digunakan atau data tidak valid.")
        input("Tekan Enter untuk melanjutkan...")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error: {e}")
        input("Tekan Enter untuk melanjutkan...")
        
    finally:
        if cursor:
            cursor.close()
        if conn:
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
            SELECT k.id_kandang, k.kapasitas, p.id_pakan, p.nama_pakan, ja.nama_jenis_ayam
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
                'id_pakan': kandang[2],  
                'pakan': kandang[3],     
                'jenis_ayam': kandang[4]  
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
            print_centered("KELOLA PAKAN KANDANG")
            print_line()

            cursor.execute("SELECT id_pakan, nama_pakan, jumlah_stok FROM pakan ORDER BY id_pakan")
            pakan_data = cursor.fetchall()
            
            print("\nSTOK PAKAN TERSEDIA:")
            if pakan_data:
                headers = ["ID", "Nama Pakan", "Stok (kg)"]
                print(tabulate(pakan_data, headers=headers, tablefmt="grid"))
            else:
                print("Tidak ada data pakan!")

            kandang_options = get_kandang_options()
            if kandang_options:
                print("\nDATA KANDANG:")
                kandang_table = []
                for kandang in kandang_options:
                    jenis_ayam = kandang['jenis_ayam']
                    pakan_saat_ini = kandang['pakan']
                    
                    kandang_table.append([
                        kandang['id'],
                        kandang['kapasitas'],
                        jenis_ayam,
                        pakan_saat_ini
                    ])
                print(tabulate(kandang_table, 
                             headers=["ID", "Kapasitas", "Jenis Ayam", "Pakan Saat Ini"], 
                             tablefmt="grid"))
            
            print("\nPILIHAN:")
            print("1. Ganti Pakan Kandang")
            print("2. Beri Pakan (Kurangi Stok)")
            print("3. Kembali")
            
            choice = input("\nPilihan (1-3): ").strip()
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("GANTI PAKAN KANDANG")
                print_line()
                
                print("\nDATA KANDANG:")
                kandang_table = []
                for kandang in kandang_options:
                    kandang_table.append([
                        kandang['id'],
                        kandang['kapasitas'],
                        kandang['jenis_ayam'],
                        kandang['pakan']
                    ])
                print(tabulate(kandang_table, 
                             headers=["ID", "Kapasitas", "Jenis Ayam", "Pakan Saat Ini"], 
                             tablefmt="grid"))
            
                if not kandang_options:
                    print("Tidak ada data kandang!")
                    continue
                
                kandang_list = [f"{k['id']}. {k['jenis_ayam']} (Pakan saat ini: {k['pakan']})" for k in kandang_options]
                print("\nPilih Kandang:")
                for kandang in kandang_list:
                    print(f"  {kandang}")
                
                kandang_id = input("\nID kandang: ")
                
                # Cari data kandang yang dipilih
                kandang_data = None
                for kandang in kandang_options:
                    if str(kandang['id']) == kandang_id:
                        kandang_data = kandang
                        break
                
                if not kandang_data:
                    print("Kandang tidak valid!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                jenis_ayam = kandang_data['jenis_ayam']
                pakan_saat_ini = kandang_data['pakan']
                
                print(f"\nKandang {kandang_id}: {jenis_ayam}")
                print(f"Pakan saat ini: {pakan_saat_ini}")
                
                # Tampilkan semua pakan yang tersedia
                pakan_options = get_pakan_options()
                if not pakan_options:
                    print("Tidak ada data pakan!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                print(f"\nPakan yang tersedia:")
                pakan_list = [f"{p['id']}. {p['nama']} (Stok: {p['stok']} kg)" for p in pakan_options]
                for pakan in pakan_list:
                    print(f"  {pakan}")
                
                pakan_id = input("\nID pakan baru: ")
                
                # Validasi pakan yang dipilih
                pakan_valid = False
                pakan_nama = ""
                pakan_stok = 0
                for pakan in pakan_options:
                    if str(pakan['id']) == pakan_id:
                        pakan_valid = True
                        pakan_nama = pakan['nama']
                        pakan_stok = pakan['stok']
                        break
                
                if not pakan_valid:
                    print("Pakan tidak valid!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                konfirmasi = input(f"\nYakin ganti pakan kandang {kandang_id} dari {pakan_saat_ini} ke {pakan_nama}? (y/n): ").lower()
                
                if konfirmasi == 'y':
                    cursor.execute("UPDATE kandang SET id_pakan = %s WHERE id_kandang = %s",
                        (pakan_id, kandang_id))
                    
                    conn.commit()
                    print(f"\nBerhasil mengganti pakan kandang {kandang_id} ke {pakan_nama}!")
                else:
                    print("Perubahan dibatalkan!")
                
                input("\nTekan Enter untuk melanjutkan...")
                
            elif choice == "2":
                clear_screen()
                print_line()
                print_centered("BERI PAKAN (KURANGI STOK)")
                print_line()
                
                if not kandang_options:
                    print("Tidak ada data kandang!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                print("\nDATA KANDANG:")
                kandang_table = []
                for kandang in kandang_options:
                    kandang_table.append([
                        kandang['id'],
                        kandang['kapasitas'],
                        kandang['jenis_ayam'],
                        kandang['pakan']
                    ])
                print(tabulate(kandang_table, 
                             headers=["ID", "Kapasitas", "Jenis Ayam", "Pakan Saat Ini"], 
                             tablefmt="grid"))
                
                # Tampilkan stok pakan
                print("\nSTOK PAKAN TERSEDIA:")
                if pakan_data:
                    headers = ["ID", "Nama Pakan", "Stok (kg)"]
                    print(tabulate(pakan_data, headers=headers, tablefmt="grid"))
                
                kandang_list = [f"{k['id']}. {k['jenis_ayam']} (Pakan: {k['pakan']})" for k in kandang_options]
                print("\nPilih Kandang yang akan diberi pakan:")
                for kandang in kandang_list:
                    print(f"  {kandang}")
                
                kandang_id = input("\nID kandang: ")
                
                # Cari data kandang yang dipilih
                kandang_data = None
                for kandang in kandang_options:
                    if str(kandang['id']) == kandang_id:
                        kandang_data = kandang
                        break
                
                if not kandang_data:
                    print("Kandang tidak valid!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                jenis_ayam = kandang_data['jenis_ayam']
                pakan_saat_ini = kandang_data['pakan']
                id_pakan_kandang = kandang_data['id_pakan']
                
                # Tampilkan pakan yang sesuai untuk kandang ini
                print(f"\nKandang {kandang_id}: {jenis_ayam}")
                print(f"Pakan yang digunakan: {pakan_saat_ini}")
                
                # Tampilkan semua pakan yang tersedia
                print("\nPAKAN YANG TERSEDIA:")
                pakan_list = []
                for pakan in pakan_data:
                    pakan_list.append(f"{pakan[0]}. {pakan[1]} (Stok: {pakan[2]} kg)")
                
                for pakan_item in pakan_list:
                    print(f"  {pakan_item}")
                
                # Pilih pakan yang akan digunakan
                pakan_id = input("\nPilih ID pakan yang akan digunakan: ")
                
                # Cari data pakan yang dipilih
                pakan_dipilih = None
                pakan_nama = ""
                for pakan in pakan_data:
                    if str(pakan[0]) == pakan_id:
                        pakan_dipilih = pakan
                        pakan_nama = pakan[1]
                        break
                
                if not pakan_dipilih:
                    print("Pakan tidak valid!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                # VALIDASI: Cek apakah pakan yang dipilih sesuai dengan pakan di kandang
                if str(pakan_dipilih[0]) != str(id_pakan_kandang):
                    print(f"\nError: Pakan yang dipilih ({pakan_nama}) tidak sesuai dengan pakan di kandang ({pakan_saat_ini})!")
                    print("Silakan ganti pakan kandang terlebih dahulu di menu 'Ganti Pakan Kandang'.")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                
                stok_tersedia = pakan_dipilih[2]
                print(f"\nStok {pakan_nama} tersedia: {stok_tersedia} kg")
                
                # Input jumlah pakan yang digunakan
                while True:
                    jumlah_input = input("\nJumlah pakan yang diberikan (kg): ").strip()

                    if not jumlah_input:
                        print("Error: Jumlah tidak boleh kosong!")
                        continue

                    if not jumlah_input.replace('.', '', 1).isdigit():
                        print("Error: Hanya boleh angka!")
                        continue
                    
                    try:
                        jumlah_digunakan = float(jumlah_input)

                        if jumlah_digunakan <= 0:
                            print("Error: Jumlah harus lebih dari 0!")
                            continue
                        
                        if jumlah_digunakan > stok_tersedia:
                            print(f"Error: Jumlah melebihi stok tersedia! (Stok: {stok_tersedia} kg)")
                            continue
                        
                        break 
                        
                    except ValueError:
                        print("Error: Input tidak valid!")

                print(f"\nKonfirmasi Pemberian Pakan:")
                print(f"Kandang: ID {kandang_id} ({jenis_ayam})")
                print(f"Pakan: {pakan_nama}")
                print(f"Jumlah: {jumlah_digunakan} kg")
                print(f"Stok sebelum: {stok_tersedia} kg")
                print(f"Stok setelah: {stok_tersedia - jumlah_digunakan} kg")
                
                konfirmasi = input("\nYakin beri pakan? (y/n): ").lower()
                
                if konfirmasi == 'y':
                    cursor.execute("""
                        UPDATE pakan 
                        SET jumlah_stok = jumlah_stok - %s 
                        WHERE id_pakan = %s
                    """, (jumlah_digunakan, pakan_id))
                    
                    conn.commit()

                    cursor.execute("SELECT jumlah_stok FROM pakan WHERE id_pakan = %s", (pakan_id,))
                    stok_baru = cursor.fetchone()[0]
                    
                    print(f"\n✓ Pemberian pakan berhasil!")
                    print(f"  Kandang: ID {kandang_id} ({jenis_ayam})")
                    print(f"  Pakan: {pakan_nama}")
                    print(f"  Jumlah: {jumlah_digunakan} kg")
                    print(f"  Stok baru: {stok_baru} kg")
                else:
                    print("Pemberian pakan dibatalkan!")
                
                input("\nTekan Enter untuk melanjutkan...")
                
            elif choice == "3":
                break
            else:
                print("Pilihan tidak valid!")
                
    except Exception as e:
        print(f"Error: {e}")
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
            print("2. Kembali")
            
            choice = input("\nPilihan (1-2): ").strip()
            
            if choice == "1":
                clear_screen()
                print_line()
                print_centered("Setujui Pemesanan")
                print_line()
                
                pemesanan_id = input("ID pemesanan yang akan disetujui: ").strip()
                
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
                break
            else:
                print("Pilihan tidak valid!")
                input("\nTekan Enter untuk melanjutkan...")

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
            AND t.status_transaksi = false
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
        while True:
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

            pesanan_dict = {}
            for pesanan in pemesanan_kirim:
                id_pesanan = pesanan[0]
                if id_pesanan not in pesanan_dict:
                    pesanan_dict[id_pesanan] = {
                        'tanggal': pesanan[1],
                        'pelanggan': pesanan[2],
                        'telp': pesanan[3],
                        'alamat': f"{pesanan[4]}, {pesanan[5]}, {pesanan[6]}",
                        'produk': [],
                        'total': 0
                    }
                
                pesanan_dict[id_pesanan]['produk'].append(f"{pesanan[9]} ({pesanan[8]} kg)")
                pesanan_dict[id_pesanan]['total'] += pesanan[11]

            table_data = []
            for id_pesanan, data in pesanan_dict.items():
                table_data.append([
                    id_pesanan,
                    data['tanggal'],
                    data['pelanggan'],
                    data['alamat'],
                    ', '.join(data['produk']),
                    f"Rp {data['total']:,}"
                ])
            
            headers = ["ID Pesanan", "Tanggal", "Pelanggan", "Alamat", "Produk", "Total"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
            print("\n1. Konfirmasi Pengiriman")
            print("2. Kembali")
            
            choice = input("\nPilihan (1-2): ").strip()
            
            if choice == "1":
                pemesanan_id = input("\nID pesanan yang sudah dikirim: ").strip()
                
                if not pemesanan_id:
                    print("ID pesanan tidak boleh kosong!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue

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
                    print("Pemesanan tidak ditemukan atau sudah dikirim!")
                    input("\nTekan Enter untuk melanjutkan...")
                    continue
                id_transaksi = result[1]
                
                print(f"\nKonfirmasi pengiriman untuk pesanan ID {pemesanan_id}")
                konfirmasi = input("Yakin pesanan sudah dikirim? (y/n): ").lower()
                
                if konfirmasi == 'y':
                    cursor.execute("""
                        UPDATE transaksi 
                        SET status_transaksi = true 
                        WHERE id_transaksi = %s
                    """, (id_transaksi,))
                    conn.commit()
                    
                    print(f"\n✓ Pesanan ID {pemesanan_id} berhasil dikonfirmasi sebagai terkirim!")
                else:
                    print("Konfirmasi dibatalkan!")
                
                input("\nTekan Enter untuk melanjutkan...")
                
            elif choice == "2":
                break
            else:
                print("Pilihan tidak valid!")
                input("\nTekan Enter untuk melanjutkan...")
                
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        input("\nTekan Enter untuk melanjutkan...")
    finally:
        cursor.close()
        conn.close()

def menu_karyawan(user_data):
    id_tugas = user_data.get("tugas")  
    
    if id_tugas == 1:  
        menu_penjaga_kandang(user_data)
    elif id_tugas == 2:  
        while True:
            clear_screen()
            print_line()
            print_centered(f"MENU KURIR - {user_data['username']}")
            print_line()
            print("1. Lihat Data Pengiriman")
            print("2. Update Status Pengiriman") 
            print("3. Logout")
            pilihan = input("\nPilihan (1-3): ")
            
            if pilihan == "1":
                clear_screen()
                print_line()
                print_centered("DATA PENGIRIMAN")
                print_line()
                
                pemesanan_kirim = get_pemesanan_dikirim()
                
                if not pemesanan_kirim:
                    print("\nTidak ada pesanan yang perlu dikirim!")
                else:

                    pesanan_dict = {}
                    for pesanan in pemesanan_kirim:
                        id_pesanan = pesanan[0]
                        if id_pesanan not in pesanan_dict:
                            pesanan_dict[id_pesanan] = {
                                'tanggal': pesanan[1],
                                'pelanggan': pesanan[2],
                                'telp': pesanan[3],
                                'alamat': f"{pesanan[4]}, {pesanan[5]}, {pesanan[6]}",
                                'produk': [],
                                'total': 0,
                                'status': 'Belum Dikirim'
                            }
                        
                        pesanan_dict[id_pesanan]['produk'].append(f"{pesanan[9]} ({pesanan[8]} kg)")
                        pesanan_dict[id_pesanan]['total'] += pesanan[11]

                    table_data = []
                    for id_pesanan, data in pesanan_dict.items():
                        table_data.append([
                            id_pesanan,
                            data['tanggal'],
                            data['pelanggan'],
                            data['telp'],
                            data['alamat'],
                            ', '.join(data['produk'][:2]),
                            f"Rp {data['total']:,}",
                            data['status']
                        ])
                    
                    headers = ["ID", "Tanggal", "Pelanggan", "Telp", "Alamat", "Produk", "Total", "Status"]
                    print(tabulate(table_data, headers=headers, tablefmt="grid"))
                    print(f"\nTotal pesanan: {len(pesanan_dict)} pesanan")
                
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
                input("\nTekan Enter untuk melanjutkan...")
    elif id_tugas == 3:  
        menu_kasir(user_data)
    else:
        print(f"\nTugas ID {id_tugas} belum memiliki menu khusus.")
        input("\nTekan Enter untuk melanjutkan...")
    
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
            ORDER BY pm.id_pemesanan ASC
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
        print_centered("EDIT LOKASI PELANGGAN")
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
        
        edit_choice = input("\nPilihan (1-2): ").strip()
        
        if edit_choice == "1":
            new_jalan = input("\nAlamat baru: ").strip()
            if not new_jalan:
                print("\nError: Alamat tidak boleh kosong!")
                input("Tekan Enter untuk melanjutkan...")
                return

            if new_jalan.isspace():
                print("\nError: Alamat tidak boleh hanya spasi!")
                input("Tekan Enter untuk melanjutkan...")
                return

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
        print(f"Error: {e}")
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
                
                if metode_choice == "1":
                    cursor.execute(
                        "UPDATE produk SET stok_produk = stok_produk - %s WHERE id_produk = %s",
                        (jumlah, produk_id))
                
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
            print("Status: Langsung disetujui.")
            print("Terima Kasih telah berbelanja")
        else:
            print(f"\nPemesanan berhasil dibuat!")
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

    id_tugas = user_data.get("tugas")  
    
    if id_tugas == 1:  
        menu_penjaga_kandang(user_data)
    elif id_tugas == 2:  
        while True:
            clear_screen()
            print_line()
            print_centered(f"MENU KURIR - {user_data['username']}")
            print_line()
            print("1. Lihat Data Pengiriman")
            print("2. Update Status Pengiriman") 
            print("3. Logout")
            pilihan = input("\nPilihan (1-3): ")
            
            if pilihan == "1":
                clear_screen()
                print_line()
                print_centered("DATA PENGIRIMAN")
                print_line()
                pemesanan_kirim = get_pemesanan_dikirim()
                
                if not pemesanan_kirim:
                    print("\nTidak ada pesanan yang perlu dikirim!")
                else:
                    print("\nDAFTAR PESANAN YANG PERLU DIKIRIM:")
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
    elif id_tugas == 3:  
        menu_kasir(user_data)
    else:
        print(f"\nTugas ID {id_tugas} belum memiliki menu khusus.")
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
        print("1. Buat Pemesanan \n2. Edit Lokasi Pelanggan \n3. Lihat Riwayat Pemesanan \n4. Logout")
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