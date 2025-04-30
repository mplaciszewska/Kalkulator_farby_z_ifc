import ifcopenshell
import customtkinter as ctk
import tkinter.messagebox

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


model = ifcopenshell.open("AC20-Institute-Var-2.ifc")

rooms = model.by_type("IfcSpace")
boundaries = model.by_type("IfcRelSpaceBoundary")

# przypisz ściany i ich powierzchnie do pokoi
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
            "area_sum": 0.0
        }

    if element.is_a("IfcWall") or element.is_a("IfcWallStandardCase"):
        wall_id = element.GlobalId
        if wall_id not in room_wall_map[room_name]["walls"]:
            room_wall_map[room_name]["walls"].add(wall_id)

            wall_area = get_wall_area(element)
            if wall_area > 0:
                room_wall_map[room_name]["area_sum"] += wall_area

for room_id, data in room_wall_map.items():
    space = data["space"]
    room_name = space.LongName or space.Name or "[bez nazwy]"
    wall_count = len(data["walls"])
    wall_area = round(data["area_sum"], 2)
    print(f"Pokój: {room_name} | Ścian: {wall_count} | Suma powierzchni ścian: {wall_area} m²")

# ------------- GUI ----------------
ctk.set_appearance_mode("light") 
ctk.set_default_color_theme("themes/red.json")

app = ctk.CTk()
app.title("Kalkulator farby")
app.geometry("400x350")

app.after(201, lambda :app.iconbitmap("themes/paint.ico"))

paint_label = ctk.CTkLabel(app, text="Wydajność farby (m²/L):")
paint_label.pack(pady=(20, 5))

paint_entry = ctk.CTkEntry(app, placeholder_text="np. 14")
paint_entry.pack(pady=5)

room_label = ctk.CTkLabel(app, text="Wybierz pokój:")
room_label.pack(pady=(20, 5))

room_dropdown = ctk.CTkOptionMenu(app, values=list(room_wall_map.keys()))
room_dropdown.pack(pady=5)
room_dropdown.set(list(room_wall_map.keys())[0])

def calculate_paint():
    try:
        room_name = room_dropdown.get()
        area = room_wall_map[room_name]["area_sum"]
        efficiency = float(paint_entry.get().replace(",", "."))

        if efficiency <= 0:
            raise ValueError("Wydajność farby musi być większa od 0")

        liters_needed = area / efficiency
        result_label.configure(
            text=f"Powierzchnia ścian: {area:.2f} m²\n\nPotrzeba: {liters_needed:.2f} L farby"
        )
    except Exception as e:
        tkinter.messagebox.showerror("Błąd", f"Nieprawidłowe dane wejściowe:\n{e}")

calc_button = ctk.CTkButton(app, text="Oblicz zapotrzebowanie", command=calculate_paint)
calc_button.pack(pady=10)

result_label = ctk.CTkLabel(app, text="", wraplength=300)
result_label.pack(pady=(20, 10))



app.mainloop()
