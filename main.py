import csv
import sqlite3
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class CSVManager:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV Manager")
        self.root.geometry("1200x720")
        self.root.configure(bg="#f8fafc")

        self.conn = sqlite3.connect(":memory:")
        self.headers = []
        self.source_file = None
        self.entry_vars = {}

        self.search_text = tk.StringVar()
        self.search_column = tk.StringVar(value="All columns")
        self.status = tk.StringVar(value="Open a CSV file to begin.")

        self.setup_style()
        self.build_ui()

    def setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f8fafc")
        style.configure("Card.TFrame", background="white")
        style.configure("Title.TLabel", background="#f8fafc",
                        foreground="#0f172a", font=("Segoe UI", 22, "bold"))
        style.configure("Primary.TButton", background="#2563eb",
                        foreground="white", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=28, background="white",
                        fieldbackground="white")
        style.configure("Treeview.Heading", background="#e2e8f0",
                        font=("Segoe UI", 10, "bold"))

    def build_ui(self):
        page = ttk.Frame(self.root, padding=20)
        page.pack(fill="both", expand=True)

        header = ttk.Frame(page)
        header.pack(fill="x", pady=(0, 14))

        ttk.Label(header, text="CSV Manager", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="Open, search, edit, delete and save CSV data using SQLite.",
            foreground="#64748b"
        ).pack(side="left", padx=14, pady=(8, 0))

        ttk.Button(header, text="Save As", command=self.save_as).pack(side="right")
        ttk.Button(header, text="Save", style="Primary.TButton",
                   command=self.save_csv).pack(side="right", padx=8)
        ttk.Button(header, text="Open CSV", command=self.open_csv).pack(side="right", padx=8)
        ttk.Button(header, text="Load Sample Data",
                   command=self.load_sample_data).pack(side="right")

        search_bar = ttk.Frame(page, style="Card.TFrame", padding=12)
        search_bar.pack(fill="x", pady=(0, 12))

        ttk.Label(search_bar, text="Search", background="white").pack(side="left")

        self.column_box = ttk.Combobox(
            search_bar,
            textvariable=self.search_column,
            values=["All columns"],
            state="readonly",
            width=16
        )
        self.column_box.pack(side="left", padx=8)

        ttk.Entry(search_bar, textvariable=self.search_text, width=35).pack(
            side="left", padx=(0, 8)
        )

        ttk.Button(search_bar, text="Find", command=self.search_records).pack(side="left")
        ttk.Button(search_bar, text="Clear", command=self.clear_search).pack(
            side="left", padx=8
        )

        body = ttk.Frame(page)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=4)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        table_card = ttk.Frame(body, style="Card.TFrame", padding=12)
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        editor_card = ttk.Frame(body, style="Card.TFrame", padding=14)
        editor_card.grid(row=0, column=1, sticky="nsew")

        self.build_table(table_card)
        self.build_editor(editor_card)

        ttk.Label(page, textvariable=self.status, foreground="#64748b").pack(
            anchor="w", pady=(10, 0)
        )

    def build_table(self, parent):
        ttk.Label(
            parent, text="CSV Records",
            background="white", foreground="#0f172a",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))

        table_frame = ttk.Frame(parent, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical",
                                 command=self.tree.yview)
        y_scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=y_scroll.set)

        self.tree.bind("<<TreeviewSelect>>", self.select_record)

    def build_editor(self, parent):
        ttk.Label(
            parent, text="Record Editor",
            background="white", foreground="#0f172a",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")

        ttk.Label(
            parent,
            text="Select a row to edit it, or enter values to add a new row.",
            background="white", foreground="#64748b",
            wraplength=260
        ).pack(anchor="w", pady=(3, 12))

        self.form_frame = ttk.Frame(parent, style="Card.TFrame")
        self.form_frame.pack(fill="x")

        actions = ttk.Frame(parent, style="Card.TFrame")
        actions.pack(fill="x", pady=14)
        actions.columnconfigure((0, 1), weight=1)

        ttk.Button(
            actions, text="Add Record",
            style="Primary.TButton",
            command=self.add_record
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

        ttk.Button(
            actions, text="Update Selected",
            command=self.update_record
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Button(
            parent, text="Delete Selected Record",
            command=self.delete_record
        ).pack(fill="x")

        ttk.Button(
            parent, text="Clear Editor",
            command=self.clear_editor
        ).pack(fill="x", pady=(8, 0))

    @staticmethod
    def quote_column(name):
        return '"' + name.replace('"', '""') + '"'

    def reset_database(self):
        self.conn.close()
        self.conn = sqlite3.connect(":memory:")

    def open_csv(self):
        path = filedialog.askopenfilename(
            title="Open CSV file",
            filetypes=[("CSV files", "*.csv")]
        )

        if not path:
            return

        encodings = ["utf-8-sig", "utf-8", "latin-1"]

        for encoding in encodings:
            try:
                with open(path, "r", newline="", encoding=encoding) as file:
                    reader = csv.reader(file)
                    headers = next(reader)
                    rows = list(reader)
                break
            except UnicodeDecodeError:
                continue
            except StopIteration:
                messagebox.showerror("Empty file", "This CSV file has no headers.")
                return
        else:
            messagebox.showerror("Error", "Unable to read this CSV file.")
            return

        headers = [header.strip() for header in headers]

        if not headers or any(not header for header in headers):
            messagebox.showerror("Invalid CSV", "Every column needs a valid name.")
            return

        if len(headers) != len(set(headers)):
            messagebox.showerror("Invalid CSV", "Column names must be unique.")
            return

        self.load_dataset(headers, rows, Path(path))

    def load_dataset(self, headers, rows, source_file=None):
        self.reset_database()
        self.headers = headers
        self.source_file = source_file

        columns = ", ".join(
            f"{self.quote_column(header)} TEXT" for header in headers
        )

        self.conn.execute(
            f"CREATE TABLE records (_id INTEGER PRIMARY KEY AUTOINCREMENT, {columns})"
        )

        placeholders = ", ".join("?" for _ in headers)
        field_names = ", ".join(self.quote_column(header) for header in headers)

        clean_rows = []
        for row in rows:
            if not any(str(value).strip() for value in row):
                continue
            clean_rows.append((row + [""] * len(headers))[:len(headers)])

        self.conn.executemany(
            f"INSERT INTO records ({field_names}) VALUES ({placeholders})",
            clean_rows
        )
        self.conn.commit()

        self.create_dynamic_form()
        self.setup_tree_columns()
        self.search_column.set("All columns")
        self.column_box["values"] = ["All columns", *headers]
        self.show_records()

        self.status.set(
            f"Loaded {len(clean_rows)} records from "
            f"{source_file.name if source_file else 'sample data'}."
        )

    def create_dynamic_form(self):
        for widget in self.form_frame.winfo_children():
            widget.destroy()

        self.entry_vars = {}

        for row, header in enumerate(self.headers):
            variable = tk.StringVar()
            self.entry_vars[header] = variable

            ttk.Label(
                self.form_frame,
                text=header,
                background="white"
            ).grid(row=row, column=0, sticky="w", pady=4)

            ttk.Entry(
                self.form_frame,
                textvariable=variable,
                width=25
            ).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=4)

        self.form_frame.columnconfigure(1, weight=1)

    def setup_tree_columns(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = self.headers

        for header in self.headers:
            self.tree.heading(header, text=header)
            self.tree.column(header, width=130, minwidth=90, anchor="w")

    def show_records(self, query=None, params=()):
        if not self.headers:
            return

        if query is None:
            fields = ", ".join(self.quote_column(header) for header in self.headers)
            query = f"SELECT _id, {fields} FROM records ORDER BY _id"

        rows = self.conn.execute(query, params).fetchall()

        self.tree.delete(*self.tree.get_children())

        for row in rows:
            self.tree.insert("", "end", iid=str(row[0]), values=row[1:])

        self.status.set(f"Showing {len(rows)} record(s).")

    def search_records(self):
        text = self.search_text.get().strip()

        if not text:
            self.show_records()
            return

        fields = ", ".join(self.quote_column(header) for header in self.headers)
        value = f"%{text}%"

        if self.search_column.get() == "All columns":
            conditions = " OR ".join(
                f"{self.quote_column(header)} LIKE ?"
                for header in self.headers
            )
            query = f"SELECT _id, {fields} FROM records WHERE {conditions} ORDER BY _id"
            self.show_records(query, [value] * len(self.headers))
        else:
            column = self.quote_column(self.search_column.get())
            query = (
                f"SELECT _id, {fields} FROM records "
                f"WHERE {column} LIKE ? ORDER BY _id"
            )
            self.show_records(query, [value])

    def clear_search(self):
        self.search_text.set("")
        self.search_column.set("All columns")
        self.show_records()

    def select_record(self, _event=None):
        selected = self.tree.selection()

        if not selected:
            return

        record_id = selected[0]
        fields = ", ".join(self.quote_column(header) for header in self.headers)

        row = self.conn.execute(
            f"SELECT {fields} FROM records WHERE _id = ?",
            (record_id,)
        ).fetchone()

        if row:
            for header, value in zip(self.headers, row):
                self.entry_vars[header].set(value)

    def clear_editor(self):
        for variable in self.entry_vars.values():
            variable.set("")
        self.tree.selection_remove(self.tree.selection())

    def add_record(self):
        if not self.headers:
            messagebox.showwarning("Open a CSV", "Open a CSV file first.")
            return

        values = [self.entry_vars[header].get().strip() for header in self.headers]

        if not any(values):
            messagebox.showwarning("Empty record", "Enter at least one value.")
            return

        fields = ", ".join(self.quote_column(header) for header in self.headers)
        placeholders = ", ".join("?" for _ in self.headers)

        self.conn.execute(
            f"INSERT INTO records ({fields}) VALUES ({placeholders})",
            values
        )
        self.conn.commit()

        self.clear_editor()
        self.show_records()
        self.status.set("New record added. Click Save to update the CSV file.")

    def update_record(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning("Select a record", "Select a row to update.")
            return

        updates = ", ".join(
            f"{self.quote_column(header)} = ?"
            for header in self.headers
        )

        values = [self.entry_vars[header].get().strip() for header in self.headers]
        values.append(selected[0])

        self.conn.execute(
            f"UPDATE records SET {updates} WHERE _id = ?",
            values
        )
        self.conn.commit()

        self.show_records()
        self.status.set("Record updated. Click Save to write changes to CSV.")

    def delete_record(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning("Select a record", "Select a row to delete.")
            return

        if not messagebox.askyesno(
            "Delete record",
            "Do you want to permanently remove the selected record?"
        ):
            return

        self.conn.execute("DELETE FROM records WHERE _id = ?", (selected[0],))
        self.conn.commit()

        self.clear_editor()
        self.show_records()
        self.status.set("Record deleted. Click Save to update the CSV.")

    def write_csv(self, path):
        fields = ", ".join(self.quote_column(header) for header in self.headers)
        rows = self.conn.execute(
            f"SELECT {fields} FROM records ORDER BY _id"
        ).fetchall()

        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(self.headers)
            writer.writerows(rows)

    def save_csv(self):
        if not self.headers:
            messagebox.showwarning("No data", "Open a CSV file first.")
            return

        if not self.source_file:
            self.save_as()
            return

        self.write_csv(self.source_file)
        self.status.set(f"Saved changes to {self.source_file.name}.")
        messagebox.showinfo("Saved", "CSV file updated successfully.")

    def save_as(self):
        if not self.headers:
            messagebox.showwarning("No data", "Open a CSV file first.")
            return

        path = filedialog.asksaveasfilename(
            title="Save CSV file",
            defaultextension=".csv",
            initialfile="updated_data.csv",
            filetypes=[("CSV files", "*.csv")]
        )

        if not path:
            return

        self.source_file = Path(path)
        self.write_csv(self.source_file)
        self.status.set(f"Saved as {self.source_file.name}.")
        messagebox.showinfo("Saved", "New CSV file created successfully.")

    def load_sample_data(self):
        headers = ["ID", "Name", "Department", "City", "Salary"]
        rows = [
            ["101", "Aarav Sharma", "Sales", "Delhi", "55000"],
            ["102", "Meera Singh", "HR", "Mumbai", "48000"],
            ["103", "Kabir Khan", "IT", "Bengaluru", "72000"],
            ["104", "Anaya Patel", "Finance", "Pune", "61000"],
            ["105", "Vihaan Gupta", "IT", "Hyderabad", "68000"],
        ]
        self.load_dataset(headers, rows)


if __name__ == "__main__":
    root = tk.Tk()
    app = CSVManager(root)
    root.mainloop()