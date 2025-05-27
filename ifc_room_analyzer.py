import ifcopenshell
import customtkinter as ctk
import tkinter.messagebox
import tkinter.filedialog
import re
from pymongo import MongoClient

from URI import URI

client = MongoClient(URI)
db = client["ifc"]
collection = db["rooms"]


def get_space_properties(space):
    flaeche = hoehe = obwod = 0.0

    try:
        if hasattr(space, "IsDefinedBy"):
            for rel in space.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcElementQuantity"):
                        for quantity in prop_set.Quantities:
                            if quantity.is_a("IfcQuantityArea") and quantity.Name in ["NetFloorArea", "GrossFloorArea", "SpaceNetFloorAreaBOMA"]:
                                flaeche = quantity.AreaValue
                            elif quantity.is_a("IfcQuantityLength") and quantity.Name in ["Height", "ClearHeight", "FinishCeilingHeight"]:
                                hoehe = quantity.LengthValue
                            elif quantity.is_a("IfcQuantityLength") and quantity.Name in ["GrossPerimeter", "NetPerimeter"]:
                                obwod = quantity.LengthValue
    except Exception as e:
        print(f"Błąd przy pobieraniu danych z pomieszczenia {space.GlobalId}: {e}")

    return flaeche, hoehe, obwod

def get_element_area(element):
    try:
        if hasattr(element, "IsDefinedBy"):
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcElementQuantity"):
                        height = width = None
                        for quantity in prop_set.Quantities:
                            if quantity.is_a("IfcQuantityArea") and quantity.Name in ["NetArea", "OuterArea", "GrossArea"]:
                                return quantity.AreaValue
                            elif quantity.is_a("IfcQuantityLength"):
                                if quantity.Name == "Height":
                                    height = quantity.LengthValue
                                elif quantity.Name == "Width":
                                    width = quantity.LengthValue
                        if height is not None and width is not None:
                            return height * width
    except Exception as e:
        print(f"Błąd przy pobieraniu powierzchni elementu {element.GlobalId}: {e}")
    return 0.0

def analyze_rooms(filepath, print_output=True):
    try:
        model = ifcopenshell.open(filepath)
    except Exception as e:
        tkinter.messagebox.showerror("Ooopsie", f"Nie można otworzyć pliku IFC:\n{e}")
        return

    spaces = model.by_type("IfcSpace")
    if not spaces:
        tkinter.messagebox.showerror("Ooopsie", f"Brak pomieszczeń w pliku IFC.")
        return

    boundaries = model.by_type("IfcRelSpaceBoundary")
    
    room_windows = {}
    room_doors = {}

    for boundary in boundaries:
        space = boundary.RelatingSpace
        element = boundary.RelatedBuildingElement

        if not space or not element:
            continue

        gid = space.GlobalId

        if element.is_a("IfcWindow"):
            if gid not in room_windows:
                room_windows[gid] = []
            area = get_element_area(element)
            room_windows[gid].append(area)

        elif element.is_a("IfcDoor"):
            if gid not in room_doors:
                room_doors[gid] = []
            area = get_element_area(element)
            room_doors[gid].append(area)

    room_data = {}

    for space in spaces:
        gid = space.GlobalId
        name = space.LongName or space.Name or "[bez nazwy]"
        flaeche, hoehe, obwod = get_space_properties(space)
        pow_sci = hoehe * obwod  # powierzchnia ścian brutto

        okna = room_windows.get(gid, [])
        suma_okien = round(sum(okna), 2) if okna else 0.0

        drzwi = room_doors.get(gid, [])
        suma_drzwi = round(sum(drzwi), 2) if drzwi else 0.0

        pow_netto = round(pow_sci - suma_okien - suma_drzwi, 2)

        if print_output:
            print(f"\n== ZNALEZIONE POMIESZCZENIA: {len(spaces)} ==")

            print(f"\nPomieszczenie ID: {gid}")
            print(f"  Nazwa: {name}")
            print(f"  Powierzchnia pomieszczenia: {flaeche} m²")
            print(f"  Wysokość: {hoehe} m")
            print(f"  Obwód: {obwod} m")
            print(f"  Powierzchnia ścian brutto: {round(pow_sci, 2)} m²")
            print(f"  Powierzchnia ścian netto: {pow_netto} m²")

            if okna:
                print(f"  Okna: {len(okna)} (suma powierzchni: {suma_okien} m²)")
            else:
                print("  Okna: brak")

            if drzwi:
                print(f"  Drzwi: {len(drzwi)} (suma powierzchni: {suma_drzwi} m²)")
            else:
                print("  Drzwi: brak")

        room_data[gid] = {
            'ifc_model': filepath,
            "name": name,
            "net_wall_area": pow_netto,
            "gross_wall_area": round(pow_sci, 2),
            "height": hoehe,
            "perimeter": obwod,
            "windows": {
                "count": len(okna),
                "total_area": suma_okien
            },
            "doors": {
                "count": len(drzwi),
                "total_area": suma_drzwi
            }
        }
    if room_data:
        for gid, room in room_data.items():
            room["_id"] = gid
            collection.replace_one({"_id": gid}, room, upsert=True)

        print(f"\nZapisano {len(room_data)} pomieszczeń do MongoDB.")

        return True
    
    return False

if __name__ == "__main__":
    filepath = "AC20-Institute-Var-2.ifc"
    analyze_rooms(filepath, print_output=False)