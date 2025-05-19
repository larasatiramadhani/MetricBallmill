import streamlit as st
import requests
import pandas as pd
from datetime import datetime, time, timedelta
import time as tm
import threading
from datetime import date

def run():
    # URL dari Google Apps Script Web App
    APPS_SCRIPT_URL_BM = "https://script.google.com/macros/s/AKfycbxzlbGe9WlFJBU5S8cAvUe5txsYAEucJmvOscyDU7jO6LLIhhoi58HyAbMVAxD2wkaj/exec"
    APPS_SCRIPT_URL_PR = "https://script.google.com/macros/s/AKfycbz5y58ApIInu1mL03bYcNS7jhBwHLhVCXnw8cPnBqDs-OzRn4BDB0axVk5BMobIog-YoQ/exec"
    # Fungsi untuk mendapatkan semua data dari Google Sheets
    def get_all_data(url):
        try:
            response = requests.get(url, params={"action": "get_data"}, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Terjadi kesalahan saat mengambil data: {e}")
            return []

    # Fungsi untuk mendapatkan opsi dari Google Sheets
    def get_options(url):
        try:
            response = requests.get(url, params={"action": "get_options"}, timeout=10)
            response.raise_for_status()
            options = response.json()
            return options
        except requests.exceptions.RequestException as e:
            st.error(f"Terjadi kesalahan saat mengambil data: {e}")
            return {}
    # Fungsi untuk mengirim data ke Google Sheets
    def add_data(form_data):
        try:
            response = requests.post(APPS_SCRIPT_URL_BM, json=form_data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": str(e)}
    def generate_spk_number(selected_date):
        bulan_romawi = {
            1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI",
            7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"
        }
        all_data = get_all_data(APPS_SCRIPT_URL_BM)
        selected_month = selected_date.month
        selected_year = selected_date.year
        selected_month_romawi = bulan_romawi[selected_month]  # Konversi bulan ke Romawi

        # Ambil semua nomor SPK untuk bulan dan tahun ini
        spk_numbers = [
            row[0] for row in all_data
            if len(row) > 0 and f"/{selected_month_romawi}/{selected_year}" in row[0]
        ]

        if spk_numbers:
            # Ambil nomor terakhir dan tambahkan 1
            last_spk = max(spk_numbers)  # Ambil nomor terbesar
            last_number = int(last_spk.split("/")[0])  # Ambil angka sebelum "/PR/"
            new_number = last_number + 1
        else:
    # Jika belum ada SPK bulan ini, mulai dari 1
            new_number = 1

        # Format nomor SPK baru
        return f"{str(new_number).zfill(2)}/BM/{selected_month_romawi}/{selected_year}"
    all_data = get_all_data(APPS_SCRIPT_URL_PR)
    options_pr = get_options(APPS_SCRIPT_URL_PR)

    # Ambil data untuk select box
    options_bm = get_options(APPS_SCRIPT_URL_BM)
############################################################## UNTUK ADD DATA ####################################
    st.session_state.setdefault("form_tanggal", date.today())
    defaults = {
        "form_nospk_pr": "", 
        "form_nospk_bm" :generate_spk_number(st.session_state["form_tanggal"]),
        "form_tanggal": st.session_state["form_tanggal"], 
        "form_jenisproduk" : "",
        "form_outputKg" : 0,
        "form_fillerKg" :0 ,
        "form_fillerBatch": 0,
    }
    # Pastikan semua nilai default ada di session state tanpa overwrite jika sudah ada
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    # Reset nilai form jika form_add_reset bernilai True
    # Pastikan form_add_reset ada di session_state
    st.session_state.setdefault("form_add_reset", False)
    if st.session_state.form_add_reset:
        st.session_state.update(defaults)
        st.session_state.form_add_reset = False  # Kembalikan ke False setelah reset
  
################################################## OVERVIEW DATA PRODUKSI ###########################################################################################
    def filter_dataframe(df):
        """
        Adds a UI on top of a dataframe to let viewers filter columns.

        Args:
            df (pd.DataFrame): Original dataframe

        Returns:
            pd.DataFrame: Filtered dataframe
        """
        modify = st.checkbox("Tambah Filter")

        if not modify:
            return df

        df_filtered = df.copy()  # Salin dataframe agar tidak mengubah aslinya

        # Konversi tipe data untuk filter

        # Filter UI
        with st.container():
            to_filter_columns = st.multiselect("Pilih kolom untuk filter", df_filtered.columns)
            for column in to_filter_columns:
                left, right = st.columns((1, 20))
                left.write("↳")

                if column == "Tanggal":  # Slider untuk tanggal
                    # Ubah format tanggalnya dulu agar bisa di sort
                    bulan_indo_to_eng = {
                        "Januari": "January", "Februari": "February", "Maret": "March", "April": "April",
                        "Mei": "May", "Juni": "June", "Juli": "July", "Agustus": "August",
                        "September": "September", "Oktober": "October", "November": "November", "Desember": "December"
                    }
                    # Hilangkan nama hari dan ubah nama bulan ke bahasa Inggris
                    df_filtered[column] = df_filtered[column].apply(lambda x: re.sub(r"^\w+, ", "", x))  # Hapus nama hari
                    df_filtered[column] = df_filtered[column].replace(bulan_indo_to_eng, regex=True)  # Ubah nama bulan

                    # Parsing ke datetime
                    df_filtered[column] = pd.to_datetime(df_filtered[column], format="%d %B %Y")

                    min_date, max_date = df_filtered[column].min().date(), df_filtered[column].max().date()

                    # Ambil input tanggal dari pengguna
                    date_range = right.date_input(
                        f"Filter {column}",
                        min_value=min_date,
                        max_value=max_date,
                        value=(min_date, max_date),  # Default ke rentang min-max
                    )

                    # Pastikan date_range selalu dalam bentuk yang benar
                    if isinstance(date_range, tuple) and len(date_range) == 2:
                        start_date, end_date = date_range
                    else:
                        start_date = end_date = date_range[0]  # Ambil elemen pertama kalau masih tuple

                    # Filter data dengan hanya membandingkan tanggal (tanpa waktu)
                    df_filtered = df_filtered[
                        (df_filtered[column].dt.date >= start_date) & 
                        (df_filtered[column].dt.date <= end_date)
                    ]

                    # Ubah format ke "Hari, Tanggal Bulan Tahun"
                    # Kamus Nama Hari Inggris → Indonesia
                    hari_eng_to_indo = {
                        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu", "Thursday": "Kamis",
                        "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
                    }
                        # **Tambahkan Nama Hari dan Format ke "Hari, Tanggal Bulan Tahun"**
                    df_filtered["Hari"] = df_filtered[column].dt.strftime('%A').map(hari_eng_to_indo)  # Konversi nama hari
                    df_filtered[column] = df_filtered[column].dt.strftime('%d %B %Y')  # Format tanggal biasa
                    df_filtered[column] = df_filtered["Hari"] + ", " + df_filtered[column]  # Gabungkan Nama Hari
                    df_filtered.drop(columns=["Hari"], inplace=True)  # Hapus kolom tambahan

                elif column in ["Jam Start", "Jam Stop",'Total Hour']:

                    df_filtered[column] = pd.to_datetime(df_filtered[column], errors='coerce').dt.time
                    # Pastikan kolom tidak kosong
                    if df_filtered[column].dropna().empty:
                        st.warning(f"Tidak ada data untuk {column}.")
                        continue  # Lewati filter ini jika tidak ada data

                    min_time, max_time = df_filtered[column].dropna().min(), df_filtered[column].dropna().max()
                    # Tambahkan validasi jika min_time == max_time
                    if min_time == max_time:
                        min_time = (datetime.combine(datetime.today(), min_time) - timedelta(minutes=30)).time()
                        max_time = (datetime.combine(datetime.today(), max_time) + timedelta(minutes=30)).time()
                    start_time, end_time = right.slider(
                        f"Filter {column}",
                        min_value=min_time,
                        max_value=max_time,
                        value=(min_time, max_time),
                        format="HH:mm"
                    )

                    df_filtered = df_filtered[
                        (df_filtered[column] >= start_time) &
                        (df_filtered[column] <= end_time)
                    ]
                    df_filtered[column] = df_filtered[column].apply(lambda x: x.strftime("%H:%M") if pd.notnull(x) else "")

                elif column in ["Nomor SPK", "BU", "Jenis Produk", "Line", "Speed(kg/jam)",
                                "Rencana Total Output (kg)", "Rencana Total Output (Batch)", 
                                "Inner (roll)", "SM", "Alasan"]:  # Filter kategori
                    unique_values = df_filtered[column].unique()
                    selected_values = right.multiselect(
                        f"Filter {column}",
                        options=unique_values,
                        default=[],
                    )
                    if selected_values:
                        df_filtered = df_filtered[df_filtered[column].isin(selected_values)]
        return df_filtered
    def overview():
        st.title("Data Overview")
        data = get_all_data(APPS_SCRIPT_URL_PR)
        columns = [
            "Nomor SPK", "Tanggal", "BU", "Jenis Produk", "Line",
            "Jam Start", "Jam Stop", "Total Hour", "Speed(kg/jam)", 
            "Rencana Total Output (kg)", "Rencana Total Output (Batch)", 
            "Inner (roll)", "SM", "Alasan"
        ]
        
        df = pd.DataFrame(data[1:], columns=columns) if data else pd.DataFrame(columns=columns)

        if data:
            # Balik urutan baris → data terbaru di atas
            df = df.iloc[::-1].reset_index(drop=True)

        if st.button("Muat Ulang Data"):
            st.cache_data.clear()
            st.rerun()

        st.dataframe(filter_dataframe(df))

    overview()
    ###################################################################################################################
    data_clean = [row for row in options_pr.get("Data Table", []) if isinstance(row, list) and len(row) > 0] 
    list_produk_bm = [row for row in options_bm.get("Dropdown List", []) if isinstance(row, list) and len(row) > 0]

    # Fungsi untuk mendapatkan daftar unik No. SPK Produksi
    def extract_unique_produk_bm(data):
        try:
            return sorted(set(row[0] for row in data if row[0]))  
        except Exception as e:
            st.error(f"Error saat mengekstrak Line: {e}")
            return []
        
    def filter_spk_by_produk(data_produksi, list_produk_bm):
        try:
            seen = set()
            result = []
            for row in reversed(data_produksi):  # dari yang paling bawah (terbaru)
                spk = row[0]
                produk = row[3]
                if spk and produk in list_produk_bm and spk not in seen:
                    seen.add(spk)
                    result.append(spk)
            return result
        except Exception as e:
            st.error(f"Error saat memfilter SPK berdasarkan produk BM: {e}")
            return []

    # # Ambil daftar unik dari dataset
    produk_bm_options = extract_unique_produk_bm(list_produk_bm)
    spk_pr_options = filter_spk_by_produk(data_clean, produk_bm_options)

    # Dropdown untuk No.SPK Produksi

    st.markdown("### 🗂️ Pilih No. SPK Produksi & Isi Tanggal Input ")
    st.markdown("---")
    
    # Inisialisasi session_state untuk tanggal dan SPK jika belum ada
    if "form_tanggal" not in st.session_state:
        st.session_state["form_tanggal"] = datetime.date.today()

    if "form_nospk_pr" not in st.session_state:
        st.session_state["form_nospk_pr"] = ""
    col1, col2 , col3 = st.columns(3)  
    with col1:
        tanggal = st.date_input("Tanggal Input", value=st.session_state.get("form_tanggal"), key="form_tanggal")
          # Simpan tanggal baru jika berbeda
        if tanggal != st.session_state["form_tanggal"]:
            st.session_state["form_tanggal"] = tanggal
    with col2:
        spk_pr = st.selectbox("Pilih No. SPK Produksi", [""] + spk_pr_options, key="form_nospk_pr")
        # Reset SPK jika nilainya tidak valid
    with col3:
        spk_bm = st.text_input("No. SPK Ballmill", value=generate_spk_number(st.session_state["form_tanggal"]), key="form_nospk_bm", disabled=True)
   
    if spk_pr:
        filler_kg = filler_batch = 0
        try:
            selected_row = next(
                row for row in data_clean
                if row[0] == spk_pr
            )

            # Simpan ke session_state agar bisa dipakai di form
            jenis_produk_pr = st.session_state["form_produk"] = selected_row[3]
            outputKg_pr = st.session_state["form_output(kg)"] = selected_row[9]
            outputBatch_pr = st.session_state["form_output(batch)"] = selected_row[10]

            ########### UNTUK PERHITUNGAN ####################################################################
            df_bm = pd.DataFrame(list_produk_bm, columns=["Item", "Siklus (kg)", "Filler", "Bt"])
         
            # Bersihkan dan ubah format data
            def clean_number_column(column):
                return (
                    column.astype(str)
                    .str.replace(",", "", regex=False)  # hapus koma (pem. ribuan)
                    .astype(float)                      # titik tetap sebagai desimal)
                )
            # ✅ Bersihkan angka pada kolom numerik
            for col in ["Siklus (kg)", "Filler", "Bt"]:
                df_bm[col] = clean_number_column(df_bm[col])

            # ✅ Baru filter berdasarkan jenis produk
            df_bm_filtered = df_bm[df_bm["Item"] == jenis_produk_pr]

            # Cari baris pertama dengan Siklus (kg) yang >= output SPK
            row_match = df_bm_filtered[df_bm_filtered["Siklus (kg)"] >= float(outputKg_pr)].sort_values("Siklus (kg)").head(1)

            # Hitung filler_kg dan filler_batch
            if not row_match.empty:
                outputKg_bm = row_match["Siklus (kg)"].values[0]
                filler_bm = row_match["Filler"].values[0]
                batch_bm = row_match["Bt"].values[0]

                filler_kg = round((float(outputKg_pr) / outputKg_bm) * filler_bm, 2)
                filler_batch = round((float(outputKg_pr) / outputKg_bm) * batch_bm, 2)
            else:
                filler_kg = filler_batch = 0

            if "form_fillerKg" not in st.session_state or tanggal != st.session_state["form_fillerKg"]:
                st.session_state["form_fillerKg"] = filler_kg

            if "form_fillerBatch" not in st.session_state or tanggal != st.session_state["form_fillerBatch"]:
                st.session_state["form_fillerBatch"] = filler_batch
            

              # Tampilkan info dengan layout kolom
            st.markdown("""
            <h3 style='text-align: center;'>💡 Informasi SPK Produksi Terpilih</h2>
            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)

            # Buat 3 kolom sejajar
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Jenis Produk**")
                st.markdown(f"<div style='font-size:20px; font-weight:bold'>{jenis_produk_pr}</div>", unsafe_allow_html=True)

            with col2:
                st.metric(label="Rencana Total Output (Kg)", value=round(float(outputKg_pr), 2))

            with col3:
                st.metric(label="Rencana Total Output (Batch)", value=round(float(outputBatch_pr), 2))

        except StopIteration:
            st.warning("Data tidak ditemukan untuk No. SPK tersebut..")
        except Exception as e:
            st.error(f"Terjadi error saat mengambil data: {e}")
            filler_kg = filler_batch = 0
        st.markdown("""
        <h3 style='text-align: center;'>🔢 Metric Ballmill</h1>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        card_style = """
            background-color: #e6f2ff;
            padding: 20px;
            border-radius: 16px;
            text-align: center;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.1);
            height: 160px;
            width: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
        """

        label_style = "font-size: 18px; font-weight: 600; margin-bottom: 8px;"
        value_style = "font-size: 28px; font-weight: bold; color: #222;"

        with col1:
            st.markdown(f"""
            <div style="{card_style}">
                <div style="{label_style}">🍬 Output Permen (Kg)</div>
                <div style="{value_style}">{float(outputKg_pr):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div style="{card_style}">
                <div style="{label_style}">⚖️ Filler yang Harus Dibuat (Kg)</div>
                <div style="{value_style}">{float(filler_kg):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div style="{card_style}">
                <div style="{label_style}">📦 Filler yang Harus Dibuat (Batch)</div>
                <div style="{value_style}">{float(filler_batch):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
    ########################################## SUBMIT DATA ################################################################
    form_completed = all(st.session_state.get(key) for key in [
        "form_tanggal"
    ])

    st.write("")
    submit_button = st.button("💾 Simpan Data", use_container_width=True,disabled=not form_completed)


    # Jika tombol "Simpan Data" ditekan
    if submit_button:
        try:
            formatted_tanggal = tanggal.strftime("%Y-%m-%d")  

            # Data yang akan dikirim ke Apps Script
            data = {
                "action": "add_data",
                "NomorSPK_PR": spk_pr,
                "NomorSPK_BM" : spk_bm,
                "Tanggal": formatted_tanggal,
                "JenisProduk" : jenis_produk_pr,
                "OutputKg": outputKg_pr,
                "FillerKg" : filler_kg,
                "FillerBatch" : filler_batch
                
            }

            # Kirim data ke Apps Script menggunakan POST request
            response = requests.post(APPS_SCRIPT_URL_BM, json=data)
            result = response.json()

            if result.get("status") == "success":
                st.success("Data berhasil ditambahkan!")
                st.session_state.form_add_reset = True
                st.rerun() 

            else:
                st.error(f"Terjadi kesalahan: {result.get('error')}")

        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    run()
