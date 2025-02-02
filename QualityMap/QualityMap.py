import tkinter as tk
from tkinter import filedialog
import ezdxf
import csv
import math

class DXFEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DXF Editor")
        self.root.geometry("800x600")

        self.create_widgets()
        self.data_entries = []
        self.current_drawing = None
        self.drawing_mode = None
        self.finish_button = None
        self.drawn_lines = []

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

    def create_buttons(self):
        buttons = [
            ("Load DXF", self.open_dxf),
            ("Scratch", lambda: self.start_drawing("scratch")),
            ("Contamination", lambda: self.start_drawing("contamination")),
            ("Other", lambda: self.start_drawing("other")),
            ("Undo", self.undo)
        ]
        for text, command in buttons:
            button = tk.Button(self.right_frame, text=text, command=command)
            button.pack(pady=10)

        self.data_listbox = tk.Listbox(self.bottom_frame)
        self.data_listbox.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)

    def start_scratch(self):
        self.drawing_mode = "scratch"
        self.create_finish_button()

    def start_contamination(self):
        self.drawing_mode = "contamination"
        self.create_finish_button()

    def start_other(self):
        self.drawing_mode = "other"
        self.create_finish_button()

    def create_finish_button(self):
        if self.finish_button:
            self.finish_button.destroy()
        self.finish_button = tk.Button(self.right_frame, text="Finished", command=self.finish_drawing)
        self.finish_button.pack(pady=10)

    def finish_drawing(self):
        self.drawing_mode = None
        if self.finish_button:
            self.finish_button.destroy()
            self.finish_button = None
        self.add_data_entry()

    def add_data_entry(self):
        entry_name = f"{self.drawing_mode.capitalize()} {len(self.data_entries) + 1}" if self.drawing_mode else f"Unknown {len(self.data_entries) + 1}"
        self.data_entries.append(entry_name)
        self.data_listbox.insert(tk.END, entry_name)

    def on_canvas_click(self, event):
        if self.drawing_mode:
            self.current_drawing = [(event.x, event.y)]

    def on_canvas_drag(self, event):
        if self.drawing_mode and self.current_drawing:
            self.current_drawing.append((event.x, event.y))
            color = "black" if self.drawing_mode == "scratch" else "red" if self.drawing_mode == "contamination" else "blue"
            line = self.canvas.create_line(self.current_drawing[-2], self.current_drawing[-1], fill=color)
            self.drawn_lines.append(line)

    def undo(self):
        if self.drawn_lines:
            last_line = self.drawn_lines.pop()
            self.canvas.delete(last_line)

    def load_dxf(self):
        file_path = filedialog.askopenfilename(filetypes=[("DXF files", "*.dxf")])
        if file_path:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            self.canvas.delete("all")

            min_x, min_y, max_x, max_y = self.calculate_bounding_box(msp)

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            scale_x = canvas_width / (max_x - min_x)
            scale_y = canvas_height / (max_y - min_y)
            scale = min(scale_x, scale_y)
            offset_x = (canvas_width - (max_x - min_x) * scale) / 2 - min_x * scale
            offset_y = (canvas_height - (max_y - min_y) * scale) / 2 - min_y * scale

            self.draw_dxf_content(msp, scale, offset_x, offset_y)

    def calculate_bounding_box(self, msp):
        min_x, min_y, max_x, max_y = None, None, None, None
        for entity in msp:
            if entity.dxftype() == 'LINE':
                x_coords = [entity.dxf.start.x, entity.dxf.end.x]
                y_coords = [entity.dxf.start.y, entity.dxf.end.y]
            elif entity.dxftype() == 'CIRCLE':
                x_coords = [entity.dxf.center.x - entity.dxf.radius, entity.dxf.center.x + entity.dxf.radius]
                y_coords = [entity.dxf.center.y - entity.dxf.radius, entity.dxf.center.y + entity.dxf.radius]
            elif entity.dxftype() == 'ARC':
                arc_points = self.get_arc_points(entity)
                x_coords = [p[0] for p in arc_points]
                y_coords = [p[1] for p in arc_points]
            else:
                continue

            if min_x is None:
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
            else:
                min_x, max_x = min(min_x, min(x_coords)), max(max_x, max(x_coords))
                min_y, max_y = min(min_y, min(y_coords)), max(max_y, max(y_coords))
        return min_x, min_y, max_x, max_y

    def draw_dxf_content(self, msp, scale, offset_x, offset_y):
        for entity in msp:
            if entity.dxftype() == 'LINE':
                x1, y1 = entity.dxf.start.x * scale + offset_x, entity.dxf.start.y * scale + offset_y
                x2, y2 = entity.dxf.end.x * scale + offset_x, entity.dxf.end.y * scale + offset_y
                self.canvas.create_line(x1, y1, x2, y2, fill="black")
            elif entity.dxftype() == 'CIRCLE':
                x, y = entity.dxf.center.x * scale + offset_x, entity.dxf.center.y * scale + offset_y
                r = entity.dxf.radius * scale
                self.canvas.create_oval(x - r, y - r, x + r, y + r, outline="black")
            elif entity.dxftype() == 'ARC':
                self.draw_arc(entity, scale, offset_x, offset_y)
            elif entity.dxftype() in ['POLYLINE', 'LWPOLYLINE']:
                self.draw_polyline(entity, scale, offset_x, offset_y)
            elif entity.dxftype() == 'ELLIPSE':
                self.draw_ellipse(entity, scale, offset_x, offset_y)
            elif entity.dxftype() == 'SPLINE':
                self.draw_spline(entity, scale, offset_x, offset_y)
            elif entity.dxftype() == 'TEXT':
                self.draw_text(entity, scale, offset_x, offset_y)
            elif entity.dxftype() == 'MTEXT':
                self.draw_mtext(entity, scale, offset_x, offset_y)
            elif entity.dxftype() == 'POINT':
                self.draw_point(entity, scale, offset_x, offset_y)

    def draw_polyline(self, entity, scale, offset_x, offset_y):
        if entity.dxftype() == 'LWPOLYLINE':
            points = [(point[0] * scale + offset_x, point[1] * scale + offset_y) for point in entity.get_points()]
        elif entity.dxftype() == 'POLYLINE':
            points = [(vertex.dxf.location.x * scale + offset_x, vertex.dxf.location.y * scale + offset_y) for vertex in entity.vertices]
        else:
            points = []

        for i in range(len(points) - 1):
            self.canvas.create_line(points[i], points[i + 1], fill="black")

    def draw_ellipse(self, entity, scale, offset_x, offset_y):
        center_x = entity.dxf.center.x * scale + offset_x
        center_y = entity.dxf.center.y * scale + offset_y
        major_axis = entity.dxf.major_axis * scale
        ratio = entity.dxf.ratio
        start_param = entity.dxf.start_param
        end_param = entity.dxf.end_param

        num_segments = 100
        param_step = (end_param - start_param) / num_segments
        points = []
        for i in range(num_segments + 1):
            param = start_param + i * param_step
            x = center_x + major_axis * math.cos(param)
            y = center_y + major_axis * ratio * math.sin(param)
            points.append((x, y))

        for i in range(len(points) - 1):
            self.canvas.create_line(points[i], points[i + 1], fill="black")

    def draw_spline(self, entity, scale, offset_x, offset_y):
        points = [(point[0] * scale + offset_x, point[1] * scale + offset_y) for point in entity.control_points]
        for i in range(len(points) - 1):
            self.canvas.create_line(points[i], points[i + 1], fill="black")

    def draw_text(self, entity, scale, offset_x, offset_y):
        x = entity.dxf.insert.x * scale + offset_x
        y = entity.dxf.insert.y * scale + offset_y
        self.canvas.create_text(x, y, text=entity.dxf.text, anchor=tk.NW, fill="black")

    def draw_mtext(self, entity, scale, offset_x, offset_y):
        x = entity.dxf.insert.x * scale + offset_x
        y = entity.dxf.insert.y * scale + offset_y
        self.canvas.create_text(x, y, text=entity.text, anchor=tk.NW, fill="black")

    def draw_point(self, entity, scale, offset_x, offset_y):
        x = entity.dxf.location.x * scale + offset_x
        y = entity.dxf.location.y * scale + offset_y
        self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="black")

    def get_arc_points(self, entity):
        center_x = entity.dxf.center.x
        center_y = entity.dxf.center.y
        radius = entity.dxf.radius
        start_angle = entity.dxf.start_angle
        end_angle = entity.dxf.end_angle

        num_segments = 100
        angle_step = (end_angle - start_angle) / num_segments
        points = []
        for i in range(num_segments + 1):
            angle = math.radians(start_angle + i * angle_step)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            points.append((x, y))
        return points

    def draw_arc(self, entity, scale, offset_x, offset_y):
        points = self.get_arc_points(entity)
        scaled_points = [(x * scale + offset_x, y * scale + offset_y) for x, y in points]
        for i in range(len(scaled_points) - 1):
            self.canvas.create_line(scaled_points[i], scaled_points[i + 1], fill="black")

if __name__ == "__main__":
    root = tk.Tk()
    app = DXFEditorApp(root)
    root.mainloop()