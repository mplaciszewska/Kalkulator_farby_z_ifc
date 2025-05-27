import ifcopenshell
import customtkinter as ctk
import tkinter.messagebox
import tkinter.filedialog
from pymongo import MongoClient

from ifc_room_analyzer import analyze_rooms
from URI import URI

client = MongoClient(URI)
db = client["ifc"]
collection = db["rooms"]


ctk.set_appearance_mode("light") 
ctk.set_default_color_theme("themes/autumn.json")

app = ctk.CTk()
app.title("Kalkulator farby")
app.geometry("400x500")

button_font = ctk.CTkFont(family="Roboto", size=13)
label_font = ctk.CTkFont(family="Roboto", size=14)

app.after(201, lambda :app.iconbitmap("themes/paint.ico"))

def show_error(title, message):
    error_window = ctk.CTkToplevel()
    error_window.title(title)
    error_window.geometry("300x150")
    error_window.resizable(False, False)

    error_window.transient(app)
    error_window.lift()
    error_window.attributes("-topmost", True)
    error_window.after(100, lambda: error_window.attributes("-topmost", False)) 
    error_window.focus_force() 

    label = ctk.CTkLabel(error_window, text=message, wraplength=260, font=label_font)
    label.pack(pady=(20, 10), padx=20)

    button = ctk.CTkButton(error_window, text="OK", command=error_window.destroy, font=button_font)
    button.pack(pady=10)

room_wall_map = {}
room_display_to_id = {}

def load_ifc_file():
    global room_wall_map, room_display_to_id

    # filepath = tkinter.filedialog.askopenfilename(filetypes=[("IFC files", "*.ifc")])
    # if not filepath:
    #     return

    # existing = list(collection.find({"ifc_model": filepath}))
    # if not existing:
    #     success = analyze_rooms(filepath, False)
    #     if not success:
    #         show_error("Błąd", "Nie udało się przetworzyć pliku IFC.")
    #         return
    #     existing = list(collection.find({"ifc_model": filepath}))
    #     print("Zapisano nowe dane do bazy danych.")
    # else:
    #     print("Znaleziono istniejące dane w bazie danych.")

    rooms = list(collection.find({})) 
    if not rooms:
        show_error("Błąd", "Brak zapisanych pomieszczeń w bazie danych.")
        return

    room_wall_map = {room["_id"]: room for room in rooms}
    room_display_to_id = {
        f"{room['name']} ({room['_id'][:6]})": room["_id"] for room in rooms
    }

    room_dropdown.configure(values=list(room_display_to_id.keys()))
    room_dropdown.set(next(iter(room_display_to_id)))

load_button = ctk.CTkButton(app, text="Wczytaj pokoje z bazy", command=load_ifc_file, font=button_font)
load_button.pack(pady=(20, 5))

# load_button = ctk.CTkButton(app, text="Wczytaj plik IFC", command=load_ifc_file, font=button_font)
# load_button.pack(pady=(15, 5))

paint_label = ctk.CTkLabel(app, text="Wydajność farby (m²/L):", font=label_font)
paint_label.pack(pady=(15, 5))

paint_entry = ctk.CTkEntry(app, placeholder_text="np. 14", font=button_font)
paint_entry.pack(pady=5)

layer_label = ctk.CTkLabel(app, text="Liczba warstw:", font=label_font)
layer_label.pack(pady=(20, 5))

layer_entry = ctk.CTkEntry(app, placeholder_text="np. 2", font=button_font)
layer_entry.pack(pady=5)

room_label = ctk.CTkLabel(app, text="Wybierz pokój:", font=label_font)
room_label.pack(pady=(20, 5))

room_dropdown = ctk.CTkOptionMenu(app, values=[""], font=button_font)
room_dropdown.set("")
room_dropdown.pack(pady=5)


def calculate_paint():
    try:
        room_display = room_dropdown.get()
        gid = room_display_to_id[room_display]
        area = room_wall_map[gid]["net_wall_area"]

        efficiency = float(paint_entry.get().replace(",", "."))
        layers = int(layer_entry.get())

        if efficiency <= 0:
            raise ValueError("Wydajność farby musi być większa od 0")
        if layers <= 0:
            raise ValueError("Liczba warstw musi być większa od 0")

        liters_needed = area / efficiency * layers

        result_label.configure(
            text=f"Powierzchnia ścian: {area:.2f} m²\n\nPotrzeba: {liters_needed:.2f} L farby"
        )
    except Exception as e:
        show_error("Ooopsie", f"Wystąpił błąd:\n{e}")


calc_button = ctk.CTkButton(app, text="Oblicz zapotrzebowanie", command=calculate_paint, font=button_font)
calc_button.pack(pady=10)

result_label = ctk.CTkLabel(app, text="", wraplength=300, font=label_font)
result_label.pack(pady=(20, 10))

app.mainloop()
