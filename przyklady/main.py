import ifcopenshell
import customtkinter as ctk
import tkinter.messagebox
import tkinter.filedialog

def get_wall_area(wall):
    try:
        if hasattr(wall, "IsDefinedBy"):
            for rel in wall.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcElementQuantity"):
                        for quantity in prop_set.Quantities:
                            if quantity.is_a("IfcQuantityArea"):
                                return quantity.AreaValue
    except Exception as e:
        print(f"Błąd przy pobieraniu powierzchni ściany {wall.GlobalId}: {e}")
    return 0.0

def get_wall_properties(wall):
    try:
        length = height = net = gross = net_fp = gross_fp = 0.0

        if hasattr(wall, "IsDefinedBy"):
            for rel in wall.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcElementQuantity"):
                        for quantity in prop_set.Quantities:
                            if quantity.is_a("IfcQuantityLength") and quantity.Name == "Length":
                                length = quantity.LengthValue
                            elif quantity.is_a("IfcQuantityLength") and quantity.Name == "Height":
                                height = quantity.LengthValue
                            elif quantity.is_a("IfcQuantityArea"):
                                if quantity.Name == "NetSideArea":
                                    net = quantity.AreaValue
                                elif quantity.Name == "GrossSideArea":
                                    gross = quantity.AreaValue
                                elif quantity.Name == "NetFootprintArea":
                                    net_fp = quantity.AreaValue
                                elif quantity.Name == "GrossFootprintArea":
                                    gross_fp = quantity.AreaValue

        print(f"Ściana {wall.Name} | Długość: {length} m | Wysokość: {height} m | Pow. netto: {net} m² | Pow. brutto: {gross} m² | Podstawa netto: {net_fp} m² | Podstawa brutto: {gross_fp} m²")

    except Exception as e:
        print(f"Błąd przy pobieraniu właściwości ściany {wall.GlobalId}: {e}")

def analyze_ifc_model(filepath):
    global room_wall_map
    try:
        model = ifcopenshell.open(filepath)
    except Exception as e:
        show_error("Ooopsie", f"Nie można otworzyć pliku IFC:\n{e}")

        return

    walls = model.by_type("IfcWall") + model.by_type("IfcWallStandardCase")
    if not walls:
        show_error("Ooopsie", "Nie znaleziono ścian w pliku IFC.")
        return
    
    boundaries = model.by_type("IfcRelSpaceBoundary")
    if not boundaries:
        show_error("Ooopsie", "Nie znaleziono granic przestrzeni w pliku IFC.")
        return
    
    print(f"Spaces: {len(model.by_type('IfcSpace'))}")
    print(f"Walls: {len(model.by_type('IfcWall')) + len(model.by_type('IfcWallStandardCase'))}")
    print(f"Boundaries: {len(model.by_type('IfcRelSpaceBoundary'))}")
    
    room_wall_map = {}

    for boundary in boundaries:
        space = boundary.RelatingSpace
        element = boundary.RelatedBuildingElement

        if not space or not element:
            continue

        room_name = space.LongName or space.Name or f"Pokój {space.GlobalId[:8]}"
        if room_name not in room_wall_map:
            room_wall_map[room_name] = {
                "space": space,
                "walls": set(),
                "area_sum": 0.0,
            }

        if element.is_a("IfcWall") or element.is_a("IfcWallStandardCase"):
            wall_id = element.GlobalId
            if wall_id not in room_wall_map[room_name]["walls"]:
                room_wall_map[room_name]["walls"].add(wall_id)

                wall_area = get_wall_area(element)
                if wall_area > 0:
                    room_wall_map[room_name]["area_sum"] += wall_area

    # odśwież dropdown
    room_dropdown.configure(values=list(room_wall_map.keys()))
    if room_wall_map:
        room_dropdown.set(list(room_wall_map.keys())[0])

    for room_id, data in room_wall_map.items():
        space = data["space"]
        room_name = space.LongName or space.Name or "[bez nazwy]"
        wall_count = len(data["walls"])
        wall_area = round(data["area_sum"], 2)
        print(f"Pokój: {room_name} | Ścian: {wall_count} | Suma powierzchni ścian: {wall_area} m²")

        print("Ściany:")
        for wall_id in data["walls"]:
            wall = model.by_guid(wall_id)
            get_wall_properties(wall)

        print("\n")

def open_model_file():
    filepath = tkinter.filedialog.askopenfilename(filetypes=[("IFC files", "*.ifc")])
    if filepath:
        analyze_ifc_model(filepath)


# ------------- GUI ----------------
ctk.set_appearance_mode("light") 
ctk.set_default_color_theme("themes/autumn.json")

app = ctk.CTk()
app.title("Kalkulator farby")
app.geometry("400x500")

button_font = ctk.CTkFont(family="Roboto", size=13)
label_font = ctk.CTkFont(family="Roboto", size=14)

app.after(201, lambda :app.iconbitmap("themes/paint.ico"))

load_button = ctk.CTkButton(app, text="Wczytaj plik IFC", command=open_model_file, font=button_font)
load_button.pack(pady=(15, 5))

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

def calculate_paint():
    try:
        room_name = room_dropdown.get()
        area = room_wall_map[room_name]["area_sum"]
        efficiency = float(paint_entry.get().replace(",", "."))
        layers = int(layer_entry.get())

        if efficiency <= 0:
            raise ValueError("Wydajność farby musi być większa od 0")
        
        if layers <= 0:
            raise ValueError("Liczba warstw musi być większa od 0")

        liters_needed = area / efficiency * layers
        result_label.configure(
            text=f"Powierzchnia ścian: {area:.2f} m²\n\nPotrzeba: {liters_needed:.2f} L farby",
        )
    except Exception as e:
        show_error("Ooopsie", f"Wystąpił błąd:\n{e}")

calc_button = ctk.CTkButton(app, text="Oblicz zapotrzebowanie", command=calculate_paint, font=button_font)
calc_button.pack(pady=10)

result_label = ctk.CTkLabel(app, text="", wraplength=300, font=label_font)
result_label.pack(pady=(20, 10))


app.mainloop()
