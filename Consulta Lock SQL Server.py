import tkinter as tk
import pyodbc
import threading
import time
import socket
from tkinter import ttk

class LockQueryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Consulta de Locks no SQL Server")

        self.connection_string = "DRIVER={SQL Server};SERVER=seu_servidor;DATABASE=seu_banco;UID=seu_usuario;PWD=sua_senha"
        self.connection = None
        self.cursor = None
        self.lock_query_thread = None
        self.running = False

        self.create_widgets()

    def create_widgets(self):
        # Rótulo explicativo
        label = tk.Label(self.root, text="Resultado:")
        label.pack(pady=5)

        # Área de tabela para resultados
        self.tree = ttk.Treeview(self.root)
        self.tree["columns"] = (
           "Hostname", "SessionID", "DatabaseID", "DatabaseName", "AssociatedEntityID", "ResourceType", "RequestMode", "RequestStatus"
        )

        # Configuração das colunas
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor=tk.CENTER)

        self.tree.pack(padx=10, pady=10)

        # Botões
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        self.start_button = tk.Button(button_frame, text="Iniciar Consulta", command=self.start_query)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(button_frame, text="Parar Consulta", command=self.stop_query, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Protocolo para fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_query(self):
        if not self.running:
            self.running = True
            self.lock_query_thread = threading.Thread(target=self.query_locks_periodically)
            self.lock_query_thread.start()
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

    def stop_query(self):
        if self.running:
            self.running = False
            self.lock_query_thread.join()
            self.clear_results()
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def query_locks_periodically(self):
        while self.running:
            self.query_locks()
            time.sleep(1)

    def query_locks(self):
        try:
            self.connection = pyodbc.connect(self.connection_string)
            self.cursor = self.connection.cursor()

            query = """SELECT request_session_id AS SessionID,
                        resource_database_id AS DatabaseID,
                        DB_NAME(resource_database_id) AS DatabaseName,
                        resource_associated_entity_id AS AssociatedEntityID,
                        resource_type AS ResourceType,
                        request_mode AS RequestMode,
                        request_status AS RequestStatus
                    FROM sys.dm_tran_locks
                    WHERE resource_database_id = DB_ID()
                    ORDER BY request_session_id, DatabaseName"""
            self.cursor.execute(query)
            locks = self.cursor.fetchall()

            self.display_results(locks, clear=True)

        except pyodbc.Error as e:
            self.display_results([("Erro ao conectar ao SQL Server:", str(e))], clear=True, color="red")

        finally:
            if self.connection:
                self.connection.close()

    def clear_treeview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
    def display_results(self, results, clear=False, color=None):
        if clear:
            self.clear_treeview()

        for row in results:
            hostname = socket.gethostname()
            self.tree.insert("", "end", values=[hostname, row[0]] + list(row[1:]))

        if color:
            for idx in range(len(results)):
                if "LOCK" in str(results[idx]):
                    self.tree.tag_configure(color, background=color)
                    self.tree.item(self.tree.get_children()[idx], tags=(color))


    def clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def on_closing(self):
        self.stop_query()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LockQueryApp(root)
    root.mainloop()
