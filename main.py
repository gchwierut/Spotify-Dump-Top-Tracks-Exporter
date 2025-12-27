import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import duckdb
import threading
import os
import string
import pandas as pd

class SpotifyIdOnlyExporter:
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Dump Top Tracks Exporter")
        self.root.geometry("800x600")
        self.db_path = None

        # --- GUI ---
        tk.Label(root, text="Spotify Dump Top Tracks Exporter", font=("Arial", 16, "bold"), pady=15).pack()



        # Database Selection
        frame_load = tk.Frame(root)
        frame_load.pack(pady=10)
        self.btn_load_db = tk.Button(frame_load, text="📂 Open DB", command=self.load_db, bg="#673AB7", fg="white")
        self.btn_load_db.pack(side="left", padx=10)
        self.lbl_db_status = tk.Label(frame_load, text="No DB loaded", fg="gray")
        self.lbl_db_status.pack(side="left")

        # Year Inputs
        frame_years = tk.Frame(root)
        frame_years.pack(pady=10)

        tk.Label(frame_years, text="Start Year:").pack(side="left", padx=5)
        self.entry_start = tk.Entry(frame_years, width=6)
        self.entry_start.insert(0, "1920")
        self.entry_start.pack(side="left", padx=5)

        tk.Label(frame_years, text="End Year:").pack(side="left", padx=5)
        self.entry_end = tk.Entry(frame_years, width=6)
        self.entry_end.insert(0, "2025")
        self.entry_end.pack(side="left", padx=5)

        self.btn_export = tk.Button(root, text="🚀 Export", command=self.export_csv, bg="#4CAF50", fg="white", font=("Arial", 14), state="disabled")
        self.btn_export.pack(pady=20)

        self.lbl_progress = tk.Label(root, text="Ready", font=("Arial", 10))
        self.lbl_progress.pack()
        self.progress = ttk.Progressbar(root, orient="horizontal", length=600, mode="determinate")
        self.progress.pack(pady=10)

    def load_db(self):
        path = filedialog.askopenfilename(filetypes=[("DuckDB files", "*.duckdb")])
        if not path: return
        self.db_path = path
        self.lbl_db_status.config(text="Loaded", fg="green")
        self.btn_export.config(state="normal")

    def get_query(self, filter_char, start_year, end_year):
        # UPDATED LOGIC:
        # We no longer sort by date. We simply want the row with the HIGHEST popularity.
        # arg_max(column_to_return, value_to_maximize)

        return f"""
            SELECT
                artists.id as artist_id,
                arg_max(tracks.id, tracks.popularity) as track_id,
                max(tracks.popularity) as track_popularity,
                arg_max(albums.id, tracks.popularity) as album_id,
                arg_max(albums.release_date, tracks.popularity) as album_release_date
            FROM artists
            LEFT JOIN track_artists ON artists.rowid = track_artists.artist_rowid
            LEFT JOIN tracks ON track_artists.track_rowid = tracks.rowid
            LEFT JOIN albums ON tracks.album_rowid = albums.rowid
            WHERE
                artists.id LIKE '{filter_char}%'
                AND CAST(SUBSTR(albums.release_date, 1, 4) AS INTEGER) BETWEEN {start_year} AND {end_year}
                AND tracks.popularity > 0
            GROUP BY artists.id
        """

    def export_csv(self):
        try:
            s = int(self.entry_start.get())
            e = int(self.entry_end.get())
        except ValueError:
            messagebox.showerror("Error", "Years must be numbers")
            return

        base_path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"top_11k_tracks_{s}_{e}.csv")
        if not base_path: return

        self.temp_path = base_path + ".temp_raw"
        self.batches = list(string.digits + string.ascii_letters)
        self.progress['maximum'] = len(self.batches) + 1
        self.progress['value'] = 0

        threading.Thread(target=self.run_process, args=(base_path, self.temp_path, s, e), daemon=True).start()

    def run_process(self, base_path, temp_path, start_year, end_year):
        try:
            con = duckdb.connect(self.db_path, read_only=True)
            con.execute("SET memory_limit='12GB'")
            con.execute("SET threads=8")

            if os.path.exists(temp_path): os.remove(temp_path)

            # --- Phase 1: Batch Extract from DB ---
            for i, char in enumerate(self.batches):
                self.root.after(0, lambda c=char: self.lbl_progress.config(text=f"Phase 1: Filtering batch '{c}'..."))
                query = self.get_query(char, start_year, end_year)
                df = con.execute(query).df()

                mode = 'w' if i == 0 else 'a'
                header = (i == 0)
                if not df.empty:
                    df.to_csv(temp_path, mode=mode, header=header, index=False)

                self.root.after(0, lambda v=i+1: self.progress.configure(value=v))

            con.close()
            self.root.after(0, lambda: self.lbl_progress.config(text="Phase 2: Sorting and Limiting to 11,000..."))

            # --- Phase 2: Sort by Popularity and Cut ---
            try:
                # 1. Read the raw CSV
                df_full = pd.read_csv(temp_path)
            except pd.errors.EmptyDataError:
                df_full = pd.DataFrame()

            if not df_full.empty:
                # 2. Dedup (Safety check)
                df_full.drop_duplicates(subset=["track_id"], keep="first", inplace=True)

                # 3. Ensure Popularity is Numeric (Crucial for correct sorting)
                df_full['track_popularity'] = pd.to_numeric(df_full['track_popularity'], errors='coerce')

                # 4. Sort TOTALLY by Popularity (Descending: 100 -> 0)
                df_full.sort_values(by="track_popularity", ascending=False, inplace=True)

                # 5. Take the top 11,000 most popular
                df_final = df_full.head(11000)

                # 6. Save
                df_final.to_csv(base_path, index=False)

                msg = f"Success!\nExported the top {len(df_final)} most popular tracks from {start_year}-{end_year}."
            else:
                msg = "No tracks found matching those criteria."

            if os.path.exists(temp_path): os.remove(temp_path)
            self.root.after(0, lambda: messagebox.showinfo("Complete", msg))

        except Exception as e:
            self.root.after(0, lambda m=str(e): messagebox.showerror("Error", m))

if __name__ == "__main__":
    root = tk.Tk()
    app = SpotifyIdOnlyExporter(root)
    root.mainloop()
