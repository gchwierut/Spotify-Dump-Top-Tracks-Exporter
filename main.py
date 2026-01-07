import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import duckdb
import threading
import os
import shutil

# Try importing spotipy for Spotify API handling
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

class SpotifyOrderedExporter:
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Exporter (Dual Export Mode)")
        self.root.geometry("800x950")
        self.db_path = None
        self.original_artist_list = []

        # --- GUI Setup ---
        tk.Label(root, text="Spotify Exporter (Dual Export)", font=("Arial", 16, "bold"), pady=15).pack()

        # File Loading Section
        frame_load = tk.Frame(root)
        frame_load.pack(pady=5)
        self.btn_load_db = tk.Button(frame_load, text="📂 Open DB", command=self.load_db, bg="#673AB7", fg="white", width=15)
        self.btn_load_db.pack(side="left", padx=10)
        self.lbl_db_status = tk.Label(frame_load, text="No DB loaded", fg="gray")
        self.lbl_db_status.pack(side="left")

        frame_artists = tk.Frame(root)
        frame_artists.pack(pady=5)
        self.btn_load_artists = tk.Button(frame_artists, text="📄 Load Artists TXT", command=self.load_artists_file, bg="#FF9800", fg="white", width=15)
        self.btn_load_artists.pack(side="left", padx=10)
        self.lbl_artists_status = tk.Label(frame_artists, text="No list loaded (Single export)", fg="gray")
        self.lbl_artists_status.pack(side="left")

        # Spotify API Section
        frame_spotify = tk.LabelFrame(root, text="Spotify Filter Options", padx=10, pady=10)
        frame_spotify.pack(pady=10, fill="x", padx=20)
        self.use_spotify_filter = tk.BooleanVar()
        self.chk_spotify = tk.Checkbutton(frame_spotify, text="Exclude artists I already 'Like' on Spotify",
                                          variable=self.use_spotify_filter, command=self.toggle_spotify_inputs)
        self.chk_spotify.pack(anchor="w")

        self.frame_creds = tk.Frame(frame_spotify)
        tk.Label(self.frame_creds, text="Client ID:").grid(row=0, column=0, sticky="e")
        self.entry_client_id = tk.Entry(self.frame_creds, width=35)
        self.entry_client_id.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(self.frame_creds, text="Client Secret:").grid(row=1, column=0, sticky="e")
        self.entry_client_secret = tk.Entry(self.frame_creds, width=35, show="*")
        self.entry_client_secret.grid(row=1, column=1, padx=5, pady=2)
        tk.Label(self.frame_creds, text="Redirect URI:").grid(row=2, column=0, sticky="e")
        self.entry_redirect = tk.Entry(self.frame_creds, width=35)
        self.entry_redirect.insert(0, "http://localhost:8888/callback")
        self.entry_redirect.grid(row=2, column=1, padx=5, pady=2)

        # Export Settings
        frame_settings = tk.LabelFrame(root, text="Export Settings", padx=10, pady=10)
        frame_settings.pack(pady=10, fill="x", padx=20)

        tk.Label(frame_settings, text="Start Year:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_start = tk.Entry(frame_settings, width=10); self.entry_start.insert(0, "1926")
        self.entry_start.grid(row=0, column=1)

        tk.Label(frame_settings, text="End Year:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_end = tk.Entry(frame_settings, width=10); self.entry_end.insert(0, "2025")
        self.entry_end.grid(row=0, column=3)

        tk.Label(frame_settings, text="Max Results:").grid(row=1, column=0, padx=5, pady=5)
        self.entry_limit = tk.Entry(frame_settings, width=10); self.entry_limit.insert(0, "11000")
        self.entry_limit.grid(row=1, column=1)

        self.btn_export = tk.Button(root, text="🚀 Export", command=self.export_csv, bg="#4CAF50", fg="white", font=("Arial", 14), state="disabled")
        self.btn_export.pack(pady=20)

        self.lbl_progress = tk.Label(root, text="Ready", font=("Arial", 10))
        self.lbl_progress.pack()
        self.progress = ttk.Progressbar(root, orient="horizontal", length=600, mode="indeterminate")
        self.progress.pack(pady=10)

    def toggle_spotify_inputs(self):
        if self.use_spotify_filter.get(): self.frame_creds.pack(pady=5)
        else: self.frame_creds.pack_forget()

    def load_db(self):
        path = filedialog.askopenfilename(filetypes=[("DuckDB files", "*.duckdb")])
        if path:
            self.db_path = path
            self.lbl_db_status.config(text="DB Loaded", fg="green")
            self.update_export_button()

    def load_artists_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.original_artist_list = [line.strip() for line in f if line.strip()]

            seen = set()
            self.original_artist_list = [x for x in self.original_artist_list if not (x.lower() in seen or seen.add(x.lower()))]

            self.lbl_artists_status.config(text=f"{len(self.original_artist_list)} artists loaded (Dual Mode)", fg="blue")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        self.update_export_button()

    def update_export_button(self):
        if self.db_path:
            self.btn_export.config(state="normal")

    def fetch_spotify_liked_artists(self, client_id, client_secret, redirect_uri):
        try:
            sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope="user-library-read"))
            liked = set()
            offset = 0
            while True:
                res = sp.current_user_saved_tracks(limit=50, offset=offset)
                if not res['items']: break
                for item in res['items']:
                    for artist in item['track']['artists']:
                        liked.add(artist['name'].lower())
                if not res['next']: break
                offset += 50
            return liked
        except Exception as e:
            print(f"Spotify Error: {e}")
            return set()

    def export_csv(self):
        try:
            s, e = int(self.entry_start.get()), int(self.entry_end.get())
            limit_str = self.entry_limit.get().strip()
            limit_val = int(limit_str) if limit_str else 0

            cid = self.entry_client_id.get(); csec = self.entry_client_secret.get(); red = self.entry_redirect.get()
            sp_creds = (cid, csec, red) if self.use_spotify_filter.get() else None

            # Determine filenames
            suffix = f"_{s}_{e}"
            filename = f"export{suffix}.csv"

            base_path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=filename)

            if base_path:
                threading.Thread(target=self.run_fast_process, args=(base_path, s, e, limit_val, sp_creds), daemon=True).start()
        except ValueError:
            messagebox.showerror("Error", "Invalid inputs")

    def build_query(self, source_table, start_year, end_year, limit_val, exclude_table_name=None):
        outer_date_filter = f"CAST(SUBSTR(al.release_date, 1, 4) AS INTEGER) BETWEEN {start_year} AND {end_year}"

        exclusion_clause = ""
        if exclude_table_name:
            exclusion_clause = f"AND a.id NOT IN (SELECT artist_id FROM {exclude_table_name})"

        query = f"""
            WITH target_artists AS (
                SELECT * FROM {source_table}
            ),
            best_track_indices AS (
                SELECT
                    ta.artist_rowid,
                    arg_max(t.rowid, t.popularity) as best_tr_internal_id
                FROM track_artists ta
                JOIN target_artists a ON ta.artist_rowid = a.rowid
                JOIN tracks t ON ta.track_rowid = t.rowid
                WHERE t.popularity > 0
                GROUP BY ta.artist_rowid
            )
            SELECT
                a.id as artist_id,
                a.name,
                a.popularity as artist_popularity,
                t.id as track_id,
                t.name as track_name,
                t.popularity as track_popularity,
                al.name as album_name,
                al.release_date
            FROM best_track_indices bt
            JOIN artists a ON bt.artist_rowid = a.rowid
            JOIN tracks t ON bt.best_tr_internal_id = t.rowid
            JOIN albums al ON t.album_rowid = al.rowid
            WHERE {outer_date_filter}
            {exclusion_clause}
            QUALIFY ROW_NUMBER() OVER (PARTITION BY t.id ORDER BY a.popularity DESC) = 1
            ORDER BY a.popularity DESC
        """
        if limit_val > 0:
            query += f" LIMIT {limit_val}"
        return query

    def run_fast_process(self, base_path, start_year, end_year, limit_val, sp_creds):
        con = None
        tmp_dir = "duckdb_tmp_storage"
        try:
            self.root.after(0, lambda: self.progress.start(10))
            self.root.after(0, lambda: self.lbl_progress.config(text="Processing DB..."))

            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)

            con = duckdb.connect(self.db_path, config={
                'memory_limit': '10GB',
                'temp_directory': tmp_dir,
                'threads': '1'
            })

            # --- PREPARE DATA ---
            final_artists_list = self.original_artist_list.copy() if self.original_artist_list else []
            if sp_creds:
                self.root.after(0, lambda: self.lbl_progress.config(text="Filtering via Spotify..."))
                liked = self.fetch_spotify_liked_artists(*sp_creds)
                if final_artists_list:
                    final_artists_list = [a for a in final_artists_list if a.lower() not in liked]

            base_dir, base_file = os.path.split(base_path)
            name, ext = os.path.splitext(base_file)
            path_matched = os.path.join(base_dir, f"{name}_matched_remainder{ext}")

            if final_artists_list:
                # === FILE 1: GLOBAL TOP ===
                self.root.after(0, lambda: self.lbl_progress.config(text="Generating File 1..."))
                query_global = self.build_query("artists", start_year, end_year, limit_val)
                con.execute(f"CREATE TEMP TABLE run1_results AS {query_global}")
                path_global_sql = base_path.replace('\\', '/')
                con.execute(f"COPY run1_results TO '{path_global_sql}' (FORMAT CSV, HEADER)")

                # === FILE 2: MATCHED LIST ===
                self.root.after(0, lambda: self.lbl_progress.config(text="Generating File 2..."))
                con.execute("CREATE TEMP TABLE input_artists (name VARCHAR)")
                data_tuples = [(name,) for name in final_artists_list]
                con.executemany("INSERT INTO input_artists VALUES (?)", data_tuples)

                # Standard case-insensitive matching without ICU unaccent
                source_matched = " (SELECT a.rowid, a.id, a.name, a.popularity FROM artists a JOIN input_artists ia ON lower(a.name) = lower(ia.name)) "

                query_matched = self.build_query(source_matched, start_year, end_year, limit_val, exclude_table_name="run1_results")
                path_matched_sql = path_matched.replace('\\', '/')
                con.execute(f"COPY ({query_matched}) TO '{path_matched_sql}' (FORMAT CSV, HEADER)")

                msg = f"Done!\n1. {base_file}\n2. {name}_matched_remainder{ext}"
            else:
                query = self.build_query("artists", start_year, end_year, limit_val)
                con.execute(f"COPY ({query}) TO '{base_path.replace('\\', '/')}' (FORMAT CSV, HEADER)")
                msg = "Export Finished!"

            self.root.after(0, lambda: messagebox.showinfo("Success", msg))

        except Exception as e:
            self.root.after(0, lambda m=str(e): messagebox.showerror("Error", m))
        finally:
            if con: con.close()
            if os.path.exists(tmp_dir): shutil.rmtree(tmp_dir, ignore_errors=True)
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.lbl_progress.config(text="Ready"))

if __name__ == "__main__":
    root = tk.Tk()
    app = SpotifyOrderedExporter(root)
    root.mainloop()
