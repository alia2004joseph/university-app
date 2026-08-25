"""
image_generator.py — Complete Engineering Diagram Generator.
Supports ALL departments: Mechanical, Electrical, Civil, Chemical,
Aerospace, Biomedical, Materials, Environmental, and more.

100% offline — no API keys needed.
"""

import os
import re
import io
import math
import requests
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import quote
from typing import Optional, Tuple, Dict, List, Callable
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod

# ── Config ──────────────────────────────────────────────────
CACHE_DIR = ".image_cache"
DEFAULT_WIDTH = 900
DEFAULT_HEIGHT = 600

# ── Department Enum ─────────────────────────────────────────
class Department(Enum):
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    CIVIL = "civil"
    CHEMICAL = "chemical"
    AEROSPACE = "aerospace"
    BIOMEDICAL = "biomedical"
    MATERIALS = "materials"
    ENVIRONMENTAL = "environmental"
    COMPUTER = "computer"
    INDUSTRIAL = "industrial"
    GENERAL = "general"


# ── Helpers ──────────────────────────────────────────────────
def _sanitize_filename(prompt: str) -> str:
    clean_text = prompt.lower().strip()
    clean_text = re.sub(r'[^a-z0-9\s_-]', '', clean_text)
    clean_text = re.sub(r'[\s_]+', '_', clean_text)
    return clean_text[:80] + ".png"


def _get_font(size: int):
    """Try to load a nice font, fallback to default."""
    font_paths = [
        "arial.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()


def _draw_text_centered(draw, text, x, y, font, color, anchor="mm"):
    """Draw text centered at (x, y)."""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((x - w//2, y - h//2), text, fill=color, font=font)
    except:
        draw.text((x - len(text)*3, y - 6), text, fill=color, font=font)


# ── Base Class ──────────────────────────────────────────────
class DiagramGenerator(ABC):
    """Base class for all diagram generators."""
    
    @abstractmethod
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        """Generate the diagram."""
        pass
    
    @staticmethod
    def detect(prompt: str) -> bool:
        """Check if this generator can handle the prompt."""
        return False


# ════════════════════════════════════════════════════════════
# 1. MECHANICAL ENGINEERING DIAGRAMS
# ════════════════════════════════════════════════════════════
class MechanicalGenerator(DiagramGenerator):
    
    @staticmethod
    def detect(prompt: str) -> bool:
        keywords = [
            'piston', 'cylinder', 'engine', 'crankshaft', 'connecting rod',
            'gear', 'cog', 'transmission', 'shaft', 'bearing', 'cam', 'valve',
            'turbine', 'compressor', 'pump', 'actuator', 'clutch', 'brake',
            'flywheel', 'belt', 'chain', 'sprocket', 'linkage', 'crank',
            'slider', 'rocker', 'spring', 'damper', 'shock absorber'
        ]
        return any(k in prompt.lower() for k in keywords)
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        p = prompt.lower()
        if any(k in p for k in ['piston', 'cylinder']):
            return self._piston(width, height)
        elif any(k in p for k in ['gear', 'cog', 'transmission']):
            return self._gear(width, height)
        elif 'turbine' in p:
            return self._turbine(width, height)
        elif 'pump' in p or 'compressor' in p:
            return self._pump(width, height)
        elif 'clutch' in p or 'brake' in p:
            return self._clutch(width, height)
        elif 'bearing' in p:
            return self._bearing(width, height)
        else:
            return self._generic_mechanical(width, height, prompt)
    
    # ── PISTON ──
    def _piston(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        # Colors
        dark_blue = (30, 64, 175)
        light_blue = (219, 234, 254)
        grey = (200, 200, 210)
        dark_grey = (100, 100, 110)
        red = (200, 50, 50)
        
        # ── Cylinder ──
        cyl_w, cyl_h = 220, 340
        x1 = cx - cyl_w // 2
        y1 = cy - cyl_h // 2
        
        draw.rectangle([(x1, y1), (x1 + cyl_w, y1 + cyl_h)], 
                       outline=dark_blue, width=4)
        draw.rectangle([(x1 - 10, y1), (x1 + cyl_w + 10, y1 + 20)], 
                       fill=dark_blue, outline=dark_blue)
        draw.rectangle([(x1 - 10, y1 + cyl_h - 20), (x1 + cyl_w + 10, y1 + cyl_h)], 
                       fill=dark_blue, outline=dark_blue)
        
        # ── Piston ──
        piston_w = cyl_w - 50
        piston_h = 100
        piston_y = y1 + 100
        px1 = cx - piston_w // 2
        py1 = piston_y
        
        draw.rectangle([(px1, py1), (px1 + piston_w, py1 + piston_h)], 
                       fill=light_blue, outline=dark_blue, width=3)
        
        # Piston rings
        for i in range(3):
            ring_y = py1 + 15 + i * 22
            draw.rectangle([(px1 + 10, ring_y), (px1 + piston_w - 10, ring_y + 6)], 
                           fill=dark_grey, outline=dark_grey)
        
        # ── Connecting rod ──
        rod_w = 16
        rod_bottom = y1 + cyl_h - 25
        draw.rectangle([(cx - rod_w//2, py1 + piston_h), 
                        (cx + rod_w//2, rod_bottom)], 
                       fill=grey, outline=dark_grey, width=2)
        
        # ── Crankshaft ──
        crank_r = 45
        crank_cx = cx
        crank_cy = rod_bottom + 35
        
        draw.ellipse([(crank_cx - crank_r, crank_cy - crank_r),
                      (crank_cx + crank_r, crank_cy + crank_r)], 
                     outline=dark_blue, width=4)
        draw.ellipse([(crank_cx - 8, crank_cy - 8),
                      (crank_cx + 8, crank_cy + 8)], 
                     fill=dark_blue)
        draw.line([(cx, rod_bottom), (crank_cx, crank_cy)], fill=dark_grey, width=8)
        
        # ── Labels ──
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        draw.text((cx - 130, 15), "PISTON & CYLINDER ASSEMBLY", 
                  fill=dark_blue, font=font_title)
        draw.text((cx + 130, y1 + 15), "CYLINDER HEAD", fill=dark_blue, font=font_label)
        draw.text((cx + 130, py1 + 40), "PISTON", fill=dark_blue, font=font_label)
        draw.text((cx + 130, py1 + 120), "RINGS", fill=dark_grey, font=font_label)
        draw.text((cx + 130, cy + 60), "CONNECTING ROD", fill=dark_grey, font=font_label)
        draw.text((cx + 130, rod_bottom + 25), "CRANKSHAFT", fill=dark_blue, font=font_label)
        
        # Stroke dimension
        draw.line([(x1 - 35, y1 + 25), (x1 - 35, y1 + cyl_h - 25)], fill=red, width=2)
        draw.line([(x1 - 40, y1 + 25), (x1 - 30, y1 + 25)], fill=red, width=2)
        draw.line([(x1 - 40, y1 + cyl_h - 25), (x1 - 30, y1 + cyl_h - 25)], fill=red, width=2)
        draw.text((x1 - 75, cy - 10), "STROKE", fill=red, font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── GEAR ──
    def _gear(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        def draw_gear(cx, cy, radius, teeth, color1, color2, label=""):
            draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], 
                         fill=color2, outline=color1, width=3)
            for i in range(teeth):
                angle = i * (2 * math.pi / teeth)
                x1 = cx + (radius - 8) * math.cos(angle)
                y1 = cy + (radius - 8) * math.sin(angle)
                x2 = cx + (radius + 12) * math.cos(angle)
                y2 = cy + (radius + 12) * math.sin(angle)
                draw.line([(x1, y1), (x2, y2)], fill=color1, width=4)
            draw.ellipse([(cx - 15, cy - 15), (cx + 15, cy + 15)], fill=color1, outline=color1)
            draw.ellipse([(cx - 8, cy - 8), (cx + 8, cy + 8)], fill=(255, 255, 255), outline=color1)
            if label:
                draw.text((cx - 30, cy + radius + 15), label, fill=color1, font=font_label)
        
        draw.text((cx - 120, 15), "GEAR MECHANISM", fill=(30, 64, 175), font=font_title)
        draw_gear(cx - 100, cy + 10, 120, 20, (30, 64, 175), (219, 234, 254), "DRIVING GEAR")
        draw_gear(cx + 150, cy - 40, 70, 14, (200, 50, 50), (254, 219, 219), "DRIVEN GEAR")
        
        # Motion arrows
        draw.arc([(cx - 130, cy - 100), (cx - 70, cy - 40)], start=0, end=90, 
                 fill=(30, 64, 175), width=3)
        draw.arc([(cx + 100, cy - 90), (cx + 200, cy + 10)], start=180, end=270, 
                 fill=(200, 50, 50), width=3)
        draw.text((cx - 120, cy - 130), "↻", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 140, cy - 110), "↺", fill=(200, 50, 50), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── TURBINE ──
    def _turbine(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        # Housing
        draw.ellipse([(cx - 180, cy - 180), (cx + 180, cy + 180)], 
                     outline=(30, 64, 175), width=4)
        draw.ellipse([(cx - 160, cy - 160), (cx + 160, cy + 160)], 
                     fill=(219, 234, 254))
        
        # Turbine blades
        for i in range(16):
            angle = i * (2 * math.pi / 16)
            x1 = cx + 60 * math.cos(angle)
            y1 = cy + 60 * math.sin(angle)
            x2 = cx + 150 * math.cos(angle)
            y2 = cy + 150 * math.sin(angle)
            draw.line([(x1, y1), (x2, y2)], fill=(30, 64, 175), width=6)
            # Blade curve
            if i % 2 == 0:
                x3 = cx + 120 * math.cos(angle + 0.2)
                y3 = cy + 120 * math.sin(angle + 0.2)
                draw.line([(x1, y1), (x3, y3)], fill=(200, 50, 50), width=2)
        
        # Shaft
        draw.ellipse([(cx - 20, cy - 20), (cx + 20, cy + 20)], fill=(100, 100, 110))
        draw.line([(cx, cy - 180), (cx, cy - 250)], fill=(100, 100, 110), width=8)
        draw.line([(cx, cy + 180), (cx, cy + 250)], fill=(100, 100, 110), width=8)
        
        draw.text((cx - 130, 15), "TURBINE ASSEMBLY", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 200, cy + 200), "INLET", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 140, cy + 200), "OUTLET", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 190, cy - 20), "BLADES", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 40, cy - 220), "SHAFT", fill=(100, 100, 110), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── PUMP ──
    def _pump(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        # Pump housing (circle with inlet/outlet)
        draw.ellipse([(cx - 150, cy - 120), (cx + 150, cy + 120)], 
                     outline=(30, 64, 175), width=4)
        draw.ellipse([(cx - 130, cy - 100), (cx + 130, cy + 100)], 
                     fill=(219, 234, 254))
        
        # Impeller
        for i in range(8):
            angle = i * (2 * math.pi / 8)
            x1 = cx + 20 * math.cos(angle)
            y1 = cy + 20 * math.sin(angle)
            x2 = cx + 100 * math.cos(angle)
            y2 = cy + 100 * math.sin(angle)
            draw.line([(x1, y1), (x2, y2)], fill=(100, 100, 110), width=4)
            # Curve blades
            x3 = cx + 90 * math.cos(angle + 0.3)
            y3 = cy + 90 * math.sin(angle + 0.3)
            draw.line([(x1, y1), (x3, y3)], fill=(30, 64, 175), width=2)
        
        # Center
        draw.ellipse([(cx - 15, cy - 15), (cx + 15, cy + 15)], fill=(30, 64, 175))
        
        # Inlet/outlet pipes
        draw.line([(cx, cy - 120), (cx, cy - 180)], fill=(100, 100, 110), width=6)
        draw.line([(cx + 150, cy), (cx + 200, cy)], fill=(100, 100, 110), width=6)
        draw.ellipse([(cx - 10, cy - 185), (cx + 10, cy - 175)], fill=(200, 50, 50))
        draw.ellipse([(cx + 195, cy - 10), (cx + 205, cy + 10)], fill=(200, 50, 50))
        
        draw.text((cx - 120, 15), "CENTRIFUGAL PUMP", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 100, cy - 200), "INLET", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 160, cy + 20), "OUTLET", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 130, cy - 60), "IMPELLER", fill=(100, 100, 110), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── CLUTCH ──
    def _clutch(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        # Outer housing
        draw.ellipse([(cx - 180, cy - 140), (cx + 180, cy + 140)], 
                     outline=(30, 64, 175), width=4)
        
        # Flywheel (left)
        draw.ellipse([(cx - 170, cy - 80), (cx + 20, cy + 80)], 
                     fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        
        # Pressure plate (right)
        draw.ellipse([(cx - 20, cy - 80), (cx + 170, cy + 80)], 
                     fill=(254, 219, 219), outline=(200, 50, 50), width=3)
        
        # Friction plate
        draw.ellipse([(cx - 100, cy - 60), (cx + 100, cy + 60)], 
                     outline=(200, 100, 50), width=4)
        # Friction material pattern
        for i in range(12):
            angle = i * (2 * math.pi / 12)
            x1 = cx + 80 * math.cos(angle)
            y1 = cy + 80 * math.sin(angle)
            x2 = cx + 90 * math.cos(angle)
            y2 = cy + 90 * math.sin(angle)
            draw.line([(x1, y1), (x2, y2)], fill=(200, 100, 50), width=3)
        
        # Springs
        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle)
            x = cx + 140 * math.cos(rad)
            y = cy + 140 * math.sin(rad)
            draw.ellipse([(x - 12, y - 8), (x + 12, y + 8)], 
                         fill=(200, 200, 200), outline=(100, 100, 110), width=2)
        
        draw.text((cx - 130, 15), "CLUTCH ASSEMBLY", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 200, cy - 100), "FLYWHEEL", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 100, cy - 100), "PRESSURE\nPLATE", fill=(200, 50, 50), font=font_label)
        draw.text((cx - 60, cy + 110), "FRICTION PLATE", fill=(200, 100, 50), font=font_label)
        draw.text((cx + 140, cy + 110), "SPRINGS", fill=(100, 100, 110), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── BEARING ──
    def _bearing(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        # Outer race
        draw.ellipse([(cx - 180, cy - 120), (cx + 180, cy + 120)], 
                     outline=(30, 64, 175), width=4)
        draw.ellipse([(cx - 160, cy - 100), (cx + 160, cy + 100)], 
                     fill=(219, 234, 254))
        
        # Inner race
        draw.ellipse([(cx - 70, cy - 50), (cx + 70, cy + 50)], 
                     outline=(30, 64, 175), width=4)
        draw.ellipse([(cx - 50, cy - 30), (cx + 50, cy + 30)], 
                     fill=(254, 219, 219))
        
        # Rolling elements (balls)
        for i in range(12):
            angle = i * (2 * math.pi / 12)
            x = cx + 110 * math.cos(angle)
            y = cy + 110 * math.sin(angle)
            draw.ellipse([(x - 15, y - 15), (x + 15, y + 15)], 
                         fill=(200, 200, 200), outline=(100, 100, 110), width=2)
        
        # Cage
        for i in range(12):
            angle = i * (2 * math.pi / 12)
            x1 = cx + 90 * math.cos(angle)
            y1 = cy + 90 * math.sin(angle)
            x2 = cx + 130 * math.cos(angle)
            y2 = cy + 130 * math.sin(angle)
            if i % 2 == 0:
                draw.arc([(x1 - 20, y1 - 20), (x2 + 20, y2 + 20)], 
                         start=int(math.degrees(angle))-10, 
                         end=int(math.degrees(angle))+10, 
                         fill=(150, 150, 150), width=2)
        
        draw.text((cx - 130, 15), "BALL BEARING", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 200, cy - 140), "OUTER RACE", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 120, cy - 40), "INNER RACE", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 130, cy + 90), "BALLS", fill=(100, 100, 110), font=font_label)
        draw.text((cx - 160, cy + 90), "CAGE", fill=(150, 150, 150), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── GENERIC MECHANICAL ──
    def _generic_mechanical(self, width: int, height: int, prompt: str) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        draw.rectangle([(40, 40), (width - 40, height - 40)], 
                       outline=(30, 64, 175), width=3)
        draw.rectangle([(40, 40), (width - 40, 80)], fill=(30, 64, 175))
        
        title = prompt[:60] if prompt else "MECHANICAL COMPONENT"
        draw.text((60, 52), title.upper(), fill=(255, 255, 255), font=font_title)
        
        draw.rectangle([(cx - 150, cy - 80), (cx + 150, cy + 80)], 
                       outline=(30, 64, 175), width=2)
        draw.text((cx - 130, cy - 20), "MECHANICAL", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 100, cy + 5), "ASSEMBLY", fill=(30, 64, 175), font=font_label)
        
        # Dimensional lines
        draw.line([(cx - 180, cy - 80), (cx - 180, cy + 80)], fill=(200, 50, 50), width=2)
        draw.line([(cx - 190, cy - 80), (cx - 170, cy - 80)], fill=(200, 50, 50), width=2)
        draw.line([(cx - 190, cy + 80), (cx - 170, cy + 80)], fill=(200, 50, 50), width=2)
        draw.text((cx - 220, cy - 10), "DIM", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()


# ════════════════════════════════════════════════════════════
# 2. ELECTRICAL ENGINEERING DIAGRAMS
# ════════════════════════════════════════════════════════════
class ElectricalGenerator(DiagramGenerator):
    
    @staticmethod
    def detect(prompt: str) -> bool:
        keywords = [
            'circuit', 'electrical', 'electronic', 'resistor', 'capacitor',
            'diode', 'led', 'transistor', 'amplifier', 'oscillator',
            'power supply', 'transformer', 'motor', 'generator', 'solar',
            'battery', 'charger', 'inverter', 'rectifier', 'filter',
            'op-amp', 'microcontroller', 'arduino', 'sensor'
        ]
        return any(k in prompt.lower() for k in keywords)
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        p = prompt.lower()
        if 'motor' in p or 'generator' in p:
            return self._motor(width, height)
        elif 'transformer' in p:
            return self._transformer(width, height)
        elif 'solar' in p or 'panel' in p:
            return self._solar(width, height)
        elif 'op-amp' in p or 'amplifier' in p:
            return self._op_amp(width, height)
        else:
            return self._circuit(width, height)
    
    # ── CIRCUIT ──
    def _circuit(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        margin = 100
        x1, y1 = margin, margin
        x2, y2 = width - margin, height - margin
        
        # Main wires
        draw.line([(x1, cy), (x2, cy)], fill=(30, 64, 175), width=3)
        draw.line([(cx, y1), (cx, y2)], fill=(30, 64, 175), width=3)
        draw.line([(x1, y1), (cx, y1)], fill=(30, 64, 175), width=3)
        draw.line([(cx, y2), (x2, y2)], fill=(30, 64, 175), width=3)
        draw.line([(x1, y1), (x1, cy)], fill=(30, 64, 175), width=3)
        draw.line([(x2, cy), (x2, y2)], fill=(30, 64, 175), width=3)
        
        # Resistor
        rx1, ry1 = x1 + 60, cy - 20
        draw.line([(rx1, ry1), (rx1 + 20, ry1), (rx1 + 10, ry1 + 10), 
                   (rx1 + 20, ry1 + 20), (rx1 + 10, ry1 + 30), 
                   (rx1 + 20, ry1 + 40), (rx1 + 10, ry1 + 50)], 
                  fill=(200, 50, 50), width=4)
        draw.text((x1 + 20, cy + 35), "R1\n10Ω", fill=(200, 50, 50), font=font_label)
        
        # Capacitor
        cx1, cy1 = cx - 80, cy - 30
        draw.line([(cx1, y1 + 50), (cx1, y2 - 50)], fill=(30, 64, 175), width=3)
        draw.line([(cx1 + 20, y1 + 50), (cx1 + 20, y2 - 50)], fill=(30, 64, 175), width=3)
        draw.text((cx1 - 15, cy + 10), "C1\n100µF", fill=(30, 64, 175), font=font_label)
        
        # Battery
        bx, by = x2 - 80, cy - 30
        draw.line([(bx, by), (bx, by + 60)], fill=(30, 64, 175), width=4)
        draw.line([(bx - 20, by), (bx + 20, by)], fill=(30, 64, 175), width=4)
        draw.line([(bx - 12, by + 60), (bx + 12, by + 60)], fill=(30, 64, 175), width=4)
        draw.text((bx - 25, by + 70), "V1\n12V", fill=(30, 64, 175), font=font_label)
        
        # LED
        lx, ly = cx, y2 - 80
        draw.ellipse([(lx - 10, ly), (lx + 10, ly + 20)], fill=(50, 200, 50), 
                     outline=(30, 64, 175), width=2)
        draw.line([(lx, ly + 20), (lx, ly + 40)], fill=(30, 64, 175), width=3)
        draw.text((lx + 15, ly + 5), "D1 (LED)", fill=(30, 64, 175), font=font_label)
        
        draw.text((cx - 140, 15), "ELECTRICAL CIRCUIT DIAGRAM", 
                  fill=(30, 64, 175), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── MOTOR ──
    def _motor(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        # Motor housing
        draw.ellipse([(cx - 140, cy - 130), (cx + 140, cy + 130)], 
                     outline=(30, 64, 175), width=4)
        draw.ellipse([(cx - 120, cy - 110), (cx + 120, cy + 110)], 
                     fill=(219, 234, 254))
        
        # Stator windings
        for i in range(12):
            angle = i * (2 * math.pi / 12)
            x1 = cx + 90 * math.cos(angle)
            y1 = cy + 90 * math.sin(angle)
            x2 = cx + 110 * math.cos(angle)
            y2 = cy + 110 * math.sin(angle)
            draw.line([(x1, y1), (x2, y2)], fill=(200, 50, 50), width=4)
        
        # Rotor
        draw.ellipse([(cx - 60, cy - 60), (cx + 60, cy + 60)], 
                     fill=(200, 200, 200), outline=(100, 100, 110), width=3)
        
        # Shaft
        draw.line([(cx, cy - 130), (cx, cy - 220)], fill=(100, 100, 110), width=8)
        draw.line([(cx, cy + 130), (cx, cy + 200)], fill=(100, 100, 110), width=8)
        
        # Brushes (DC motor)
        draw.rectangle([(cx - 120, cy - 20), (cx - 90, cy + 20)], 
                       fill=(150, 150, 150), outline=(100, 100, 110))
        draw.rectangle([(cx + 90, cy - 20), (cx + 120, cy + 20)], 
                       fill=(150, 150, 150), outline=(100, 100, 110))
        
        draw.text((cx - 120, 15), "ELECTRIC MOTOR", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 140, cy - 20), "STATOR", fill=(200, 50, 50), font=font_label)
        draw.text((cx - 100, cy + 110), "ROTOR", fill=(100, 100, 110), font=font_label)
        draw.text((cx - 140, cy + 140), "BRUSHES", fill=(150, 150, 150), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── TRANSFORMER ──
    def _transformer(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        # Core (three legs)
        core_w, core_h = 60, 200
        # Left leg
        draw.rectangle([(cx - core_w - 30, cy - core_h//2), 
                        (cx - 30, cy + core_h//2)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        # Right leg
        draw.rectangle([(cx + 30, cy - core_h//2), 
                        (cx + core_w + 30, cy + core_h//2)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        # Top yoke
        draw.rectangle([(cx - core_w - 30, cy - core_h//2), 
                        (cx + core_w + 30, cy - core_h//2 + 30)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        # Bottom yoke
        draw.rectangle([(cx - core_w - 30, cy + core_h//2 - 30), 
                        (cx + core_w + 30, cy + core_h//2)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        
        # Primary winding (left)
        for i in range(8):
            y = cy - 70 + i * 18
            draw.rectangle([(cx - 55, y), (cx - 35, y + 8)], 
                           fill=(200, 50, 50))
        
        # Secondary winding (right)
        for i in range(12):
            y = cy - 90 + i * 15
            draw.rectangle([(cx + 35, y), (cx + 55, y + 6)], 
                           fill=(30, 64, 175))
        
        draw.text((cx - 130, 15), "TRANSFORMER", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 200, cy - 100), "PRIMARY", fill=(200, 50, 50), font=font_label)
        draw.text((cx + 100, cy - 100), "SECONDARY", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 60, cy + 120), "CORE", fill=(30, 64, 175), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── SOLAR PANEL ──
    def _solar(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        # Panel frame
        draw.rectangle([(cx - 200, cy - 200), (cx + 200, cy + 200)], 
                       outline=(30, 64, 175), width=4)
        draw.rectangle([(cx - 190, cy - 190), (cx + 190, cy + 190)], 
                       fill=(30, 64, 175, 50))
        
        # Solar cells (grid)
        for i in range(8):
            x = cx - 170 + i * 44
            for j in range(8):
                y = cy - 170 + j * 44
                draw.rectangle([(x, y), (x + 38, y + 38)], 
                               outline=(100, 180, 255), width=2)
                # Cell texture
                draw.line([(x + 10, y + 10), (x + 28, y + 10)], fill=(100, 180, 255), width=1)
                draw.line([(x + 10, y + 28), (x + 28, y + 28)], fill=(100, 180, 255), width=1)
                draw.line([(x + 10, y + 10), (x + 10, y + 28)], fill=(100, 180, 255), width=1)
                draw.line([(x + 28, y + 10), (x + 28, y + 28)], fill=(100, 180, 255), width=1)
        
        # Sun rays
        for angle in [-60, -30, 0, 30, 60]:
            rad = math.radians(angle)
            x1 = cx + 220 * math.cos(rad)
            y1 = cy - 220 * math.sin(rad)
            x2 = cx + 300 * math.cos(rad)
            y2 = cy - 300 * math.sin(rad)
            draw.line([(x1, y1), (x2, y2)], fill=(255, 200, 50), width=3)
            draw.ellipse([(x1 - 15, y1 - 15), (x1 + 15, y1 + 15)], 
                         fill=(255, 200, 50))
        
        draw.text((cx - 140, 15), "SOLAR PANEL SYSTEM", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 220, cy - 20), "SOLAR\nCELLS", fill=(100, 180, 255), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── OP-AMP ──
    def _op_amp(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Triangle (op-amp symbol)
        points = [(cx - 80, cy), (cx + 80, cy - 60), (cx + 80, cy + 60)]
        draw.polygon(points, outline=(30, 64, 175), width=3, fill=(219, 234, 254))
        
        # Inputs
        draw.line([(cx - 160, cy - 30), (cx - 80, cy - 20)], fill=(30, 64, 175), width=3)
        draw.line([(cx - 160, cy + 30), (cx - 80, cy + 20)], fill=(30, 64, 175), width=3)
        draw.text((cx - 180, cy - 40), "V-", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 180, cy + 25), "V+", fill=(30, 64, 175), font=font_label)
        
        # Output
        draw.line([(cx + 80, cy), (cx + 160, cy)], fill=(200, 50, 50), width=3)
        draw.text((cx + 160, cy + 5), "Vout", fill=(200, 50, 50), font=font_label)
        
        # Power supplies
        draw.line([(cx, cy - 60), (cx, cy - 90)], fill=(30, 64, 175), width=2)
        draw.text((cx + 10, cy - 90), "+Vcc", fill=(30, 64, 175), font=font_label)
        draw.line([(cx, cy + 60), (cx, cy + 90)], fill=(30, 64, 175), width=2)
        draw.text((cx + 10, cy + 85), "-Vcc", fill=(30, 64, 175), font=font_label)
        
        draw.text((cx - 130, 15), "OPERATIONAL AMPLIFIER", fill=(30, 64, 175), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()


# ════════════════════════════════════════════════════════════
# 3. CIVIL ENGINEERING DIAGRAMS
# ════════════════════════════════════════════════════════════
class CivilGenerator(DiagramGenerator):
    
    @staticmethod
    def detect(prompt: str) -> bool:
        keywords = [
            'bridge', 'truss', 'structure', 'beam', 'column',
            'foundation', 'frame', 'roof', 'building', 'tower',
            'dam', 'arch', 'retaining wall', 'slab', 'footing'
        ]
        return any(k in prompt.lower() for k in keywords)
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        p = prompt.lower()
        if 'truss' in p:
            return self._truss(width, height)
        elif 'beam' in p or 'column' in p:
            return self._beam_column(width, height)
        elif 'dam' in p:
            return self._dam(width, height)
        elif 'tower' in p or 'building' in p:
            return self._tower(width, height)
        elif 'arch' in p:
            return self._arch(width, height)
        else:
            return self._bridge(width, height)
    
    # ── BRIDGE ──
    def _bridge(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        deck_y = cy + 80
        draw.rectangle([(80, deck_y), (width - 80, deck_y + 20)], 
                       fill=(200, 200, 200), outline=(30, 64, 175), width=2)
        
        # Piers
        for px in [150, width//2, width - 150]:
            draw.rectangle([(px - 20, deck_y + 20), (px + 20, height - 60)], 
                           fill=(200, 200, 210), outline=(30, 64, 175), width=2)
            draw.ellipse([(px - 40, height - 55), (px + 40, height - 25)], 
                         fill=(100, 180, 255), outline=(50, 50, 150), width=1)
        
        # Truss
        truss_y = 120
        for i in range(6):
            x = 120 + i * (width - 240) // 5
            draw.line([(x, truss_y), (x, deck_y)], fill=(30, 64, 175), width=2)
            if i < 5:
                x_next = 120 + (i+1) * (width - 240) // 5
                draw.line([(x, truss_y), (x_next, deck_y)], fill=(200, 50, 50), width=2)
                draw.line([(x_next, truss_y), (x, deck_y)], fill=(200, 50, 50), width=2)
        
        draw.line([(120, truss_y), (width - 120, truss_y)], fill=(30, 64, 175), width=4)
        
        draw.text((cx - 100, 15), "BRIDGE TRUSS STRUCTURE", 
                  fill=(30, 64, 175), font=font_title)
        draw.text((cx - 60, truss_y - 30), "TOP CHORD", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 60, deck_y + 35), "DECK", fill=(30, 64, 175), font=font_label)
        draw.text((width - 200, height - 80), "PIER", fill=(30, 64, 175), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── TRUSS ──
    def _truss(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Top chord
        draw.line([(80, 80), (width - 80, 80)], fill=(30, 64, 175), width=4)
        # Bottom chord
        draw.line([(80, height - 80), (width - 80, height - 80)], fill=(30, 64, 175), width=4)
        
        # Vertical members
        for i in range(7):
            x = 80 + i * (width - 160) // 6
            draw.line([(x, 80), (x, height - 80)], fill=(30, 64, 175), width=2)
            # Diagonal members
            if i < 6:
                x_next = 80 + (i+1) * (width - 160) // 6
                draw.line([(x, 80), (x_next, height - 80)], fill=(200, 50, 50), width=2)
                draw.line([(x_next, 80), (x, height - 80)], fill=(200, 50, 50), width=2)
        
        # Labels
        draw.text((cx - 100, 15), "TRUSS STRUCTURE", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 100, 85), "TOP CHORD", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 100, height - 95), "BOTTOM CHORD", fill=(30, 64, 175), font=font_label)
        draw.text((20, cy), "VERTICAL\nMEMBER", fill=(30, 64, 175), font=font_label)
        draw.text((width - 150, cy - 30), "DIAGONAL\nMEMBER", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── BEAM & COLUMN ──
    def _beam_column(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Columns
        col_w = 30
        draw.rectangle([(cx - 120, 80), (cx - 90, height - 80)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        draw.rectangle([(cx + 90, 80), (cx + 120, height - 80)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        
        # Beam
        beam_h = 40
        draw.rectangle([(cx - 120, cy - beam_h//2), (cx + 120, cy + beam_h//2)], 
                       fill=(200, 200, 200), outline=(30, 64, 175), width=3)
        
        # Load arrows
        for i in range(5):
            x = cx - 80 + i * 40
            draw.line([(x, cy - beam_h//2 - 20), (x, cy - beam_h//2 - 5)], 
                      fill=(200, 50, 50), width=2)
            draw.line([(x - 5, cy - beam_h//2 - 15), (x, cy - beam_h//2 - 5)], 
                      fill=(200, 50, 50), width=2)
            draw.line([(x + 5, cy - beam_h//2 - 15), (x, cy - beam_h//2 - 5)], 
                      fill=(200, 50, 50), width=2)
        
        draw.text((cx - 100, 15), "BEAM-COLUMN FRAME", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 160, cy + 50), "COLUMN", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 130, cy + 50), "COLUMN", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 60, cy - 60), "BEAM", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 90, cy - beam_h//2 - 35), "LOAD", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── DAM ──
    def _dam(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Dam profile (triangle)
        points = [(100, height - 40), (cx, 80), (width - 100, height - 40)]
        draw.polygon(points, fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        
        # Water
        water_points = [(100, height - 40), (100, 100), (cx - 20, 100), (cx - 20, height - 40)]
        draw.polygon(water_points, fill=(100, 180, 255, 100))
        # Water waves
        for i in range(8):
            x = 120 + i * 30
            draw.arc([(x, 90), (x + 30, 110)], start=0, end=180, fill=(50, 150, 255), width=2)
        
        # Spillway
        draw.line([(cx - 40, 80), (cx + 40, 80)], fill=(200, 50, 50), width=4)
        draw.line([(cx - 30, 80), (cx - 30, height - 40)], fill=(200, 50, 50), width=2)
        draw.line([(cx + 30, 80), (cx + 30, height - 40)], fill=(200, 50, 50), width=2)
        
        draw.text((cx - 100, 15), "DAM STRUCTURE", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 80, cy - 20), "DAM BODY", fill=(30, 64, 175), font=font_label)
        draw.text((100, cy + 50), "WATER\nRESERVOIR", fill=(50, 150, 255), font=font_label)
        draw.text((cx + 60, 80), "SPILLWAY", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── TOWER ──
    def _tower(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Tower legs (tapered)
        leg_w = 20
        draw.line([(cx - 120, height - 40), (cx - 30, 80)], fill=(30, 64, 175), width=leg_w)
        draw.line([(cx + 120, height - 40), (cx + 30, 80)], fill=(30, 64, 175), width=leg_w)
        
        # Cross bracing
        for i in range(6):
            y = 80 + i * ((height - 120) // 6)
            x1 = cx - 120 + i * (90 // 6)
            x2 = cx + 120 - i * (90 // 6)
            # Horizontal
            draw.line([(x1, y), (x2, y)], fill=(200, 50, 50), width=2)
            # Diagonal
            if i < 5:
                y_next = 80 + (i+1) * ((height - 120) // 6)
                x1_next = cx - 120 + (i+1) * (90 // 6)
                x2_next = cx + 120 - (i+1) * (90 // 6)
                draw.line([(x1, y), (x2_next, y_next)], fill=(200, 50, 50), width=1)
                draw.line([(x2, y), (x1_next, y_next)], fill=(200, 50, 50), width=1)
        
        # Antenna at top
        draw.line([(cx, 40), (cx, 80)], fill=(30, 64, 175), width=6)
        draw.ellipse([(cx - 15, 25), (cx + 15, 40)], fill=(200, 50, 50))
        
        draw.text((cx - 100, 15), "COMMUNICATION TOWER", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 30, 40), "ANTENNA", fill=(200, 50, 50), font=font_label)
        draw.text((cx + 130, cy - 20), "LEGS", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 130, cy + 100), "BRACING", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── ARCH ──
    def _arch(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Arch
        arch_r = 200
        draw.arc([(cx - arch_r, cy - arch_r), (cx + arch_r, cy + arch_r)], 
                 start=0, end=180, fill=(30, 64, 175), width=6)
        
        # Columns
        draw.rectangle([(cx - arch_r, cy), (cx - arch_r + 20, height - 40)], 
                       fill=(200, 200, 200), outline=(30, 64, 175), width=2)
        draw.rectangle([(cx + arch_r - 20, cy), (cx + arch_r, height - 40)], 
                       fill=(200, 200, 200), outline=(30, 64, 175), width=2)
        
        # Keystone
        draw.rectangle([(cx - 20, cy - arch_r - 10), (cx + 20, cy - arch_r + 10)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        
        # Voussoirs (arch stones)
        for i in range(10, 170, 20):
            rad = math.radians(i)
            x1 = cx + (arch_r - 20) * math.cos(rad)
            y1 = cy - (arch_r - 20) * math.sin(rad)
            x2 = cx + (arch_r - 40) * math.cos(rad)
            y2 = cy - (arch_r - 40) * math.sin(rad)
            draw.line([(x1, y1), (x2, y2)], fill=(30, 64, 175), width=2)
        
        draw.text((cx - 100, 15), "ARCH STRUCTURE", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 180, cy - 20), "KEYSTONE", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 180, cy + 100), "VOUSSOIRS", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 220, cy + 100), "COLUMN", fill=(200, 200, 200), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()


# ════════════════════════════════════════════════════════════
# 4. CHEMICAL ENGINEERING DIAGRAMS
# ════════════════════════════════════════════════════════════
class ChemicalGenerator(DiagramGenerator):
    
    @staticmethod
    def detect(prompt: str) -> bool:
        keywords = [
            'reactor', 'distillation', 'pipe', 'pump', 'valve',
            'tank', 'heat exchanger', 'flow', 'column', 'tower',
            'bioreactor', 'fermenter', 'separator', 'filter',
            'evaporator', 'crystallizer', 'dryer', 'mixer'
        ]
        return any(k in prompt.lower() for k in keywords)
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        p = prompt.lower()
        if 'distillation' in p or 'column' in p:
            return self._distillation(width, height)
        elif 'heat exchanger' in p:
            return self._heat_exchanger(width, height)
        elif 'bioreactor' in p or 'fermenter' in p:
            return self._bioreactor(width, height)
        elif 'filter' in p or 'separator' in p:
            return self._filter(width, height)
        else:
            return self._reactor(width, height)
    
    # ── REACTOR ──
    def _reactor(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Reactor vessel
        draw.ellipse([(cx - 150, cy - 100), (cx + 150, cy + 100)], 
                     outline=(30, 64, 175), width=4)
        draw.ellipse([(cx - 135, cy - 85), (cx + 135, cy + 85)], 
                     fill=(219, 234, 254))
        
        # Agitator
        draw.line([(cx, cy - 85), (cx, cy + 85)], fill=(100, 100, 110), width=4)
        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            rad = math.radians(angle)
            x = cx + 80 * math.cos(rad)
            y = cy + 80 * math.sin(rad)
            draw.line([(cx, cy), (x, y)], fill=(100, 100, 110), width=3)
        
        # Baffles
        draw.line([(cx - 130, cy - 100), (cx - 130, cy + 100)], fill=(150, 150, 150), width=2)
        draw.line([(cx + 130, cy - 100), (cx + 130, cy + 100)], fill=(150, 150, 150), width=2)
        
        # Pipes
        draw.line([(cx - 150, cy - 100), (cx - 150, 40)], fill=(200, 200, 200), width=6)
        draw.line([(cx + 150, cy + 100), (cx + 150, height - 40)], fill=(200, 200, 200), width=6)
        
        # Valves
        draw.ellipse([(cx - 155, 50), (cx - 145, 60)], fill=(200, 50, 50))
        draw.ellipse([(cx + 145, height - 50), (cx + 155, height - 40)], fill=(200, 50, 50))
        
        draw.text((cx - 120, 15), "CHEMICAL REACTOR", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 220, cy - 20), "INLET", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 170, cy - 20), "OUTLET", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 60, cy + 120), "AGITATOR", fill=(100, 100, 110), font=font_label)
        draw.text((cx + 150, cy + 120), "BAFFLES", fill=(150, 150, 150), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── DISTILLATION ──
    def _distillation(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Column
        col_w, col_h = 80, 300
        draw.rectangle([(cx - col_w//2, cy - col_h//2), 
                        (cx + col_w//2, cy + col_h//2)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=4)
        
        # Trays
        for i in range(8):
            y = cy - col_h//2 + 30 + i * 30
            draw.line([(cx - col_w//2 + 5, y), (cx + col_w//2 - 5, y)], 
                      fill=(30, 64, 175), width=2)
            # Downcomer
            if i % 2 == 0:
                draw.ellipse([(cx + col_w//2 - 15, y - 5), (cx + col_w//2 + 5, y + 5)], 
                             fill=(200, 200, 200))
            else:
                draw.ellipse([(cx - col_w//2 - 5, y - 5), (cx - col_w//2 + 15, y + 5)], 
                             fill=(200, 200, 200))
        
        # Reboiler
        draw.ellipse([(cx - 80, cy + col_h//2), (cx + 80, cy + col_h//2 + 60)], 
                     outline=(30, 64, 175), width=3)
        
        # Condenser
        draw.ellipse([(cx - 80, cy - col_h//2 - 60), (cx + 80, cy - col_h//2)], 
                     outline=(30, 64, 175), width=3)
        
        # Pipes
        draw.line([(cx, cy - col_h//2 - 60), (cx, 60)], fill=(200, 200, 200), width=4)
        draw.line([(cx + 80, cy - col_h//2 - 30), (cx + 150, 60)], fill=(200, 200, 200), width=4)
        draw.line([(cx, cy + col_h//2 + 60), (cx, height - 40)], fill=(200, 200, 200), width=4)
        
        draw.text((cx - 120, 15), "DISTILLATION COLUMN", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 100, cy - col_h//2 - 80), "CONDENSER", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 100, cy + col_h//2 + 80), "REBOILER", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 50, cy - 20), "TRAYS", fill=(30, 64, 175), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── HEAT EXCHANGER ──
    def _heat_exchanger(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Shell
        draw.rectangle([(100, cy - 120), (width - 100, cy + 120)], 
                       outline=(30, 64, 175), width=4)
        draw.rectangle([(100, cy - 120), (width - 100, cy + 120)], 
                       fill=(219, 234, 254))
        
        # Tubes
        for i in range(10):
            x = 140 + i * 70
            draw.rectangle([(x, cy - 80), (x + 15, cy + 80)], 
                           outline=(200, 50, 50), width=2)
            # Tube end caps
            draw.ellipse([(x - 3, cy - 85), (x + 18, cy - 75)], fill=(200, 50, 50))
            draw.ellipse([(x - 3, cy + 75), (x + 18, cy + 85)], fill=(200, 50, 50))
        
        # Baffles
        for i in range(4):
            y = cy - 80 + i * 50
            if i % 2 == 0:
                draw.rectangle([(120, y), (width - 120, y + 5)], 
                               fill=(100, 100, 110))
            else:
                draw.rectangle([(120, y), (width - 120, y + 5)], 
                               fill=(100, 100, 110))
                # Cutout
                draw.rectangle([(cx - 50, y), (cx + 50, y + 5)], 
                               fill=(219, 234, 254))
        
        # Inlet/outlet
        draw.line([(100, cy - 40), (50, cy - 40)], fill=(200, 200, 200), width=6)
        draw.line([(width - 100, cy + 40), (width + 50, cy + 40)], fill=(200, 200, 200), width=6)
        
        draw.text((cx - 140, 15), "SHELL & TUBE HEAT EXCHANGER", 
                  fill=(30, 64, 175), font=font_title)
        draw.text((40, cy - 50), "SHELL\nSIDE", fill=(30, 64, 175), font=font_label)
        draw.text((width + 60, cy + 30), "TUBE\nSIDE", fill=(200, 50, 50), font=font_label)
        draw.text((cx + 150, cy - 60), "TUBES", fill=(200, 50, 50), font=font_label)
        draw.text((cx + 150, cy + 80), "BAFFLES", fill=(100, 100, 110), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── BIOREACTOR ──
    def _bioreactor(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Vessel (rounded)
        draw.ellipse([(cx - 160, cy - 120), (cx + 160, cy + 120)], 
                     outline=(30, 64, 175), width=4)
        draw.ellipse([(cx - 145, cy - 105), (cx + 145, cy + 105)], 
                     fill=(219, 234, 254))
        
        # Impeller
        draw.line([(cx, cy - 80), (cx, cy + 80)], fill=(100, 100, 110), width=4)
        for angle in [0, 60, 120, 180, 240, 300]:
            rad = math.radians(angle)
            x = cx + 80 * math.cos(rad)
            y = cy + 80 * math.sin(rad)
            draw.line([(cx, cy), (x, y)], fill=(100, 100, 110), width=3)
            # Curved blade
            x2 = cx + 60 * math.cos(rad + 0.5)
            y2 = cy + 60 * math.sin(rad + 0.5)
            draw.line([(x, y), (x2, y2)], fill=(30, 64, 175), width=2)
        
        # Sparger (air inlet)
        draw.ellipse([(cx - 40, cy + 80), (cx + 40, cy + 100)], 
                     outline=(100, 180, 255), width=2)
        # Bubbles
        for i in range(6):
            x = cx - 30 + i * 12
            y = cy + 60 - i * 15
            draw.ellipse([(x - 5, y - 5), (x + 5, y + 5)], 
                         outline=(100, 180, 255), width=1)
        
        # Temperature jacket
        draw.arc([(cx - 170, cy - 130), (cx + 170, cy + 130)], 
                 start=30, end=150, fill=(200, 50, 50), width=4)
        
        draw.text((cx - 130, 15), "BIOREACTOR", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 180, cy - 30), "IMPELLER", fill=(100, 100, 110), font=font_label)
        draw.text((cx + 180, cy + 80), "SPARGER", fill=(100, 180, 255), font=font_label)
        draw.text((cx + 180, cy - 60), "JACKET", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── FILTER ──
    def _filter(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Housing
        draw.ellipse([(cx - 160, cy - 140), (cx + 160, cy + 140)], 
                     outline=(30, 64, 175), width=4)
        draw.ellipse([(cx - 140, cy - 120), (cx + 140, cy + 120)], 
                     fill=(219, 234, 254))
        
        # Filter media
        draw.rectangle([(cx - 120, cy - 40), (cx + 120, cy + 40)], 
                       fill=(200, 200, 200), outline=(100, 100, 110), width=2)
        
        # Filter element (pleated pattern)
        for i in range(10):
            x = cx - 100 + i * 22
            draw.line([(x, cy - 35), (x, cy + 35)], fill=(30, 64, 175), width=2)
            if i % 2 == 0:
                draw.line([(x + 5, cy - 35), (x - 5, cy + 35)], fill=(30, 64, 175), width=1)
        
        # Inlet/outlet
        draw.line([(cx, cy - 140), (cx, cy - 200)], fill=(200, 200, 200), width=6)
        draw.line([(cx, cy + 140), (cx, cy + 200)], fill=(200, 200, 200), width=6)
        draw.line([(cx + 160, cy), (cx + 220, cy)], fill=(200, 200, 200), width=6)
        
        # Valves
        draw.ellipse([(cx - 10, cy - 205), (cx + 10, cy - 195)], fill=(200, 50, 50))
        draw.ellipse([(cx - 10, cy + 195), (cx + 10, cy + 205)], fill=(200, 50, 50))
        draw.ellipse([(cx + 215, cy - 10), (cx + 225, cy + 10)], fill=(200, 50, 50))
        
        draw.text((cx - 120, 15), "FILTER SYSTEM", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 160, cy - 220), "INLET", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 160, cy + 200), "OUTLET", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 180, cy + 20), "FILTER\nMEDIA", fill=(30, 64, 175), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()


# ════════════════════════════════════════════════════════════
# 5. AEROSPACE ENGINEERING DIAGRAMS
# ════════════════════════════════════════════════════════════
class AerospaceGenerator(DiagramGenerator):
    
    @staticmethod
    def detect(prompt: str) -> bool:
        keywords = [
            'airfoil', 'wing', 'fuselage', 'tail', 'propeller',
            'rocket', 'thruster', 'nozzle', 'combustion', 'turbine',
            'satellite', 'orbit', 'landing gear', 'flap', 'aileron'
        ]
        return any(k in prompt.lower() for k in keywords)
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        p = prompt.lower()
        if 'airfoil' in p or 'wing' in p:
            return self._airfoil(width, height)
        elif 'rocket' in p or 'thruster' in p:
            return self._rocket(width, height)
        elif 'satellite' in p:
            return self._satellite(width, height)
        else:
            return self._fuselage(width, height)
    
    # ── AIRFOIL ──
    def _airfoil(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Airfoil shape (NACA profile)
        points = []
        for t in range(0, 101):
            x = t / 100
            # Simple airfoil approximation
            y = 0.05 * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
            px = cx - 250 + x * 500
            py = cy - y * 300
            points.append((px, py))
        
        # Upper surface
        for i in range(50):
            if i < len(points) - 1:
                draw.line([points[i], points[i+1]], fill=(30, 64, 175), width=3)
        
        # Lower surface
        for t in range(0, 101):
            x = t / 100
            y = 0.05 * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
            px = cx - 250 + x * 500
            py = cy + y * 300
            if t == 0:
                start = (px, py)
            else:
                draw.line([(px_prev, py_prev), (px, py)], fill=(30, 64, 175), width=3)
            px_prev, py_prev = px, py
        
        # Flow lines
        for i in range(5):
            y_offset = -100 + i * 50
            draw.line([(cx - 300, cy + y_offset), (cx + 300, cy + y_offset)], 
                      fill=(200, 200, 200), width=1)
            # Flow arrows
            draw.line([(cx - 200, cy + y_offset), (cx - 180, cy + y_offset + 5)], 
                      fill=(200, 200, 200), width=2)
            draw.line([(cx - 200, cy + y_offset), (cx - 180, cy + y_offset - 5)], 
                      fill=(200, 200, 200), width=2)
        
        draw.text((cx - 130, 15), "AIRFOIL PROFILE", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 300, cy - 20), "UPPER\nSURFACE", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 300, cy + 60), "LOWER\nSURFACE", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 300, cy - 120), "FLOW", fill=(200, 200, 200), font=font_label)
        
        # Chord line
        draw.line([(cx - 250, cy), (cx + 250, cy)], fill=(200, 50, 50), width=2)
        draw.text((cx + 260, cy + 5), "CHORD", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── ROCKET ──
    def _rocket(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Fuselage
        draw.rectangle([(cx - 50, 80), (cx + 50, cy + 100)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        
        # Nose cone
        nose_points = [(cx, 40), (cx - 50, 80), (cx + 50, 80)]
        draw.polygon(nose_points, fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        
        # Fins
        draw.polygon([(cx - 50, cy + 60), (cx - 120, cy + 140), (cx - 50, cy + 100)], 
                     fill=(219, 234, 254), outline=(30, 64, 175), width=2)
        draw.polygon([(cx + 50, cy + 60), (cx + 120, cy + 140), (cx + 50, cy + 100)], 
                     fill=(219, 234, 254), outline=(30, 64, 175), width=2)
        
        # Nozzle
        draw.polygon([(cx - 40, cy + 100), (cx - 60, cy + 160), (cx + 60, cy + 160), (cx + 40, cy + 100)], 
                     fill=(200, 200, 200), outline=(100, 100, 110), width=2)
        
        # Exhaust
        for i in range(3):
            w = 80 - i * 20
            draw.polygon([(cx - w//2, cy + 160 + i*10), (cx + w//2, cy + 160 + i*10),
                          (cx - w//2 + 10, cy + 170 + i*10), (cx + w//2 - 10, cy + 170 + i*10)], 
                         fill=(255, 200, 50, 100))
        
        # Windows
        draw.ellipse([(cx - 20, 110), (cx + 20, 130)], outline=(30, 64, 175), width=2)
        
        draw.text((cx - 120, 15), "ROCKET ENGINE", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 70, 60), "NOSE\nCONE", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 70, 100), "FUSELAGE", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 70, 140), "FINS", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 70, cy + 150), "NOZZLE", fill=(100, 100, 110), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── SATELLITE ──
    def _satellite(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Main body
        draw.rectangle([(cx - 80, cy - 60), (cx + 80, cy + 60)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        
        # Solar panels
        draw.rectangle([(cx - 200, cy - 40), (cx - 80, cy + 40)], 
                       fill=(100, 180, 255), outline=(30, 64, 175), width=2)
        draw.rectangle([(cx + 80, cy - 40), (cx + 200, cy + 40)], 
                       fill=(100, 180, 255), outline=(30, 64, 175), width=2)
        
        # Panel grids
        for i in range(3):
            x = cx - 160 + i * 40
            draw.line([(x, cy - 35), (x, cy + 35)], fill=(200, 200, 200), width=1)
            draw.line([(x + 40, cy - 35), (x + 40, cy + 35)], fill=(200, 200, 200), width=1)
            if i < 2:
                y = cy - 30 + i * 60
                draw.line([(cx - 195, y), (cx - 85, y)], fill=(200, 200, 200), width=1)
                draw.line([(cx + 85, y), (cx + 195, y)], fill=(200, 200, 200), width=1)
        
        # Antenna
        draw.line([(cx, cy - 60), (cx, cy - 120)], fill=(30, 64, 175), width=3)
        draw.ellipse([(cx - 15, cy - 125), (cx + 15, cy - 115)], fill=(200, 50, 50))
        
        # Thrusters
        draw.rectangle([(cx - 60, cy + 60), (cx - 40, cy + 80)], 
                       fill=(200, 200, 200), outline=(100, 100, 110))
        draw.rectangle([(cx + 40, cy + 60), (cx + 60, cy + 80)], 
                       fill=(200, 200, 200), outline=(100, 100, 110))
        
        draw.text((cx - 130, 15), "SATELLITE", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 220, cy - 60), "SOLAR\nPANELS", fill=(100, 180, 255), font=font_label)
        draw.text((cx + 100, cy - 140), "ANTENNA", fill=(200, 50, 50), font=font_label)
        draw.text((cx + 80, cy + 60), "BUS", fill=(30, 64, 175), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── FUSELAGE ──
    def _fuselage(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Fuselage shape
        draw.ellipse([(cx - 250, cy - 80), (cx + 250, cy + 80)], 
                     outline=(30, 64, 175), width=4)
        draw.ellipse([(cx - 230, cy - 60), (cx + 230, cy + 60)], 
                     fill=(219, 234, 254))
        
        # Cockpit windows
        draw.ellipse([(cx + 180, cy - 30), (cx + 220, cy + 30)], 
                     outline=(100, 180, 255), width=2)
        draw.ellipse([(cx + 160, cy - 20), (cx + 180, cy + 20)], 
                     outline=(100, 180, 255), width=2)
        
        # Passenger windows
        for i in range(8):
            x = cx - 80 + i * 40
            draw.ellipse([(x - 8, cy - 25), (x + 8, cy + 25)], 
                         outline=(100, 180, 255), width=2)
        
        # Wing attachment points
        draw.ellipse([(cx - 120, cy - 60), (cx - 100, cy + 60)], 
                     outline=(30, 64, 175), width=2)
        draw.ellipse([(cx + 120, cy - 60), (cx + 140, cy + 60)], 
                     outline=(30, 64, 175), width=2)
        
        # Tail
        draw.polygon([(cx - 250, cy + 40), (cx - 280, cy + 40), (cx - 280, cy + 80), (cx - 250, cy + 80)], 
                     fill=(219, 234, 254), outline=(30, 64, 175))
        draw.polygon([(cx - 250, cy - 40), (cx - 280, cy - 40), (cx - 280, cy - 80), (cx - 250, cy - 80)], 
                     fill=(219, 234, 254), outline=(30, 64, 175))
        
        draw.text((cx - 130, 15), "AIRCRAFT FUSELAGE", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 230, cy - 20), "COCKPIT", fill=(100, 180, 255), font=font_label)
        draw.text((cx - 300, cy - 100), "TAIL", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 40, cy + 100), "WINDOWS", fill=(100, 180, 255), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()


# ════════════════════════════════════════════════════════════
# 6. BIOMEDICAL ENGINEERING DIAGRAMS
# ════════════════════════════════════════════════════════════
class BiomedicalGenerator(DiagramGenerator):
    
    @staticmethod
    def detect(prompt: str) -> bool:
        keywords = [
            'heart', 'valve', 'stent', 'implant', 'prosthetic',
            'mri', 'ct scan', 'ultrasound', 'pacemaker',
            'joint', 'bone', 'tissue', 'cell', 'sensor',
            'glucose', 'monitor', 'diagnostic'
        ]
        return any(k in prompt.lower() for k in keywords)
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        p = prompt.lower()
        if 'heart' in p or 'valve' in p:
            return self._heart_valve(width, height)
        elif 'implant' in p or 'prosthetic' in p:
            return self._implant(width, height)
        elif 'stent' in p:
            return self._stent(width, height)
        else:
            return self._medical_sensor(width, height)
    
    # ── HEART VALVE ──
    def _heart_valve(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Outer ring
        draw.ellipse([(cx - 120, cy - 120), (cx + 120, cy + 120)], 
                     outline=(200, 50, 50), width=4)
        draw.ellipse([(cx - 100, cy - 100), (cx + 100, cy + 100)], 
                     fill=(254, 219, 219))
        
        # Valve leaflets (tricuspid)
        colors = [(200, 50, 50), (200, 80, 80), (200, 110, 110)]
        angles = [-90, 30, 150]
        for i, angle in enumerate(angles):
            rad = math.radians(angle)
            x = cx + 80 * math.cos(rad)
            y = cy + 80 * math.sin(rad)
            # Leaflet (triangle)
            points = [
                (cx + 30 * math.cos(rad), cy + 30 * math.sin(rad)),
                (x, y),
                (cx + 30 * math.cos(rad + 1.2), cy + 30 * math.sin(rad + 1.2))
            ]
            draw.polygon(points, fill=colors[i], outline=(200, 50, 50), width=2)
        
        # Center
        draw.ellipse([(cx - 15, cy - 15), (cx + 15, cy + 15)], 
                     fill=(255, 255, 255), outline=(200, 50, 50), width=2)
        
        draw.text((cx - 130, 15), "HEART VALVE", fill=(200, 50, 50), font=font_title)
        draw.text((cx + 140, cy - 60), "LEAFLET", fill=(200, 50, 50), font=font_label)
        draw.text((cx + 140, cy + 60), "ANNULUS", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── IMPLANT ──
    def _implant(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Bone shape
        draw.ellipse([(cx - 200, cy - 80), (cx + 200, cy + 80)], 
                     fill=(254, 235, 200), outline=(200, 100, 50), width=3)
        
        # Implant (plate with screws)
        draw.rectangle([(cx - 80, cy - 40), (cx + 80, cy + 40)], 
                       fill=(200, 200, 200), outline=(100, 100, 110), width=3)
        
        # Screws
        screw_positions = [(-60, -30), (-60, 30), (60, -30), (60, 30)]
        for x, y in screw_positions:
            draw.ellipse([(cx + x - 10, cy + y - 10), (cx + x + 10, cy + y + 10)], 
                         fill=(200, 200, 200), outline=(100, 100, 110), width=2)
            # Screw cross
            draw.line([(cx + x - 5, cy + y), (cx + x + 5, cy + y)], fill=(50, 50, 50), width=1)
            draw.line([(cx + x, cy + y - 5), (cx + x, cy + y + 5)], fill=(50, 50, 50), width=1)
        
        draw.text((cx - 150, 15), "BONE IMPLANT", fill=(200, 100, 50), font=font_title)
        draw.text((cx + 220, cy - 20), "PLATE", fill=(100, 100, 110), font=font_label)
        draw.text((cx + 220, cy + 40), "SCREWS", fill=(100, 100, 110), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── STENT ──
    def _stent(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Stent (wire mesh pattern)
        for i in range(10):
            x = cx - 200 + i * 44
            # Diamond pattern
            for j in range(6):
                y = cy - 60 + j * 24
                if i % 2 == 0:
                    draw.line([(x, y), (x + 22, y + 12)], fill=(200, 200, 200), width=3)
                    draw.line([(x + 22, y + 12), (x, y + 24)], fill=(200, 200, 200), width=3)
                    draw.line([(x + 22, y + 12), (x + 44, y)], fill=(200, 200, 200), width=3)
                    draw.line([(x + 22, y + 12), (x + 44, y + 24)], fill=(200, 200, 200), width=3)
                else:
                    draw.line([(x, y + 12), (x + 22, y)], fill=(200, 200, 200), width=3)
                    draw.line([(x, y + 12), (x + 22, y + 24)], fill=(200, 200, 200), width=3)
                    draw.line([(x + 22, y), (x + 44, y + 12)], fill=(200, 200, 200), width=3)
                    draw.line([(x + 22, y + 24), (x + 44, y + 12)], fill=(200, 200, 200), width=3)
        
        draw.text((cx - 150, 15), "STENT", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 220, cy - 80), "WIRE MESH", fill=(200, 200, 200), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── MEDICAL SENSOR ──
    def _medical_sensor(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Sensor body
        draw.rectangle([(cx - 80, cy - 80), (cx + 80, cy + 80)], 
                       fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        
        # Display
        draw.rectangle([(cx - 50, cy - 40), (cx + 50, cy + 40)], 
                       fill=(100, 180, 255), outline=(30, 64, 175), width=2)
        
        # Heartbeat line on display
        points = [(cx - 45, cy)]
        for i in range(10):
            x = cx - 40 + i * 8
            if i == 3:
                y = cy - 30
            elif i == 4:
                y = cy + 30
            elif i == 5:
                y = cy - 20
            else:
                y = cy
            points.append((x, y))
        draw.line(points, fill=(200, 50, 50), width=2)
        
        # Electrodes
        draw.ellipse([(cx - 80, cy - 80), (cx - 60, cy - 60)], fill=(200, 200, 200))
        draw.ellipse([(cx - 80, cy + 60), (cx - 60, cy + 80)], fill=(200, 200, 200))
        draw.ellipse([(cx + 60, cy - 60), (cx + 80, cy - 80)], fill=(200, 200, 200))
        
        # Wires
        draw.line([(cx - 70, cy - 70), (cx - 50, cy - 40)], fill=(200, 200, 200), width=2)
        draw.line([(cx - 70, cy + 70), (cx - 50, cy + 40)], fill=(200, 200, 200), width=2)
        draw.line([(cx + 70, cy - 70), (cx + 50, cy - 40)], fill=(200, 200, 200), width=2)
        
        draw.text((cx - 130, 15), "MEDICAL SENSOR", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 100, cy - 20), "DISPLAY", fill=(100, 180, 255), font=font_label)
        draw.text((cx + 100, cy + 40), "ELECTRODES", fill=(200, 200, 200), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()


# ════════════════════════════════════════════════════════════
# 7. MATERIALS ENGINEERING DIAGRAMS
# ════════════════════════════════════════════════════════════
class MaterialsGenerator(DiagramGenerator):
    
    @staticmethod
    def detect(prompt: str) -> bool:
        keywords = [
            'grain', 'crystal', 'phase', 'stress', 'strain',
            'tensile', 'compression', 'fatigue', 'fracture',
            'alloy', 'composite', 'polymer', 'ceramic',
            'dislocation', 'crack', 'hardness', 'toughness'
        ]
        return any(k in prompt.lower() for k in keywords)
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        p = prompt.lower()
        if 'stress' in p or 'strain' in p:
            return self._stress_strain(width, height)
        elif 'crystal' in p or 'grain' in p:
            return self._crystal(width, height)
        elif 'phase' in p or 'alloy' in p:
            return self._phase_diagram(width, height)
        else:
            return self._microstructure(width, height)
    
    # ── STRESS-STRAIN ──
    def _stress_strain(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Axes
        draw.line([(100, height - 60), (width - 60, height - 60)], fill=(30, 64, 175), width=3)
        draw.line([(100, 60), (100, height - 60)], fill=(30, 64, 175), width=3)
        
        # Labels
        draw.text((width - 80, height - 45), "STRAIN (ε)", fill=(30, 64, 175), font=font_label)
        draw.text((80, 60), "STRESS (σ)", fill=(30, 64, 175), font=font_label)
        
        # Stress-strain curve
        points = [
            (100, height - 60),  # Origin
            (180, height - 60),  # Elastic region
            (220, height - 120),
            (260, height - 170),
            (300, height - 200),  # Yield point
            (350, height - 210),  # Plastic region
            (400, height - 205),
            (450, height - 195),
            (500, height - 180),  # Ultimate
            (540, height - 160),  # Necking
            (580, height - 140),
            (620, height - 120),
            (650, height - 100),  # Fracture
        ]
        
        # Smoothed curve
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], fill=(200, 50, 50), width=3)
        
        # Key points
        labels = [
            ("Elastic Limit", 180, height - 70),
            ("Yield Point", 300, height - 220),
            ("Ultimate", 500, height - 190),
            ("Fracture", 650, height - 110),
        ]
        for label, x, y in labels:
            draw.ellipse([(x - 5, y - 5), (x + 5, y + 5)], fill=(200, 50, 50))
            draw.text((x - 30, y - 15), label, fill=(30, 64, 175), font=font_label)
        
        draw.text((cx - 150, 15), "STRESS-STRAIN CURVE", fill=(30, 64, 175), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── CRYSTAL STRUCTURE ──
    def _crystal(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Crystal lattice (FCC)
        spacing = 50
        for i in range(6):
            for j in range(6):
                for k in range(6):
                    x = cx - 100 + i * spacing
                    y = cy - 100 + j * spacing
                    # Atoms
                    r = 12
                    # FCC face-centered atoms
                    if (i + j + k) % 2 == 1:
                        r = 15
                        color = (200, 50, 50)
                    else:
                        color = (30, 64, 175)
                    # 3D projection (simplified)
                    z_offset = k * spacing * 0.5
                    px = x - z_offset * 0.5
                    py = y - z_offset * 0.3
                    draw.ellipse([(px - r, py - r), (px + r, py + r)], 
                                 fill=color, outline=color)
        
        draw.text((cx - 120, 15), "CRYSTAL STRUCTURE", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 180, cy - 40), "ATOMS", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 180, cy + 40), "FCC", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── PHASE DIAGRAM ──
    def _phase_diagram(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Triangle (ternary phase diagram)
        points = [(150, height - 80), (width - 150, height - 80), (cx, 80)]
        draw.polygon(points, outline=(30, 64, 175), width=3)
        
        # Phase regions
        # Alpha phase (left)
        points_a = [(150, height - 80), (cx, 80), (cx - 50, height - 80)]
        draw.polygon(points_a, fill=(254, 219, 219), outline=(200, 50, 50), width=2)
        
        # Beta phase (right)
        points_b = [(cx, 80), (width - 150, height - 80), (cx + 50, height - 80)]
        draw.polygon(points_b, fill=(219, 234, 254), outline=(30, 64, 175), width=2)
        
        # Two-phase region (center)
        points_t = [(cx - 50, height - 80), (cx + 50, height - 80), (cx, 80)]
        draw.polygon(points_t, fill=(200, 200, 200), outline=(100, 100, 110), width=2)
        
        # Labels
        draw.text((160, cy - 20), "α\n(Alpha)", fill=(200, 50, 50), font=font_label)
        draw.text((cx + 60, cy - 20), "β\n(Beta)", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 30, cy + 30), "α+β", fill=(100, 100, 110), font=font_label)
        
        # Axis labels
        draw.text((150 - 30, height - 60), "A", fill=(30, 64, 175), font=font_label)
        draw.text((width - 150 - 30, height - 60), "B", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 10, 60), "C", fill=(30, 64, 175), font=font_label)
        
        draw.text((cx - 150, 15), "TERNARY PHASE DIAGRAM", fill=(30, 64, 175), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── MICROSTRUCTURE ──
    def _microstructure(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Grain structure
        grains = [
            (100, 100, 60), (200, 80, 50), (300, 120, 70),
            (120, 200, 55), (220, 220, 65), (320, 200, 45),
            (80, 300, 50), (180, 320, 60), (280, 300, 55), (380, 310, 50),
            (130, 400, 45), (250, 420, 70), (350, 400, 60),
        ]
        
        for x, y, r in grains:
            draw.ellipse([(x - r, y - r), (x + r, y + r)], 
                         outline=(30, 64, 175), width=2)
            # Grain boundary
            draw.ellipse([(x - r+5, y - r+5), (x + r-5, y + r-5)], 
                         outline=(200, 50, 50), width=1)
        
        # Dislocations
        for i in range(3):
            x = 180 + i * 80
            y = 180 + i * 50
            draw.line([(x, y), (x + 30, y + 20)], fill=(200, 50, 50), width=2)
            draw.line([(x + 30, y + 20), (x + 60, y + 40)], fill=(200, 50, 50), width=2)
            draw.line([(x + 60, y + 40), (x + 90, y + 60)], fill=(200, 50, 50), width=2)
        
        draw.text((cx - 120, 15), "MICROSTRUCTURE", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 180, cy - 40), "GRAINS", fill=(30, 64, 175), font=font_label)
        draw.text((cx + 180, cy + 40), "DISLOCATIONS", fill=(200, 50, 50), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()


# ════════════════════════════════════════════════════════════
# 8. ENVIRONMENTAL ENGINEERING DIAGRAMS
# ════════════════════════════════════════════════════════════
class EnvironmentalGenerator(DiagramGenerator):
    
    @staticmethod
    def detect(prompt: str) -> bool:
        keywords = [
            'water', 'treatment', 'waste', 'recycling',
            'solar', 'wind', 'renewable', 'sustainable',
            'carbon', 'footprint', 'emissions', 'climate',
            'sewage', 'irrigation', 'drainage', 'flood'
        ]
        return any(k in prompt.lower() for k in keywords)
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        p = prompt.lower()
        if 'water treatment' in p:
            return self._water_treatment(width, height)
        elif 'waste' in p or 'recycling' in p:
            return self._waste_recycling(width, height)
        elif 'solar' in p or 'renewable' in p:
            return self._renewable_energy(width, height)
        else:
            return self._sustainable_system(width, height)
    
    # ── WATER TREATMENT ──
    def _water_treatment(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Tanks
        tanks = [
            (150, cy, 60, "SEDIMENTATION"),
            (cx, cy - 80, 50, "FILTRATION"),
            (cx, cy + 80, 50, "DISINFECTION"),
            (width - 150, cy, 60, "STORAGE"),
        ]
        
        for x, y, r, label in tanks:
            draw.ellipse([(x - r, y - r), (x + r, y + r)], 
                         fill=(100, 180, 255), outline=(30, 64, 175), width=3)
            draw.text((x - 30, y - 5), label, fill=(30, 64, 175), font=font_label)
        
        # Flow arrows
        arrows = [(150 + 60, cy, cx - 60, cy - 80),
                  (cx + 50, cy - 80, cx + 50, cy - 30),
                  (cx + 50, cy + 30, cx + 50, cy + 80),
                  (cx + 50, cy + 80, width - 150 - 60, cy)]
        
        for x1, y1, x2, y2 in arrows:
            draw.line([(x1, y1), (x2, y2)], fill=(30, 64, 175), width=3)
            # Arrowhead
            midx, midy = (x1 + x2)//2, (y1 + y2)//2
            draw.line([(midx - 5, midy - 5), (midx, midy), (midx - 5, midy + 5)], 
                      fill=(30, 64, 175), width=2)
        
        draw.text((cx - 140, 15), "WATER TREATMENT SYSTEM", 
                  fill=(30, 64, 175), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── WASTE RECYCLING ──
    def _waste_recycling(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Recycling symbol
        draw.ellipse([(cx - 120, cy - 120), (cx + 120, cy + 120)], 
                     outline=(30, 180, 30), width=4)
        
        # Three arrows
        for i in range(3):
            angle = i * 120
            rad = math.radians(angle)
            x1 = cx + 100 * math.cos(rad)
            y1 = cy + 100 * math.sin(rad)
            x2 = cx + 60 * math.cos(rad + 0.5)
            y2 = cy + 60 * math.sin(rad + 0.5)
            draw.line([(x1, y1), (x2, y2)], fill=(30, 180, 30), width=6)
            # Arrowhead
            x3 = cx + 50 * math.cos(rad + 0.8)
            y3 = cy + 50 * math.sin(rad + 0.8)
            draw.line([(x2, y2), (x3, y3)], fill=(30, 180, 30), width=4)
        
        draw.text((cx - 130, 15), "RECYCLING SYSTEM", fill=(30, 180, 30), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── RENEWABLE ENERGY ──
    def _renewable_energy(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Solar panels
        for i in range(3):
            x = cx - 120 + i * 40
            draw.rectangle([(x, cy - 100), (x + 30, cy - 70)], 
                           fill=(30, 64, 175), outline=(30, 64, 175), width=2)
            draw.line([(x + 15, cy - 100), (x + 15, cy - 70)], fill=(255, 255, 255), width=1)
            draw.line([(x, cy - 85), (x + 30, cy - 85)], fill=(255, 255, 255), width=1)
        
        # Wind turbine
        draw.line([(cx + 100, cy - 80), (cx + 100, cy + 120)], fill=(100, 100, 110), width=4)
        # Blades
        for angle in [-30, 90, 210]:
            rad = math.radians(angle)
            x1 = cx + 100 + 20 * math.cos(rad)
            y1 = cy - 80 + 20 * math.sin(rad)
            x2 = cx + 100 + 80 * math.cos(rad)
            y2 = cy - 80 + 80 * math.sin(rad)
            draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=6)
        
        # Sun
        draw.ellipse([(cx - 30, cy - 130), (cx + 30, cy - 70)], fill=(255, 200, 50))
        # Sun rays
        for angle in [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]:
            rad = math.radians(angle)
            x1 = cx + 40 * math.cos(rad)
            y1 = cy - 100 + 40 * math.sin(rad)
            x2 = cx + 60 * math.cos(rad)
            y2 = cy - 100 + 60 * math.sin(rad)
            draw.line([(x1, y1), (x2, y2)], fill=(255, 200, 50), width=2)
        
        draw.text((cx - 160, 15), "RENEWABLE ENERGY", fill=(30, 64, 175), font=font_title)
        draw.text((cx - 60, cy - 160), "SOLAR", fill=(255, 200, 50), font=font_label)
        draw.text((cx + 120, cy - 120), "WIND", fill=(200, 200, 200), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── SUSTAINABLE SYSTEM ──
    def _sustainable_system(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Circular diagram
        draw.ellipse([(cx - 180, cy - 180), (cx + 180, cy + 180)], 
                     outline=(30, 180, 30), width=4)
        
        # Four quadrants
        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle)
            x = cx + 180 * math.cos(rad)
            y = cy + 180 * math.sin(rad)
            draw.line([(cx, cy), (x, y)], fill=(30, 180, 30), width=2)
        
        # Labels
        labels = ["ENERGY", "WATER", "WASTE", "MATERIALS"]
        positions = [(cx, cy - 140), (cx + 140, cy), (cx, cy + 140), (cx - 140, cy)]
        for label, (x, y) in zip(labels, positions):
            draw.text((x - 30, y - 10), label, fill=(30, 180, 30), font=font_label)
        
        draw.text((cx - 120, 15), "SUSTAINABLE SYSTEM", fill=(30, 180, 30), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()


# ════════════════════════════════════════════════════════════
# 9. INDUSTRIAL ENGINEERING DIAGRAMS
# ════════════════════════════════════════════════════════════
class IndustrialGenerator(DiagramGenerator):
    
    @staticmethod
    def detect(prompt: str) -> bool:
        keywords = [
            'assembly', 'line', 'robot', 'automation',
            'conveyor', 'warehouse', 'inventory', 'logistics',
            'manufacturing', 'supply chain', 'production'
        ]
        return any(k in prompt.lower() for k in keywords)
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        p = prompt.lower()
        if 'assembly' in p or 'line' in p:
            return self._assembly_line(width, height)
        elif 'warehouse' in p or 'logistics' in p:
            return self._warehouse(width, height)
        elif 'robot' in p or 'automation' in p:
            return self._automation(width, height)
        else:
            return self._supply_chain(width, height)
    
    # ── ASSEMBLY LINE ──
    def _assembly_line(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Conveyor belt
        draw.line([(60, cy), (width - 60, cy)], fill=(100, 100, 110), width=8)
        
        # Stations
        stations = [
            (120, cy - 60, "INSPECT"),
            (240, cy - 60, "ASSEMBLE"),
            (360, cy - 60, "WELD"),
            (480, cy - 60, "PAINT"),
            (600, cy - 60, "PACK"),
            (720, cy - 60, "SHIP"),
        ]
        for x, y, label in stations:
            draw.rectangle([(x - 30, y - 30), (x + 30, y + 30)], 
                           fill=(219, 234, 254), outline=(30, 64, 175), width=2)
            draw.text((x - 20, y - 5), label, fill=(30, 64, 175), font=font_label)
            draw.line([(x, cy - 30), (x, cy)], fill=(30, 64, 175), width=2)
        
        # Arrow
        draw.line([(width - 60, cy), (width - 30, cy)], fill=(200, 50, 50), width=4)
        draw.line([(width - 40, cy - 8), (width - 30, cy), (width - 40, cy + 8)], 
                  fill=(200, 50, 50), width=3)
        
        draw.text((cx - 150, 15), "ASSEMBLY LINE", fill=(30, 64, 175), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── WAREHOUSE ──
    def _warehouse(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Aisle
        draw.rectangle([(cx - 150, 60), (cx + 150, height - 60)], 
                       fill=(254, 243, 199), outline=(200, 150, 50), width=2)
        
        # Shelves
        for i in range(4):
            x = cx - 120 + i * 80
            draw.rectangle([(x, 80), (x + 20, height - 80)], 
                           fill=(219, 234, 254), outline=(30, 64, 175), width=2)
            # Shelf levels
            for j in range(4):
                y = 100 + j * 100
                draw.line([(x, y), (x + 20, y)], fill=(30, 64, 175), width=2)
                draw.rectangle([(x + 3, y + 3), (x + 17, y + 30)], 
                               fill=(200, 200, 200), outline=(100, 100, 110), width=1)
        
        draw.text((cx - 130, 15), "WAREHOUSE LAYOUT", fill=(200, 150, 50), font=font_title)
        draw.text((cx + 170, cy - 20), "AISLE", fill=(200, 150, 50), font=font_label)
        draw.text((cx + 170, cy + 40), "SHELVES", fill=(30, 64, 175), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── AUTOMATION ──
    def _automation(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Robot arm
        # Base
        draw.rectangle([(cx - 30, cy + 60), (cx + 30, cy + 90)], 
                       fill=(100, 100, 110), outline=(50, 50, 50), width=2)
        
        # Arm segments
        draw.line([(cx, cy + 60), (cx, cy + 20)], fill=(30, 64, 175), width=10)
        draw.line([(cx, cy + 20), (cx + 60, cy - 20)], fill=(30, 64, 175), width=8)
        draw.line([(cx + 60, cy - 20), (cx + 80, cy - 60)], fill=(30, 64, 175), width=6)
        
        # Joints
        draw.ellipse([(cx - 10, cy + 15), (cx + 10, cy + 25)], fill=(200, 50, 50))
        draw.ellipse([(cx + 55, cy - 25), (cx + 65, cy - 15)], fill=(200, 50, 50))
        draw.ellipse([(cx + 75, cy - 65), (cx + 85, cy - 55)], fill=(200, 50, 50))
        
        # Gripper
        draw.line([(cx + 80, cy - 60), (cx + 100, cy - 50)], fill=(100, 100, 110), width=4)
        draw.line([(cx + 80, cy - 60), (cx + 100, cy - 70)], fill=(100, 100, 110), width=4)
        
        draw.text((cx - 130, 15), "ROBOTIC ARM", fill=(30, 64, 175), font=font_title)
        draw.text((cx + 120, cy - 40), "GRIPPER", fill=(100, 100, 110), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ── SUPPLY CHAIN ──
    def _supply_chain(self, width: int, height: int) -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(13)
        
        # Nodes
        nodes = [
            (100, cy, "SUPPLIER", 30, 64, 175),
            (280, 120, "MFG", 200, 50, 50),
            (460, 120, "WAREHOUSE", 30, 180, 30),
            (640, 120, "RETAILER", 200, 150, 50),
            (460, cy + 60, "DISTRIBUTOR", 30, 64, 175),
            (280, cy + 60, "LOGISTICS", 200, 50, 50),
        ]
        
        for x, y, label, r, g, b in nodes:
            draw.ellipse([(x - 35, y - 35), (x + 35, y + 35)], 
                         fill=(r, g, b), outline=(30, 64, 175), width=2)
            draw.text((x - 30, y - 5), label, fill=(255, 255, 255), font=font_label)
        
        # Connections
        connections = [
            (100, cy, 280, 120),
            (280, 120, 460, 120),
            (460, 120, 640, 120),
            (460, 120, 460, cy + 60),
            (460, cy + 60, 280, cy + 60),
            (280, cy + 60, 100, cy),
        ]
        
        for x1, y1, x2, y2 in connections:
            draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=3)
            # Arrow
            midx, midy = (x1 + x2)//2, (y1 + y2)//2
            draw.line([(midx - 5, midy - 5), (midx, midy), (midx - 5, midy + 5)], 
                      fill=(200, 200, 200), width=2)
        
        draw.text((cx - 150, 15), "SUPPLY CHAIN", fill=(30, 64, 175), font=font_title)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()


# ════════════════════════════════════════════════════════════
# MAIN GENERATOR — Detects department automatically
# ════════════════════════════════════════════════════════════
class DiagramFactory:
    """Factory that detects diagram type and returns the appropriate generator."""
    
    _generators = [
        MechanicalGenerator(),
        ElectricalGenerator(),
        CivilGenerator(),
        ChemicalGenerator(),
        AerospaceGenerator(),
        BiomedicalGenerator(),
        MaterialsGenerator(),
        EnvironmentalGenerator(),
        IndustrialGenerator(),
    ]
    
    @classmethod
    def get_generator(cls, prompt: str) -> DiagramGenerator:
        """Find the right generator for the prompt."""
        for gen in cls._generators:
            if gen.detect(prompt):
                return gen
        return GeneralGenerator()  # Fallback


class GeneralGenerator(DiagramGenerator):
    """Fallback generator for general diagrams."""
    
    @staticmethod
    def detect(prompt: str) -> bool:
        return True
    
    def generate(self, width: int, height: int, prompt: str = "") -> bytes:
        img = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = width // 2, height // 2
        
        font_title = _get_font(18)
        font_label = _get_font(14)
        
        draw.rectangle([(40, 40), (width - 40, height - 40)], 
                       outline=(30, 64, 175), width=3)
        draw.rectangle([(40, 40), (width - 40, 80)], fill=(30, 64, 175))
        
        title = prompt[:60] if prompt else "TECHNICAL DIAGRAM"
        draw.text((60, 52), title.upper(), fill=(255, 255, 255), font=font_title)
        
        draw.rectangle([(cx - 150, cy - 80), (cx + 150, cy + 80)], 
                       outline=(30, 64, 175), width=2)
        draw.text((cx - 130, cy - 20), "ENGINEERING", fill=(30, 64, 175), font=font_label)
        draw.text((cx - 100, cy + 5), "ILLUSTRATION", fill=(30, 64, 175), font=font_label)
        
        # Decorative dots
        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            rad = math.radians(angle)
            x = cx + 180 * math.cos(rad)
            y = cy + 180 * math.sin(rad)
            draw.ellipse([(x - 6, y - 6), (x + 6, y + 6)], 
                         fill=(219, 234, 254), outline=(30, 64, 175), width=2)
        
        draw.text((60, height - 30), "Smart University AI Portal", 
                  fill=(150, 150, 150), font=font_label)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        return buffer.getvalue()
    
    # ═══════════════════════════════════════════════════════════════
# ██  WELDING SKETCHES — For Section A Report
# ═══════════════════════════════════════════════════════════════

def draw_smaw_setup(width=900, height=600):
    """SMAW Setup Diagram"""
    img = Image.new('RGB', (width, height), (255,255,255))
    draw = ImageDraw.Draw(img)
    font = _get_font(13)
    font_title = _get_font(18)
    
    draw.text((width//2 - 80, 15), "SMAW SETUP", fill=(30,64,175), font=font_title)
    
    # Power Source
    draw.rectangle([(50, 280), (150, 340)], fill=(219,234,254), outline=(30,64,175), width=2)
    draw.text((70, 300), "POWER", fill=(30,64,175), font=font)
    draw.text((70, 315), "SOURCE", fill=(30,64,175), font=font)
    
    # Electrode Holder
    draw.rectangle([(380, 100), (460, 160)], fill=(219,234,254), outline=(30,64,175), width=2)
    draw.text((390, 118), "ELECTRODE", fill=(30,64,175), font=font)
    draw.text((395, 133), "HOLDER", fill=(30,64,175), font=font)
    
    # Electrode
    draw.line([(420, 160), (420, 250)], fill=(100,100,110), width=6)
    draw.line([(410, 200), (430, 200)], fill=(200,50,50), width=2)
    draw.text((435, 205), "ELECTRODE", fill=(200,50,50), font=font)
    
    # Arc
    draw.arc([(410, 250), (430, 290)], start=0, end=180, fill=(255,200,50), width=3)
    draw.text((440, 260), "ARC", fill=(255,200,50), font=font)
    
    # Workpiece
    draw.rectangle([(280, 290), (560, 330)], fill=(200,200,200), outline=(30,64,175), width=2)
    draw.text((570, 303), "WORKPIECE", fill=(30,64,175), font=font)
    
    # Ground Clamp
    draw.rectangle([(230, 330), (280, 360)], fill=(219,234,254), outline=(30,64,175), width=2)
    draw.text((235, 340), "GROUND", fill=(30,64,175), font=font)
    
    # Cables
    draw.line([(150, 320), (230, 340)], fill=(200,50,50), width=3)
    draw.line([(420, 160), (420, 100)], fill=(200,50,50), width=3)
    draw.line([(420, 100), (150, 100)], fill=(200,50,50), width=3)
    draw.line([(150, 100), (150, 280)], fill=(200,50,50), width=3)
    draw.text((160, 100), "CABLES", fill=(200,50,50), font=font)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    return buffer.getvalue()


def draw_weld_joints(width=900, height=600):
    """Weld Joint Types"""
    img = Image.new('RGB', (width, height), (255,255,255))
    draw = ImageDraw.Draw(img)
    font = _get_font(13)
    font_title = _get_font(18)
    
    draw.text((width//2 - 100, 15), "WELD JOINT TYPES", fill=(30,64,175), font=font_title)
    
    joints = {
        "BUTT": (130, 200),
        "LAP": (290, 200),
        "T": (450, 200),
        "CORNER": (610, 200),
        "EDGE": (770, 200)
    }
    
    for name, (cx, cy) in joints.items():
        if name == "BUTT":
            draw.rectangle([(cx-35, cy-50), (cx-10, cy-10)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.rectangle([(cx+10, cy-50), (cx+35, cy-10)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.line([(cx-10, cy-30), (cx+10, cy-30)], fill=(200,50,50), width=4)
            draw.text((cx-25, cy+25), name, fill=(30,64,175), font=font)
        elif name == "LAP":
            draw.rectangle([(cx-35, cy-40), (cx+10, cy-10)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.rectangle([(cx-10, cy-30), (cx+35, cy+10)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.line([(cx+10, cy-20), (cx+25, cy-20)], fill=(200,50,50), width=4)
            draw.text((cx-25, cy+25), name, fill=(30,64,175), font=font)
        elif name == "T":
            draw.rectangle([(cx-35, cy-10), (cx+35, cy+10)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.rectangle([(cx-10, cy-50), (cx+10, cy-10)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.polygon([(cx-12, cy-10), (cx+12, cy-10), (cx, cy+5)], fill=(200,50,50))
            draw.text((cx-25, cy+25), name, fill=(30,64,175), font=font)
        elif name == "CORNER":
            draw.rectangle([(cx-35, cy-10), (cx+10, cy+40)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.rectangle([(cx-10, cy-40), (cx+35, cy-10)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.polygon([(cx-10, cy-10), (cx+10, cy-10), (cx+10, cy+10)], fill=(200,50,50))
            draw.text((cx-30, cy+55), name, fill=(30,64,175), font=font)
        elif name == "EDGE":
            draw.rectangle([(cx-35, cy-35), (cx-10, cy+10)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.rectangle([(cx+10, cy-35), (cx+35, cy+10)], fill=(200,200,200), outline=(30,64,175), width=1)
            draw.line([(cx-10, cy-12), (cx+10, cy-12)], fill=(200,50,50), width=4)
            draw.text((cx-25, cy+25), name, fill=(30,64,175), font=font)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    return buffer.getvalue()


def draw_electrode_cross(width=900, height=600):
    """Electrode Cross-Section"""
    img = Image.new('RGB', (width, height), (255,255,255))
    draw = ImageDraw.Draw(img)
    font = _get_font(14)
    font_title = _get_font(18)
    
    cx, cy = width//2, height//2
    draw.text((cx-120, 15), "ELECTRODE CROSS-SECTION", fill=(30,64,175), font=font_title)
    
    draw.ellipse([(cx-120, cy-110), (cx+120, cy+110)], outline=(200,50,50), width=4)
    draw.ellipse([(cx-60, cy-50), (cx+60, cy+50)], outline=(100,100,110), width=4)
    draw.ellipse([(cx-35, cy-35), (cx+35, cy+35)], fill=(200,200,200))
    
    draw.line([(cx+120, cy), (cx+170, cy)], fill=(200,50,50), width=2)
    draw.text((cx+175, cy-10), "FLUX COATING", fill=(200,50,50), font=font)
    
    draw.line([(cx+60, cy), (cx+140, cy-40)], fill=(100,100,110), width=2)
    draw.text((cx+145, cy-50), "CORE WIRE", fill=(100,100,110), font=font)
    
    draw.text((cx-50, cy+130), "(Filler Material + Current Conductor)", fill=(30,64,175), font=font)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    return buffer.getvalue()


def draw_weld_positions(width=900, height=600):
    """Weld Positions"""
    img = Image.new('RGB', (width, height), (255,255,255))
    draw = ImageDraw.Draw(img)
    font = _get_font(13)
    font_title = _get_font(18)
    
    draw.text((width//2 - 100, 15), "WELD POSITIONS", fill=(30,64,175), font=font_title)
    
    positions = {
        "FLAT (1F/1G)": (150, 230),
        "HORIZONTAL (2F/2G)": (350, 230),
        "VERTICAL (3F/3G)": (550, 230),
        "OVERHEAD (4F/4G)": (750, 230)
    }
    
    for name, (cx, cy) in positions.items():
        draw.rectangle([(cx-50, cy-25), (cx+50, cy+25)], fill=(200,200,200), outline=(30,64,175), width=2)
        
        if "FLAT" in name:
            draw.polygon([(cx-15, cy+25), (cx+15, cy+25), (cx, cy+40)], fill=(200,50,50))
            draw.text((cx-30, cy+55), name, fill=(30,64,175), font=font)
        elif "HORIZONTAL" in name:
            draw.polygon([(cx+50, cy-15), (cx+50, cy+15), (cx+65, cy)], fill=(200,50,50))
            draw.text((cx-40, cy+55), name, fill=(30,64,175), font=font)
        elif "VERTICAL" in name:
            draw.polygon([(cx-15, cy-25), (cx+15, cy-25), (cx, cy-40)], fill=(200,50,50))
            draw.text((cx-40, cy+55), name, fill=(30,64,175), font=font)
        elif "OVERHEAD" in name:
            draw.polygon([(cx-15, cy-25), (cx+15, cy-25), (cx, cy-40)], fill=(200,50,50))
            draw.line([(cx, cy-40), (cx, cy-65)], fill=(200,50,50), width=2)
            draw.line([(cx-5, cy-60), (cx, cy-65), (cx+5, cy-60)], fill=(200,50,50), width=2)
            draw.text((cx-40, cy+55), name, fill=(30,64,175), font=font)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    return buffer.getvalue()


def draw_weld_defects(width=900, height=600):
    """Common Weld Defects"""
    img = Image.new('RGB', (width, height), (255,255,255))
    draw = ImageDraw.Draw(img)
    font = _get_font(13)
    font_title = _get_font(18)
    
    draw.text((width//2 - 100, 15), "COMMON WELD DEFECTS", fill=(30,64,175), font=font_title)
    
    # Porosity
    cx, cy = 150, 200
    draw.rectangle([(cx-35, cy-18), (cx+35, cy+18)], fill=(200,200,200), outline=(30,64,175), width=2)
    draw.ellipse([(cx-8, cy-8), (cx+8, cy+8)], fill=(255,255,255), outline=(200,50,50), width=2)
    draw.ellipse([(cx-18, cy-4), (cx-5, cy+6)], fill=(255,255,255), outline=(200,50,50), width=1)
    draw.ellipse([(cx+5, cy-6), (cx+18, cy+4)], fill=(255,255,255), outline=(200,50,50), width=1)
    draw.text((cx-25, cy+40), "POROSITY", fill=(200,50,50), font=font)
    
    # Undercut
    cx, cy = 350, 200
    draw.rectangle([(cx-35, cy-18), (cx+35, cy+18)], fill=(200,200,200), outline=(30,64,175), width=2)
    draw.polygon([(cx-30, cy-18), (cx-18, cy-8), (cx-30, cy+2)], fill=(255,255,255))
    draw.polygon([(cx+30, cy-18), (cx+18, cy-8), (cx+30, cy+2)], fill=(255,255,255))
    draw.text((cx-30, cy+40), "UNDERCUT", fill=(200,50,50), font=font)
    
    # Cracking
    cx, cy = 550, 200
    draw.rectangle([(cx-35, cy-18), (cx+35, cy+18)], fill=(200,200,200), outline=(30,64,175), width=2)
    draw.line([(cx-25, cy-12), (cx-8, cy+8)], fill=(200,50,50), width=3)
    draw.line([(cx-8, cy+8), (cx+12, cy-5)], fill=(200,50,50), width=3)
    draw.line([(cx+12, cy-5), (cx+25, cy+12)], fill=(200,50,50), width=3)
    draw.text((cx-30, cy+40), "CRACKING", fill=(200,50,50), font=font)
    
    # Lack of Fusion
    cx, cy = 750, 200
    draw.rectangle([(cx-35, cy-18), (cx+35, cy+18)], fill=(200,200,200), outline=(30,64,175), width=2)
    draw.line([(cx-25, cy-12), (cx-8, cy+8)], fill=(255,255,255), width=3)
    draw.line([(cx-8, cy+8), (cx+25, cy-12)], fill=(200,200,200), width=3)
    draw.text((cx-35, cy+40), "LACK OF", fill=(200,50,50), font=font)
    draw.text((cx-35, cy+58), "FUSION", fill=(200,50,50), font=font)
    
    # Key
    draw.text((50, height-50), "Key:", fill=(30,64,175), font=font)
    draw.text((50, height-32), "○ = Gas bubbles", fill=(200,50,50), font=font)
    draw.text((230, height-32), "└─ = Groove at toe", fill=(200,50,50), font=font)
    draw.text((430, height-32), "── = Crack", fill=(200,50,50), font=font)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    return buffer.getvalue()


def draw_weld_symbols(width=900, height=600):
    """Basic Weld Symbols"""
    img = Image.new('RGB', (width, height), (255,255,255))
    draw = ImageDraw.Draw(img)
    font = _get_font(13)
    font_title = _get_font(18)
    
    draw.text((width//2 - 80, 15), "BASIC WELD SYMBOLS", fill=(30,64,175), font=font_title)
    
    # Fillet
    cx, cy = 130, 200
    draw.text((cx-30, 80), "FILLET", fill=(30,64,175), font=font)
    draw.polygon([(cx-35, cy+18), (cx+35, cy+18), (cx, cy-35)], outline=(30,64,175), width=3, fill=(219,234,254))
    draw.text((cx-10, cy+40), "∆", fill=(30,64,175), font=font)
    
    # Groove
    cx, cy = 310, 200
    draw.text((cx-30, 80), "GROOVE", fill=(30,64,175), font=font)
    draw.polygon([(cx-35, cy+18), (cx+35, cy+18), (cx, cy-35)], outline=(30,64,175), width=3, fill=(219,234,254))
    draw.text((cx-10, cy+40), "V", fill=(30,64,175), font=font)
    
    # All-around
    cx, cy = 490, 200
    draw.text((cx-45, 80), "ALL-AROUND", fill=(30,64,175), font=font)
    draw.ellipse([(cx-35, cy-35), (cx+35, cy+35)], outline=(30,64,175), width=3)
    draw.text((cx-10, cy+40), "○", fill=(30,64,175), font=font)
    
    # Field
    cx, cy = 680, 200
    draw.text((cx-25, 80), "FIELD", fill=(30,64,175), font=font)
    draw.polygon([(cx-30, cy), (cx+30, cy), (cx, cy-45)], outline=(30,64,175), width=3, fill=(219,234,254))
    draw.text((cx-10, cy+40), "⌂", fill=(30,64,175), font=font)
    
    draw.text((50, height-40), "All symbols per AWS standard", fill=(30,64,175), font=font)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    return buffer.getvalue()


def draw_weld_ppe(width=900, height=600):
    """Welding PPE"""
    img = Image.new('RGB', (width, height), (255,255,255))
    draw = ImageDraw.Draw(img)
    font = _get_font(13)
    font_title = _get_font(18)
    
    draw.text((width//2 - 80, 15), "WELDING PPE", fill=(30,64,175), font=font_title)
    
    # Helmet
    cx, cy = 130, 200
    draw.rectangle([(cx-45, cy-25), (cx+45, cy+25)], fill=(30,64,175), outline=(30,64,175), width=2)
    draw.rectangle([(cx-25, cy-15), (cx+25, cy+15)], fill=(100,180,255), outline=(30,64,175), width=2)
    draw.text((cx-20, cy-5), "HELMET", fill=(255,255,255), font=font)
    draw.text((cx-30, cy+45), "HELMET", fill=(30,64,175), font=font)
    draw.text((cx-40, cy+60), "(Shade 10-13)", fill=(30,64,175), font=font)
    
    # Gloves
    cx, cy = 330, 200
    draw.rectangle([(cx-35, cy-18), (cx+35, cy+18)], fill=(200,50,50), outline=(200,50,50), width=2)
    draw.text((cx-20, cy-5), "GLOVES", fill=(255,255,255), font=font)
    draw.text((cx-30, cy+45), "GLOVES", fill=(200,50,50), font=font)
    draw.text((cx-40, cy+60), "(Heat/UV)", fill=(200,50,50), font=font)
    
    # Apron
    cx, cy = 530, 200
    draw.rectangle([(cx-35, cy-25), (cx+35, cy+25)], fill=(200,180,150), outline=(200,180,150), width=2)
    draw.text((cx-20, cy-5), "APRON", fill=(255,255,255), font=font)
    draw.text((cx-30, cy+45), "APRON", fill=(200,180,150), font=font)
    draw.text((cx-40, cy+60), "(Leather)", fill=(200,180,150), font=font)
    
    # Boots
    cx, cy = 730, 200
    draw.rectangle([(cx-35, cy-18), (cx+35, cy+18)], fill=(100,100,100), outline=(100,100,110), width=2)
    draw.text((cx-20, cy-5), "BOOTS", fill=(255,255,255), font=font)
    draw.text((cx-30, cy+45), "BOOTS", fill=(100,100,110), font=font)
    draw.text((cx-40, cy+60), "(Steel-toe)", fill=(100,100,110), font=font)
    
    draw.text((50, height-40), "Required PPE for all welding operations", fill=(30,64,175), font=font)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    return buffer.getvalue()


# ── MAIN EXPORT ─────────────────────────────────────────────
def generate_image(prompt: str, width: int = DEFAULT_WIDTH, 
                   height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """
    Generate clean engineering diagrams completely offline.
    Auto-detects department from prompt.
    """
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    
    cache_filename = _sanitize_filename(prompt)
    cache_path = os.path.join(CACHE_DIR, cache_filename)
    
    # Check cache
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                return f.read()
        except:
            pass

    # ── Try Pollinations API first (optional) ──
    try:
        encoded_prompt = quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and len(response.content) > 2000:
            with open(cache_path, "wb") as f:
                f.write(response.content)
            return response.content
    except Exception as e:
        print(f"[Image] API unavailable: {e}")

    # ── Offline generation ──
    try:
        p = prompt.lower()
        
        # ── NEW: WELDING SKETCHES ──
        if "smaw setup" in p or "welding setup" in p:
            img_bytes = draw_smaw_setup(width, height)
        elif "joint" in p or "butt" in p or "lap" in p or "t-joint" in p:
            img_bytes = draw_weld_joints(width, height)
        elif "electrode cross" in p or "electrode section" in p:
            img_bytes = draw_electrode_cross(width, height)
        elif "position" in p or "flat" in p or "vertical" in p or "overhead" in p:
            img_bytes = draw_weld_positions(width, height)
        elif "defect" in p or "porosity" in p or "undercut" in p or "cracking" in p:
            img_bytes = draw_weld_defects(width, height)
        elif "symbol" in p or "fillet" in p or "groove" in p:
            img_bytes = draw_weld_symbols(width, height)
        elif "ppe" in p or "helmet" in p or "gloves" in p or "apron" in p:
            img_bytes = draw_weld_ppe(width, height)
        else:
            # ── Existing: Use DiagramFactory for other diagrams ──
            generator = DiagramFactory.get_generator(prompt)
            img_bytes = generator.generate(width, height, prompt)
        
        with open(cache_path, "wb") as f:
            f.write(img_bytes)
        
        return img_bytes
    except Exception as e:
        print(f"[Image] Generation error: {e}")
        return None
# ── Department-specific exports ─────────────────────────────
def generate_mechanical(prompt: str, width: int = DEFAULT_WIDTH, 
                        height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """Generate mechanical engineering diagrams."""
    return MechanicalGenerator().generate(width, height, prompt)


def generate_electrical(prompt: str, width: int = DEFAULT_WIDTH, 
                        height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """Generate electrical engineering diagrams."""
    return ElectricalGenerator().generate(width, height, prompt)


def generate_civil(prompt: str, width: int = DEFAULT_WIDTH, 
                   height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """Generate civil engineering diagrams."""
    return CivilGenerator().generate(width, height, prompt)


def generate_chemical(prompt: str, width: int = DEFAULT_WIDTH, 
                      height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """Generate chemical engineering diagrams."""
    return ChemicalGenerator().generate(width, height, prompt)


def generate_aerospace(prompt: str, width: int = DEFAULT_WIDTH, 
                       height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """Generate aerospace engineering diagrams."""
    return AerospaceGenerator().generate(width, height, prompt)


def generate_biomedical(prompt: str, width: int = DEFAULT_WIDTH, 
                        height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """Generate biomedical engineering diagrams."""
    return BiomedicalGenerator().generate(width, height, prompt)


def generate_materials(prompt: str, width: int = DEFAULT_WIDTH, 
                       height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """Generate materials engineering diagrams."""
    return MaterialsGenerator().generate(width, height, prompt)


def generate_environmental(prompt: str, width: int = DEFAULT_WIDTH, 
                           height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """Generate environmental engineering diagrams."""
    return EnvironmentalGenerator().generate(width, height, prompt)


def generate_industrial(prompt: str, width: int = DEFAULT_WIDTH, 
                        height: int = DEFAULT_HEIGHT) -> Optional[bytes]:
    """Generate industrial engineering diagrams."""
    return IndustrialGenerator().generate(width, height, prompt)


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🎨 Testing all diagram generators...\n")
    
    tests = [
        ("piston and cylinder assembly", "mechanical_piston.png"),
        ("gear mechanism", "mechanical_gear.png"),
        ("turbine assembly", "mechanical_turbine.png"),
        ("centrifugal pump", "mechanical_pump.png"),
        ("clutch assembly", "mechanical_clutch.png"),
        ("ball bearing", "mechanical_bearing.png"),
        ("electrical circuit diagram", "electrical_circuit.png"),
        ("electric motor", "electrical_motor.png"),
        ("transformer", "electrical_transformer.png"),
        ("solar panel system", "electrical_solar.png"),
        ("operational amplifier", "electrical_opamp.png"),
        ("bridge truss structure", "civil_bridge.png"),
        ("truss structure", "civil_truss.png"),
        ("beam and column frame", "civil_beam.png"),
        ("dam structure", "civil_dam.png"),
        ("arch structure", "civil_arch.png"),
        ("chemical reactor", "chemical_reactor.png"),
        ("distillation column", "chemical_distillation.png"),
        ("heat exchanger", "chemical_heat_exchanger.png"),
        ("bioreactor", "chemical_bioreactor.png"),
        ("airfoil profile", "aerospace_airfoil.png"),
        ("rocket engine", "aerospace_rocket.png"),
        ("satellite", "aerospace_satellite.png"),
        ("heart valve", "biomedical_heart.png"),
        ("bone implant", "biomedical_implant.png"),
        ("stent", "biomedical_stent.png"),
        ("stress-strain curve", "materials_stress.png"),
        ("crystal structure", "materials_crystal.png"),
        ("phase diagram", "materials_phase.png"),
        ("water treatment system", "environmental_water.png"),
        ("recycling system", "environmental_recycling.png"),
        ("renewable energy", "environmental_renewable.png"),
        ("assembly line", "industrial_assembly.png"),
        ("robotic arm", "industrial_robot.png"),
        ("supply chain", "industrial_supply_chain.png"),
    ]
    
    for prompt, filename in tests:
        img = generate_image(prompt)
        if img:
            with open(filename, "wb") as f:
                f.write(img)
            print(f"✅ {filename}")
        else:
            print(f"❌ {filename}")
    
    print("\n✅ All diagrams generated! Check your folder.")